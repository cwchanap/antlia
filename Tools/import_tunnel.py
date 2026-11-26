"""TD centreline KMZ -> metre-scale Cross-Harbour extension. Regeneration needs Shapely.

Run the reviewed WGS84 archive with --whole-wong-tai-sin-district for the current map.
Use the matching district or --hk1980 flags with corresponding earlier snapshots.
The source supplies XY, travel direction and relative road levels; metric elevations are authored.
"""
import datetime
import hashlib
import heapq
import json
import math
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from shapely import constrained_delaunay_triangles
from shapely.geometry import LineString, Point, Polygon, box, shape, mapping
from shapely.ops import nearest_points, substring, transform as transform_geometry, unary_union
from import_map import ROOT, NS, SOURCE, ORIGIN, local
from export_runtime_harbour import encode as encode_runtime_harbour

# Explicit source routes make the chosen connections reviewable, including the return loop.
SOUTH = ['ID_012620','ID_04550','ID_021392','ID_034845','ID_034844',
         'ID_028388','ID_024203','ID_024204','ID_010882','ID_010888','ID_02420']
ISLAND = ['ID_012023','ID_020805','ID_020804','ID_020806','ID_020846','ID_018216',
          'ID_026889','ID_025514','ID_028222','ID_028228','ID_028232','ID_028223',
          'ID_024646','ID_024647','ID_024648','ID_015864','ID_015762','ID_015777',
          'ID_02171','ID_04970','ID_035497','ID_02104']
NORTH = ['ID_014428','ID_019595','ID_019594','ID_06075','ID_024201','ID_024200',
         'ID_034781','ID_035476','ID_034422','ID_021368','ID_034845','ID_034844',
         'ID_011064','ID_033974','ID_013342','ID_010929','ID_010930','ID_010931']
TUBES = [('Southbound', ['ID_010882','ID_010888']), ('Northbound',['ID_019594','ID_06075'])]
RAMPS = {'Southbound':['ID_024204','ID_010882','ID_010888'],
         'Northbound':['ID_019594','ID_06075','ID_024201']}

ISLAND_BOUNDS = (-2400,350,2050,2100)
KOWLOON_BOUNDS = (-900,-3350,650,-1191.124)
WEST_BOUNDS = (-2700,-4800,650,50)
NORTHWEST_BOUNDS = (-4600,-6000,650,-3900)
KWAI_CHUNG_BOUNDS = (-6500,-8500,-3100,-4400)
TSUEN_WAN_BOUNDS = (-8500,-11000,-3900,-6900)
WEST_COAST_BOUNDS = (-13800,-11200,-6400,-6900)
EAST_KOWLOON_BOUNDS = (550,-6400,4900,-100)
KOWLOON_CITY_NORTH_FILL_BOUNDS = (250,-6075,550,-6000)
WONG_TAI_SIN_DISTRICT_BOUNDS = (550,-7110,5380,-100)
# Required unnamed ground-level connections, ordered in the government's one-way direction.
# Other unnamed access links remain excluded until their access and clearance are assessed.
EAST_ROUNDABOUTS = [('Hereford / Renfrew',['TD_107211','TD_107576','TD_107598','TD_107575','TD_107601']),
                   ('Ho Tung / Oxford',['TD_107564','TD_107580','TD_107235'])]
WEST_ROUNDABOUTS = [('Kwai Yue / Kwai Hei',['TD_8457','TD_9137','TD_9138'])]
REQUIRED_ROUNDABOUTS = EAST_ROUNDABOUTS + WEST_ROUNDABOUTS
HAMMER_HILL_ROUNDABOUT = [
    'TD_103019', 'TD_103025', 'TD_103024', 'TD_103020', 'TD_103027', 'TD_103026',
]
WESTERN_APPROACHES = ['TD_57333']
# Ground-level Kowloon Tong links reviewed against the exact TD centreline archive.
REVIEWED_KOWLOON_TONG_ROADS = [
    'TD_108064', 'TD_108061', 'TD_108062', 'TD_108063', 'TD_107934', 'TD_107935',
    'TD_107715', 'TD_107716', 'TD_107718', 'TD_107719',
    'TD_107656', 'TD_107657', 'TD_110086', 'TD_107620',
    'TD_107621', 'TD_107623', 'TD_107624',
    'TD_108065', 'TD_108066', 'TD_107747',
    'TD_107225', 'TD_107587',
]
# These source-current branches were inspected with the 2026-10-28 junction fix
# and deliberately deferred: they extend beyond TD_57333 or are a separate spur.
DEFERRED_CONNECTED_ROADS = {
    'TD_297076': ('SHA TSUI ROAD',104.7),
    'TD_59096': ('WING YIN STREET',214.9),
    'TD_93429': ('WING SHUN STREET',49.2),
    'TD_97744': ('WING SHUN STREET',109.0),
}
KOWLOON_CITY_DEFERRED_ROADS = {
    'TD_267096': 'Link from Shing Fung Road to the unmodeled Kai Tak Bridge approach.',
    'TD_266963': 'One-way link from TD_267096 to the deferred bridge entrance.',
    'TD_274787': 'One-way Kai Tak Bridge Road entrance leads to TD_266683, which crosses Kowloon Bay and requires a separately modeled deck.',
}
KOWLOON_STREETS = set('ARGYLE STREET|ARTHUR STREET|BATTERY STREET|BUTE STREET|CANTON ROAD|CHANGSHA STREET|CHI WO STREET|DUNDAS STREET|FA YUEN STREET|FIFE STREET|GASCOIGNE ROAD|HAK PO STREET|HAMILTON STREET|JORDAN ROAD|KANSU STREET|KWONG WA STREET|MAN CHEONG STREET|MAN MING LANE|MAN SING STREET|MAN WAI STREET|MAN YING STREET|MAN YUEN STREET|MARKET STREET|MAU LAM STREET|MONG KOK ROAD|NANKING STREET|NATHAN ROAD|NELSON STREET|NING PO STREET|PAK HOI STREET|PARKES STREET|PITT STREET|PORTLAND STREET|PRINCE EDWARD ROAD WEST|PUBLIC SQUARE STREET|RECLAMATION STREET|SAI YEE STREET|SAI YEUNG CHOI STREET SOUTH|SAIGON STREET|SHANGHAI STREET|SHANTUNG STREET|SHEK LUNG STREET|SOY STREET|TAK CHEONG LANE|TAK CHEONG STREET|TEMPLE STREET|TUNG CHOI STREET|TUNG KUN STREET|WAI CHING STREET|WATERLOO ROAD|WING SING LANE|WOOSUNG STREET|YIM PO FONG STREET|YIN CHONG STREET'.split("|"))
KOWLOON = ['TD_104673', 'TD_104583', 'TD_104627', 'TD_105179', 'TD_104554', '-TD_104684', '-TD_104685', 'TD_104623', 'TD_104963', 'TD_104966', 'TD_104591', 'TD_104822', 'TD_104866', 'TD_104865', 'TD_104821', 'TD_104852', '-TD_104868', '-TD_104869', 'TD_104873', 'TD_104872', 'TD_104871', 'TD_105196', 'TD_105757', 'TD_106742', 'TD_106741', 'TD_105849', 'TD_105760', '-TD_105850', '-TD_105852', 'TD_106985', 'TD_105836', 'TD_105867', 'TD_105871', 'TD_105890']
ISLAND_STREETS = set("GLOUCESTER ROAD|HENNESSY ROAD|HARBOUR ROAD|CONVENTION AVENUE|EXPO DRIVE|EXPO DRIVE EAST|FLEMING ROAD|TONNOCHY ROAD|MARSH ROAD|JAFFE ROAD|LOCKHART ROAD|JOHNSTON ROAD|PERCIVAL STREET|CANAL ROAD EAST|CANAL ROAD WEST|CAUSEWAY ROAD|YEE WO STREET|FENWICK STREET".split("|"))
ISLAND_STREETS.update("QUEEN'S ROAD CENTRAL|WELLINGTON STREET|D'AGUILAR STREET|STANLEY STREET|QUEENSWAY|DES VOEUX ROAD CENTRAL|CHATER ROAD|CONNAUGHT ROAD CENTRAL|HARCOURT ROAD|MURRAY ROAD|GARDEN ROAD|COTTON TREE DRIVE|PEDDER STREET|ICE HOUSE STREET|JACKSON ROAD|BANK STREET|CLUB STREET|EDINBURGH PLACE|CONNAUGHT PLACE|TAMAR STREET|TIM WA AVENUE|TIM MEI AVENUE|LUNG WO ROAD|LUNG WUI ROAD|LUNG KING STREET|LUNG HOP STREET|FENWICK PIER STREET|ARSENAL STREET|RODNEY STREET|DRAKE STREET".split("|"))
# Negative IDs traverse two-way source sections in reverse.
SCENIC = [
    'ID_012023', 'ID_020805', 'ID_020804', 'ID_020806', 'ID_020846', 'ID_018216', '-ID_026889',
    'ID_025514', 'ID_028222', 'ID_028228', 'ID_028232', 'ID_028223', 'ID_024646', 'ID_024647',
    'ID_024648', 'ID_015864', 'ID_015762', 'ID_015761', 'ID_015760', 'ID_021189', 'ID_021188',
    'ID_021181', 'ID_031979', 'ID_032307', 'ID_01967', 'ID_00440', 'ID_02282', 'ID_06283',
    'ID_06282', 'ID_00185', 'ID_00130', 'ID_00500', 'ID_01582', 'ID_01936', 'ID_01778',
    'ID_01870', 'ID_01871', 'ID_00993', '-ID_00005', '-ID_00606', 'ID_02920', 'ID_014396',
    'ID_033303', 'ID_02832', 'ID_02146', 'ID_036465', 'ID_036466', 'ID_01912', 'ID_016037',
    'ID_015766', 'ID_015765', 'ID_015763', 'ID_015760', 'ID_021189', 'ID_021185', 'ID_015725',
    'ID_015726', 'ID_033399', 'ID_015890', 'ID_015889', 'ID_015805', 'ID_023176', 'ID_015888',
    'ID_02968', 'ID_030734', 'ID_030733', 'ID_033109', 'ID_033110', 'ID_026356', 'ID_026357',
    'ID_010405', 'ID_014865', 'ID_014864', 'ID_01719', 'ID_00809', 'ID_00230', 'ID_01004',
    'ID_02103', 'ID_01361', 'ID_013379', '-ID_022282', 'ID_02308', 'ID_00440', 'ID_02282',
    'ID_06283', 'ID_06282', 'ID_00185', 'ID_00130', 'ID_00500', 'ID_01582', 'ID_01936',
    'ID_01778', 'ID_01870', 'ID_01871', 'ID_00993', '-ID_00005', '-ID_00606', 'ID_02920',
    'ID_014396', 'ID_033303', '-ID_00331', 'ID_01912', 'ID_016037', 'ID_015766', 'ID_015765',
    'ID_015764', 'ID_015762', 'ID_015777', 'ID_02171', 'ID_04970', 'ID_035497', 'ID_02104',
]


CENTRAL = [
    'ID_03706', 'ID_01868', 'TD_5316', 'TD_4670', 'TD_592', 'TD_897', 'TD_1281', 'TD_613',
    'TD_4995', 'TD_363', 'TD_4996', 'TD_166', 'TD_3080', 'TD_916', 'TD_273003', 'TD_2141',
    'TD_804', 'TD_272894', 'TD_3647', '-TD_5539', 'TD_1940', '-TD_1729', 'TD_465', 'TD_885',
    'TD_4085', 'TD_401', 'TD_605', 'TD_2855', 'TD_117', 'TD_1457', 'TD_1353', 'TD_564',
    'TD_3491', 'TD_2680', 'TD_1863', 'TD_5490', 'TD_5550', 'TD_4674', 'TD_3460', 'TD_3866',
    'TD_4202', 'TD_2309', 'ID_00120', '-ID_01868', '-ID_03706',
]

WEST = ['TD_260907', 'TD_105631', 'TD_105630', 'TD_106942', 'TD_106922', 'TD_106928', 'TD_106913', 'TD_105588', 'TD_275367', 'TD_267593', 'TD_267591', 'TD_267588', 'TD_267587', 'TD_267589', 'TD_280243', 'TD_267590', 'TD_267592', 'TD_275363', 'TD_105589', 'TD_106912', 'TD_106927', 'TD_106922', 'TD_106943', 'TD_271383', 'TD_164670', 'TD_164669', 'TD_106916', 'TD_116115', 'TD_109993', 'TD_106923', 'TD_105602', 'TD_106930', 'TD_105597', 'TD_105612', 'TD_261601', 'TD_106935', 'TD_107180', 'TD_106798', 'TD_107181', 'TD_105753', 'TD_105692', 'TD_107047', 'TD_106756', 'TD_106755', 'TD_106750', 'TD_106156', 'TD_106124', 'TD_107046', 'TD_106192', 'TD_107057', '-TD_106775', 'TD_106199', 'TD_106214', 'TD_106215', 'TD_106216', '-TD_106353', 'TD_106695', 'TD_106322', 'TD_106326', '-TD_107068', 'TD_107075', 'TD_106630', 'TD_106629', 'TD_106632', 'TD_107090', 'TD_272324', '-TD_106375', '-TD_106363', 'TD_106376', 'TD_107074', 'TD_106377']
SHAM_SHUI_PO = ['TD_105889', 'TD_105888', 'TD_106994', 'TD_106031', '-TD_107037', '-TD_107035', 'TD_107024', 'TD_106054', 'TD_106035', 'TD_105789', 'TD_106268', 'TD_106348', 'TD_106347', 'TD_106349', 'TD_105799', 'TD_105350', '-TD_105343', '-TD_106429', 'TD_107084', '-TD_106344', '-TD_106364', 'TD_106698', 'TD_110026', '-TD_106346', 'TD_106274', 'TD_106278', 'TD_106280', 'TD_106252', 'TD_106263']
LAI_CHI_KOK = ['TD_106264', 'TD_106374', 'TD_106373', 'TD_106375', 'TD_115929', 'TD_272323', 'TD_107085', '-TD_106632', '-TD_106633', 'TD_106581', 'TD_7363', '-TD_7659', 'TD_7370', 'TD_8329', 'TD_7673', 'TD_9641', 'TD_9653', 'TD_9642', 'TD_8320', 'TD_8318', 'TD_9680', 'TD_9014', 'TD_9009', 'TD_7648', 'TD_8663', 'TD_8651', 'TD_8644', 'TD_8042', 'TD_272313', 'TD_8047', '-TD_9040']

KWAI_CHUNG = ['-TD_8649', 'TD_8642', '-TD_65324', '-TD_65325', 'TD_9625', 'TD_7680', '-TD_271769', '-TD_271768', '-TD_271765', '-TD_271766', '-TD_284304', '-TD_8372', '-TD_271767', '-TD_9109', '-TD_9716', '-TD_7434', '-TD_8099', '-TD_272049', '-TD_7421', '-TD_272246', '-TD_7757', '-TD_284844', '-TD_284462', 'TD_65149', 'TD_268542', 'TD_65148', '-TD_65146', 'TD_9739', 'TD_8063', 'TD_8747', 'TD_7822', 'TD_59597', 'TD_57351', 'TD_57350', 'TD_64614', 'TD_64615', 'TD_57349', 'TD_56902', '-TD_57353', '-TD_58246', 'TD_59623', 'TD_58626', '-TD_57610', 'TD_64700', 'TD_57160', 'TD_57609', '-TD_58053', '-TD_57159', 'TD_59443', '-TD_57603', 'TD_59576', 'TD_60105', 'TD_56923', 'TD_59193', 'TD_59640', 'TD_57617', 'TD_59559', '-TD_65200', 'TD_59154']

TSUEN_WAN = ['-TD_59580', 'TD_60092', 'TD_57811', 'TD_60091', 'TD_60090', 'TD_276664', 'TD_58197', 'TD_58666', 'TD_58689', 'TD_59610', '-TD_56927', '-TD_56928', 'TD_57334', 'TD_59618', 'TD_58228', 'TD_58695', 'TD_56926', 'TD_57355', '-TD_57817', 'TD_59211', 'TD_58661', 'TD_56954', 'TD_60099', 'TD_58705', 'TD_93377', 'TD_283753', 'TD_283752', 'TD_93378', 'TD_93374', 'TD_96024', 'TD_59149', 'TD_58683', 'TD_57758', 'TD_58237', '-TD_58660', 'TD_59182', 'TD_64267', '-TD_93402', '-TD_93339', 'TD_93347', '-TD_93341', '-TD_93342', 'TD_111741', '-TD_111740', 'TD_111736', 'TD_116769', 'TD_93252', '-TD_93408', 'TD_93010', 'TD_93410', 'TD_93113', 'TD_271773', 'TD_92993']

WEST_COAST = ['TD_271771', 'TD_271772', 'TD_261429', 'TD_92931', 'TD_92932', 'TD_92933', 'TD_92936', 'TD_93220', 'TD_272364', '-TD_271771', '-TD_92993', '-TD_271773', '-TD_93113', 'TD_93409', '-TD_93010', 'TD_93408', 'TD_93456', 'TD_93398', 'TD_111730', 'TD_111904', 'TD_111903', 'TD_93222', 'TD_93088', 'TD_96854', 'TD_93012', 'TD_93013', 'TD_93015', 'TD_93201', 'TD_265762', 'TD_164214', 'TD_93016', 'TD_93078', 'TD_93077', 'TD_93205', '-TD_96546', 'TD_96551', 'TD_96550', 'TD_93296', 'TD_93298', 'TD_93297', 'TD_93424', 'TD_93423', 'TD_165439', 'TD_93212', 'TD_110626', 'TD_110628', 'TD_110603', 'TD_110596', 'TD_110592', 'TD_110589', 'TD_110575', 'TD_110581', 'TD_110605', 'TD_110604', 'TD_110617', 'TD_110615', 'TD_93631', 'TD_93754', 'TD_93753', 'TD_93752', 'TD_93751', 'TD_93655', 'TD_93654', 'TD_93515', 'TD_93744', 'TD_116022', 'TD_93750', 'TD_93742', 'TD_93746', 'TD_93799', 'TD_96621', 'TD_98692', 'TD_93745', 'TD_93748', 'TD_93749']

EAST_KOWLOON = ['ID_012620', 'ID_04550', 'TD_104615', 'TD_105206', 'TD_104990', 'TD_104606', 'TD_104511', '-TD_104986', 'TD_104987', 'TD_104513', 'TD_104510', '-TD_104988', 'TD_104989', 'TD_104512', '-TD_104984', 'TD_104985', 'TD_102104', '-TD_102105', '-TD_102106', 'TD_102273', 'TD_283746', 'TD_102274', '-TD_102154', '-TD_102267', 'TD_102230', '-TD_102217', 'TD_102194', 'TD_115828', '-TD_104072', '-TD_102234', '-TD_102235', 'TD_104074', 'TD_102197', 'TD_102198', 'TD_115826', 'TD_104073', 'TD_102214', 'TD_102261', '-TD_102267', 'TD_102230', '-TD_102217', '-TD_102215', 'TD_103738', '-TD_102218', '-TD_102219', 'TD_102229', '-TD_102221', '-TD_102222', 'TD_102228', '-TD_102225', '-TD_102452', 'TD_102451', 'TD_102172', '-TD_102269', 'TD_102550', '-TD_102548', 'TD_102549', 'TD_103565', 'TD_103571', 'TD_103570', 'TD_103572', 'TD_103568', 'TD_103567', 'TD_103575', 'TD_103574', '-TD_102556', '-TD_102529', 'TD_102533', 'TD_102546', '-TD_102552', 'TD_102566', 'TD_102567', 'TD_102565', 'TD_103633', '-TD_261278', 'TD_261276', 'TD_284230', 'TD_284229', 'TD_284792', 'TD_284841', 'TD_285567', 'TD_284888', 'TD_104007', 'TD_102528', 'TD_103554', 'TD_102563', 'TD_102561', 'TD_102673', 'TD_103798', 'TD_103791', 'TD_102569', 'TD_103586', 'TD_102709', 'TD_103767', '-TD_102416', 'TD_102711', '-TD_102712', '-TD_102713', 'TD_102690', '-TD_109796', 'TD_102677']
WONG_TAI_SIN = ['-TD_102650','-TD_115861','-TD_102706','-TD_102390','-TD_102389','-TD_102402',
                'TD_102381','-TD_102403','TD_102405','TD_102395','TD_102408','TD_102407',
                'TD_102394','TD_102421','TD_102596','TD_102593','-TD_102594','-TD_102376',
                '-TD_102380','-TD_271127','-TD_102589','TD_102591','-TD_107810','TD_102426',
                'TD_102423','TD_102432','TD_102435','TD_102434','TD_102429','-TD_102665',
                'TD_102580','TD_103436','TD_103488','TD_103731','TD_103486','TD_102669',
                'TD_103804','TD_102670','TD_272331']
WONG_TAI_SIN_NETWORK = ['TD_103730']
# From Wong Tai Sin Road through Tsz Wan Shan and Po Kong Village Road to Lung Poon Street.
DIAMOND_HILL = [
    'TD_102715', 'TD_102761', 'TD_261466', 'TD_102817', 'TD_102828', 'TD_103823',
    'TD_102822', 'TD_102798', 'TD_102788', 'TD_102787', 'TD_102748', 'TD_102785',
    'TD_103279', 'TD_103373', 'TD_103420', 'TD_103419', 'TD_271929', 'TD_103418',
    'TD_103272', 'TD_103409', 'TD_103366', 'TD_109834', 'TD_103394', 'TD_261450',
    'TD_104123', 'TD_103367', 'TD_103372', 'TD_115580', 'TD_103354', '-TD_103277',
    '-TD_103282', '-TD_103283', 'TD_103339', 'TD_103338', 'TD_103337', '-TD_103336',
    'TD_103291', '-TD_103290', '-TD_103288', 'TD_103382', '-TD_103377', '-TD_103375',
    'TD_272783', 'TD_103383', '-TD_103378', '-TD_103379', 'TD_103380', 'TD_103938',
    '-TD_103835', '-TD_102939', 'TD_103941', 'TD_272445', 'TD_103385', 'TD_103391',
    'TD_103937', 'TD_164890', 'TD_102838', 'TD_273245',
]
# Public, ground-level streets connected in both directions to the retained map.
WONG_TAI_SIN_DISTRICT_ROADS = {
    'TD_102843', 'TD_102871', 'TD_102872', 'TD_102926', 'TD_103005',
    'TD_103023', 'TD_103036', 'TD_103277', 'TD_103281',
    'TD_103282', 'TD_103283', 'TD_103288', 'TD_103289', 'TD_103290', 'TD_103291',
    'TD_103305', 'TD_103306', 'TD_103307', 'TD_103308', 'TD_103309', 'TD_103310',
    'TD_103311', 'TD_103313', 'TD_103314', 'TD_103315', 'TD_103316', 'TD_103317',
    'TD_103319', 'TD_103321', 'TD_103322', 'TD_103323', 'TD_103324', 'TD_103325',
    'TD_103327', 'TD_103328', 'TD_103329', 'TD_103330', 'TD_103332', 'TD_103333',
    'TD_103334', 'TD_103335', 'TD_103336', 'TD_103337', 'TD_103338', 'TD_103339',
    'TD_103340', 'TD_103341', 'TD_103343', 'TD_103344', 'TD_103345', 'TD_103346',
    'TD_103355', 'TD_103376', 'TD_103382', 'TD_103433', 'TD_103434',
    'TD_103843', 'TD_103848', 'TD_103849', 'TD_103885', 'TD_103942', 'TD_103943',
    'TD_103953', 'TD_104130',
    'TD_109836', 'TD_109837', 'TD_115590', 'TD_269008', 'TD_269009', 'TD_272446',
    'TD_272447', 'TD_272463', 'TD_272483', 'TD_284314', 'TD_284333', 'TD_284356',
}.union(HAMMER_HILL_ROUNDABOUT)
# The Choi Hung Road loop requires an unmodeled interchange to exit legally.
# Keep its connected surface approaches and defer the loop and its Hammer Hill stubs.
WONG_TAI_SIN_DEFERRED_ROADS = {
    'TD_102853', 'TD_102854', 'TD_102855', 'TD_102856', 'TD_102857', 'TD_102858',
    'TD_102961', 'TD_103009', 'TD_103017', 'TD_103827', 'TD_103828', 'TD_103846',
    'TD_103862', 'TD_103863',
}
# Follow the surveyed one-way approach past Choi Hung into the retained Hammer Hill roundabout.
CHOI_HUNG_TO_HAMMER_HILL = [
    'TD_102872', 'TD_102856', 'TD_102961', 'TD_103828', 'TD_103863', 'TD_103009',
    'TD_103017', 'TD_273265', 'TD_103859', 'TD_103858', 'TD_103429', 'TD_103428',
    'TD_103861', 'TD_270803', 'TD_270804', 'TD_103960', 'TD_165412', 'TD_280343',
    'TD_103447', 'TD_103877', 'TD_103022', 'TD_103027',
]
CHOI_HUNG_SIDE_LOOP = ['TD_103017', 'TD_103862', 'TD_103827', 'TD_103828']
HAMMER_HILL_DECKS = {'TD_103671', 'TD_103672'}
HAMMER_HILL_MERGE = {
    'approaches': ['TD_103877', 'TD_104038'],
    'departure': 'TD_103022',
    'height_m': 3.3105,
}
HAMMER_HILL_MERGE_ROADS = {*HAMMER_HILL_MERGE['approaches'], HAMMER_HILL_MERGE['departure']}
HAMMER_HILL_WEST_EXIT = [
    'TD_103024', 'TD_103021', 'TD_104039', 'TD_103672', 'TD_104037', 'TD_102858',
    'TD_102857', 'TD_102926', 'TD_102871', 'TD_283007',
]
HAMMER_HILL_EAST_ENTRY = [
    'TD_102872', 'TD_102843', '-TD_102857', '-TD_102858', 'TD_103844',
    'TD_104036', 'TD_103671', 'TD_104038', 'TD_103022', 'TD_103027',
]
LUNG_CHEUNG_UNDERPASS = ['TD_103832', 'TD_103841', 'TD_102964', 'TD_103871', 'TD_103429']
# The last westbound section and the underpass endpoints predate the district expansion.
WONG_TAI_SIN_NETWORK_ROADS = {
    member.lstrip('-') for member in (
        CHOI_HUNG_TO_HAMMER_HILL+CHOI_HUNG_SIDE_LOOP+HAMMER_HILL_WEST_EXIT[:-1]+
        HAMMER_HILL_EAST_ENTRY+LUNG_CHEUNG_UNDERPASS[1:-1])
}
# These one-way carriageway widths preserve the standard 3.5 m building setback.
WONG_TAI_SIN_NARROW_CARRIAGEWAYS = {
    'TD_102856':6.0,'TD_103858':6.0,'TD_103428':6.0,'TD_103861':6.0,'TD_103672':6.0,
    'TD_103841':11.5,
}
WONG_TAI_SIN_CENTERLINE_SHA256 = 'ebdc7052bbd07fbc3f6f068012ba8354e62c9f3c21c080d6cd43f334b1169adf'
KAI_TAK = [
    'TD_261277', 'TD_261274', '-TD_261256', 'TD_261255', 'TD_261253',
    'TD_261246', 'TD_281785', 'TD_281805', 'TD_285648', 'TD_284207',
    'TD_280443', 'TD_284288', 'TD_266569', 'TD_285316', 'TD_266658',
    'TD_266564', 'TD_266657', 'TD_266604', 'TD_266574', '-TD_267098',
    'TD_267095', 'TD_266609', 'TD_266610', 'TD_266625', 'TD_266623',
    'TD_266639', 'TD_266631', 'TD_285337', 'TD_266630', 'TD_266640',
    'TD_266645', 'TD_266646', 'TD_266647', 'TD_266648',
]
KAI_TAK_NETWORK = ['TD_284206']  # Opposite carriageway of the Shing Fung Road deck.
CHI_MAN_STREET_ID = 'TD_105191'
# Chi Man Street's surveyed centreline passes within 2.64 m of the SPCA footprint.
CHI_MAN_STREET_WIDTH = 5.0
SINGLE_LANE_WIDTHS = {'TD_103438':3.2,'TD_103954':3.0}

TST_PROMENADE_SITE = '1503005628'
TST_SALISBURY_SITE = '1810015202'
TST_EAST_SHORELINE = '1101166493'
TST_WEST_SHORELINE = '1101166503'
SOUTHWEST_EDIT_BOUNDS = (-1121.441, -670, 47.987940581, 232)
SOUTHWEST_CHART_GAP_BOUNDS = (-1121.441, -80, -891, 232)
SOUTHWEST_PROMENADE_BOUNDS = (-460, 170, SOUTHWEST_EDIT_BOUNDS[2], SOUTHWEST_EDIT_BOUNDS[3])
MUSEUM_WATER_BOUNDS = (SOUTHWEST_EDIT_BOUNDS[2], 130, 112, 222)


def southwest_source_geometry(geometry):
    """Convert source WGS84 geometry to the game's local metre coordinates."""
    scale_x=111320*math.cos(math.radians(ORIGIN[1]))
    return transform_geometry(lambda x,y,z=None:((x-ORIGIN[0])*scale_x,-(y-ORIGIN[1])*111320),geometry)


def southwest_support_and_water(kowloon, tst_site_land):
    """Use exact chart water and cached iB1000 footprints to repair the southwest apron."""
    water_path=ROOT/'Data/southwest-water-source.geojson'
    shoreline_path=ROOT/'Data/southwest-shoreline-source.geojson'
    buildings_path=ROOT/'Data/southwest-building-ground-source.geojson'
    cultural_site_path=ROOT/'Data/southwest-public-spaces-source.geojson'
    water_data=json.loads(water_path.read_text())
    shoreline_data=json.loads(shoreline_path.read_text())
    buildings_data=json.loads(buildings_path.read_text())
    cultural_data=json.loads(cultural_site_path.read_text())
    water=unary_union([shape(feature['geometry']) for feature in water_data['features']])
    decks=unary_union([southwest_source_geometry(shape(feature['geometry'])) for feature in shoreline_data['features']
                       if feature['properties'].get('source_type') in ('JPW','FFL')])
    buildings=unary_union([southwest_source_geometry(shape(feature['geometry'])) for feature in buildings_data['features']])
    cultural_site=unary_union([southwest_source_geometry(shape(feature['geometry'])) for feature in cultural_data['features']
                               if feature['properties'].get('layer')=='Site' and feature['properties'].get('SITEID')=='1503005422'])
    # The public promenade extends below the Cultural Centre Site boundary.
    promenade=box(*SOUTHWEST_PROMENADE_BOUNDS).difference(water)
    support=unary_union([decks,buildings,cultural_site.difference(water),promenade])
    edit_window=box(*SOUTHWEST_EDIT_BOUNDS)
    chart_gap=box(*SOUTHWEST_CHART_GAP_BOUNDS).intersection(kowloon).difference(support)
    museum_water=water.intersection(kowloon).intersection(box(*MUSEUM_WATER_BOUNDS)).difference(support.union(tst_site_land))
    water_cut=unary_union([water.intersection(kowloon).intersection(edit_window).difference(support),chart_gap,museum_water])
    assert water.is_valid and support.is_valid and water_cut.is_valid, 'Southwest source geometry is invalid'
    assert water_cut.area>400000, 'Official water boundary no longer covers the reviewed apron'
    return water_cut,support,museum_water,decks,shoreline_data,water_path,shoreline_path,buildings_path,cultural_site_path


def build_tst_shoreline_geometry(district, east_land, site_features, east_shoreline, west_shoreline):
    """Return the source-supported TST sites, apron water cut, and joined waterfront edge."""
    sites={f['properties']['SITEID']:shape(f['geometry']) for f in site_features}
    assert set(sites)=={TST_PROMENADE_SITE,TST_SALISBURY_SITE}, 'Unexpected TST source-site set'
    promenade=sites[TST_PROMENADE_SITE]

    def source_lines(features, shoreline_id):
        return [LineString([local(p) for p in feature['geometry']['coordinates']])
                for feature in features if str(feature['properties'].get('SHORELINEID'))==shoreline_id]

    east_lines=source_lines(east_shoreline,TST_EAST_SHORELINE)
    west_lines=source_lines(west_shoreline,TST_WEST_SHORELINE)
    assert len(east_lines)==1 and west_lines, 'Required TST SWA source fragments changed'
    east_line=east_lines[0]
    parts=list(promenade.geoms) if promenade.geom_type=='MultiPolygon' else [promenade]
    west_endpoints=[Point(p) for line in west_lines for p in (line.coords[0],line.coords[-1])]
    candidate=[]
    for part in parts:
        ring=LineString(part.exterior.coords)
        west_join=min(west_endpoints,key=ring.distance)
        east_endpoint=min((Point(east_line.coords[0]),Point(east_line.coords[-1])),key=ring.distance)
        candidate.append((ring.distance(west_join)+ring.distance(east_endpoint),part,ring,west_join,east_endpoint))
    _,part,ring,west_join,east_join=min(candidate,key=lambda row:row[0])
    west_anchor=nearest_points(ring,west_join)[0]
    east_anchor=nearest_points(ring,east_join)[0]
    assert west_anchor.distance(west_join)<.02 and east_anchor.distance(east_join)<.02, \
        'TST source Site perimeter no longer joins the surveyed seawall fragments'
    start,end=ring.project(west_anchor),ring.project(east_anchor)
    assert abs(end-start)<ring.length/2, 'TST seaward Site arc is ambiguous'
    site_arc=substring(ring,min(start,end),max(start,end))
    site_coords=list(site_arc.coords)
    if start>end:site_coords.reverse()
    east_coords=list(east_line.coords)
    if Point(east_coords[-1]).distance(east_anchor)<Point(east_coords[0]).distance(east_anchor):east_coords.reverse()
    assert math.dist(site_coords[-1],east_coords[0])<.02, 'TST Site / SWA join changed'
    site_coords[-1]=east_coords[0]
    waterfront=LineString(site_coords+east_coords[1:])
    assert waterfront.is_simple and 1100<waterfront.length<1180, 'TST source frontage changed'

    top=district.bounds[3]
    top_edge=LineString([(waterfront.bounds[0]-1,top),(waterfront.bounds[2]+1,top)])
    crossings=waterfront.intersection(top_edge)
    crossings=[crossings] if crossings.geom_type=='Point' else list(getattr(crossings,'geoms',[]))
    crossings=[p for p in crossings if p.geom_type=='Point']
    assert len(crossings)==1, 'The TST waterfront must meet the old apron edge once'
    crossing=crossings[0]
    coast_segment=substring(waterfront,waterfront.project(crossing),waterfront.length)
    east_end=coast_segment.coords[-1]
    source_water=Polygon(list(coast_segment.coords)+[(east_end[0],top),(crossing.x,top)])
    assert source_water.is_valid, 'TST source water cut is invalid'

    # The eastern official land source covers the rest of the former apron through its old edge.
    east_clip=box(550,-1220,district.bounds[2],top)
    east_cut=district.difference(east_land).intersection(east_clip)
    east_parts=[p for p in (east_cut.geoms if hasattr(east_cut,'geoms') else [east_cut])
                if p.geom_type=='Polygon' and p.area>.01]
    east_cut=unary_union(east_parts)
    west_cut=district.intersection(source_water)
    cut=unary_union([east_cut,west_cut])
    if cut.geom_type=='GeometryCollection':
        cut=unary_union([p for p in cut.geoms if p.geom_type in ('Polygon','MultiPolygon') and p.area>.01])
    assert cut.is_valid and cut.area>300000, 'TST apron water cut is incomplete'
    return unary_union(list(sites.values())),cut,waterfront,east_cut

def hammer_hill_deck_profiles(lines, *, legacy_merge=False):
    # Relative level one is surveyed. The 7 m decks and their approach grades are authored.
    profiles={}
    def add_ramp(members,start,end,flat_start=0,flat_finish=0):
        total=sum(lines[ident].length for ident in members)-flat_start-flat_finish
        assert total>0, (members,'Level approach exceeds ramp length')
        offset=-flat_start
        for ident in members:
            profiles[ident]=(offset,total,start,end)
            offset+=lines[ident].length
    def height(ident,distance):
        offset,total,start,end=profiles[ident]
        phase=max(0,min(1,(offset+distance)/total))
        return start+(end-start)*(1-math.cos(math.pi*phase))/2
    add_ramp(('TD_103021','TD_104039'),0,7)
    add_ramp(('TD_104037',),7,0)
    add_ramp(('TD_104036',),0,7)
    add_ramp(('TD_103671',),7,7)
    add_ramp(('TD_103672',),7,7)
    # Hold all overlapping carriageways at the same level and taper smoothly into the shared apron.
    lung_cheung,bridge=HAMMER_HILL_MERGE['approaches']
    departure=HAMMER_HILL_MERGE['departure']
    if legacy_merge:
        # The pre-apron release tapered each approach into the same endpoint only.
        add_ramp((bridge,departure),7,0)
        add_ramp((lung_cheung,),0,height(bridge,lines[bridge].length))
    else:
        merge_height=HAMMER_HILL_MERGE['height_m']
        add_ramp((lung_cheung,),0,merge_height,flat_finish=20)
        add_ramp((bridge,),7,merge_height,flat_finish=20)
        add_ramp((departure,),merge_height,0,flat_start=8)
    return profiles,height


def migrate_hammer_hill_merge(roads, prior_roads, prior_decks, lines):
    present=HAMMER_HILL_MERGE_ROADS & prior_roads.keys()
    if not present and prior_decks is None:
        return False
    if present!=HAMMER_HILL_MERGE_ROADS or prior_decks is None:
        raise ValueError('The existing Hammer Hill merge inventory is incomplete')
    legacy=prior_decks=={'source_ids':sorted(HAMMER_HILL_DECKS),'authored_height_m':7}
    if legacy:
        _,legacy_height=hammer_hill_deck_profiles(lines,legacy_merge=True)
    elif prior_decks.get('merge')!=HAMMER_HILL_MERGE:
        raise ValueError('The existing Hammer Hill merge uses an unsupported profile')
    for road in roads:
        ident=road['id']
        if ident not in present:
            continue
        expected=road
        if legacy:
            length=lines[ident].length
            points=[[x,round(legacy_height(ident,min(i*4,length)),4),z]
                    for i,(x,_,z) in enumerate(road['points'])]
            expected=dict(road,points=points)
        if prior_roads[ident]!=expected:
            raise ValueError(f'{ident} differs from the reviewed Hammer Hill merge profile')
    return legacy


def build(source, *, retain_road_inventory=False, complete_kowloon_city=False,
          complete_wong_tai_sin=False, whole_wong_tai_sin=False):
    complete_wong_tai_sin = complete_wong_tai_sin or whole_wong_tai_sin
    complete_kowloon_city = complete_kowloon_city or complete_wong_tai_sin
    if retain_road_inventory and complete_kowloon_city:
        raise ValueError('Select either the retained road inventory or the Kowloon City district refresh')
    previous = json.loads((ROOT/'Data/cross-harbour-source.geojson').read_text())
    if 'wong_tai_sin_network_sections' in previous['metadata'] and not whole_wong_tai_sin:
        raise ValueError('Use --whole-wong-tai-sin-district to rebuild the full Wong Tai Sin road network')
    if whole_wong_tai_sin and 'wong_tai_sin_deferred_roads' not in previous['metadata']:
        raise ValueError('The full Wong Tai Sin network requires the reviewed Diamond Hill snapshot')
    if 'wong_tai_sin_district_boundary_sha256' in previous['metadata'] and not complete_wong_tai_sin:
        raise ValueError('Use --wong-tai-sin-district to rebuild the Wong Tai Sin and Diamond Hill map')
    if complete_wong_tai_sin and 'kowloon_city_district_boundary_sha256' not in previous['metadata']:
        raise ValueError('Wong Tai Sin expansion requires the reviewed Kowloon City district snapshot')
    if 'kowloon_city_district_boundary_sha256' in previous['metadata'] and not complete_kowloon_city:
        raise ValueError('Use --kowloon-city-district to rebuild the expanded Kowloon City map')
    if complete_kowloon_city and '--hk1980' in sys.argv:
        raise ValueError('The Kowloon City road archive uses WGS84. Omit --hk1980')
    deferred = set(KOWLOON_CITY_DEFERRED_ROADS) if complete_kowloon_city else set()
    district_roads = WONG_TAI_SIN_DISTRICT_ROADS
    wong_tai_sin_deferred = WONG_TAI_SIN_DEFERRED_ROADS
    if whole_wong_tai_sin:
        district_roads = district_roads | WONG_TAI_SIN_NETWORK_ROADS
        wong_tai_sin_deferred = wong_tai_sin_deferred - WONG_TAI_SIN_NETWORK_ROADS
    if complete_wong_tai_sin:
        deferred.update(wong_tai_sin_deferred)
    previous_features = [f for f in previous['features'] if f['properties']['source_id'] not in deferred]
    coast_data=json.loads((ROOT/'Data/west-kowloon-coast.json').read_text())
    northwest_coast=json.loads((ROOT/'Data/lai-chi-kok-coast.json').read_text())
    # Keep the established coast exactly; only add land outside its earlier map rectangle.
    west_land=unary_union([shape(coast_data['land']),shape(northwest_coast['land']).difference(box(*WEST_BOUNDS))])
    assert west_land.is_valid and west_land.geom_type=='Polygon', 'Northwest land must join the existing mainland'
    kwai_chung_coast=json.loads((ROOT/'Data/kwai-chung-coast.json').read_text())
    prior_region=unary_union([box(*WEST_BOUNDS),box(*NORTHWEST_BOUNDS)])
    west_land=unary_union([west_land,shape(kwai_chung_coast['land']).difference(prior_region)])
    assert west_land.is_valid and west_land.geom_type=='Polygon', 'Kwai Chung land must join the existing mainland'
    tsuen_wan_coast=json.loads((ROOT/'Data/tsuen-wan-coast.json').read_text())
    kwai_region=unary_union([prior_region,box(*KWAI_CHUNG_BOUNDS)])
    west_land=unary_union([west_land,shape(tsuen_wan_coast['land']).difference(kwai_region)])
    assert west_land.is_valid and west_land.geom_type=='Polygon', 'Tsuen Wan land must join the existing mainland'
    west_coast=json.loads((ROOT/'Data/west-coast-coast.json').read_text())
    tsuen_region=unary_union([kwai_region,box(*TSUEN_WAN_BOUNDS)])
    west_land=unary_union([west_land,shape(west_coast['land']).difference(tsuen_region)])
    assert west_land.is_valid and west_land.geom_type=='Polygon', 'West coast land must join the existing mainland'
    east_coast=json.loads((ROOT/'Data/east-kowloon-coast.json').read_text())
    east_land=shape(east_coast['land'])
    east_bounds=tuple(east_coast['bounds'])
    roundabouts=REQUIRED_ROUNDABOUTS
    if complete_wong_tai_sin:
        wong_tai_sin_boundary_path=ROOT/'Data/wong-tai-sin-district-boundary.geojson'
        boundary_source=wong_tai_sin_boundary_path.read_bytes()
        wong_tai_sin_data=json.loads(boundary_source)
        feature,=wong_tai_sin_data['features']
        feature_bytes=json.dumps(feature,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
        feature_sha256=hashlib.sha256(feature_bytes).hexdigest()
        if (feature_sha256!=wong_tai_sin_data['metadata']['feature_sha256']
                or feature['properties']['District']!='Wong Tai Sin District'
                or feature['properties']['地區號碼']!='H'):
            raise ValueError('Invalid official Wong Tai Sin District boundary provenance')
        terrain_provenance=east_coast['metadata'].get('wong_tai_sin_district_land',{})
        if (east_bounds!=WONG_TAI_SIN_DISTRICT_BOUNDS
                or terrain_provenance.get('district_feature_sha256')!=feature_sha256):
            raise ValueError('Build the official Wong Tai Sin district terrain before importing its streets')
        wong_tai_sin_extent=transform_geometry(lambda x,y,z=None:local((x,y)),shape(feature['geometry']))
        roundabouts=REQUIRED_ROUNDABOUTS+[('Hammer Hill / Fung Tak',HAMMER_HILL_ROUNDABOUT)]
    east_shoreline_path=ROOT/'Data/east-kowloon-shoreline.geojson'
    east_shoreline_data=json.loads(east_shoreline_path.read_text())
    island_coast=json.loads((ROOT/'Data/island-coast.json').read_text())
    island=shape(island_coast['land'])
    district_data=json.loads((ROOT/'Data/nathan-road.json').read_text())
    old_district=box(*district_data['bounds'])
    old_kowloon=unary_union([old_district,box(*KOWLOON_BOUNDS)])
    district_boundary_path=ROOT/'Data/kowloon-city-district-boundary.geojson'
    if complete_kowloon_city:
        feature,=json.loads(district_boundary_path.read_text())['features']
        district_extent=transform_geometry(lambda x,y,z=None:local((x,y)),shape(feature['geometry']))
        # The district boundary locates the gap, while CEDD establishes mainland coverage.
        mainland_source=east_shoreline_data['kai_tak_coast_sources']['reclamation']
        mainland_feature,=mainland_source['features']
        mainland=transform_geometry(lambda x,y,z=None:local((x,y)),shape(mainland_feature['geometry']))
        north_fill=box(*KOWLOON_CITY_NORTH_FILL_BOUNDS)
        assert mainland.covers(north_fill), 'Government mainland polygon does not cover the northern fill'
        west_land=west_land.union(north_fill)
        assert west_land.is_valid and west_land.geom_type=='Polygon', 'Northern fill must join western Kowloon'
        surveyed_ground=unary_union([old_kowloon,west_land,east_land])
    ids = set(SOUTH+ISLAND+NORTH+[i.lstrip("-") for i in SCENIC+CENTRAL+KOWLOON+WEST+SHAM_SHUI_PO+LAI_CHI_KOK+KWAI_CHUNG+TSUEN_WAN+WEST_COAST+EAST_KOWLOON+WONG_TAI_SIN+WONG_TAI_SIN_NETWORK])
    ids.update(i for _,members in roundabouts for i in members)
    ids.update(WESTERN_APPROACHES)
    ids.update(REVIEWED_KOWLOON_TONG_ROADS)
    # ROUTE_ID is the stable source key. Pin old sections to their source snapshot
    # and validate a requested datum conversion against shared geometry before connecting new roads.
    existing = {f['properties']['ROUTE_ID']:f for f in previous_features}
    kai_tak_ids={ident.lstrip('-') for ident in KAI_TAK+KAI_TAK_NETWORK}
    retained = {f['properties']['source_id'] for f in previous_features}
    include_kai_tak=complete_kowloon_city or kai_tak_ids <= retained
    if include_kai_tak:
        ids.update(kai_tak_ids)
    if complete_wong_tai_sin:
        ids.update(ident.lstrip('-') for ident in DIAMOND_HILL)
    if whole_wong_tai_sin:
        ids.update(ident.lstrip('-') for ident in CHOI_HUNG_TO_HAMMER_HILL)
        ids.update(ident.lstrip('-') for ident in HAMMER_HILL_WEST_EXIT+HAMMER_HILL_EAST_ENTRY)
    transform = None
    if '--hk1980' in sys.argv:
        from pyproj import Transformer
        transform = Transformer.from_crs(4611,4326,always_xy=True)
    with source.open('rb') as source_stream:
        source_hash=hashlib.file_digest(source_stream,'sha256').hexdigest()
    if complete_wong_tai_sin and source_hash!=WONG_TAI_SIN_CENTERLINE_SHA256:
        raise ValueError('Wong Tai Sin requires the reviewed WGS84 Transport Department centreline archive')
    records = {f['properties']['source_id']:f for f in previous_features} if complete_kowloon_city else {}
    matched = 0; changed = []
    with zipfile.ZipFile(source) as archive, archive.open('doc.kml') as stream:
        for _, element in ET.iterparse(stream, events=('end',)):
            if element.tag != f"{{{NS['k']}}}Placemark":
                continue
            props = dict(re.findall(r'<td>([A-Z_]+)</td>\s*<td>(.*?)</td>', element.findtext('k:description','',NS)))
            prior = existing.get(props.get('ROUTE_ID'))
            ident = prior['properties']['source_id'] if prior else 'TD_'+props['ROUTE_ID']
            if ident in deferred or (complete_wong_tai_sin and not prior and ident not in ids
                                     and ident not in district_roads):
                element.clear()
                continue
            if prior or ident in ids or props.get('ELEVATION')=='0' or (props.get('ELEVATION')=='1' and props.get('STREET_ENAME','').startswith('CASTLE PEAK ROAD')):
                coords = [list(map(float,w.split(','))) for w in element.find('.//k:coordinates',NS).text.split()]
                if transform:coords = [[*transform.transform(*p[:2]),p[2]] for p in coords]
                if prior:
                    pinned=prior['geometry']['coordinates']
                    if whole_wong_tai_sin and ident in HAMMER_HILL_MERGE_ROADS and pinned!=coords:
                        raise ValueError(f'{ident} differs from the reviewed Hammer Hill merge centreline')
                    if pinned==coords:
                        matched+=1
                    else:
                        before=[local(p) for p in pinned]
                        after=[local(p) for p in coords]
                        # Corresponding vertices bound the distance between their connecting segments.
                        aligned=len(before)==len(after) and all(math.dist(a,b)<.025 for a,b in zip(before,after))
                        if aligned or (math.dist(before[0],after[0])<.025
                                       and LineString(before).hausdorff_distance(LineString(after))<.025):
                            matched+=1
                        else:
                            changed.append(ident)
                    coords=pinned
                line=LineString([local(p) for p in coords])
                name=props.get('STREET_ENAME','')
                if complete_wong_tai_sin:
                    auto_selection=ident in district_roads
                    if auto_selection:
                        level='1' if whole_wong_tai_sin and ident in HAMMER_HILL_DECKS else '0'
                        assert (props.get('ELEVATION')==level and props.get('TRAVEL_DIRECTION') in ('1','2','3')
                                and wong_tai_sin_extent.intersection(line).length>line.length/2
                                and surveyed_ground.covers(line.buffer(6.05))), \
                            (ident,'Reviewed Wong Tai Sin section no longer qualifies as a district surface street')
                elif complete_kowloon_city:
                    # Import connected surface streets within the official district, with room for the authored carriageway.
                    auto_selection=(not prior and ident not in ids and props.get('ELEVATION')=='0'
                                    and props.get('TRAVEL_DIRECTION') in ('1','2','3')
                                    and name not in ('','-99','&lt;Null&gt;')
                                    and not any(s in name for s in ('HIGHWAY','CROSSING','CORRIDOR','FLYOVER','INTERCHANGE','TUNNEL'))
                                    and district_extent.intersection(line).length>line.length/2
                                    and surveyed_ground.covers(line.buffer(6.05)))
                else:
                    north=name in KOWLOON_STREETS and line.bounds[1]<KOWLOON_BOUNDS[3] and box(KOWLOON_BOUNDS[0],KOWLOON_BOUNDS[1],KOWLOON_BOUNDS[2],-1130).covers(line.buffer(12))
                    west=(props.get('ELEVATION')=='0' or (props.get('ELEVATION')=='1' and name.startswith('CASTLE PEAK ROAD') and line.bounds[2]<TSUEN_WAN_BOUNDS[0])) and props.get('TRAVEL_DIRECTION')!='4' and name not in ('','-99','&lt;Null&gt;','TUEN MUN ROAD','TSUEN WAN ROAD') and not any(s in name for s in ('HIGHWAY','CROSSING','CORRIDOR','FLYOVER','INTERCHANGE')) and west_land.covers(line.buffer(12)) and line.difference(old_kowloon).length>1
                    east=props.get('ELEVATION')=='0' and props.get('TRAVEL_DIRECTION')!='4' and name not in ('','-99','&lt;Null&gt;') and not any(s in name for s in ('HIGHWAY','CROSSING','CORRIDOR','FLYOVER','INTERCHANGE','TUNNEL')) and east_land.covers(line.buffer(12)) and line.difference(old_kowloon).length>1
                    auto_selection=north or west or east or (name in ISLAND_STREETS and island.covers(line.buffer(12)))
                if ident in ids or prior or (auto_selection and not retain_road_inventory):
                    records[ident] = prior if prior else {'type':'Feature','properties':dict(props, source_id=ident, source_sha256=source_hash),
                                      'geometry':{'type':'LineString','coordinates':coords}}
            element.clear()
    assert ids <= records.keys(), 'Source road IDs changed; review the extract before rebuilding.'
    if complete_wong_tai_sin:
        assert set(records)==retained|district_roads, \
            'Wong Tai Sin must add only the reviewed district sections'
    if retain_road_inventory:
        assert set(records)==retained|set(REVIEWED_KOWLOON_TONG_ROADS), \
            'Retained-road mode must preserve prior roads plus only the reviewed Kowloon Tong links'
    assert matched>400, 'Road datum does not agree with the existing map'
    print('ANTILA_ROAD_DATUM_OK:',matched,'shared sections within 2.5 cm; pinned older revisions:',changed)
    original = {i:LineString([local(p) for p in f['geometry']['coordinates']]) for i,f in records.items()}
    for name,members in roundabouts:
        for ident,next_id in zip(members,members[1:]+members[:1]):
            props=records[ident]['properties']
            assert props['ELEVATION']=='0' and props['TRAVEL_DIRECTION']=='3',(name,'Roundabout source access changed')
            assert math.dist(original[ident].coords[-1],original[next_id].coords[0])<.12,(name,'Roundabout source ring is open')
    # Retain only the connected island street component; source coordinates stay unmodified.
    nodes = {}
    for ident,line in original.items():
        for p in (line.coords[0],line.coords[-1]):nodes.setdefault(tuple(round(v,1) for v in p),set()).add(ident)
    assert retained <= records.keys(), 'Previously imported streets must remain present'
    selected=set(ids)|retained;connected=set(selected);pending=list(connected)
    while pending:
        line=original[pending.pop()]
        for p in (line.coords[0],line.coords[-1]):
            for ident in nodes[tuple(round(v,1) for v in p)]-connected:
                connected.add(ident);pending.append(ident)
    deferred_reachable=(connected-selected)&DEFERRED_CONNECTED_ROADS.keys()
    unreviewed=connected-selected-deferred_reachable
    if deferred_reachable:
        print('ANTILA_TUNNEL_REVIEW_DEFERRED: source sections and centreline lengths m:',
              [(ident,*DEFERRED_CONNECTED_ROADS[ident]) for ident in sorted(deferred_reachable)])
    if complete_wong_tai_sin:
        assert district_roads <= connected, 'Reviewed Wong Tai Sin streets must remain connected'
        print('ANTILA_WONG_TAI_SIN_SURFACE_NETWORK:',len(district_roads-retained),'new reviewed sections')
    elif complete_kowloon_city:
        print('ANTILA_KOWLOON_CITY_SURFACE_NETWORK:',len(unreviewed),'connected sections with district and land support')
    elif unreviewed:
        print('ANTILA_TUNNEL_REVIEW_REQUIRED: reachable source sections not explicitly selected:',sorted(unreviewed))
    # Preserve broad connected-road discovery, except sections explicitly deferred by source review.
    connected.difference_update(DEFERRED_CONNECTED_ROADS.keys()-selected)
    # Preserve earlier road order as well as geometry (seeded scenery uses this order).
    records={i:records[i] for i in [f['properties']['source_id'] for f in previous_features]+[i for i in records if i not in retained] if i in connected}
    original={i:original[i] for i in records}
    lines = dict(original)
    # One 3.7 m connector is digitised opposite to this trip, but explicitly permits both directions.
    assert records['ID_026889']['properties']['TRAVEL_DIRECTION']=='1'
    lines['ID_026889'] = LineString(list(lines['ID_026889'].coords)[::-1])
    tube_info = {}
    tubes = []
    for name, members in TUBES:
        length = sum(lines[i].length for i in members)
        assert 1840 < length < 1880, (name,length)
        model_members=RAMPS[name]
        model_length=sum(lines[i].length for i in model_members)
        distance = 0
        for i in model_members:
            tube_info[i] = (distance,model_length)
            distance += lines[i].length
        tubes.append({'name':name,'source_ids':members,'length_m':length,
                      'model_source_ids':model_members,'modeled_length_m':model_length})
    roads = []
    # Source level 1 identifies the deck; smooth authored ramps follow connected road endpoints.
    # ponytail: 7 m deck / 150 m ramps supply bus clearance; replace heights with surveyed levels when available.
    # These Cornwall Street records cross a railway, which Antila does not model.
    # Keep their source level for provenance while representing their road surface at street elevation.
    STREET_LEVEL_RAIL_CROSSINGS={'TD_107934','TD_107935'}
    new_profiles={}
    if whole_wong_tai_sin:
        new_profiles,hammer_hill_height=hammer_hill_deck_profiles(lines)
    adjacent={};ends={};incident={};deck={i for i,r in records.items()
        if r['properties']['ELEVATION']=='1' and i not in STREET_LEVEL_RAIL_CROSSINGS and i not in new_profiles}
    for ident,line in lines.items():
        if ident in tube_info:continue
        a,b=(tuple(round(v,1) for v in p) for p in (line.coords[0],line.coords[-1]));ends[ident]=(a,b)
        incident.setdefault(a,[]).append(ident);incident.setdefault(b,[]).append(ident)
    # Shared junction aprons stay level so diverging ramp surfaces cannot cut into one another.
    wide_junctions={'ID_028222','ID_028228','ID_028221'}
    aprons={}
    for ident,(a,b) in ends.items():
        line=lines[ident];radii=[]
        for side,node in enumerate((a,b)):
            others=[lines[i] for i in incident[node] if i!=ident]
            radius=0
            if len(others)>1 or ident in wide_junctions:
                radius=12
                while radius<line.length and any(line.interpolate(radius if side==0 else line.length-radius).distance(other)<7.5 for other in others):radius+=4
            radii.append(min(radius,line.length))
        aprons[ident]=radii;cost=max(0,line.length-sum(radii))
        adjacent.setdefault(a,[]).append((b,cost));adjacent.setdefault(b,[]).append((a,cost))
    distances={n:0 for ident in deck for n in ends[ident]};queue=[(0,n) for n in distances];heapq.heapify(queue)
    while queue:
        distance,node=heapq.heappop(queue)
        if distance!=distances[node]:continue
        for other,length in adjacent[node]:
            value=distance+length
            if value<150 and value<distances.get(other,math.inf):
                distances[other]=value;heapq.heappush(queue,(value,other))
    def deck_height(ident,d,length):
        if ident in deck:return 7
        a,b=ends[ident];ra,rb=aprons[ident]
        da,db=distances.get(a,math.inf),distances.get(b,math.inf)
        # A short link between two raised junctions must not sag below both endpoints.
        if da<150 and db<150 and length-ra-rb<150:
            ha=7*(1+math.cos(math.pi*da/150))/2;hb=7*(1+math.cos(math.pi*db/150))/2
            t=max(0,min(1,(d-ra)/max(.001,length-ra-rb)))
            return ha+(hb-ha)*(1-math.cos(math.pi*t))/2
        distance=min(distances.get(a,math.inf)+max(0,d-ra),distances.get(b,math.inf)+max(0,length-d-rb))
        return 7*(1+math.cos(math.pi*distance/150))/2 if distance<150 else 0
    for ident,line in lines.items():
        samples = [min(s*4,line.length) for s in range(math.ceil(line.length/4)+1)]
        points = []
        for d in samples:
            x,z = line.interpolate(d).coords[0]
            y = 0
            if ident in tube_info:
                offset,total = tube_info[ident]
                # ponytail: smooth authored depth, replace with surveyed longitudinal levels if obtained.
                y = -32*math.sin(math.pi*(offset+d)/total)
            elif ident in new_profiles:y=hammer_hill_height(ident,d)
            else:y=deck_height(ident,d,line.length)
            points.append([round(x,4),round(y,4),round(z,4)])
        elevated=any(p[1]>.01 for p in points)
        # Author single-lane widths from measured source spacing and bus clearance.
        width=SINGLE_LANE_WIDTHS.get(ident,12 if ident in wide_junctions else 6 if elevated else 12)
        if whole_wong_tai_sin and ident in WONG_TAI_SIN_NARROW_CARRIAGEWAYS:
            assert records[ident]['properties']['TRAVEL_DIRECTION']=='3', (ident,'Narrow carriageway must be one-way')
            width=WONG_TAI_SIN_NARROW_CARRIAGEWAYS[ident]
        roads.append({'id':ident,'name':records[ident]['properties']['STREET_ENAME'],
                      'tunnel':ident in tube_info,'ramp':ident in ('ID_024204','ID_024201'),
                      'elevated':elevated,'source_level':int(records[ident]['properties']['ELEVATION']),
                      'width':9.1 if ident in tube_info else width,
                      'points':points})
    migrated_merge=False
    if complete_kowloon_city:
        # New branches must not refit the geometry or authored grades of earlier drives.
        previous_map=json.loads((ROOT/'Data/cross-harbour.json').read_text())
        prior_roads={r['id']:r for r in previous_map['roads']}
        if complete_wong_tai_sin:
            if whole_wong_tai_sin:
                prior_decks=previous_map['metadata'].get('wong_tai_sin_decks')
                if prior_decks!=previous['metadata'].get('wong_tai_sin_decks'):
                    raise ValueError('Road and source snapshots disagree about the Hammer Hill merge')
                migrated_merge=migrate_hammer_hill_merge(roads,prior_roads,prior_decks,lines)
            refresh=HAMMER_HILL_MERGE_ROADS if migrated_merge else set()
            roads=[r if r['id'] in refresh else prior_roads.get(r['id'],r) for r in roads]
        else:
            prior_route_ids={ident.lstrip('-') for route in previous_map['routes'][:14] for ident in route['source_ids']}
            # Shing Fung Road gains a surveyed relative-level deck, so its approaches need authored grades.
            roads=[r if r['name']=='SHING FUNG ROAD' and r['id'] not in prior_route_ids else prior_roads.get(r['id'],r) for r in roads]
    by_id = {r['id']:r for r in roads}
    if complete_kowloon_city and CHI_MAN_STREET_ID in by_id:
        by_id[CHI_MAN_STREET_ID]['width'] = CHI_MAN_STREET_WIDTH
    if whole_wong_tai_sin:
        for members in (CHOI_HUNG_SIDE_LOOP,HAMMER_HILL_WEST_EXIT,HAMMER_HILL_EAST_ENTRY,LUNG_CHEUNG_UNDERPASS):
            previous_end=None
            for member in members:
                ident=member.lstrip('-')
                reverse=member.startswith('-')
                direction=records[ident]['properties']['TRAVEL_DIRECTION']
                assert direction in (('1','2') if reverse else ('1','3')), (member,'Source direction changed')
                points=by_id[ident]['points']
                start,end=(points[-1],points[0]) if reverse else (points[0],points[-1])
                assert previous_end is None or math.dist(previous_end,start)<.12, \
                    (member,'Reviewed junction must join continuously')
                previous_end=end
    routes = []
    itineraries=[('Hung Hom → Hong Kong Island',SOUTH),('Wan Chai return loop',ISLAND),('Hong Kong Island → Kowloon',NORTH),('Wan Chai / Causeway Bay scenic drive',SCENIC),('Admiralty / Central loop',CENTRAL),('Jordan → Yau Ma Tei → Mong Kok',KOWLOON),('West Kowloon → Tai Kok Tsui → Sham Shui Po',WEST),('Mong Kok → Sham Shui Po',SHAM_SHUI_PO),('Sham Shui Po → Cheung Sha Wan → Lai Chi Kok',LAI_CHI_KOK),('Mei Foo → Lai King → Kwai Chung',KWAI_CHUNG),('Kwai Chung → Tsuen Wan',TSUEN_WAN),('Tsuen Wan → Ting Kau → Sham Tseng',WEST_COAST),('Hung Hom → Whampoa → To Kwa Wan → Kowloon City',EAST_KOWLOON),('Kowloon City → Wong Tai Sin',WONG_TAI_SIN)]
    if include_kai_tak:
        itineraries.append(('Kai Tak → Kai Tak Cruise Terminal',KAI_TAK))
    if complete_wong_tai_sin:
        itineraries.append(('Wong Tai Sin → Diamond Hill',DIAMOND_HILL))
    if whole_wong_tai_sin:
        itineraries.append(('Choi Hung → Hammer Hill',CHOI_HUNG_TO_HAMMER_HILL))
    for name,members in itineraries:
        points = []
        check_direction=members in (WEST,SHAM_SHUI_PO,LAI_CHI_KOK,KWAI_CHUNG,TSUEN_WAN,WEST_COAST,EAST_KOWLOON,WONG_TAI_SIN,KAI_TAK,DIAMOND_HILL,CHOI_HUNG_TO_HAMMER_HILL)
        for ident in members:
            reverse=ident.startswith('-');ident=ident.lstrip('-')
            p = by_id[ident]['points']
            if check_direction:
                assert records[ident]['properties']['TRAVEL_DIRECTION'] in (('1','2') if reverse else ('1','3')), 'New drive violates source travel direction'
            if reverse:
                assert records[ident]['properties']['TRAVEL_DIRECTION'] in ('1','2'), 'Source direction forbids reversing this section'
                # ID_026889 is already reversed for the original island route.
                if ident!='ID_026889':p=p[::-1]
            assert not points or math.dist(points[-1],p[0]) < .12, (name,ident,'gap')
            points.extend(p if not points else p[1:])
        routes.append({'name':name,'source_ids':members,'points':points})
        if check_direction:
            for a,b,c in zip(points,points[1:],points[2:]):
                dot=sum((b[i]-a[i])*(c[i]-b[i]) for i in range(3))/(math.dist(a,b)*math.dist(b,c))
                assert dot>-.5, (name,'Drive turns back sharply; choose a continuous source route')
    assert math.dist(routes[4]['points'][0],routes[4]['points'][-1])<.12, 'Central loop must close'
    if complete_wong_tai_sin:
        prior_routes=previous_map['routes']
        if migrated_merge:
            earlier_choi_hung=[point for i,ident in enumerate(CHOI_HUNG_TO_HAMMER_HILL)
                               for point in prior_roads[ident]['points'][bool(i):]]
            if len(prior_routes)!=17 or prior_routes[16]!=dict(routes[16],points=earlier_choi_hung):
                raise ValueError('The existing Choi Hung itinerary differs from the reviewed pre-apron route')
            prior_routes=prior_routes[:16]
        assert routes[:len(prior_routes)]==prior_routes, 'Wong Tai Sin must preserve earlier drives'
        assert routes[15]['points'][0]==routes[13]['points'][-1], 'Diamond Hill must join the Wong Tai Sin drive'
    for a,b in zip(routes[:3],routes[1:3]):
        assert math.dist(a['points'][-1],b['points'][0]) < .02, 'Gap between crossing and return loop'
    # Cut only open portals out of the old ground. Deep tunnel sections pass below intact streets.
    cutouts = []
    for members in RAMPS.values():
        points = [p for i,ident in enumerate(members) for p in by_id[ident]['points'][0 if i==0 else 1:]]
        run = []
        for a,b in zip(points,points[1:]):
            if max(a[1],b[1]) > -7:
                if not run:run.append((a[0],a[2]))
                run.append((b[0],b[2]))
            elif run:
                cutouts.append(LineString(run).buffer(5.4,cap_style=2));run=[]
        if run:cutouts.append(LineString(run).buffer(5.4,cap_style=2))
    bounds = district_data['bounds']
    # Keep the established inland base, but replace its unsupported waterfront apron from source coast.
    district = box(bounds[0]-110,bounds[1]-130,bounds[2]+110,bounds[3]+120)
    tst_site_path=ROOT/'Data/tst-shoreline-source.geojson'
    tst_site_data=json.loads(tst_site_path.read_text())
    east_shoreline=east_shoreline_data['features']
    west_shoreline=json.loads((ROOT/'Data/west-kowloon-shoreline.geojson').read_text())['features']
    tst_site_land,tst_water_cut,tst_frontier,tst_east_cut=build_tst_shoreline_geometry(
        district,east_land,tst_site_data['features'],east_shoreline,west_shoreline)
    kowloon=unary_union([district,box(*KOWLOON_BOUNDS),west_land,east_land]).difference(tst_water_cut)
    kowloon=unary_union([kowloon,tst_site_land])
    southwest_water_cut,southwest_support,museum_water,southwest_decks,southwest_shoreline_data,southwest_water_path,southwest_shoreline_path,southwest_building_path,southwest_site_path=southwest_support_and_water(kowloon,tst_site_land)
    kowloon=unary_union([kowloon.difference(southwest_water_cut),southwest_support,tst_site_land])
    assert kowloon.is_valid and kowloon.geom_type in ('Polygon','MultiPolygon'), 'Corrected mainland geometry is invalid'
    island_geometry=island
    land = unary_union([kowloon,island_geometry])
    for road in roads:
        if not road['tunnel']:
            carriageway=LineString([(p[0],p[2]) for p in road['points']]).buffer(road['width']/2)
            assert carriageway.difference(land).area<.01, (road['id'],road['name'],'carriageway outside land')
    # Flat cutout ends must meet the tunnel floors without extending past their endpoints.
    ground = land.difference(unary_union(cutouts))
    for street in district_data['side_roads']:
        assert ground.covers(LineString(street['points']).buffer(9)), (street['name'],'portal cut breaks the existing street')
    water = box(WEST_COAST_BOUNDS[0]-500,WEST_COAST_BOUNDS[1]-250,east_bounds[2]+500,2350).difference(land)
    water_triangles = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(water).geoms]
    for road in roads:
        for x,y,z in road['points']:
            if road['tunnel'] and -6.5 < y < -1:
                assert ground.distance(Point(x,z)) > 4.5, 'Ground crosses a portal opening'
    surface = unary_union([LineString([(p[0],p[2]) for p in r['points']]).buffer(r['width']/2) for r in roads if not r['tunnel'] and not r['elevated']]).difference(unary_union(cutouts))
    surface_triangles = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(surface).geoms]
    ground_triangles = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(ground).geoms]
    deck_paving = southwest_decks.intersection(ground)
    deck_faces = list(constrained_delaunay_triangles(deck_paving).geoms)
    assert deck_paving.is_valid and deck_paving.area>0 and abs(sum(t.area for t in deck_faces)-deck_paving.area)<.01, \
        'Surveyed deck paving triangulation is empty, invalid or incomplete'
    harbour_paving_triangles = [list(t.exterior.coords)[:3] for t in deck_faces]
    assert abs(sum(abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2 for a,b,c in ground_triangles)-ground.area)<.01
    metadata = {'provider':'Transport Department, HKSAR Government','source':SOURCE,
        'source_sha256':source_hash,
        'retrieved_utc':previous['metadata']['retrieved_utc'] if previous['metadata']['source_sha256']==source_hash else datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'processed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'origin_wgs84':ORIGIN,
        'source_crs':'EPSG:4611' if transform else 'EPSG:4326',
        'retained_source_sha256':previous['metadata'].get('retained_source_sha256',previous['metadata']['source_sha256']),
        'coordinate_processing':'New roads: HK1980 geographic to WGS84 (EPSG:4611 to EPSG:4326). Existing roads pinned by stable ROUTE_ID to the retained source snapshot; over 400 shared sections validate the datum within 2.5 cm. Connected endpoints checked after conversion.' if transform else 'WGS84 coordinates used directly',
        'terms':'https://data.gov.hk/en/terms-and-conditions', 'world_units_per_metre':1,
        'dictionary':'https://static.data.gov.hk/td/road-network-v2/dataspec/rdnet_dataspec.zip',
        'tunnel_reference':'https://www.td.gov.hk/en/transport_in_hong_kong/tunnels_and_bridges_n/location_map/index_t.html',
        'tst_shoreline_source_sha256':hashlib.sha256(tst_site_path.read_bytes()).hexdigest(),
        'southwest_water_source_sha256':hashlib.sha256(southwest_water_path.read_bytes()).hexdigest(),
        'southwest_shoreline_source_sha256':hashlib.sha256(southwest_shoreline_path.read_bytes()).hexdigest(),
        'southwest_building_source_sha256':hashlib.sha256(southwest_building_path.read_bytes()).hexdigest(),
        'southwest_cultural_site_source_sha256':hashlib.sha256(southwest_site_path.read_bytes()).hexdigest(),
        'southwest_cultural_site_source':'Data/southwest-public-spaces-source.geojson',
        'southwest_edit_bounds':list(SOUTHWEST_EDIT_BOUNDS),
        'southwest_chart_gap_bounds':list(SOUTHWEST_CHART_GAP_BOUNDS),
        'southwest_promenade_bounds':list(SOUTHWEST_PROMENADE_BOUNDS),
        'museum_water_bounds':list(MUSEUM_WATER_BOUNDS),
        'southwest_water_correction_area_m2':round(southwest_water_cut.area,3),
        'southwest_water_correction_bounds':list(southwest_water_cut.bounds),
        'southwest_source_support_area_m2':round(southwest_support.area,3),
        'note':'Original XY preserved in approximate local metre coordinates. ELEVATION is a relative road level, not metres. Road widths are authored: 6 m for elevated carriageways, 12 m for broad roads including the low Hung Hing / Tonnochy approach, 3.2 m for TD_103438 and 3.0 m for TD_103954, based on source spacing and analytic bus clearance; widths are not surveyed. Tunnel depth 32 m, 5.6 m interior and 7 m elevated decks with cosine ramps over 150 m outside shared level junction aprons are authored. Aprons extend until adjoining centreline branches separate by 7.5 m. Shorelines derive from LandsD iB1000 with recorded gap repairs; the TST apron is bounded by SWA 1101166493 and the joined Site 1503005628 frontage, with source Site footprints retained. The southwest water cut follows georeferenced LandsD KN12/KN13 water fills clipped to legacy ground and edit bounds; a source-free connector through the reviewed offshore gap is clipped to legacy ground and excludes all iB1000 support, with no wall emitted on its edge. iB1000 JPW/FFL decks, building footprints, non-water Site 1503005422 and the charted public promenade beyond the Site are retained. Turn restrictions are not inferred.'}
    # Enclose the joined mainland, including the retained TST apron. Its old district
    # rectangle is now internal; source seawalls below replace only coincident edges.
    border=kowloon.boundary
    shore=unary_union([*[LineString(p) for p in coast_data['coastline']],
        unary_union([LineString(p) for p in northwest_coast['coastline']]).difference(box(*WEST_BOUNDS)),
        unary_union([LineString(p) for p in kwai_chung_coast['coastline']]).difference(prior_region),
        unary_union([LineString(p) for p in tsuen_wan_coast['coastline']]).difference(kwai_region),
        unary_union([LineString(p) for p in west_coast['coastline']]).difference(tsuen_region),
        unary_union([LineString(p) for p in east_coast['coastline']]).difference(unary_union([west_land,box(*KOWLOON_BOUNDS)]))]).difference(district.buffer(.1)).difference(unary_union(cutouts).buffer(1))
    southwest_swa=[]
    museum_swa=[]
    southwest_window=box(*SOUTHWEST_EDIT_BOUNDS)
    museum_window=box(*MUSEUM_WATER_BOUNDS)
    for feature in southwest_shoreline_data['features']:
        if feature['properties'].get('source_type')!='SWA':
            continue
        line=southwest_source_geometry(shape(feature['geometry']))
        if line.intersects(museum_window):
            museum_swa.append(line.intersection(museum_window))
        if line.intersects(southwest_window.buffer(50)):
            southwest_swa.append(line.difference(museum_window))
    # Snap the surveyed museum wall to the shared game terrain edge through the chart seam.
    museum_wall=border.intersection(museum_water.boundary).intersection(unary_union(museum_swa).buffer(.5))
    shore=unary_union([shore,tst_frontier,*southwest_swa,museum_wall]).difference(unary_union(cutouts).buffer(1))
    def line_parts(g):
        return [list(p.coords) for p in (g.geoms if hasattr(g,'geoms') else [g]) if p.geom_type=='LineString' and p.length>.5]
    if complete_kowloon_city:
        metadata['kowloon_city_district_boundary_sha256']=hashlib.sha256(district_boundary_path.read_bytes()).hexdigest()
        metadata['kowloon_city_deferred_roads']=KOWLOON_CITY_DEFERRED_ROADS
        metadata['kowloon_city_north_fill']={
            'bounds':list(KOWLOON_CITY_NORTH_FILL_BOUNDS),
            'area_m2':north_fill.area,
            'source':mainland_source['metadata']['source'],
            'response_sha256':mainland_source['metadata']['response_sha256'],
        }
    if complete_wong_tai_sin:
        metadata['wong_tai_sin_district_boundary_sha256']=hashlib.sha256(boundary_source).hexdigest()
        metadata['wong_tai_sin_deferred_roads']=sorted(wong_tai_sin_deferred)
    if whole_wong_tai_sin:
        metadata['wong_tai_sin_network_sections']=sorted(WONG_TAI_SIN_NETWORK_ROADS-WONG_TAI_SIN_DISTRICT_ROADS)
        metadata['wong_tai_sin_decks']={
            'source_ids':sorted(HAMMER_HILL_DECKS),'authored_height_m':7,'merge':HAMMER_HILL_MERGE,
            'westbound_exit':HAMMER_HILL_WEST_EXIT,'eastbound_entry':HAMMER_HILL_EAST_ENTRY,
        }
    output = {'metadata':metadata,'bounds':[WEST_COAST_BOUNDS[0]-80,WEST_COAST_BOUNDS[1]-80,east_bounds[2]+80,ISLAND_BOUNDS[3]+50], 'island_bounds':ISLAND_BOUNDS, 'kowloon_north_bounds':KOWLOON_BOUNDS,
              'island_land':island_coast['land'],'island_coastline':line_parts(unary_union([LineString(p) for p in island_coast['coastline']]).difference(unary_union(cutouts).buffer(1))),
              'island_boundary':line_parts(island.boundary.intersection(box(*ISLAND_BOUNDS).boundary)), 'island_coast_metadata':island_coast['metadata'],
              'kowloon_east_land':mapping(east_land),'east_kowloon_bounds':east_bounds,'east_coast_metadata':east_coast['metadata'],
              'kowloon_west_land':mapping(west_land),'kowloon_coastline':line_parts(shore),'kowloon_boundary':line_parts(border.difference(shore.buffer(.3)).difference(southwest_water_cut.boundary.buffer(.3))), 'coast_metadata':coast_data['metadata'],
              'kowloon_northwest_bounds':NORTHWEST_BOUNDS,'northwest_coast_metadata':northwest_coast['metadata'],'kwai_chung_bounds':KWAI_CHUNG_BOUNDS,'kwai_chung_coast_metadata':kwai_chung_coast['metadata'],
              'tsuen_wan_bounds':TSUEN_WAN_BOUNDS,'tsuen_wan_coast_metadata':tsuen_wan_coast['metadata'],
              'west_coast_bounds':WEST_COAST_BOUNDS,'west_coast_metadata':west_coast['metadata'],'roads':roads,
              'routes':routes,'tubes':tubes,'ground_triangles':ground_triangles,'water_triangles':water_triangles,'surface_triangles':surface_triangles,
              'harbour_paving_triangles':harbour_paving_triangles}
    payloads=[(ROOT/'Data/cross-harbour-source.geojson',json.dumps({'type':'FeatureCollection','metadata':metadata,'features':list(records.values())},ensure_ascii=False,separators=(',',':'),allow_nan=False)),
              (ROOT/'Data/cross-harbour.json',json.dumps(output,ensure_ascii=False,separators=(',',':'),allow_nan=False)),
              (ROOT/'Data/cross-harbour-runtime.json',encode_runtime_harbour(output))]
    staged=[]
    try:
        for target,payload in payloads:
            with tempfile.NamedTemporaryFile(dir=target.parent,prefix=target.name+'.',suffix='.part',delete=False) as stream:
                stream.write(payload.encode('utf-8'));staged.append(Path(stream.name))
        for temp,(target,_) in zip(staged,payloads):temp.replace(target)
    finally:
        for temp in staged:temp.unlink(missing_ok=True)
    print('ANTILA_TUNNEL_DATA_OK:',len(roads),'source sections;',[(t['name'],round(t['length_m'],1)) for t in tubes],'; continuous routes',len(routes))
    if retain_road_inventory:
        print('ANTILA_ROAD_INVENTORY_RETAINED:',len(records),'source sections')


if __name__ == '__main__':
    build(Path(sys.argv[1]),retain_road_inventory='--retain-road-inventory' in sys.argv[2:],
          complete_kowloon_city='--kowloon-city-district' in sys.argv[2:],
          complete_wong_tai_sin='--wong-tai-sin-district' in sys.argv[2:],
          whole_wong_tai_sin='--whole-wong-tai-sin-district' in sys.argv[2:])
