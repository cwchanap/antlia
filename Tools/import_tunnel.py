"""TD centreline KMZ -> metre-scale Cross-Harbour extension. Regeneration needs Shapely.

Run: .venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-centerline.kmz --hk1980
The source supplies XY, travel direction and relative road levels; metric elevations are authored.
"""
import datetime
import hashlib
import heapq
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from shapely import constrained_delaunay_triangles
from shapely.geometry import LineString, Point, box, shape, mapping
from shapely.ops import unary_union
from import_map import ROOT, NS, SOURCE, ORIGIN, local

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
NORTHWEST_BOUNDS = (-4600,-6000,0,-3900)
KWAI_CHUNG_BOUNDS = (-6500,-8500,-3100,-4400)
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

def build(source):
    coast_data=json.loads((ROOT/'Data/west-kowloon-coast.json').read_text())
    northwest_coast=json.loads((ROOT/'Data/lai-chi-kok-coast.json').read_text())
    # Keep the established coast exactly; only add land outside its earlier map rectangle.
    west_land=unary_union([shape(coast_data['land']),shape(northwest_coast['land']).difference(box(*WEST_BOUNDS))])
    assert west_land.is_valid and west_land.geom_type=='Polygon', 'Northwest land must join the existing mainland'
    kwai_chung_coast=json.loads((ROOT/'Data/kwai-chung-coast.json').read_text())
    prior_region=unary_union([box(*WEST_BOUNDS),box(*NORTHWEST_BOUNDS)])
    west_land=unary_union([west_land,shape(kwai_chung_coast['land']).difference(prior_region)])
    assert west_land.is_valid and west_land.geom_type=='Polygon', 'Kwai Chung land must join the existing mainland'
    island_coast=json.loads((ROOT/'Data/island-coast.json').read_text())
    island=shape(island_coast['land'])
    district_data=json.loads((ROOT/'Data/nathan-road.json').read_text())
    old_district=box(*district_data['bounds'])
    old_kowloon=unary_union([old_district,box(*KOWLOON_BOUNDS)])
    ids = set(SOUTH+ISLAND+NORTH+[i.lstrip("-") for i in SCENIC+CENTRAL+KOWLOON+WEST+SHAM_SHUI_PO+LAI_CHI_KOK+KWAI_CHUNG])
    # Current TD KMZ uses HK1980 geographic coordinates and renumbers KML IDs.
    # ROUTE_ID is the stable source key. Pin old sections to their source snapshot
    # and validate the datum against shared geometry before connecting new roads.
    previous = json.loads((ROOT/'Data/cross-harbour-source.geojson').read_text())
    existing = {f['properties']['ROUTE_ID']:f for f in previous['features']}
    transform = None
    if '--hk1980' in sys.argv:
        from pyproj import Transformer
        transform = Transformer.from_crs(4611,4326,always_xy=True)
    source_hash = hashlib.file_digest(open(source,'rb'),'sha256').hexdigest()
    records = {}; matched = 0; changed = []
    with zipfile.ZipFile(source) as archive, archive.open('doc.kml') as stream:
        for _, element in ET.iterparse(stream, events=('end',)):
            if element.tag != f"{{{NS['k']}}}Placemark":
                continue
            props = dict(re.findall(r'<td>([A-Z_]+)</td>\s*<td>(.*?)</td>', element.findtext('k:description','',NS)))
            prior = existing.get(props.get('ROUTE_ID'))
            ident = prior['properties']['source_id'] if prior else 'TD_'+props['ROUTE_ID']
            if prior or ident in ids or props.get('ELEVATION')=='0':
                coords = [list(map(float,w.split(','))) for w in element.find('.//k:coordinates',NS).text.split()]
                if transform:coords = [[*transform.transform(*p[:2]),p[2]] for p in coords]
                if prior:
                    before=LineString([local(p) for p in prior['geometry']['coordinates']])
                    after=LineString([local(p) for p in coords])
                    if before.hausdorff_distance(after)<.025 and math.dist(before.coords[0],after.coords[0])<.025:matched+=1
                    else:changed.append(ident)
                    coords=prior['geometry']['coordinates']
                line=LineString([local(p) for p in coords])
                north=props.get('STREET_ENAME') in KOWLOON_STREETS and line.bounds[1]<KOWLOON_BOUNDS[3] and box(KOWLOON_BOUNDS[0],KOWLOON_BOUNDS[1],KOWLOON_BOUNDS[2],-1130).covers(line.buffer(12))
                name=props.get('STREET_ENAME','')
                west=props.get('ELEVATION')=='0' and props.get('TRAVEL_DIRECTION')!='4' and name not in ('','-99','&lt;Null&gt;') and not any(s in name for s in ('HIGHWAY','CROSSING','CORRIDOR','FLYOVER','INTERCHANGE')) and west_land.covers(line.buffer(12)) and line.difference(old_kowloon).length>1
                if ident in ids or prior or north or west or (name in ISLAND_STREETS and island.covers(line.buffer(12))):
                    records[ident] = prior if prior else {'type':'Feature','properties':dict(props, source_id=ident, source_sha256=source_hash),
                                      'geometry':{'type':'LineString','coordinates':coords}}
            element.clear()
    assert ids <= records.keys(), 'Source road IDs changed; review the extract before rebuilding.'
    assert matched>400, 'Road datum does not agree with the existing map'
    print('ANTILA_ROAD_DATUM_OK:',matched,'shared sections within 2.5 cm; pinned older revisions:',changed)
    original = {i:LineString([local(p) for p in f['geometry']['coordinates']]) for i,f in records.items()}
    # Retain only the connected island street component; source coordinates stay unmodified.
    nodes = {}
    for ident,line in original.items():
        for p in (line.coords[0],line.coords[-1]):nodes.setdefault(tuple(round(v,1) for v in p),set()).add(ident)
    retained={f['properties']['source_id'] for f in previous['features']}
    assert retained <= records.keys(), 'Previously imported streets must remain present'
    connected=set(ids)|retained;pending=list(connected)
    while pending:
        line=original[pending.pop()]
        for p in (line.coords[0],line.coords[-1]):
            for ident in nodes[tuple(round(v,1) for v in p)]-connected:connected.add(ident);pending.append(ident)
    # Preserve earlier road order as well as geometry (seeded scenery uses this order).
    records={i:records[i] for i in [f['properties']['source_id'] for f in previous['features']]+[i for i in records if i not in retained] if i in connected}
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
    adjacent={};ends={};incident={};deck={i for i,r in records.items() if r['properties']['ELEVATION']=='1'}
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
            else:y=deck_height(ident,d,line.length)
            points.append([round(x,4),round(y,4),round(z,4)])
        elevated=any(p[1]>.01 for p in points)
        # Retain turning room at the tight Hung Hing / Tonnochy approach below the flyover.
        width=12 if ident in wide_junctions else 6 if elevated else 12
        roads.append({'id':ident,'name':records[ident]['properties']['STREET_ENAME'],
                      'tunnel':ident in tube_info,'ramp':ident in ('ID_024204','ID_024201'),
                      'elevated':elevated,'source_level':int(records[ident]['properties']['ELEVATION']),
                      'width':9.1 if ident in tube_info else width,
                      'points':points})
    by_id = {r['id']:r for r in roads}
    routes = []
    for name,members in [('Hung Hom → Hong Kong Island',SOUTH),('Wan Chai return loop',ISLAND),('Hong Kong Island → Kowloon',NORTH),('Wan Chai / Causeway Bay scenic drive',SCENIC),('Admiralty / Central loop',CENTRAL),('Jordan → Yau Ma Tei → Mong Kok',KOWLOON),('West Kowloon → Tai Kok Tsui → Sham Shui Po',WEST),('Mong Kok → Sham Shui Po',SHAM_SHUI_PO),('Sham Shui Po → Cheung Sha Wan → Lai Chi Kok',LAI_CHI_KOK),('Mei Foo → Lai King → Kwai Chung',KWAI_CHUNG)]:
        points = []
        for ident in members:
            reverse=ident.startswith('-');ident=ident.lstrip('-')
            p = by_id[ident]['points']
            if members in (WEST,SHAM_SHUI_PO,LAI_CHI_KOK,KWAI_CHUNG):
                assert records[ident]['properties']['TRAVEL_DIRECTION'] in (('1','2') if reverse else ('1','3')), 'New drive violates source travel direction'
            if reverse:
                assert records[ident]['properties']['TRAVEL_DIRECTION'] in ('1','2'), 'Source direction forbids reversing this section'
                # ID_026889 is already reversed for the original island route.
                if ident!='ID_026889':p=p[::-1]
            assert not points or math.dist(points[-1],p[0]) < .12, (name,ident,'gap')
            points.extend(p if not points else p[1:])
        routes.append({'name':name,'source_ids':members,'points':points})
        if members in (WEST,SHAM_SHUI_PO,LAI_CHI_KOK,KWAI_CHUNG):
            for a,b,c in zip(points,points[1:],points[2:]):
                dot=sum((b[i]-a[i])*(c[i]-b[i]) for i in range(3))/(math.dist(a,b)*math.dist(b,c))
                assert dot>-.5, (name,'Drive turns back sharply; choose a continuous source route')
    assert math.dist(routes[4]['points'][0],routes[4]['points'][-1])<.12, 'Central loop must close'
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
    # shortcut: this inland map edge is authored, replace it when eastern Kowloon is sourced.
    district = box(bounds[0]-110,bounds[1]-130,bounds[2]+110,bounds[3]+120)
    kowloon=unary_union([district,box(*KOWLOON_BOUNDS),west_land])
    land = unary_union([kowloon,island])
    for road in roads:
        if not road['tunnel']:
            carriageway=LineString([(p[0],p[2]) for p in road['points']]).buffer(road['width']/2)
            assert carriageway.difference(land).area<.01, (road['id'],road['name'],'carriageway outside land')
    # Flat cutout ends must meet the tunnel floors without extending past their endpoints.
    ground = land.difference(unary_union(cutouts))
    for street in district_data['side_roads']:
        assert ground.covers(LineString(street['points']).buffer(9)), (street['name'],'portal cut breaks the existing street')
    water = box(KWAI_CHUNG_BOUNDS[0]-500,KWAI_CHUNG_BOUNDS[1]-250,2550,2350).difference(land)
    water_triangles = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(water).geoms]
    for road in roads:
        for x,y,z in road['points']:
            if road['tunnel'] and -6.5 < y < -1:
                assert ground.distance(Point(x,z)) > 4.5, 'Ground crosses a portal opening'
    surface = unary_union([LineString([(p[0],p[2]) for p in r['points']]).buffer(r['width']/2) for r in roads if not r['tunnel'] and not r['elevated']]).difference(unary_union(cutouts))
    surface_triangles = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(surface).geoms]
    ground_triangles = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(ground).geoms]
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
        'note':'Original XY preserved in approximate local metre coordinates. ELEVATION is a relative road level, not metres. Depth 32 m, widths (6 m elevated carriageways; 12 m at the low Hung Hing / Tonnochy approach), 5.6 m tunnel interior and 7 m elevated decks with cosine ramps over 150 m outside shared level junction aprons are authored. Aprons extend until adjoining centreline branches separate by 7.5 m. Shorelines derive from LandsD iB1000 with recorded gap repairs. Turn restrictions are not inferred.'}
    # Only outer edges remain: remove old internal north/west fences at the map seams.
    border=kowloon.boundary.intersection(box(KWAI_CHUNG_BOUNDS[0],KWAI_CHUNG_BOUNDS[1],WEST_BOUNDS[2],WEST_BOUNDS[3])).difference(district.buffer(.1))
    shore=unary_union([*[LineString(p) for p in coast_data['coastline']],
        unary_union([LineString(p) for p in northwest_coast['coastline']]).difference(box(*WEST_BOUNDS)),
        unary_union([LineString(p) for p in kwai_chung_coast['coastline']]).difference(prior_region)]).difference(district.buffer(.1))
    def line_parts(g):
        return [list(p.coords) for p in (g.geoms if hasattr(g,'geoms') else [g]) if p.geom_type=='LineString' and p.length>.5]
    output = {'metadata':metadata,'bounds':[KWAI_CHUNG_BOUNDS[0]-80,KWAI_CHUNG_BOUNDS[1]-80,ISLAND_BOUNDS[2]+80,ISLAND_BOUNDS[3]+50], 'island_bounds':ISLAND_BOUNDS, 'kowloon_north_bounds':KOWLOON_BOUNDS,
              'island_land':island_coast['land'],'island_coastline':line_parts(unary_union([LineString(p) for p in island_coast['coastline']]).difference(unary_union(cutouts).buffer(1))),
              'island_boundary':line_parts(island.boundary.intersection(box(*ISLAND_BOUNDS).boundary)), 'island_coast_metadata':island_coast['metadata'],
              'kowloon_west_land':mapping(west_land),'kowloon_coastline':line_parts(shore),'kowloon_boundary':line_parts(border.difference(shore.buffer(.3))), 'coast_metadata':coast_data['metadata'],
              'kowloon_northwest_bounds':NORTHWEST_BOUNDS,'northwest_coast_metadata':northwest_coast['metadata'],'kwai_chung_bounds':KWAI_CHUNG_BOUNDS,'kwai_chung_coast_metadata':kwai_chung_coast['metadata'],'roads':roads,
              'routes':routes,'tubes':tubes,'ground_triangles':ground_triangles,'water_triangles':water_triangles,'surface_triangles':surface_triangles}
    (ROOT/'Data/cross-harbour-source.geojson').write_text(json.dumps({'type':'FeatureCollection','metadata':metadata,'features':list(records.values())},ensure_ascii=False,separators=(',',':')))
    (ROOT/'Data/cross-harbour.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
    print('ANTILA_TUNNEL_DATA_OK:',len(roads),'source sections;',[(t['name'],round(t['length_m'],1)) for t in tubes],'; continuous routes',len(routes))


if __name__ == '__main__':
    build(Path(sys.argv[1]))
