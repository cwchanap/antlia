"""Refresh the reviewed Kowloon, Wong Tai Sin and western New Territories sites from iB1000 sheets.

Offline rebuild: .venv-geodata/bin/python Tools/import_east_open_spaces.py
Verified source refresh: --extract CACHE_DIR TILE_MANIFEST_JSON. Downloads are staged separately.
"""
import hashlib
import json
import math
import random
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely import constrained_delaunay_triangles, make_valid, union_all
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import nearest_points, polylabel

from import_buildings import LANDMARK_LAYOUT_IDS, WIDE
from import_map import ORIGIN, ROOT, local
from import_open_spaces import encoded, replace_outputs

SOURCE = ROOT / 'Data/east-kowloon-open-spaces-source.geojson'
KOWLOON_CITY_SOURCE = ROOT / 'Data/kowloon-city-open-spaces-source.geojson'
TARGET = ROOT / 'Data/east-kowloon-open-spaces.json'
SITES = {
    '1503005871': 'Hutchison Park', '1503005901': 'Tai Wan Shan Park',
    '1503005881': 'Hoi Sham Park', '1503005751': 'Ko Shan Road Park',
    '1503005870': 'To Kwa Wan Recreation Ground', '1503005863': 'Kowloon Walled City Park',
    '1503005866': 'Carpenter Road Park', '1503005714': 'Kowloon Tsai Park',
    '1910071209': 'Hung Hom Harbourfront', '1503005853': 'Morse Park',
    '1503005716': 'Junction Road Park', '1503005939': 'Choi Hung Road Playground',
    '1503005718': 'Lion Rock Park', '1910059822': 'Diamond Hill Water Feature Park',
    '1503005810': 'Ma Chai Hang Recreation Ground', '1503005961': 'Fung Tak Park',
    '1910064509': 'Hoi Fan Road Park', '1503000381': 'Central Kwai Chung Park',
    '1503005413': 'Shek Kip Mei Park', '1503000390': 'Lai Chi Kok Park',
    '1503005076': 'Nam Cheong Park', '1503000414': 'Shing Mun Valley Park',
    '1910069198': 'Kwai Chung Park', '1503000199': 'Tsuen Wan Park',
    '1810011761': 'Tsuen Wan Riviera Park',
    '1910053970': 'West Kowloon Art Park', '1910053968': 'West Kowloon Waterfront Promenade',
    '1503005535': 'Signal Hill Garden', '1503005281': 'King George V Memorial Park',
    '1810014504': "King's Park Rest Garden", '1810044652': 'Man Cheong Street Park',
    '1503005514': "King's Park Recreation Ground", '1910056230': 'Hoi Fai Road Park',
    '1810032161': 'Hoi Fai Road Promenade', '1910062401': 'Hoi Fai Road Playable Space',
    '1503005115': 'Lok Kwan Street Park', '1503005152': 'Sycamore Playground',
    '1503005112': 'Tung Chau Street Park', '1503005184': 'Maple Street Playground',
    '1503005071': 'Sham Shui Po Park', '1503005077': 'Sham Shui Po Park Stage 2',
    '1503005508': 'Cornwall Street Park',
    '1503005450': 'Tai Hang Tung Recreation Ground',
    '1503005180': 'Nam Cheong Street Sitting-out Area No. 1',
    '1503005170': 'Nam Cheong Street Sitting-out Area No. 2',
    '1503005157': 'Nam Cheong Street Sitting-out Area No. 3',
    '1503005144': 'Nam Cheong Street Sitting-out Area No. 4',
    '1503005135': 'Nam Cheong Street Sitting-out Area No. 5',
    '1503005123': 'Nam Cheong Street Sitting-out Area No. 6',
    '1810015202': 'Salisbury Garden', '1503005628': 'Tsim Sha Tsui Promenade',
    '1503005539': 'To Yuen Street Playground',
    '1503005553': 'Kent Road Garden',
    '1503005688': 'Kam Shing Road Recreation Ground',
    '1503005627': "Cornwall Street Children's Playground",
    '1503005605': 'Cornwall Street/Ede Road Garden',
    '1502005648': 'Dorset Crescent Rest Garden'
}
SITE_BOUNDS = {
    '1503005871': [1826.7959910512027, -1521.0092856069375, 1997.8916879763524, -1306.9636430950327],
    '1503005901': [2037.6486812819355, -1278.063228570602, 2173.1167578527516, -1175.2341889791328],
    '1503005881': [1871.9432176891537, -2313.0317466918095, 2098.9824712245095, -1907.50746359212],
    '1503005751': [1150.5355297886654, -2311.348484227767, 1488.8607329272077, -1980.592032698378],
    '1503005870': [1776.6033510928078, -2791.75414020496, 1989.0173508778378, -2584.594445656426],
    '1503005863': [1713.639059908951, -4257.891011711707, 1980.2293124785942, -4037.4259302626224],
    '1503005866': [1532.3517004685953, -4161.18955329226, 2063.6765085864463, -3965.8787816273525],
    '1503005714': [1017.1909054534431, -4443.349740243774, 1358.1608900809742, -3849.1581288892426],
    '1910071209': [996.1195523483505, -509.6529589592727, 1104.5937895171367, -250.0385285930514],
    '1503005853': [1760.3173751329005, -5119.457393558613, 2288.845400516954, -4427.280784936417],
    '1503005716': [1111.5256304827312, -4950.948383086019, 1362.970881793604, -4737.835897821695],
    '1503005939': [2383.6107490413233, -4923.582929906242, 2702.2700728422237, -4616.948406871777],
    '1503005718': [970.8043299925458, -5773.7397669791135, 1328.0121736031258, -5398.5069190814365],
    '1910059822': [2677.233575864375, -5076.5110562881055, 3118.7957031399997, -4844.495887636024],
    '1503005810': [1596.190587643832, -5569.804171876455, 1779.3897064693133, -5405.642652004627],
    '1503005961': [2579.047443432498, -5372.188813796862, 2689.693166883958, -5229.831197913318],
    '1910064509': [-1732.3521805766952, -3082.8655755309037, -1595.4998534662866, -2860.294866206161],
    '1503000381': [-4224.798083177408, -7272.529653382138, -3844.879898541535, -6308.095521732379],
    '1503005413': [-377.5248763264252, -4941.30469055476, -58.370218496456424, -4328.298200843563],
    '1503000390': [-3848.078468328502, -5148.89470854557, -3078.5897515369866, -4167.693809688551],
    '1503005076': [-1734.542226475257, -3399.3829735405134, -1385.123684107868, -3024.9134984630628],
    '1503000414': [-4962.622008269732, -9275.338028197904, -4251.971198185875, -8693.337462672245],
    '1910069198': [-5738.491640333387, -6589.061843381081, -5436.021150340948, -6399.916456318958],
    '1503000199': [-6528.625296719309, -8184.949144270538, -5964.900747322041, -7708.218422287199],
    '1810011761': [-6275.605829581109, -7799.665424696743, -6056.081895757306, -7284.462980134114],
    '1910053970': [-1831.0353809512374, -709.5238493750487, -1309.2104412691604, -418.2179236684354],
    '1910053968': [-1844.9970041881563, -779.2609975340628, -1385.0293145235157, -412.86686047887343],
    '1503005535': [145.52016642531788, -177.0681259898693, 298.7952849282159, -76.28345295586243],
    '1503005281': [-522.6205778570213, -1192.990912212117, -332.0936352142512, -979.7224756516015],
    '1810014504': [-113.5994242313828, -2093.2157491966536, 262.1135745788614, -1697.527859509935],
    '1810044652': [-714.2778014037433, -1545.1126765177023, -493.3505960595956, -1467.5739388310212],
    '1503005514': [51.23933942903191, -1823.6672282809404, 230.3236804541109, -1655.4714192484646],
    '1910056230': [-1789.642927451708, -2504.886635238703, -1580.0835295479185, -2431.2678908980406],
    '1810032161': [-1554.1739178593814, -2456.1283240504367, -1306.6522404973896, -2379.672410957372],
    '1910062401': [-1363.0572002526908, -2451.042414745998, -1288.7521186363074, -2382.426637521099],
    '1503005115': [-1274.1720652979172, -3237.2806001490662, -1172.5071260522582, -3139.8277085772716],
    '1503005152': [-1017.8655269765485, -3340.365202545591, -894.8959111937979, -3239.243753954827],
    '1810015202': [-16.222274335771317, 46.34833773822592, 107.6766580037026, 187.49272546624837],
    '1503005628': [47.097204680243934, -563.1437743563861, 1497.657196720194, 234.52322778670478],
    '1503005112': [-1588.0, -3665.0, -1155.0, -3307.0],
    '1503005184': [-755.5, -3707.5, -666.5, -3576.5],
    '1503005071': [-1767.5, -4082.0, -1493.5, -3822.0],
    '1503005077': [-1574.0, -4229.5, -1444.5, -4104.5],
    '1503005508': [-34.684, -5001.113, 291.41, -4727.462],
    '1503005450': [-229.0, -3824.0, -33.0, -3535.0],
    '1503005180': [-800.5, -4006.0, -765.5, -3967.0],
    '1503005170': [-882.0, -3960.0, -803.5, -3867.5],
    '1503005157': [-964.5, -3849.0, -895.5, -3769.5],
    '1503005144': [-1022.0, -3755.5, -972.5, -3700.0],
    '1503005135': [-1074.5, -3672.0, -1042.0, -3635.5],
    '1503005123': [-1164.5, -3565.0, -1131.0, -3527.5],
    '1503005539': [123.13099230492396, -4507.785661290719, 311.5588637507497, -4372.92891861463],
    '1503005553': [274.28299674953536, -4976.053088604485, 356.76591380939664, -4842.823513774506],
    '1503005688': [888.7075355264844, -4971.8356200062335, 957.0683793298907, -4923.595133201732],
    '1503005627': [565.2197060929971, -4999.5485865793025, 647.1870113841206, -4912.513075648936],
    '1503005605': [521.3739568407511, -5084.048885132747, 562.6412497623163, -5042.671667403392],
    '1502005648': [531.8485767517519, -4901.547815149071, 572.3166904735032, -4864.117693043855]
}
SITE_AREAS = {
    '1503005870': 24129.94, '1503005866': 57783.76, '1503005714': 151727.3,
    '1503005863': 30698.27, '1503005901': 9752.8, '1503005871': 24977.52,
    '1910071209': 13430.51, '1503005751': 51213.79, '1503005881': 32665.73,
    '1503005853': 138311.6389966884, '1503005716': 34258.67063764957,
    '1503005939': 40047.64332197038, '1503005718': 63997.520086180004,
    '1910059822': 28530.14636659569, '1503005810': 20193.488710215668,
    '1503005961': 10929.43612446799,
    '1910064509': 16418.810903934194, '1503000381': 105755.54982705388,
    '1503005413': 79801.42638753576, '1503000390': 221549.941513457,
    '1503005076': 47091.25146438434, '1503000414': 150237.2351947325,
    '1910069198': 15853.528033861303, '1503000199': 69395.69676229537,
    '1810011761': 43016.26394057317,
    '1910053970': 99677.2820046619,
    '1910053968': 6432.290492387278,
    '1503005535': 11547.961327522948, '1503005281': 13586.283568312276,
    '1810014504': 36266.53750994386, '1810044652': 10427.386024104726,
    '1503005514': 18393.355258367916, '1910056230': 9224.006733543949,
    '1810032161': 4319.435964020405, '1910062401': 1277.1171287110856,
    '1503005115': 9353.440140114008, '1503005152': 6204.625105055409,
    '1810015202': 11576.070459787783, '1503005628': 22131.935354565583,
    '1503005112': 44882.37, '1503005184': 7404.41,
    '1503005071': 29806.73, '1503005077': 8728.01,
    '1503005508': 23984.65,
    '1503005450': 46914.57, '1503005180': 464.88,
    '1503005170': 1301.54, '1503005157': 1093.88,
    '1503005144': 723.40, '1503005135': 356.09,
    '1503005123': 377.91,
    '1503005539': 6059.90, '1503005553': 4838.52,
    '1503005688': 1694.16, '1503005627': 5343.39,
    '1503005605': 404.36, '1502005648': 594.10
}
GROUND_SCOPE_SITE_IDS = frozenset({'1810015202', '1503005628', '1503005508'})
SIDE_ROAD_SITE_IDS = frozenset({
    '1503005535', '1503005281', '1810015202', '1503005628'
})
SIT_OUT_SITE_IDS = frozenset({
    '1503005180', '1503005170', '1503005157', '1503005144', '1503005135', '1503005123'
})
COMPACT_PLAZA_SITE_IDS = frozenset({'1503005605', '1502005648'})
SIT_OUT_BENCH_POSITIONS = {
    '1503005180': ((-771.5, -4000.5), 1),
    '1503005170': ((-856.25, -3897), 1),
    '1503005157': ((-958.25, -3775.25), 1),
    '1503005144': ((-979, -3750), 1),
    '1503005135': ((-1062.6, -3649.3), .9),
    '1503005123': ((-1159.5, -3532.2), .8),
}
SITE_WITHOUT_FIXTURE_REQUIREMENT = frozenset({
    '1910062401', '1503005184', '1503005077', '1503005688', '1502005648'
}) | SIT_OUT_SITE_IDS
SHORELINE = json.loads((ROOT / 'Data/east-kowloon-shoreline.geojson').read_text())['metadata']
INDEX_URL = SHORELINE['source']
# The official iB1000 query extends north beyond the current terrain coast bounds.
BBOX = (114.1, 22.295, 114.204, 22.38)
CACHE = Path('/tmp/antila-west-kowloon-2026-11-17/tiles')
INDEX_RESPONSE = ROOT / 'Data/kowloon-open-spaces-index.json'
INDEX_SHA256 = 'de172d2216a2c0d9a7d67979a03e133019348096b3c8b159a0f13f55e4332667'
COAST_FILES = (
    ROOT / 'Data/east-kowloon-coast.json', ROOT / 'Data/west-kowloon-coast.json',
    ROOT / 'Data/lai-chi-kok-coast.json', ROOT / 'Data/kwai-chung-coast.json',
    ROOT / 'Data/tsuen-wan-coast.json'
)
NS = {'g': 'http://www.opengis.net/gml', 'f': 'http://www.safe.com/gml/fme'}
LAYERS = ('Site', 'BuiltStructurePolygon')
KINDS = {'FOF': 'field', 'BAC': 'court', 'TEC': 'court', 'RAT': 'track'}
EXPECTED_SPORT_FRAGMENTS = {
    '1500001706': ('11-NE-21A', '11-NE-21C'),
    '1500004972': ('11-NE-21C',), '1500004971': ('11-NE-21C',),
    '1910087164': ('11-NE-16C',), '1910087165': ('11-NE-16C',),
    '1910087166': ('11-NE-16C',), '1910087167': ('11-NE-16C',),
    '1500001704': ('11-NE-16C',), '1500001702': ('11-NE-16C',),
    '1500001703': ('11-NE-16C',), '1500002363': ('11-NW-20D',),
    '1500001700': ('11-NE-16A',), '1500001701': ('11-NE-16A',),
    '1500001698': ('11-NE-16A',), '1500001699': ('11-NE-16A',),
    '1500001652': ('11-NE-11A',), '1500001648': ('11-NE-11A',),
    '1500001649': ('11-NE-11A',), '1500001650': ('11-NE-11A',),
    '1500001651': ('11-NE-11A',), '1810060612': ('11-NW-15B',),
    '1500001950': ('11-NW-10D', '11-NW-15B'),
    '1500001887': ('11-NW-15B',),
    '1500001948': ('11-NW-10D', '11-NW-15B'),
    '1500001949': ('11-NW-10D', '11-NW-15B'),
    '1500001881': ('11-NW-15B',), '1500001883': ('11-NW-15B',),
    '1500001874': ('11-NW-15B',),
    '1500001891': ('11-NW-10D',), '1500001892': ('11-NW-10D',),
    '1500001893': ('11-NW-10D',), '1500001894': ('11-NW-10D',),
    '1500001896': ('11-NW-10D',), '1500001897': ('11-NW-10D',),
    '1500001898': ('11-NW-10D',), '1500001899': ('11-NW-10D',),
    '1500001900': ('11-NW-10D',), '1500001901': ('11-NW-10D',),
    '1910085624': ('11-NE-1C', '11-NE-6A', '11-NW-10B', '11-NW-5D'),
    '1810000218': ('11-NE-6A', '11-NE-6C'),
    '1500001593': ('11-NE-6A',), '1500001585': ('11-NE-6A',),
    '1500001584': ('11-NE-6A',), '1500001583': ('11-NE-6A',),
    '1910084728': ('11-NE-6C',), '1810000220': ('11-NE-6C',),
    '1810000219': ('11-NE-6C',), '1810000217': ('11-NE-6C',),
    '1810000193': ('11-NE-6C',), '1500001608': ('11-NE-6C',),
    '1500001607': ('11-NE-6C',), '1500001606': ('11-NE-6C',),
    '1500001605': ('11-NE-6C',), '1500001604': ('11-NE-6C',),
    '1500001603': ('11-NE-6C',),
    '1500001622': ('11-NE-6B', '11-NE-6D'),
    '1500001621': ('11-NE-6B', '11-NE-6D'),
    '1500004960': ('11-NE-6D',), '1500004959': ('11-NE-6D',),
    '1500001618': ('11-NE-6D',), '1500001617': ('11-NE-6D',),
    '1500001616': ('11-NE-6D',),
    '1500002747': ('11-NW-10D',), '1500001940': ('11-NW-10D',),
    '1500001939': ('11-NW-10D',), '1500001938': ('11-NW-10D',),
    '1500001937': ('11-NW-10D',), '1500001936': ('11-NW-10D',),
    '1500001935': ('11-NW-10D',), '1500001934': ('11-NW-10D',),
    '1500001932': ('11-NW-10D',),
    '1500000750': ('6-SE-20D',), '1500000753': ('6-SE-20D',),
    '1500000756': ('6-SE-25B',), '1500000757': ('6-SE-25B',),
    '1500000760': ('6-SE-25B',), '1500001283': ('7-SW-16B',),
    '1500001285': ('7-SW-16B',), '1500001287': ('7-SW-11D',),
    '1500001289': ('7-SW-11D',), '1500001358': ('7-SW-22C',),
    '1500001359': ('7-SW-22C',), '1500001360': ('7-SW-22C',),
    '1500001361': ('7-SW-22C',), '1500001811': ('11-NW-7C',),
    '1500001812': ('11-NW-7C',), '1500001813': ('11-NW-7C',),
    '1500001817': ('11-NW-7C',), '1500001822': ('11-NW-7C',),
    '1500001823': ('11-NW-7A',), '1500001906': ('11-NW-9D',),
    '1500001913': ('11-NW-9D',), '1500001923': ('11-NW-9D',),
    '1500001924': ('11-NW-9D',), '1500001925': ('11-NW-9D',),
    '1500001926': ('11-NW-9D',), '1500001927': ('11-NW-9D',),
    '1500001928': ('11-NW-9D',), '1500001929': ('11-NW-9D',),
    '1500001930': ('11-NW-9D',), '1500004915': ('6-SE-20D',),
    '1500004916': ('6-SE-20D',), '1500004917': ('6-SE-25B',),
    '1500004918': ('6-SE-25B',), '1500004927': ('7-SW-16B',),
    '1500004928': ('7-SW-11D', '7-SW-12C'), '1500004937': ('11-NW-7C',),
    '1500004938': ('11-NW-7C',), '1500004939': ('11-NW-7C',),
    '1500004985': ('11-NW-9D',), '1500004986': ('11-NW-9D',),
    '1810018589': ('7-SW-11D', '7-SW-16B'),
    '1810061752': ('7-SW-11D', '7-SW-16B'),
    '1910085685': ('6-SE-25B', '6-SE-25D'),
    '1910085686': ('6-SE-25B', '6-SE-25D'),
    '1910086770': ('6-SE-25B',), '1910088624': ('11-NW-18B',),
    '1910088625': ('11-NW-18B',), '1910088626': ('11-NW-18B',),
    '1910088666': ('6-SE-25B',),
    '1500001977': ('11-NW-24D',), '1500001978': ('11-NW-24D',),
    '1500002016': ('11-NW-24B',), '1500002017': ('11-NW-24B',),
    '1500002018': ('11-NW-24B',), '1500002019': ('11-NW-24B',),
    '1500002020': ('11-NW-24B',), '1500002021': ('11-NW-24B',),
    '1500002074': ('11-NW-14C',), '1500002075': ('11-NW-14C',),
    '1500001861': ('11-NW-14B',), '1500001862': ('11-NW-14B',),
    '1500001863': ('11-NW-14B',), '1500001864': ('11-NW-14B',),
    '1500002076': ('11-NW-13D',),
    '1500002077': ('11-NW-13D', '11-NW-14C'),
    '1500002078': ('11-NW-14C',),
    '1500002080': ('11-NW-13D',), '1500002081': ('11-NW-13D',),
    '1500002082': ('11-NW-13D',),
    '1500002090': ('11-NW-14C',),
    '1500002093': ('11-NW-14A', '11-NW-14C'),
    '1500002094': ('11-NW-14C',),
    '1500005007': ('11-NW-13D',), '1500005008': ('11-NW-13D',),
    '1810017066': ('11-NW-13B',), '1810025769': ('11-NW-14D',),
    '1500004994': ('11-NW-24B',), '1500004995': ('11-NW-24B',),
    '1500001910': ('11-NW-10C',), '1500001941': ('11-NW-10C',),
    '1500001955': ('11-NW-10A',),
}
GML_SPORT_IDS = frozenset(EXPECTED_SPORT_FRAGMENTS)
GATEBALL_IDS = frozenset({'1500001863', '1500001864'})
EXPECTED_SITE_FRAGMENTS = {
    '1503005714': ('11-NW-10D', '11-NW-15B'),
    '1503005716': ('11-NW-10B', '11-NW-10D'),
    '1503005718': ('11-NW-10B', '11-NW-5D'),
    '1503005751': ('11-NW-20D',),
    '1503005810': ('11-NE-1C', '11-NE-6A', '11-NW-10B', '11-NW-5D'),
    '1503005853': ('11-NE-6A', '11-NE-6C', '11-NE-6C', '11-NE-6C', '11-NE-6C'),
    '1503005863': ('11-NE-11A',),
    '1503005866': ('11-NE-11A', '11-NW-15B'),
    '1503005870': ('11-NE-16A',), '1503005871': ('11-NE-21A',),
    '1503005881': ('11-NE-16C',),
    '1503005901': ('11-NE-21A', '11-NE-21C'),
    '1503005939': ('11-NE-6B', '11-NE-6C', '11-NE-6D'),
    '1503005961': ('11-NE-6B',),
    '1810011761': ('6-SE-25B', '6-SE-25D'),
    '1910059822': ('11-NE-6B', '11-NE-6D'), '1910071209': ('11-SW-5B',),
    '1910064509': ('11-NW-13D', '11-NW-18B'),
    '1503000381': ('11-NW-2A', '7-SW-22C'),
    '1503005413': ('11-NW-9B', '11-NW-9D'),
    '1503000390': ('11-NW-12B', '11-NW-7A', '11-NW-7B', '11-NW-7C', '11-NW-7D', '11-NW-7D'),
    '1503005076': ('11-NW-13D', '11-NW-18B'),
    '1503000414': ('7-SW-11D', '7-SW-12C', '7-SW-16B'),
    '1910069198': ('11-NW-1A',),
    '1503000199': ('6-SE-20D', '6-SE-25B', '6-SE-25B'),
    '1910053970': ('11-NW-23D', '11-NW-23D', '11-SW-3B'),
    '1910053968': ('11-NW-23D', '11-SW-3B'),
    '1503005535': ('11-SW-4B', '11-SW-5A'),
    '1503005281': ('11-NW-24D',),
    '1810014504': ('11-NW-19D', '11-NW-19D', '11-NW-20C', '11-NW-24B', '11-NW-25A'),
    '1810044652': ('11-NW-24A', '11-NW-24B'),
    '1503005514': ('11-NW-24B', '11-NW-25A', '11-NW-25A', '11-NW-25A'),
    '1910056230': ('11-NW-18B', '11-NW-18D'),
    '1810032161': ('11-NW-18D', '11-NW-18D'),
    '1910062401': ('11-NW-18D', '11-NW-19C'),
    '1503005115': ('11-NW-14C',), '1503005152': ('11-NW-14C',),
    '1503005112': ('11-NW-13D', '11-NW-14C'),
    '1503005184': ('11-NW-14A', '11-NW-14C'),
    '1503005071': ('11-NW-13B',), '1503005077': ('11-NW-13B',),
    '1503005508': ('11-NW-9B', '11-NW-9D', '11-NW-9D', '11-NW-10C'),
    '1503005450': ('11-NW-14B', '11-NW-14D'),
    '1503005180': ('11-NW-14A',), '1503005170': ('11-NW-14A',),
    '1503005157': ('11-NW-14A',), '1503005144': ('11-NW-14A',),
    '1503005135': ('11-NW-14C',), '1503005123': ('11-NW-14C',),
    '1810015202': ('11-SW-4D',),
    '1503005628': ('11-SW-4D', '11-SW-5A', '11-SW-5B', '11-SW-5C'),
    '1503005539': ('11-NW-9D', '11-NW-9D', '11-NW-10C'),
    '1503005553': ('11-NW-10A', '11-NW-10C'),
    '1503005688': ('11-NW-10A', '11-NW-10B'),
    '1503005627': ('11-NW-10A',),
    '1503005605': ('11-NW-10A',),
    '1502005648': ('11-NW-10A', '11-NW-10C'),
}
GML_SITE_IDS = frozenset(SITES)
KOWLOON_CITY_SITES = {
    '1503005642': ('Carmel Village Street Garden', 3863.01),
    '1503005679': ('Ho Man Tin Park', 18000.86),
    '1503005683': ('Perth Street Sports Ground', 19453.47),
    '1503005701': ('Ho Man Tin East Service Reservoir Playground', 31616.44),
    '1810022853': ('Ho Man Tin East Sitting-out Area No. 1', 5104.70),
}
KOWLOON_CITY_SPORTS = {
    '1500002029': ('1503005679', 'BAC'), '1500002030': ('1503005679', 'FOF'),
    '1500004996': ('1503005679', 'BAC'),
    '1500002064': ('1503005683', 'BAC'), '1500002065': ('1503005683', 'BAC'),
    '1500002066': ('1503005683', 'FOF'), '1810060613': ('1503005683', 'RAT'),
    '1500004997': ('1503005701', 'FOF'), '1500004998': ('1503005701', 'FOF'),
}
SITES.update({uid: name for uid, (name, _) in KOWLOON_CITY_SITES.items()})
SITE_AREAS.update({uid: area for uid, (_, area) in KOWLOON_CITY_SITES.items()})
EXPECTED_SITE_IDS = frozenset(SITES)
EXPECTED_SPORTS = GML_SPORT_IDS | frozenset(KOWLOON_CITY_SPORTS)
WESTERN_SITE_COAST = {
    '1910064509': 'west-kowloon', '1503005413': 'lai-chi-kok',
    '1503000390': 'lai-chi-kok', '1503005076': 'west-kowloon',
    '1503000414': 'tsuen-wan', '1503000381': 'kwai-chung',
    '1910069198': 'kwai-chung', '1503000199': 'tsuen-wan',
    '1810011761': 'tsuen-wan',
    '1910053970': 'west-kowloon', '1910053968': 'west-kowloon',
    '1503005535': 'west-kowloon', '1503005281': 'west-kowloon',
    '1810014504': 'west-kowloon', '1810044652': 'west-kowloon',
    '1503005514': 'west-kowloon', '1910056230': 'west-kowloon',
    '1810032161': 'west-kowloon', '1910062401': 'west-kowloon',
    '1503005115': 'west-kowloon', '1503005152': 'west-kowloon',
    '1503005112': 'west-kowloon', '1503005184': 'west-kowloon',
    '1503005071': 'west-kowloon', '1503005077': 'west-kowloon',
    '1503005450': 'west-kowloon', '1503005508': 'lai-chi-kok',
    '1503005180': 'west-kowloon',
    '1503005170': 'west-kowloon', '1503005157': 'west-kowloon',
    '1503005144': 'west-kowloon', '1503005135': 'west-kowloon',
    '1503005123': 'west-kowloon',
    '1810015202': 'west-kowloon', '1503005628': 'west-kowloon',
    '1503005539': 'lai-chi-kok', '1503005553': 'lai-chi-kok',
    '1503005627': 'lai-chi-kok', '1503005605': 'lai-chi-kok',
    '1502005648': 'lai-chi-kok'
}
EASTERN_SITE_IDS = EXPECTED_SITE_IDS - WESTERN_SITE_COAST.keys()
SHEET_CACHE_EXPECTED = 230
WIP_LABEL = 'WIP Sep 2026'
FOOTBALL_REFERENCE = 'https://www.lcsd.gov.hk/clpss/en/webApp/PhoneAddress.do?ftid=4'
KGV_FOOTBALL_REFERENCE = 'https://www.lcsd.gov.hk/clpss/en/webApp/Facility/Details.do?ftid=56'
SYCAMORE_FOOTBALL_REFERENCE = 'https://www.lcsd.gov.hk/clpss/en/webApp/Facility/Details.do?did=17&fcid=8&ftid=11'
TUNG_CHAU_REFERENCE = 'https://www.lcsd.gov.hk/en/parks/tcsp/facilities/outdoor.html'
MAPLE_STREET_REFERENCE = 'https://www.lcsd.gov.hk/en/common/images/en/doc/2020/HAB366E.pdf'
TAI_HANG_TUNG_PLAN_REFERENCE = 'https://www.lcsd.gov.hk/ls/tender/en/list/forms/LCLSQLRKSSPTHTRG202001_EN.pdf'
PERTH_FOOTBALL_REFERENCE = 'https://www.lcsd.gov.hk/clpss/en/webApp/Facility/Details.do?did=4&fcid=8&ftid=3'
HOI_SHAM_REFERENCE = 'https://www.lcsd.gov.hk/clpss/en/webApp/PhoneAddress.do?ftid=42'
TO_KWA_WAN_REFERENCE = 'https://www.info.gov.hk/gia/general/201306/30/P201306280790_print.htm'
SOURCE_TO_WGS84 = Transformer.from_crs(2326, 4326, always_xy=True)


def priority_boxes():
    scale_x = 111320 * math.cos(math.radians(ORIGIN[1]))
    return {uid: box(ORIGIN[0] + b[0] / scale_x, ORIGIN[1] - b[3] / 111320,
                     ORIGIN[0] + b[2] / scale_x, ORIGIN[1] - b[1] / 111320)
            for uid, b in SITE_BOUNDS.items()}


def index_polygon(geometry):
    if 'rings' in geometry:
        rings = geometry['rings']
        if not rings:
            raise ValueError('Empty iB1000 index tile geometry')
        return make_valid(Polygon(rings[0], rings[1:]))
    if all(key in geometry for key in ('xmin', 'ymin', 'xmax', 'ymax')):
        return box(geometry['xmin'], geometry['ymin'], geometry['xmax'], geometry['ymax'])
    raise ValueError('Unrecognized iB1000 index tile geometry')


def validate_index(index):
    if index.get('error') or index.get('exceededTransferLimit') or not index.get('features'):
        raise ValueError('Incomplete or empty official iB1000 index response')
    rows = []
    seen = set()
    for feature in index['features']:
        props = feature.get('attributes', {})
        tile = str(props.get('SHEETNO', '')).removeprefix('T')
        url = props.get('GML', '')
        revision = props.get('REVISIONDATE')
        geom = feature.get('geometry')
        if not tile or tile in seen or not url.startswith('https://open.hkmapservice.gov.hk/OpenData/directDownload?'):
            raise ValueError('Missing, duplicate, or unexpected official iB1000 tile row')
        if revision is None or not geom:
            raise ValueError('iB1000 index row is missing revision or whole-sheet geometry: ' + tile)
        polygon = index_polygon(geom)
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError('Invalid iB1000 tile geometry: ' + tile)
        seen.add(tile)
        rows.append(dict(tile=tile, url=url, revision_date=revision, geometry=geom))
    return rows


def select_tiles(index_tiles):
    boxes = priority_boxes()
    site_union = union_all(list(boxes.values()))
    selected = []
    candidates = []
    for row in index_tiles:
        tile = index_polygon(row['geometry'])
        candidates.append(tile)
        if tile.intersects(site_union):
            selected.append(row)
    if not selected:
        raise ValueError('No complete iB1000 sheets cover the reviewed site bounds')
    coverage = union_all([index_polygon(row['geometry']) for row in selected])
    for uid, site_box in boxes.items():
        if site_box.difference(coverage).area > 1e-10:
            raise ValueError('Selected whole-sheet tiles do not cover the reviewed bounds: ' + uid)
    return sorted(selected, key=lambda row: row['tile'])


def validate_manifest(manifest):
    if manifest.get('index_url') != INDEX_URL or tuple(manifest.get('bbox_wgs84', ())) != BBOX:
        raise ValueError('Unexpected iB1000 index source or extent')
    expected_bounds = {uid: list(bounds) for uid, bounds in SITE_BOUNDS.items()}
    if manifest.get('site_bounds') != expected_bounds:
        raise ValueError('Tile manifest does not use the reviewed surveyed site bounds')
    if manifest.get('index_sha256') != INDEX_SHA256:
        raise ValueError('Tile manifest is not backed by the reviewed complete official index')
    index_sources = manifest.get('index_sources', [])
    response_path = str(INDEX_RESPONSE.relative_to(ROOT))
    matching_sources = [row for row in index_sources if row.get('kind') == 'expanded_39_site_official_index']
    if len(matching_sources) != 1 or matching_sources[0].get('path') != response_path or \
            matching_sources[0].get('sha256') != INDEX_SHA256 or matching_sources[0].get('bbox_wgs84') != list(BBOX):
        raise ValueError('Tile manifest is missing the reviewed expanded official-index response')
    response = INDEX_RESPONSE.read_bytes()
    if hashlib.sha256(response).hexdigest() != INDEX_SHA256:
        raise ValueError('The saved complete official iB1000 index response changed')
    official_rows = validate_index(json.loads(response))
    if len(official_rows) != SHEET_CACHE_EXPECTED:
        raise ValueError('The saved official iB1000 index response is incomplete')
    index_tiles = manifest.get('index_tiles')
    if (not isinstance(index_tiles, list) or len(index_tiles) != SHEET_CACHE_EXPECTED or
            len({row.get('tile') for row in index_tiles}) != SHEET_CACHE_EXPECTED):
        raise ValueError('Missing or incomplete whole-sheet iB1000 index selection')
    official_by_tile = {row['tile']: row for row in official_rows}
    for row in index_tiles:
        official = official_by_tile.get(row.get('tile'))
        if official is None or any(row.get(key) != official.get(key)
                                   for key in ('tile', 'url', 'revision_date', 'geometry')):
            raise ValueError('Cached index rows differ from the reviewed official response: ' + str(row.get('tile')))
    expected = select_tiles(official_rows)
    rows = manifest.get('tiles', [])
    names = [row.get('tile') for row in rows]
    if names != [row['tile'] for row in expected]:
        raise ValueError('Incomplete, duplicate, or unexpected whole-sheet tile selection')
    index_by_tile = official_by_tile
    for row in rows:
        source = index_by_tile[row['tile']]
        if row.get('url') != source.get('url') or row.get('revision_date') != source.get('revision_date'):
            raise ValueError('Selected tile provenance differs from official index: ' + row['tile'])
        if row.get('index_source') != matching_sources[0]['kind']:
            raise ValueError('Selected tile index vintage is inconsistent: ' + row['tile'])
        digest = row.get('sha256', '')
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest.lower()):
            raise ValueError('Invalid iB1000 tile SHA-256: ' + row['tile'])
    return rows


def regional_land():
    land_parts = []
    regions = []
    for path in COAST_FILES:
        data = json.loads(path.read_text())
        region = box(*data['bounds'])
        land_parts.append(make_valid(shape(data['land']).intersection(region)))
        regions.append(region)
    return union_all(land_parts), union_all(regions)


def site_land_geometries():
    east_path = ROOT / 'Data/east-kowloon-coast.json'
    east_data = json.loads(east_path.read_text())
    east_bounds = box(*east_data['bounds'])
    east_land = shape(east_data['land']).intersection(east_bounds)
    result = {uid: east_land for uid in EASTERN_SITE_IDS}
    for uid, region_name in WESTERN_SITE_COAST.items():
        path = next(path for path in COAST_FILES if path.stem == region_name + '-coast')
        data = json.loads(path.read_text())
        bounds = box(*data['bounds'])
        result[uid] = make_valid(shape(data['land']).intersection(bounds))
    network = json.loads((ROOT / 'Data/cross-harbour.json').read_text())
    ground = union_all([Polygon(triangle) for triangle in network['ground_triangles']])
    for uid in GROUND_SCOPE_SITE_IDS:
        result[uid] = ground
    return result


def fragment_counter(features, layer, id_field):
    return Counter((str(feature.get('properties', {}).get(id_field)),
                    str(feature.get('properties', {}).get('tile')))
                   for feature in features
                   if feature.get('properties', {}).get('layer') == layer)


def validate_source_fragments(source):
    raw = json.loads(source)
    if raw.get('type') != 'FeatureCollection' or not isinstance(raw.get('features'), list):
        raise AssertionError('Missing government feature collection')
    features = raw['features']
    site_features = [feature for feature in features if feature.get('properties', {}).get('layer') == 'Site']
    sport_features = [feature for feature in features
                      if feature.get('properties', {}).get('layer') == 'BuiltStructurePolygon']
    if len(site_features) + len(sport_features) != len(features) or any(
            feature.get('properties', {}).get('USAGETYPE') not in KINDS for feature in sport_features):
        raise AssertionError('Government source contains an unexpected layer or sport category')
    site_ids = {str(feature.get('properties', {}).get('SITEID')) for feature in site_features}
    sport_ids = {str(feature.get('properties', {}).get('BUILTSTRUCTUREPOLYGONID')) for feature in sport_features}
    if site_ids != GML_SITE_IDS:
        raise AssertionError(f'Raw source Site IDs differ from reviewed IDs; missing={sorted(GML_SITE_IDS-site_ids)}; unexpected={sorted(site_ids-GML_SITE_IDS)}')
    if sport_ids != GML_SPORT_IDS:
        raise AssertionError(f'Raw source sports IDs differ from reviewed IDs; missing={sorted(GML_SPORT_IDS-sport_ids)}; unexpected={sorted(sport_ids-GML_SPORT_IDS)}')
    expected_sites = Counter((site_id, tile) for site_id, tiles in EXPECTED_SITE_FRAGMENTS.items()
                             for tile in tiles)
    actual_sites = fragment_counter(features, 'Site', 'SITEID')
    if actual_sites != expected_sites:
        raise AssertionError('Raw source Site geometry differs from reviewed fragments; missing=' +
                             repr(sorted((expected_sites-actual_sites).elements())) +
                             '; unexpected=' + repr(sorted((actual_sites-expected_sites).elements())))
    expected_sports = Counter((source_id, tile) for source_id, tiles in EXPECTED_SPORT_FRAGMENTS.items()
                              for tile in tiles)
    actual_sports = fragment_counter(features, 'BuiltStructurePolygon', 'BUILTSTRUCTUREPOLYGONID')
    if actual_sports != expected_sports:
        raise AssertionError('Raw source sports differ from reviewed fragments; missing=' +
                             repr(sorted((expected_sports-actual_sports).elements())) +
                             '; unexpected=' + repr(sorted((actual_sports-expected_sports).elements())))
    if len(features) != 284:
        raise AssertionError('The reviewed source must contain exactly 284 Site and sport fragments')
    metadata = raw.get('metadata', {})
    if set(metadata.get('site_revisions', {})) != GML_SITE_IDS or \
            set(metadata.get('sports_revisions', {})) != GML_SPORT_IDS:
        raise AssertionError('Government source is missing complete Site or sports revision provenance')
    return raw


def combined_source(source):
    raw = validate_source_fragments(source)
    payload = KOWLOON_CITY_SOURCE.read_bytes()
    survey = json.loads(payload)
    metadata = survey['metadata']
    if survey['type'] != 'FeatureCollection' or metadata['source_crs'] != 'EPSG:4326':
        raise ValueError('Expected the Kowloon City WGS84 survey extract')
    sites, sports = {}, {}
    for feature in survey['features']:
        props = feature['properties']
        if props['STATUS'] != 'E' or not isinstance(props['LASTUPDATEDATE'], int):
            raise ValueError('Invalid Kowloon City survey status or revision date')
        if props['layer'] == 'Site':
            target, key = sites, 'SITEID'
        elif props['layer'] == 'BuiltStructurePolygon':
            target, key = sports, 'BUILTSTRUCTUREPOLYGONID'
        else:
            raise ValueError('Unexpected Kowloon City survey layer')
        uid = str(props[key])
        if uid in target:
            raise ValueError('Duplicate Kowloon City survey ID: ' + uid)
        props[key] = uid
        target[uid] = feature
    if sites.keys() != KOWLOON_CITY_SITES.keys() or sports.keys() != KOWLOON_CITY_SPORTS.keys():
        raise ValueError('Incomplete reviewed Kowloon City recreation survey')
    labels = {str(row['site_id']): row['annotation'] for row in metadata['site_annotations']}
    if labels.keys() != sites.keys() or len(labels) != len(metadata['site_annotations']):
        raise ValueError('Missing surveyed Kowloon City site annotations')
    for uid, annotation in labels.items():
        text = ' '.join(annotation['properties']['TEXTSTRING'].split())
        expected_text = 'Homantin East Sitting-out Area No.1' if uid == '1810022853' else KOWLOON_CITY_SITES[uid][0]
        if text != expected_text or not shape(sites[uid]['geometry']).covers(shape(annotation['geometry'])):
            raise ValueError('Kowloon City annotation no longer identifies its site: ' + uid)
    for uid, (site_id, usage) in KOWLOON_CITY_SPORTS.items():
        feature = sports[uid]
        if feature['properties']['USAGETYPE'] != usage or \
                not source_local(sites[site_id]).covers(source_local(feature)):
            raise ValueError('Kowloon City sports outline differs from the reviewed site: ' + uid)
    raw['features'].extend(survey['features'])
    raw['metadata']['site_revisions'].update({uid: [f['properties']['LASTUPDATEDATE']] for uid, f in sites.items()})
    raw['metadata']['sports_revisions'].update({uid: [f['properties']['LASTUPDATEDATE']] for uid, f in sports.items()})
    raw['metadata']['source_manifests'].append({'path': str(KOWLOON_CITY_SOURCE.relative_to(ROOT)),
        'source': metadata['source'], 'sha256': hashlib.sha256(payload).hexdigest(),
        'retrieved_utc': metadata['retrieved_utc']})
    return raw


def source_ring(element):
    result = []
    for node in element.findall('.//g:posList', NS):
        values = list(map(float, node.text.split()))
        if len(values) < 6 or len(values) % 3 or not all(math.isfinite(v) for v in values):
            raise ValueError(f'Invalid iB1000 polygon ring: {len(values)} ordinates')
        points = [list(SOURCE_TO_WGS84.transform(values[i + 1], values[i]))
                  for i in range(0, len(values), 3)]
        if result:
            if math.dist(result[-1], points[0]) > 1e-8:
                raise ValueError('Disconnected iB1000 polygon ring')
            points = points[1:]
        result.extend(points)
    if len(result) < 4 or math.dist(result[0], result[-1]) > 1e-8:
        raise ValueError('Open iB1000 polygon ring')
    return result


def parse_polygon(item, tile, layer):
    props = {e.tag.split('}')[-1]: e.text for e in item if e.tag.startswith('{' + NS['f'] + '}')}
    if layer == 'Site' and props.get('SITEID') not in GML_SITE_IDS:
        return []
    if layer == 'BuiltStructurePolygon' and props.get('USAGETYPE') not in KINDS:
        return []
    if props.get('STATUS') != 'E':
        return []
    ident = props.get('SITEID' if layer == 'Site' else 'BUILTSTRUCTUREPOLYGONID')
    if not ident:
        raise ValueError('iB1000 polygon feature is missing its source identifier: ' + tile)
    features = []
    for patch in item.findall('.//g:PolygonPatch', NS):
        exterior = patch.find('g:exterior', NS)
        if exterior is None:
            raise ValueError('iB1000 polygon is missing its exterior ring: ' + ident)
        rings = [source_ring(exterior), *[source_ring(h) for h in patch.findall('g:interior', NS)]]
        if Polygon(rings[0], rings[1:]).is_empty:
            raise ValueError('Empty iB1000 source polygon: ' + ident)
        features.append({'type': 'Feature', 'properties': props | {'layer': layer, 'tile': tile},
                         'geometry': {'type': 'Polygon', 'coordinates': rings}})
    if not features:
        raise ValueError('Recognized iB1000 polygon has no PolygonPatch: ' + ident)
    return features


def parse_annotations(archive, tile):
    result = []
    for layer in ('SiteAnno', 'SubSiteAnno'):
        name = f'{tile}/Layers/Buildings/{layer}.gml'
        if name not in archive.namelist():
            continue
        doc = ET.fromstring(archive.read(name))
        if doc.tag != '{' + NS['g'] + '}FeatureCollection':
            raise ValueError('Invalid iB1000 annotation layer: ' + name)
        for member in doc.findall(f'g:featureMember/f:{layer}', NS):
            text = member.find('f:TextString', NS)
            pos = member.find('.//g:pos', NS)
            if text is None or not text.text or pos is None:
                continue
            values = list(map(float, pos.text.split()))
            if len(values) < 2 or not all(math.isfinite(v) for v in values):
                raise ValueError('Invalid iB1000 site annotation position: ' + tile)
            lon, lat = SOURCE_TO_WGS84.transform(values[1], values[0])
            props = {e.tag.split('}')[-1]: e.text for e in member if e.tag.startswith('{' + NS['f'] + '}')}
            result.append({'text': ' '.join(text.text.split()), 'tile': tile, 'layer': layer,
                           'last_updated': props.get('LASTUPDATEDATE'), 'position_wgs84': [lon, lat]})
    return result


def extract(cache, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    tile_rows = validate_manifest(manifest)
    found = []
    annotations = []
    for row in tile_rows:
        path = Path(cache) / (row['tile'] + '.zip')
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != row['sha256']:
            raise ValueError('Government ZIP checksum mismatch: ' + row['tile'])
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('Corrupt iB1000 archive: ' + row['tile'])
            for layer in LAYERS:
                name = f"{row['tile']}/Layers/Buildings/{layer}.gml"
                expected_fragments = EXPECTED_SITE_FRAGMENTS if layer == 'Site' else EXPECTED_SPORT_FRAGMENTS
                has_expected = any(row['tile'] in tiles for tiles in expected_fragments.values())
                if name not in archive.namelist():
                    if has_expected:
                        raise ValueError('Missing required government layer: ' + name)
                    continue
                doc = ET.fromstring(archive.read(name))
                if doc.tag != '{' + NS['g'] + '}FeatureCollection':
                    raise ValueError('Invalid government layer: ' + name)
                systems = [e.get('srsName') for e in doc.iter() if e.get('srsName')]
                if not systems or any(crs != 'EPSG:2326' for crs in systems):
                    raise ValueError('Unexpected iB1000 CRS: ' + name)
                members = doc.findall(f'g:featureMember/f:{layer}', NS)
                if not members and has_expected:
                    raise ValueError('Empty or unrecognized required government layer: ' + name)
                for item in members:
                    found.extend(parse_polygon(item, row['tile'], layer))
            annotations.extend(parse_annotations(archive, row['tile']))

    sites = defaultdict(list)
    for feature in found:
        if feature['properties']['layer'] == 'Site':
            uid = feature['properties']['SITEID']
            sites[uid].append(source_local(feature))
    if set(sites) != GML_SITE_IDS:
        raise ValueError('Incomplete source Site geometry: ' + ', '.join(sorted(GML_SITE_IDS - sites.keys())))
    land, region = regional_land()
    site_geometries = {uid: union_all(parts).intersection(land).intersection(region) for uid, parts in sites.items()}
    site_union = union_all(list(site_geometries.values()))
    source_features = [feature for feature in found if feature['properties']['layer'] == 'Site']
    for feature in found:
        if feature['properties']['layer'] != 'BuiltStructurePolygon':
            continue
        if source_local(feature).intersection(site_union).area > 1:
            source_features.append(feature)
    if not any(f['properties']['layer'] == 'BuiltStructurePolygon' for f in source_features):
        raise ValueError('The selected iB1000 sheets contain no source sports surfaces')

    site_revisions = {uid: sorted({f['properties'].get('LASTUPDATEDATE') for f in source_features
                                   if f['properties']['layer'] == 'Site' and f['properties']['SITEID'] == uid})
                      for uid in SITES if uid in GML_SITE_IDS}
    sport_revisions = {uid: sorted({f['properties'].get('LASTUPDATEDATE') for f in source_features
                                    if f['properties']['layer'] == 'BuiltStructurePolygon' and
                                    f['properties']['BUILTSTRUCTUREPOLYGONID'] == uid})
                       for uid in sorted({f['properties']['BUILTSTRUCTUREPOLYGONID'] for f in source_features
                                          if f['properties']['layer'] == 'BuiltStructurePolygon'})}
    relevant_annotations = []
    for annotation in annotations:
        point = Point(local(annotation['position_wgs84']))
        for uid, site in site_geometries.items():
            if site.covers(point):
                relevant_annotations.append(annotation | {'site': uid})
                break
    metadata = {
        'provider': 'Lands Department, HKSAR Government', 'source': INDEX_URL,
        'index_url': INDEX_URL, 'bbox_wgs84': list(BBOX),
        'retrieved_utc': manifest['retrieved_utc'], 'source_crs': 'EPSG:2326',
        'axis_order': 'GML northing,easting,height; converted to WGS84',
        'terms': SHORELINE.get('terms'), 'origin_wgs84': ORIGIN,
        'index_sha256': manifest['index_sha256'], 'index_sources': manifest.get('index_sources', []),
        'source_manifests': manifest.get('source_manifests', []),
        'tile_manifest_sha256': hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
        'tiles': [{k: row[k] for k in ('tile', 'url', 'revision_date', 'sha256')} |
                  {'retrieved_utc': row.get('retrieved_utc', manifest['retrieved_utc']),
                   'index_source': row.get('index_source') or 'official_index'} for row in tile_rows],
        'site_revisions': site_revisions, 'sports_revisions': sport_revisions,
        'source_annotations': relevant_annotations,
        'known_wip_annotations': [a for a in relevant_annotations if WIP_LABEL.lower() in a['text'].lower()],
        'note': 'Government Site and BuiltStructurePolygon geometries are retained from complete selected iB1000 sheets. Sports and site source dates vary; Carpenter Road has a WIP Sep 2026 source annotation. Paths, access, surface styling, planting and furniture are authored approximations.'
    }
    if not metadata['known_wip_annotations']:
        # Retain the reviewed warning if the annotation label is absent from a selected sheet.
        metadata['known_wip_annotations'] = [{'site': '1503005866', 'text': WIP_LABEL,
                                               'source': 'reviewed priority-site annotation; see selected sheet revision metadata'}]
    return encoded({'type': 'FeatureCollection', 'metadata': metadata, 'features': source_features})


def source_local(feature):
    geometry = feature['geometry']
    parts = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
    return make_valid(union_all([Polygon([local(p) for p in coords[0]],
                                        [[local(p) for p in ring] for ring in coords[1:]])
                                 for coords in parts]))


def geometry_rings(poly):
    return [list(poly.exterior.coords)[:-1], *[list(ring.coords)[:-1] for ring in poly.interiors]]


def geometry_polygons(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if hasattr(geom, 'geoms'):
        return [part for item in geom.geoms for part in geometry_polygons(item)]
    return []


def polygon_triangles(poly):
    faces = list(constrained_delaunay_triangles(poly).geoms)
    if abs(sum(face.area for face in faces) - poly.area) > .01:
        raise ValueError('Polygon triangulation lost source area')
    return [list(face.exterior.coords)[:-1] for face in faces]


def safe_site_polygons(*, include_southwest_landmarks=True):
    layout_paths = sorted(ROOT.glob('Data/*layout.json'))
    if len(layout_paths) != 9:
        raise ValueError(f'Expected all nine loaded building layouts; found {len(layout_paths)}')
    buildings = []
    pavement_patches = []
    inputs = {}
    for path in layout_paths:
        inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        data = json.loads(path.read_text())
        buildings.extend(Polygon(b['rings'][0], b['rings'][1:]) for b in data['buildings']
                         if include_southwest_landmarks or b['id'] not in LANDMARK_LAYOUT_IDS)
        pavement_patches.extend(Polygon(p['polygon']) for p in data['pavement_patches'])
    lots = union_all(buildings)
    road_path = ROOT / 'Data/cross-harbour.json'
    inputs[str(road_path.relative_to(ROOT))] = hashlib.sha256(road_path.read_bytes()).hexdigest()
    district_roads_path = ROOT / 'Data/nathan-road.json'
    inputs[str(district_roads_path.relative_to(ROOT))] = hashlib.sha256(district_roads_path.read_bytes()).hexdigest()
    for coast_path in COAST_FILES:
        inputs[str(coast_path.relative_to(ROOT))] = hashlib.sha256(coast_path.read_bytes()).hexdigest()
    east_path = ROOT / 'Data/east-kowloon-coast.json'
    east_data = json.loads(east_path.read_text())
    east_land = shape(east_data['land'])
    east_bounds = box(*east_data['bounds'])
    roads = []
    prop_roads = []
    street_targets = []
    carriageways = []
    network = json.loads(road_path.read_text())
    for road in network['roads']:
        if road['tunnel'] and not road.get('ramp', False):
            continue
        line = LineString([(p[0], p[2]) for p in road['points']])
        if not line.intersects(east_bounds):
            continue
        roads.append(line.buffer(max(12, road['width']) / 2 + 3.5, join_style='mitre'))
        prop_roads.append(line.buffer(max(12, road['width']) / 2 + 8, join_style='mitre'))
        street_targets.append(line.buffer(max(12, road['width']) / 2 + 3, join_style='mitre'))
        carriageways.append(line.buffer(max(12, road['width']) / 2, join_style='mitre'))
    ground = union_all([Polygon(triangle) for triangle in network['ground_triangles']])
    bounds = network['bounds']
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    resolution = min(2, 16384 / max(width, height))
    pixels_x, pixels_y = min(16384, math.ceil(width * resolution)), min(16384, math.ceil(height * resolution))
    pixel_radius = math.hypot(width / pixels_x, height / pixels_y) / 2
    paving_margin = pixel_radius + math.hypot(width / pixels_x, height / pixels_y)
    east = (union_all(roads), union_all(prop_roads), east_land.intersection(east_bounds),
            union_all(street_targets), union_all(carriageways))

    west_regions = {}
    for coast_path in COAST_FILES:
        region_name = coast_path.stem.removesuffix('-coast')
        if region_name == 'east-kowloon' or region_name not in set(WESTERN_SITE_COAST.values()):
            continue
        data = json.loads(coast_path.read_text())
        bounds = box(*data['bounds'])
        region_roads = []
        region_prop_roads = []
        region_street_targets = []
        region_carriageways = []
        for road in network['roads']:
            if road['tunnel'] and not road.get('ramp', False):
                continue
            line = LineString([(p[0], p[2]) for p in road['points']])
            regional_line = line.intersection(bounds)
            if regional_line.is_empty:
                continue
            region_roads.append(regional_line.buffer(max(12, road['width']) / 2 + 3.5, join_style='mitre'))
            region_prop_roads.append(regional_line.buffer(max(12, road['width']) / 2 + 8, join_style='mitre'))
            region_street_targets.append(regional_line.buffer(max(12, road['width']) / 2 + 3, join_style='mitre'))
            region_carriageways.append(regional_line.buffer(max(12, road['width']) / 2, join_style='mitre'))
        west_regions[region_name] = (
            union_all(region_roads), union_all(region_prop_roads),
            make_valid(shape(data['land']).intersection(bounds)),
            union_all(region_street_targets), union_all(region_carriageways))
    return (inputs, lots, *east[:2], east[2], east[3], east[4], ground, west_regions,
            union_all(pavement_patches), paving_margin)


def site_road_scope(site_id, site, region, district_roads):
    if site_id not in SIDE_ROAD_SITE_IDS:
        return region
    road_buffers, prop_buffers, target_buffers, carriageway_buffers = [], [], [], []

    def add_road(line, width):
        if line.is_empty or site.distance(line) > 250:
            return
        road_buffers.append(line.buffer(width / 2 + 3.5, quad_segs=2, join_style='mitre'))
        prop_buffers.append(line.buffer(width / 2 + 8, quad_segs=2, join_style='mitre'))
        target_buffers.append(line.buffer(width / 2 + 3, quad_segs=2, join_style='mitre'))
        carriageway_buffers.append(line.buffer(width / 2, quad_segs=2, join_style='mitre'))

    add_road(LineString(district_roads['road_points']), 20)
    for road in district_roads['side_roads']:
        add_road(LineString(road['points']), 18 if road['name'] in WIDE else 12)
    return (
        union_all([region[0], *road_buffers]),
        union_all([region[1], *prop_buffers]),
        region[2],
        union_all([region[3], *target_buffers]),
        union_all([region[4], *carriageway_buffers]),
    )


def ground_scope_region(region, east_region, ground):
    return (
        union_all([region[0], east_region[0]]),
        union_all([region[1], east_region[1]]),
        ground,
        union_all([region[3], east_region[3]]),
        union_all([region[4], east_region[4]]),
    )


def lok_kwan_street_targets(site, road_network):
    context = site.buffer(250)
    targets = []
    for road in road_network['roads']:
        if road.get('name') != 'LOK KWAN STREET' or (road['tunnel'] and not road.get('ramp', False)):
            continue
        line = LineString([(point[0], point[2]) for point in road['points']]).intersection(context)
        if not line.is_empty:
            targets.append(line.buffer(max(12, road['width']) / 2 + 3, join_style='mitre'))
    if not targets:
        raise ValueError('LOK KWAN STREET is missing from the reviewed road network')
    return union_all(targets)


def publicly_connected_path_components(paths, access, street_targets, lots, pavement_patches, paving_margin):
    if paths.is_empty or street_targets.is_empty:
        return []
    context = paths.envelope.buffer(250 + paving_margin)
    local_targets = street_targets.intersection(context)
    local_lots = lots.intersection(context)
    local_patches = pavement_patches.intersection(context)
    paved = make_valid(union_all([
        paths.buffer(paving_margin), access.buffer(paving_margin),
        local_targets.buffer(paving_margin), local_lots.buffer(3 + paving_margin),
        local_patches.buffer(paving_margin)
    ]).difference(local_lots))
    return [part for part in geometry_polygons(paved) if part.intersects(local_targets)]


def path_network(site_id, site, safe, sports, street_targets, carriageways, land, building_clearance,
                 lots, pavement_patches, paving_margin):
    blocked = sports.buffer(3.5) if not sports.is_empty else Polygon()
    free = make_valid(safe.difference(blocked))
    linework = []
    path_parts = []
    access_parts = []
    if site_id in SIT_OUT_SITE_IDS | COMPACT_PLAZA_SITE_IDS:
        # Compact surveyed plots have room for shared paving and seating on their safe ground.
        path_parts.extend(part for part in geometry_polygons(free) if part.area >= 5)
        linework.extend(LineString(ring.coords) for part in path_parts
                        for ring in (part.exterior, *part.interiors))
        sample_clearance = 1.1
        path_half_width = 1.8
    else:
        sample_clearance = 1.1
        path_half_width = 2.4 if site_id == '1503005077' else 1.8
        access_parts = []
        for part in geometry_polygons(free):
            if part.area < 80:
                continue
            inset = part.buffer(-1.5 if site_id == '1910053968' else -4, join_style='mitre')
            if inset.is_empty:
                inset = part.buffer(-1.5, join_style='mitre')
            if inset.is_empty:
                continue
            for inset_part in geometry_polygons(inset):
                if inset_part.area < 40:
                    continue
                centre = polylabel(inset_part, tolerance=.25)
                rectangle = list(inset_part.minimum_rotated_rectangle.exterior.coords)[:4]
                edges = [(rectangle[(i + 1) % 4][0] - rectangle[i][0],
                          rectangle[(i + 1) % 4][1] - rectangle[i][1]) for i in range(4)]
                lengths = [math.hypot(*v) for v in edges]
                primary_index = max(range(4), key=lambda i: lengths[i])
                secondary_index = (primary_index + 1) % 4
                primary = edges[primary_index]
                primary_len = lengths[primary_index]
                secondary = edges[secondary_index]
                secondary_len = lengths[secondary_index]
                a = (primary[0] / primary_len, primary[1] / primary_len)
                b = (secondary[0] / secondary_len, secondary[1] / secondary_len)
                lines = [LineString([(centre.x - a[0] * primary_len, centre.y - a[1] * primary_len),
                                     (centre.x + a[0] * primary_len, centre.y + a[1] * primary_len)]),
                         LineString([(centre.x - b[0] * secondary_len, centre.y - b[1] * secondary_len),
                                     (centre.x + b[0] * secondary_len, centre.y + b[1] * secondary_len)])]
                if primary_len > 45:
                    for offset in (-primary_len / 3, primary_len / 3):
                        x, z = centre.x + a[0] * offset, centre.y + a[1] * offset
                        lines.append(LineString([(x - b[0] * secondary_len, z - b[1] * secondary_len),
                                                 (x + b[0] * secondary_len, z + b[1] * secondary_len)]))
                perimeter = inset_part.boundary
                linework.extend(lines)
                linework.extend([LineString(ring.coords) for ring in (inset_part.exterior, *inset_part.interiors)])
                path_parts.append(perimeter.buffer(path_half_width, join_style='round'))
                path_parts.extend(line.buffer(path_half_width, cap_style='round') for line in lines)
    paths = make_valid(union_all(path_parts).intersection(free)) if path_parts else Polygon()
    # Join separated loops across clear garden ground; existing public paving can serve the rest.
    parts = [part for part in geometry_polygons(paths) if part.area >= 1]
    path_samples = []
    for part in parts:
        point = polylabel(part, tolerance=.1)
        if part.boundary.distance(point) > sample_clearance:
            path_samples.append([point.x, point.y])
    while len(parts) > 1:
        candidates = sorted((parts[i].distance(parts[j]), i, j)
                            for i in range(len(parts)) for j in range(i + 1, len(parts)))
        for _, i, j in candidates:
            start, end = nearest_points(parts[i], parts[j])
            centerline = LineString([start, end])
            corridor = centerline.buffer(1.8)
            if corridor.difference(free.buffer(.01)).area > .01:
                continue
            joined = union_all([parts[i], parts[j], corridor])
            parts = [part for k, part in enumerate(parts) if k not in (i, j)] + [joined]
            linework.append(centerline)
            break
        else:
            break
    paths = union_all(parts)
    # Safe-area clipping can leave isolated scraps too narrow for a clearance-safe connectivity probe.
    retained = []
    discarded_component = False
    sampled = [Point(sample) for sample in path_samples]
    for part in geometry_polygons(paths):
        if part.area < 1:
            discarded_component = True
            continue
        if any(part.covers(sample) for sample in sampled):
            retained.append(part)
            continue
        point = polylabel(part, tolerance=.1)
        if part.boundary.distance(point) <= sample_clearance:
            discarded_component = True
            continue
        retained.append(part)
        path_samples.append([point.x, point.y])
        sampled.append(point)
    # Keep the original geometry serialization when every component is usable; re-union only
    # when clipping left a component that cannot safely retain a connectivity probe.
    if discarded_component:
        paths = union_all(retained) if retained else Polygon()

    # Connect interior paths to the existing street paving edge. The authored corridor may
    # leave the government site boundary, but it must stay on mainland land and clear buildings.
    access_reason = 'no nearby street paving'
    if site_id in {'1503005077', '1503005553', '1503005605'} and not paths.is_empty:
        # These reviewed sites have a clear authored route where the nearest-road segment is blocked.
        centerline = (LineString([(-1501, -4110), (-1556, -4043)]) if site_id == '1503005077'
                      else LineString([(280, -4960), (211.171, -5015.263)]) if site_id == '1503005553'
                      else LineString([(559, -5048), (581, -5042)]))
        corridor = centerline.buffer(1.8, cap_style='flat')
        reasons = []
        if centerline.length > 250:
            reasons.append(f'length={centerline.length:.2f}m exceeds 250m')
        if corridor.difference(land.buffer(.01)).area > .01:
            reasons.append('corridor leaves mainland ground')
        if corridor.intersection(building_clearance).area > .01:
            reasons.append('corridor enters building clearance')
        if corridor.intersection(carriageways).area > .01:
            reasons.append('corridor enters a carriageway')
        if corridor.intersection(blocked).area > .01:
            reasons.append('corridor enters a sports clearance')
        if corridor.intersection(paths).area <= .1:
            reasons.append('corridor misses the path component')
        if not corridor.intersects(street_targets):
            reasons.append('corridor misses existing public paving')
        if not reasons:
            access_parts.append(corridor)
            linework.append(centerline)
        else:
            access_reason = '; '.join(reasons)
    elif not paths.is_empty and not street_targets.is_empty:
        start, end = nearest_points(paths, street_targets.boundary)
        toward_street = (end.x - start.x, end.y - start.y)
        distance = math.hypot(*toward_street)
        approach_depth = .75 if site_id in SIT_OUT_SITE_IDS else 2.5
        start_inside = Point(start.x - toward_street[0] / max(distance, .01) * approach_depth,
                             start.y - toward_street[1] / max(distance, .01) * approach_depth)
        if distance < .01:
            start_inside = nearest_points(paths.buffer(-1).boundary, start)[0]
        approach = LineString([start_inside, start])
        centerline = LineString([start_inside, end])
        # Do not draw an entrance across a carriageway, seawall or building footprint.
        if centerline.length <= 250 and free.buffer(.01).covers(approach):
            corridor = centerline.buffer(1.8, cap_style='flat')
            if site_id == '1910071209':
                original_area = corridor.area
                corridor = make_valid(corridor.intersection(land))
                clipped_parts = geometry_polygons(corridor)
                retained = corridor.area / original_area if original_area else 0
                inside_land = retained >= .99 and len(clipped_parts) == 1
            else:
                inside_land = corridor.difference(land.buffer(.01)).area <= .01
            clear_buildings = corridor.intersection(building_clearance).area <= .01
            clear_carriageway = corridor.intersection(carriageways).area <= .01
            clear_sports = corridor.intersection(blocked).area <= .01
            joins_path = corridor.intersection(paths).area > .1
            joins_street = (site_id != '1910071209' or
                            corridor.intersects(street_targets))
            if inside_land and clear_buildings and clear_carriageway and clear_sports and joins_path and joins_street:
                access_parts.append(corridor)
                linework.append(centerline)
            else:
                access_reason = f'land={inside_land}, buildings={clear_buildings}, road={clear_carriageway}, sports={clear_sports}, path={joins_path}, street={joins_street}'
        else:
            access_reason = f'entrance route is {centerline.length:.1f} m or does not begin on an interior path'

    access = union_all(access_parts) if access_parts else Polygon()
    rejected_components = []
    if site_id in WESTERN_SITE_COAST and not paths.is_empty:
        connected = publicly_connected_path_components(paths, access, street_targets, lots,
                                                      pavement_patches, paving_margin)
        retained = []
        extra_access = []
        for index, component in enumerate(geometry_polygons(paths)):
            if any(public.intersects(component) for public in connected):
                retained.append(component)
                continue
            reason = 'no street target'
            if not street_targets.is_empty:
                start, end = nearest_points(component, street_targets.boundary)
                toward_street = (end.x - start.x, end.y - start.y)
                distance = math.hypot(*toward_street)
                approach_depth = .75 if site_id in SIT_OUT_SITE_IDS else 2.5
                start_inside = Point(start.x - toward_street[0] / max(distance, .01) * approach_depth,
                                     start.y - toward_street[1] / max(distance, .01) * approach_depth)
                if distance < .01:
                    start_inside = nearest_points(component.buffer(-1).boundary, start)[0]
                approach = LineString([start_inside, start])
                centerline = LineString([start_inside, end])
                corridor = centerline.buffer(1.8, cap_style='flat')
                reasons = []
                if centerline.length > 250:
                    reasons.append(f'length={centerline.length:.2f}m exceeds 250m')
                if not free.buffer(.01).covers(approach):
                    reasons.append('approach leaves the safe site')
                if corridor.difference(land.buffer(.01)).area > .01:
                    reasons.append('corridor leaves mainland ground')
                if corridor.intersection(building_clearance).area > .01:
                    reasons.append('corridor enters building clearance')
                if corridor.intersection(carriageways).area > .01:
                    reasons.append('corridor enters a carriageway')
                if corridor.intersection(blocked).area > .01:
                    reasons.append('corridor enters a sports clearance')
                if corridor.intersection(component).area <= .1:
                    reasons.append('corridor misses the path component')
                if not reasons:
                    retained.append(component)
                    extra_access.append(corridor)
                    linework.append(centerline)
                    continue
                reason = '; '.join(reasons)
            rejected_components.append(dict(site=site_id, component=f'{site_id}:{index:02d}',
                                            area_m2=round(component.area, 2), reason=reason))
        if rejected_components:
            paths = union_all(retained) if retained else Polygon()
            path_samples = [sample for sample in path_samples
                            if any(part.covers(Point(sample)) for part in retained)]
            linework = [line for line in linework if line.intersects(paths)]
        if extra_access:
            access = union_all([access, *extra_access])
        connected = publicly_connected_path_components(paths, access, street_targets, lots,
                                                      pavement_patches, paving_margin)
        if any(not any(public.intersects(component) for public in connected)
               for component in geometry_polygons(paths)):
            raise ValueError(f'{site_id}: retained western paths do not connect to public paving')
    if paths.is_empty or paths.area < 80:
        raise ValueError(f'{site_id}: could not create useful connected paths in source site ({paths.area:.2f} m²)')
    if access.is_empty:
        raise ValueError(f'{site_id}: could not connect site paths to existing street paving ({access_reason})')
    return paths, access, linework, path_samples, rejected_components


def football_style(site_id, source_id, source_area):
    if source_id in GATEBALL_IDS:
        return 'court', 'LCSD Tai Hang Tung Recreation Ground plan identifies this FOF outline as a gateball court.'
    if site_id == '1503005112' and source_id in {'1500002078', '1500002094'}:
        return 'court', 'LCSD lists Tung Chau Street Park five-a-side and seven-a-side football pitches as hard-surface.'
    if site_id == '1503005184' and source_id == '1500002093':
        return 'court', 'LCSD lists Maple Street Playground football pitch as hard-surface.'
    if (site_id, source_id) in {('1503005281', '1500001977'), ('1503005152', '1500002075')}:
        return 'court', 'LCSD lists the football pitch at this site as hard-surface.'
    if source_id in ('1500001948', '1500001949'):
        return 'court', 'LCSD lists two hard-surface seven-a-side pitches at Kowloon Tsai Park.'
    if source_id in ('1500001881', '1500001883', '1500001874'):
        return 'field', 'LCSD lists three turf football pitches at Kowloon Tsai Park.'
    if source_id in ('1500001702', '1500001703'):
        return 'court', 'LCSD lists five-a-side football at Hoi Sham Park.'
    if source_id == '1500002030':
        return 'court', 'LCSD identifies the Ho Man Tin Park pitch as hard-surface.'
    if source_id == '1500002066':
        return 'court', 'LCSD identifies the smaller Perth Street pitch outside the running track as hard-surface.'
    if source_id in ('1500001706', '1500002363', '1500001698', '1500001699', '1500001652') and source_area < 4000:
        return 'court', 'Small iB1000 FOF surfaces are styled as hard football courts; surface finish is an authored approximation.'
    return 'field', 'iB1000 FOF source geometry retained; field finish is an authored approximation.'


def sport_fitting_rectangle(poly, source_id):
    rectangle = poly.minimum_rotated_rectangle
    if poly.area / rectangle.area <= .9:
        return None
    kent_court = source_id == '1500001941'
    inset = rectangle.buffer(-(.5 if kent_court else .2), join_style='mitre')
    if not poly.covers(inset):
        return None
    if kent_court:
        return inset
    if source_id in KOWLOON_CITY_SPORTS and not poly.covers(rectangle):
        close_fit = rectangle.buffer(-.02, join_style='mitre')
        return close_fit if poly.covers(close_fit) else inset
    return rectangle


def trim_reservoir_paving(layout):
    site_id = '1503005701'
    garden = next(garden for garden in layout['gardens'] if garden['site'] == site_id)
    entrance = union_all([Polygon(rings[0], rings[1:]) for rings in garden['access']])
    paths = [Polygon(rings[0], rings[1:]) for rings in garden['paths']]
    # The far court-side strips are too small and disconnected from the retained paths and entry.
    detached = [path for path in paths if path.area < 80 and path.disjoint(entrance)]
    if not detached:
        return
    removed = union_all(detached)
    garden['paths'] = [rings for rings, path in zip(garden['paths'], paths) if path not in detached]
    garden['samples'] = [sample for sample in garden['samples'] if not removed.covers(Point(sample))]
    garden['paving_area_m2'] = round(union_all([entrance, *(path for path in paths if path not in detached)]).area, 2)

    xmin, zmin, xmax, zmax = removed.bounds
    layout['paving'] = [triangle for triangle in layout['paving']
                        if not (xmin <= triangle[0][0] <= xmax and zmin <= triangle[0][1] <= zmax
                                and removed.covers(Polygon(triangle).representative_point()))]
    layout['fixtures'] = [fixture for fixture in layout['fixtures']
                          if not (fixture['site'] == site_id and fixture['asset'] == 'bench' and
                                  removed.distance(Point(fixture['position'])) <= fixture['radius'] + 1.8)]
    site = next(site for site in layout['sites'] if site['id'] == site_id)
    site['fixtures'] = sum(fixture['site'] == site_id for fixture in layout['fixtures'])


def build(source):
    raw = combined_source(source)
    inputs, lots, roads, prop_roads, land, street_targets, carriageways, ground, west_regions, \
        pavement_patches, paving_margin = safe_site_polygons(include_southwest_landmarks=False)
    district_roads = json.loads((ROOT / 'Data/nathan-road.json').read_text())
    road_network = json.loads((ROOT / 'Data/cross-harbour.json').read_text())
    kowloon_layout = json.loads((ROOT / 'Data/building-layout.json').read_text())
    southwest_lots = union_all([Polygon(b['rings'][0], b['rings'][1:]) for b in kowloon_layout['buildings']
                                if b['id'] in LANDMARK_LAYOUT_IDS])
    west_kowloon_layout = json.loads((ROOT / 'Data/west-kowloon-layout.json').read_text())
    tung_chau_building = next((building for building in west_kowloon_layout['buildings']
                               if building['id'] == 214665), None)
    if tung_chau_building is None:
        raise ValueError('Tung Chau Street Park building shell is missing from its layout')
    tung_chau_building_shell = make_valid(Polygon(tung_chau_building['rings'][0]))
    all_lots = lots.union(southwest_lots)
    building_clearance = lots.buffer(4)
    full_building_clearance = all_lots.buffer(4)
    east_region = (roads, prop_roads, land, street_targets, carriageways)
    site_regions = {uid: west_regions[WESTERN_SITE_COAST[uid]] if uid in WESTERN_SITE_COAST else east_region
                    for uid in SITES}
    for uid in GROUND_SCOPE_SITE_IDS:
        site_regions[uid] = ground_scope_region(site_regions[uid], east_region, ground)
    site_lands = {uid: region[2] for uid, region in site_regions.items()}
    site_parts = defaultdict(list)
    sports_parts = defaultdict(list)
    attributes = {}
    source_features = raw['features']
    for feature in source_features:
        props = feature.get('properties', {})
        if feature.get('geometry', {}).get('type') not in ('Polygon', 'MultiPolygon'):
            raise ValueError('Unexpected government source geometry')
        poly = source_local(feature)
        if poly.is_empty or not poly.is_valid:
            raise ValueError('Invalid government source polygon')
        if props.get('layer') == 'Site' and props.get('SITEID') in SITES:
            site_parts[props['SITEID']].append(poly)
        elif props.get('layer') == 'BuiltStructurePolygon' and props.get('USAGETYPE') in KINDS:
            source_id = props.get('BUILTSTRUCTUREPOLYGONID')
            if not source_id:
                raise ValueError('Sports source feature is missing its source ID')
            sports_parts[source_id].append(poly)
            attributes[source_id] = props
    sites = {uid: union_all(parts).intersection(site_lands[uid]) for uid, parts in site_parts.items()}
    if set(sites) != set(SITES):
        raise ValueError('Government source is missing one or more reviewed sites')
    for uid, site in sites.items():
        expected_area = SITE_AREAS[uid]
        if site.is_empty or not site.is_valid or abs(site.area - expected_area) > max(1, expected_area * .002):
            raise ValueError('Source site differs from reviewed bounds or mainland clipping: ' + uid)
    assignment = defaultdict(list)
    for source_id, parts in sports_parts.items():
        raw_poly = union_all(parts)
        overlaps = sorted(((raw_poly.intersection(site).area, uid) for uid, site in sites.items()), reverse=True)
        area, uid = overlaps[0]
        if area > 20:
            poly = raw_poly.intersection(site_lands[uid])
            if poly.area > 20:
                assignment[uid].append((source_id, poly, attributes[source_id]))

    sites_out = []
    surfaces = []
    sports = []
    paving = []
    fixtures = []
    gardens = []
    path_component_rejections = []
    global_fixture_points = []
    source_sport_ids = set()
    clearance_by_region = {}
    for uid, name in SITES.items():
        site = sites[uid]
        site_regions[uid] = site_road_scope(uid, site, site_regions[uid], district_roads)
        if uid == '1503005115':
            region = site_regions[uid]
            site_regions[uid] = (*region[:3], lok_kwan_street_targets(site, road_network), region[4])
        site_roads, site_prop_roads, site_land, site_street_targets, site_carriageways = site_regions[uid]
        # A park entrance can reach 250 m beyond its site, plus paving and building clearances.
        near_landmarks = site.distance(southwest_lots) <= 256 + paving_margin
        site_lots = all_lots if near_landmarks else lots
        site_building_clearance = full_building_clearance if near_landmarks else building_clearance
        clearance_key = (near_landmarks, id(site_roads))
        if clearance_key not in clearance_by_region:
            clearance_by_region[clearance_key] = union_all([site_building_clearance, site_roads])
        safe = make_valid(site.difference(clearance_by_region[clearance_key]))
        minimum_safe_area = 50 if uid in SIT_OUT_SITE_IDS else 100
        if safe.is_empty or safe.area < minimum_safe_area:
            raise ValueError('Building and road clearance removed the usable area: ' + uid)
        fixture_ground = (make_valid(safe.difference(tung_chau_building_shell))
                          if uid == '1503005112' else safe)
        site_sports = assignment[uid]
        # A running track's inner ring encloses its athletics infield, not garden space.
        source_union = union_all([(union_all([Polygon(p.exterior) for p in geometry_polygons(poly)])
            if props['USAGETYPE']=='RAT' else poly).intersection(site) for _,poly,props in site_sports]) if site_sports else Polygon()
        if uid == '1910053968':
            # The promenade enters through Art Park; its direct road approach crosses a building.
            park = next(garden for garden in gardens if garden['site'] == '1910053970')
            site_street_targets = union_all([site_street_targets, *[Polygon(rings[0], rings[1:])
                for rings in park['paths']]])
        paths, access, linework, path_samples, rejected = path_network(
            uid, site, safe, source_union, site_street_targets, site_carriageways,
            ground if uid == '1910071209' else site_land,
            site_building_clearance, site_lots, pavement_patches, paving_margin)
        path_component_rejections.extend(rejected)
        sample_clearance = 1.1
        for access_part in geometry_polygons(access):
            point = polylabel(access_part, tolerance=.1)
            if access_part.boundary.distance(point) > sample_clearance:
                path_samples.append([point.x, point.y])
        if not path_samples:
            raise ValueError('Garden path lacks an interior paving-mask sample: ' + uid)
        for source_id, poly, props in site_sports:
            clipped = make_valid(poly.intersection(site).intersection(safe))
            if clipped.is_empty or clipped.area < 20:
                raise ValueError('Source sports outline was lost during safe-area clipping: ' + source_id)
            style, style_note = (football_style(uid, source_id, poly.area) if props['USAGETYPE'] == 'FOF'
                                 else (KINDS[props['USAGETYPE']], 'Source sport category from iB1000.'))
            source_sport_ids.add(source_id)
            for part in geometry_polygons(clipped):
                sample = polylabel(part, tolerance=.1)
                surfaces.append(dict(site=uid, source_id=source_id, usage=props['USAGETYPE'], kind=style,
                                     rings=geometry_rings(part), triangles=polygon_triangles(part),
                                     sample=[sample.x, sample.y]))
            # The Blender script receives only intact, source-contained rectangles.
            if props['USAGETYPE'] != 'RAT' and clipped.symmetric_difference(poly.intersection(site)).area < .01 and site.covers(poly) and safe.covers(poly):
                fitting = sport_fitting_rectangle(poly, source_id)
                if fitting is not None:
                    coords = list(fitting.exterior.coords)[:-1]
                    if math.dist(coords[0], coords[1]) > math.dist(coords[1], coords[2]):
                        coords = coords[1:] + coords[:1]
                    center = fitting.centroid
                    axis = (coords[2][0] - coords[1][0], coords[2][1] - coords[1][1])
                    length = math.hypot(*axis)
                    if length > 1:
                        sports.append(dict(site=uid, source_id=source_id, usage=props['USAGETYPE'], kind=style,
                                           classification=style_note, center=[center.x, center.y],
                                           forward=[axis[0] / length, axis[1] / length],
                                           width=math.dist(coords[0], coords[1]), length=length))
        sport_block = source_union.buffer(4) if not source_union.is_empty else Polygon()
        planting = fixture_ground.difference(union_all([sport_block, paths.buffer(3.5), access.buffer(3.5), site_prop_roads]))
        rng = random.Random(int(uid))
        props_out = []
        xmin, zmin, xmax, zmax = site.bounds
        spacing = 13 if site.area < 30000 else 19
        jitter = min(3, spacing * .16)
        for x in range(math.ceil(xmin / spacing) * spacing, math.floor(xmax), spacing):
            for z in range(math.ceil(zmin / spacing) * spacing, math.floor(zmax), spacing):
                point = Point(x + rng.uniform(-jitter, jitter), z + rng.uniform(-jitter, jitter))
                radius = 1.6
                if planting.covers(point.buffer(radius)):
                    if any(point.distance(existing) < radius + existing_radius + 2 for existing, existing_radius in global_fixture_points):
                        continue
                    item = dict(site=uid, asset='banyan' if len(props_out) % 4 == 0 else 'street-tree',
                                position=[point.x, point.y], yaw=rng.uniform(0, math.tau), radius=radius,
                                scale=.52 if len(props_out) % 4 == 0 else .62)
                    props_out.append(item)
                    global_fixture_points.append((point, radius))

        # Benches sit off path edges with clear approach corridors and source/building/road clearance.
        for line in linework:
            for segment in (line,) if line.geom_type == 'LineString' else getattr(line, 'geoms', ()):
                if segment.length < 24:
                    continue
                for d in range(12, int(segment.length), 26):
                    centre = segment.interpolate(d)
                    before = segment.interpolate(max(0, d - 1))
                    after = segment.interpolate(min(segment.length, d + 1))
                    dx, dz = after.x - before.x, after.y - before.y
                    length = math.hypot(dx, dz)
                    if length < .01:
                        continue
                    normal = (-dz / length, dx / length)
                    for side in (-1, 1):
                        point = Point(centre.x + normal[0] * side * 3.5, centre.y + normal[1] * side * 3.5)
                        radius = 1.05
                        if not fixture_ground.covers(point.buffer(radius)) or paths.distance(point) < 1.1 or access.distance(point) < 2.5:
                            continue
                        if source_union.distance(point) < 5 or prop_roads.distance(point) < radius:
                            continue
                        if any(point.distance(existing) < radius + existing_radius + 4 for existing, existing_radius in global_fixture_points):
                            continue
                        item = dict(site=uid, asset='bench', position=[point.x, point.y],
                                    yaw=math.atan2(-dx, -dz), radius=radius, scale=1)
                        props_out.append(item)
                        global_fixture_points.append((point, radius))
                        break

        if not any(f['asset'] in ('street-tree', 'banyan') for f in props_out):
            # Narrow court-side beds can miss the tree grid; fit a planter to usable planting ground.
            for part in geometry_polygons(planting):
                point = polylabel(part, tolerance=.1)
                radius = 1.1
                if not part.covers(point.buffer(radius)):
                    continue
                if any(point.distance(existing) < radius + existing_radius + 2 for existing, existing_radius in global_fixture_points):
                    continue
                props_out.append(dict(site=uid, asset='planter', position=[point.x, point.y], yaw=0,
                                      radius=radius, scale=1))
                global_fixture_points.append((point, radius))
                break
        if uid in SIT_OUT_SITE_IDS and not any(f['asset'] == 'bench' for f in props_out):
            position, scale = SIT_OUT_BENCH_POSITIONS[uid]
            point = Point(position)
            radius = 1.05 * scale
            if not paths.covers(point.buffer(radius)):
                raise ValueError('Sitting-out bench does not fit on the existing paved area: ' + uid)
            if any(point.distance(Point(sample)) < (3.0 if scale == 1 else 2.7)
                   for sample in path_samples):
                raise ValueError('Sitting-out bench is too close to its paving probe: ' + uid)
            if access.distance(point) < (2.15 if scale == 1 else radius + .75):
                raise ValueError('Sitting-out bench blocks its entrance clearance: ' + uid)
            if any(point.distance(existing) < radius + existing_radius + 4
                   for existing, existing_radius in global_fixture_points):
                raise ValueError('Sitting-out bench overlaps another fixture: ' + uid)
            props_out.append(dict(site=uid, asset='bench', position=list(position),
                                  yaw=0, radius=radius, scale=scale))
            global_fixture_points.append((point, radius))
        if uid in COMPACT_PLAZA_SITE_IDS:
            # Fit furniture only where the paved ground can still support a walking ring.
            # Dorset's street buffers overlap the plot. The site clearance already reserves
            # 3.5 m beyond each surface carriageway, enough for compact seating here.
            compact_road_clearance = site_roads if uid == '1502005648' else site_prop_roads
            candidates = []
            for part in geometry_polygons(paths):
                boundary = LineString(part.exterior.coords)
                centre = part.representative_point()
                for distance_along in range(1, int(boundary.length), 2):
                    edge = boundary.interpolate(distance_along)
                    dx, dz = centre.x - edge.x, centre.y - edge.y
                    length = math.hypot(dx, dz)
                    if length < .01:
                        continue
                    direction = (dx / length, dz / length)
                    for inset in (2, 3, 4, 5, 6):
                        candidates.append(Point(edge.x + direction[0] * inset,
                                                edge.y + direction[1] * inset))
            for asset, radius, minimum_distance in (('bench', 1.05, 3),
                                                     ('planter', 1.1, 2.5),
                                                     ('planter', 1.1, 2.5)):
                placed = False
                for point in candidates:
                    if not fixture_ground.covers(point.buffer(radius)) or not paths.covers(
                            point.buffer(radius + (.4 if asset == 'bench' else 0))):
                        continue
                    if any(point.distance(Point(sample)) < minimum_distance for sample in path_samples):
                        continue
                    if access.distance(point) < 2.15 or compact_road_clearance.distance(point) < radius:
                        continue
                    separation = 4 if asset == 'bench' else 2
                    if any(point.distance(existing) < radius + existing_radius + separation
                           for existing, existing_radius in global_fixture_points):
                        continue
                    item = dict(site=uid, asset=asset, position=[point.x, point.y], yaw=0,
                                radius=radius, scale=1)
                    props_out.append(item)
                    global_fixture_points.append((point, radius))
                    placed = True
                    break
                if not placed:
                    raise ValueError('Compact plaza could not fit its bench and planting safely: ' + uid)
        if uid not in SITE_WITHOUT_FIXTURE_REQUIREMENT and (
                len(props_out) < 3 or not any(f['asset'] in ('street-tree', 'banyan', 'planter') for f in props_out)):
            raise ValueError('Site has too few clear planting or furniture fixtures: ' + uid)
        fixtures.extend(props_out)
        paved = make_valid(union_all([paths, access]))
        for part in geometry_polygons(paved):
            paving.extend(polygon_triangles(part))
        path_rings = [geometry_rings(part) for part in geometry_polygons(paths)]
        access_rings = [geometry_rings(part) for part in geometry_polygons(access)]
        gardens.append(dict(site=uid, rings=[geometry_rings(part) for part in geometry_polygons(site)],
                            paths=path_rings, access=access_rings, samples=path_samples,
                            paving_area_m2=round(paved.area, 2)))
        sites_out.append(dict(id=uid, name=name, source_area_m2=round(site.area, 2),
                              bounds=list(site.bounds), fixtures=len(props_out)))

    if len(gardens) != len(SITES) or len({s['source_id'] for s in sports}) != len(sports):
        raise ValueError('Every reviewed site must have one garden and unique sports fittings')
    surface_shapes = [Polygon(s['rings'][0], s['rings'][1:]) for s in surfaces]
    for item, poly in zip(surfaces, surface_shapes):
        if poly.intersection(all_lots).area > .01 or poly.intersection(site_regions[item['site']][0]).area > .01:
            raise ValueError('Source sports surface overlaps a building or road: ' + item['source_id'])
    minimum_fixtures = 3 * (len(SITES) - len(SITE_WITHOUT_FIXTURE_REQUIREMENT & SITES.keys()))
    if source_sport_ids != EXPECTED_SPORTS or len(surfaces) < len(EXPECTED_SPORTS) or \
            len(fixtures) < minimum_fixtures or not paving:
        raise ValueError('East recreation source geometry or authored details are incomplete')
    all_x = [site['bounds'][i] for site in sites_out for i in (0, 2)]
    all_z = [site['bounds'][i] for site in sites_out for i in (1, 3)]
    min_x, min_z = math.floor(min(all_x)), math.floor(min(all_z))
    max_x, max_z = math.ceil(max(all_x)), math.ceil(max(all_z))
    classification = {
        'note': 'Government iB1000 outlines are retained. Surface finish is game styling; gateball outlines receive simple court markings, small football outlines are styled as hard courts, and identified turf fields remain fields.',
        'references': [HOI_SHAM_REFERENCE, TO_KWA_WAN_REFERENCE, FOOTBALL_REFERENCE,
                       KGV_FOOTBALL_REFERENCE, SYCAMORE_FOOTBALL_REFERENCE,
                       TUNG_CHAU_REFERENCE, MAPLE_STREET_REFERENCE,
                       TAI_HANG_TUNG_PLAN_REFERENCE, PERTH_FOOTBALL_REFERENCE],
        'hard_football_ids': ['1500001702', '1500001703', '1500001706', '1500002363',
                             '1500001698', '1500001699', '1500001652', '1500001948', '1500001949',
                             '1500001977', '1500002075', '1500002078', '1500002094', '1500002093',
                             '1500002030', '1500002066'],
        'turf_football_ids': ['1500001881', '1500001883', '1500001874'],
        'gateball_ids': sorted(GATEBALL_IDS)
    }
    source_metadata = raw['metadata']
    metadata = dict(provider=source_metadata['provider'], source=source_metadata['source'],
                    retrieved_utc=raw['metadata']['retrieved_utc'], source_sha256=hashlib.sha256(source).hexdigest(),
                    inputs_sha256=inputs, origin_wgs84=ORIGIN, source_revisions=raw['metadata']['site_revisions'],
                    sports_revisions=raw['metadata']['sports_revisions'],
                    index_url=source_metadata['index_url'], bbox_wgs84=source_metadata['bbox_wgs84'],
                    index_sha256=source_metadata['index_sha256'], index_sources=source_metadata['index_sources'],
                    tile_manifest_sha256=source_metadata['tile_manifest_sha256'],
                    source_manifests=source_metadata['source_manifests'], source_tiles=source_metadata['tiles'],
                    source_feature_count=len(raw['features']),
                    source_site_fragment_count=sum(len(tiles) for tiles in EXPECTED_SITE_FRAGMENTS.values()) + len(KOWLOON_CITY_SITES),
                    source_sport_fragment_count=sum(len(tiles) for tiles in EXPECTED_SPORT_FRAGMENTS.values()) + len(KOWLOON_CITY_SPORTS),
                    known_wip_annotations=raw['metadata']['known_wip_annotations'],
                    western_path_component_rejections=path_component_rejections,
                    source_classification=classification,
                    note='Source-bounded Kowloon and western New Territories open spaces. The Kowloon City records come from CEDD’s iB1000 service. Salisbury Garden and Tsim Sha Tsui Promenade are scoped to current shared ground support. Source sports are clipped clear of current building layouts and roads. Paths, access, paving, planting, benches, planters and surface finish are authored approximations; source dates do not establish current access or venue status.')
    output = {'metadata': metadata, 'bounds': [min_x, min_z, max_x - min_x, max_z - min_z],
              'sites': sites_out, 'surfaces': surfaces, 'paving': paving, 'fixtures': fixtures,
              'sports': sports, 'gardens': gardens, 'play_areas': []}
    from import_southwest_public_spaces import add_southwest_public_spaces
    add_southwest_public_spaces(
        output, ROOT / 'Data/southwest-public-spaces-source.geojson',
        ground=ground, lots=all_lots,
        road_hard=west_regions['west-kowloon'][0],
        street_targets=west_regions['west-kowloon'][3],
        district_roads=district_roads, inputs_sha256=inputs)
    trim_reservoir_paving(output)
    return encoded(output)


def validate_layout(source, target):
    from import_southwest_public_spaces import SITE_NAMES, validate_southwest_public_spaces

    raw = combined_source(source)
    data = json.loads(target)
    if data['metadata'].get('source_manifests') != raw['metadata']['source_manifests']:
        raise AssertionError('Derived open spaces do not match their supplemental survey provenance')
    layout_sports = {str(surface.get('source_id')) for surface in data.get('surfaces', [])}
    if layout_sports != EXPECTED_SPORTS:
        raise AssertionError(f'Derived surfaces differ from reviewed source IDs; missing={sorted(EXPECTED_SPORTS-layout_sports)}; unexpected={sorted(layout_sports-EXPECTED_SPORTS)}')
    reviewed_sites = EXPECTED_SITE_IDS | SITE_NAMES.keys()
    if {s['id'] for s in data.get('sites', [])} != reviewed_sites or len(data['sites']) != len(reviewed_sites):
        raise AssertionError('Expected all reviewed open spaces and both southwest waterfront sites')
    if data.get('play_areas') != [] or len(data['gardens']) != len(reviewed_sites) or {g['site'] for g in data['gardens']} != reviewed_sites:
        raise AssertionError('Unexpected authored play areas or duplicate garden IDs')
    minimum_fixtures = 3 * (len(SITES) - len(SITE_WITHOUT_FIXTURE_REQUIREMENT & SITES.keys()))
    if len(data.get('surfaces', [])) < len(EXPECTED_SPORTS) or len(data.get('fixtures', [])) < minimum_fixtures:
        raise AssertionError('Missing source sports or authored garden details')
    expected_source = defaultdict(list)
    for feature in raw.get('features', []):
        props = feature['properties']
        if props.get('layer') == 'Site':
            expected_source[props['SITEID']].append(source_local(feature))
    if set(expected_source) != set(SITES):
        raise AssertionError('Source GeoJSON is missing a complete site boundary')
    inputs = data.get('metadata', {}).get('inputs_sha256', {})
    expected_inputs = {str(path.relative_to(ROOT)) for path in ROOT.glob('Data/*layout.json')}
    expected_inputs.update(str(path.relative_to(ROOT)) for path in COAST_FILES)
    expected_inputs.add('Data/cross-harbour.json')
    expected_inputs.add('Data/nathan-road.json')
    expected_inputs.add('Data/southwest-public-spaces-source.geojson')
    if set(inputs) != expected_inputs or len([p for p in inputs if p.endswith('layout.json')]) != 9:
        raise AssertionError('All nine building layouts, current roads and five coastal land inputs must be hashed')
    if not data['metadata'].get('known_wip_annotations'):
        raise AssertionError('Known Carpenter Road WIP annotation was lost')

    def polygons(rings_list):
        return union_all([Polygon(rings[0], rings[1:]) for rings in rings_list])

    land_by_site = site_land_geometries()
    source_sites = {uid: union_all(parts).intersection(land_by_site[uid]) for uid, parts in expected_source.items()}
    gardens = {g['site']: g for g in data['gardens']}
    surface_ids = [s['source_id'] for s in data['surfaces']]
    sport_ids = [s['source_id'] for s in data['sports']]
    if len(set(sport_ids)) != len(sport_ids):
        raise AssertionError('A source sport outline is fitted more than once')
    for uid in SITES:
        garden = gardens[uid]
        site = polygons(garden['rings'])
        if site.symmetric_difference(source_sites[uid]).area > .02:
            raise AssertionError(uid + ': source site geometry differs from retained iB1000')
        paths = polygons(garden['paths'])
        access = polygons(garden['access']) if garden['access'] else Polygon()
        paved = union_all([paths, access])
        if paths.area < 80 or paths.difference(site).area > .01 or garden['paving_area_m2'] != round(paved.area, 2):
            raise AssertionError(uid + ': missing source-bounded interior paving')
        sample_clearance = 1.1
        if not garden['samples'] or any(not paved.covers(Point(sample)) or paved.boundary.distance(Point(sample)) <= sample_clearance for sample in garden['samples']):
            raise AssertionError(uid + ': paving samples are too close to a path edge')
        for part in geometry_polygons(paved):
            if part.area >= 1 and not any(part.covers(Point(sample)) for sample in garden['samples']):
                raise AssertionError(uid + ': retained paving component has no connectivity probe')
        if access.is_empty or access.intersection(paths).area < .1:
            raise AssertionError(uid + ': missing connected site access polygons')
        if uid in SIT_OUT_SITE_IDS and not any(f['site'] == uid and f['asset'] == 'bench'
                                               for f in data['fixtures']):
            raise AssertionError(uid + ': sitting-out area bench missing')
        if uid in SIT_OUT_SITE_IDS:
            position, scale = SIT_OUT_BENCH_POSITIONS[uid]
            bench = next(f for f in data['fixtures'] if f['site'] == uid and f['asset'] == 'bench')
            point = Point(position)
            radius = 1.05 * scale
            if bench['position'] != list(position) or bench['radius'] != radius or bench['scale'] != scale:
                raise AssertionError(uid + ': authored sitting-out bench position or size changed')
            if not paths.covers(point.buffer(radius)) or any(
                    point.distance(Point(sample)) < (3.0 if scale == 1 else 2.7)
                    for sample in garden['samples']) or \
                    access.distance(point) < (2.15 if scale == 1 else radius + .75):
                raise AssertionError(uid + ': sitting-out bench blocks a paving probe or entrance')
        if uid in COMPACT_PLAZA_SITE_IDS:
            fixtures = [fixture for fixture in data['fixtures'] if fixture['site'] == uid]
            benches = [fixture for fixture in fixtures if fixture['asset'] == 'bench']
            planters = [fixture for fixture in fixtures if fixture['asset'] == 'planter']
            if len(benches) != 1 or len(planters) < 2:
                raise AssertionError(uid + ': compact plaza needs one bench and two planters')
            point = Point(benches[0]['position'])
            walk_ring = point.buffer(benches[0]['radius'] + .4).boundary
            if not paths.covers(walk_ring) or any(point.distance(Point(sample)) < 3
                                                  for sample in garden['samples']) or \
                    access.distance(point) < 2.15:
                raise AssertionError(uid + ': compact-plaza bench lacks clear surrounding walk and entrance')
        if uid in SITE_WITHOUT_FIXTURE_REQUIREMENT:
            continue
        if len([f for f in data['fixtures'] if f['site'] == uid]) < 3:
            raise AssertionError(uid + ': useful garden fixtures missing')
        if not any(f['site'] == uid and f['asset'] == 'bench' for f in data['fixtures']):
            raise AssertionError(uid + ': bench missing')
        if not any(f['site'] == uid and f['asset'] in ('street-tree', 'banyan', 'planter') for f in data['fixtures']):
            raise AssertionError(uid + ': planting missing')
    for source_id in set(surface_ids):
        patches = [Polygon(s['rings'][0], s['rings'][1:]) for s in data['surfaces'] if s['source_id'] == source_id]
        if sum(p.area for p in patches)-union_all(patches).area > .01:
            raise AssertionError('A government sports surface is duplicated: ' + source_id)
    _, lots, _, _, _, _, _, ground, west_regions, _, _ = safe_site_polygons()
    roads, _, _, street_targets, _ = west_regions['west-kowloon']
    validate_southwest_public_spaces(data, ROOT / 'Data/southwest-public-spaces-source.geojson', ground, lots, roads, street_targets)
    site_fragments = sum(len(tiles) for tiles in EXPECTED_SITE_FRAGMENTS.values()) + len(KOWLOON_CITY_SITES)
    sport_fragments = sum(len(tiles) for tiles in EXPECTED_SPORT_FRAGMENTS.values()) + len(KOWLOON_CITY_SPORTS)
    print(f'ANTILA_EAST_OPEN_SPACE_DATA_OK: {len(data["sites"])} government sites; '
          f'{site_fragments} Site fragments; {len(EXPECTED_SPORTS)} source sports across {sport_fragments} sheet fragments; '
          f'{len(data["surfaces"])} rendered surfaces; {len(data["sports"])} intact rectangle fittings; '
          f'{len(data["fixtures"])} authored fixtures')


def preserve_unchanged_park_layouts(layout, previous_layout):
    current=json.loads(layout)
    previous=json.loads(previous_layout)
    old_sites={site['id']:site for site in previous['sites']}
    new_sites={site['id']:site for site in current['sites']}
    old_gardens={garden['site']:garden for garden in previous['gardens']}
    new_gardens={garden['site']:garden for garden in current['gardens']}
    old_fixtures=defaultdict(list)
    new_fixtures=defaultdict(list)
    for fixture in previous['fixtures']:
        old_fixtures[fixture['site']].append(fixture)
    for fixture in current['fixtures']:
        new_fixtures[fixture['site']].append(fixture)

    def garden_geometry(garden,field):
        return union_all([Polygon(rings[0],rings[1:]) for rings in garden[field]])

    unchanged_sites=set()
    for uid in old_gardens.keys() & new_gardens.keys():
        if not all(old_sites[uid][field]==new_sites[uid][field]
                   for field in ('id','name','bounds','source_area_m2')):
            continue
        old_garden,new_garden=old_gardens[uid],new_gardens[uid]
        if not all(garden_geometry(old_garden,field).symmetric_difference(
                   garden_geometry(new_garden,field)).area<=.01
                   for field in ('rings','paths','access')):
            continue
        paved=union_all([garden_geometry(new_garden,'paths'),
                         garden_geometry(new_garden,'access')])
        samples=[Point(sample) for sample in new_garden['samples']]
        if not samples or any(not paved.covers(sample) or
                              paved.boundary.distance(sample)<=1.1 for sample in samples):
            continue
        if any(not any(part.covers(sample) for sample in samples)
               for part in geometry_polygons(paved) if part.area>=1):
            continue
        unchanged_sites.add(uid)

    current['gardens']=[old_gardens[garden['site']] if garden['site'] in unchanged_sites else garden
                         for garden in current['gardens']]
    current['sites']=[old_sites[site['id']] if site['id'] in unchanged_sites else site
                      for site in current['sites']]
    current['fixtures']=[fixture for site in current['sites']
                         for fixture in (old_fixtures if site['id'] in unchanged_sites else
                                         new_fixtures)[site['id']]]
    if sum(site['fixtures'] for site in current['sites'])!=len(current['fixtures']):
        raise ValueError('Preserved site fixture counts do not match the fixture records')
    return encoded(current)


def refresh(cache=None, manifest=None, source_path=SOURCE, target_path=TARGET):
    source = extract(cache, manifest) if cache is not None else source_path.read_bytes()
    validate_source_fragments(source)
    layout = build(source)
    if target_path.is_file():
        previous=target_path.read_bytes()
        current_metadata=json.loads(layout)['metadata']
        previous_metadata=json.loads(previous).get('metadata',{})
        if previous_metadata.get('source_sha256')==current_metadata['source_sha256'] and \
                previous_metadata.get('inputs_sha256')==current_metadata['inputs_sha256'] and \
                previous_metadata.get('source_manifests')==current_metadata['source_manifests']:
            layout=preserve_unchanged_park_layouts(layout,previous)
    validate_layout(source, layout)
    outputs = ([(source_path, source)] if cache is not None else []) + [(target_path, layout)]
    replace_outputs(outputs)
    data = json.loads(layout)
    print('ANTILA_EAST_OPEN_SPACE_IMPORT_OK:', len(data['surfaces']), 'source surfaces;',
          len(data['sports']), 'intact sport fittings;', len(data['fixtures']), 'fixtures;',
          len(data['paving']), 'paving triangles')


if __name__ == '__main__':
    if '--extract' in sys.argv:
        refresh(Path(sys.argv[sys.argv.index('--extract') + 1]), Path(sys.argv[sys.argv.index('--extract') + 2]))
    else:
        refresh()
