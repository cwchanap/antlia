"""TD centreline KMZ -> metre-scale Cross-Harbour extension. Regeneration needs Shapely.

Run: .venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-centerline.kmz --hk1980
The source supplies XY and travel direction; the 32 m depth profile is authored.
"""
import datetime
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from shapely import constrained_delaunay_triangles
from shapely.geometry import LineString, Point, box
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

ISLAND_BOUNDS = (-2400,1100,2050,2100)
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

def build(source):
    ids = set(SOUTH+ISLAND+NORTH+[i.lstrip("-") for i in SCENIC+CENTRAL])
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
            if ident in ids or (props.get('STREET_ENAME') in ISLAND_STREETS and props.get('ELEVATION')=='0'):
                coords = [list(map(float,w.split(','))) for w in element.find('.//k:coordinates',NS).text.split()]
                if transform:coords = [[*transform.transform(*p[:2]),p[2]] for p in coords]
                if prior:
                    before=LineString([local(p) for p in prior['geometry']['coordinates']])
                    after=LineString([local(p) for p in coords])
                    if before.hausdorff_distance(after)<.025 and math.dist(before.coords[0],after.coords[0])<.025:matched+=1
                    else:changed.append(ident)
                    coords=prior['geometry']['coordinates']
                if ident in ids or box(*ISLAND_BOUNDS).covers(LineString([local(p) for p in coords]).buffer(12)):
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
    connected=set(ids);pending=list(ids)
    while pending:
        line=original[pending.pop()]
        for p in (line.coords[0],line.coords[-1]):
            for ident in nodes[tuple(round(v,1) for v in p)]-connected:connected.add(ident);pending.append(ident)
    records={i:r for i,r in records.items() if i in connected}
    original={i:r for i,r in original.items() if i in connected}
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
            points.append([round(x,4),round(y,4),round(z,4)])
        roads.append({'id':ident,'name':records[ident]['properties']['STREET_ENAME'],
                      'tunnel':ident in tube_info,'ramp':ident in ('ID_024204','ID_024201'),
                      'width':9.1 if ident in tube_info else 12,
                      'points':points})
    by_id = {r['id']:r for r in roads}
    routes = []
    for name,members in [('Hung Hom → Hong Kong Island',SOUTH),('Wan Chai return loop',ISLAND),('Hong Kong Island → Kowloon',NORTH),('Wan Chai / Causeway Bay scenic drive',SCENIC),('Admiralty / Central loop',CENTRAL)]:
        points = []
        for ident in members:
            reverse=ident.startswith('-');ident=ident.lstrip('-')
            p = by_id[ident]['points']
            if reverse:
                assert records[ident]['properties']['TRAVEL_DIRECTION']=='1', 'Only two-way source sections may be reversed'
                # ID_026889 is already reversed for the original island route.
                if ident!='ID_026889':p=p[::-1]
            assert not points or math.dist(points[-1],p[0]) < .12, (name,ident,'gap')
            points.extend(p if not points else p[1:])
        routes.append({'name':name,'source_ids':members,'points':points})
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
    district_data = json.loads((ROOT/'Data/nathan-road.json').read_text())
    bounds = district_data['bounds']
    district = box(bounds[0]-110,bounds[1]-120,bounds[2]+110,bounds[3]+120)
    # Authored land apron around the island roads; shoreline is scenery, not survey data.
    island = box(*ISLAND_BOUNDS)
    land = unary_union([district,island])
    ground = land.difference(unary_union(cutouts).buffer(.05))
    for street in district_data['side_roads']:
        assert ground.covers(LineString(street['points']).buffer(9)), (street['name'],'portal cut breaks the existing street')
    water = box(min(-2250,ISLAND_BOUNDS[0]-250),-550,2550,2350).difference(land)
    water_triangles = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(water).geoms]
    for road in roads:
        for x,y,z in road['points']:
            if road['tunnel'] and -6.5 < y < -1:
                assert ground.distance(Point(x,z)) > 4.5, 'Ground crosses a portal opening'
    surface = unary_union([LineString([(p[0],p[2]) for p in r['points']]).buffer(r['width']/2) for r in roads if not r['tunnel']]).difference(unary_union(cutouts))
    surface_triangles = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(surface).geoms]
    ground_triangles = [list(t.exterior.coords)[:3] for t in constrained_delaunay_triangles(ground).geoms]
    assert abs(sum(abs((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2 for a,b,c in ground_triangles)-ground.area)<.01
    metadata = {'provider':'Transport Department, HKSAR Government','source':SOURCE,
        'source_sha256':source_hash,
        'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'origin_wgs84':ORIGIN,
        'source_crs':'EPSG:4611' if transform else 'EPSG:4326',
        'retained_source_sha256':previous['metadata'].get('retained_source_sha256',previous['metadata']['source_sha256']),
        'coordinate_processing':'New roads: HK1980 geographic to WGS84 (EPSG:4611 to EPSG:4326). Existing roads pinned by stable ROUTE_ID to the retained source snapshot; over 400 shared sections validate the datum within 2.5 cm. Connected endpoints checked after conversion.' if transform else 'WGS84 coordinates used directly',
        'terms':'https://data.gov.hk/en/terms-and-conditions', 'world_units_per_metre':1,
        'dictionary':'https://static.data.gov.hk/td/road-network-v2/dataspec/rdnet_dataspec.zip',
        'tunnel_reference':'https://www.td.gov.hk/en/transport_in_hong_kong/tunnels_and_bridges_n/location_map/index_t.html',
        'note':'Original XY preserved. ELEVATION is a relative road level, not metres. Depth 32 m, widths, 5.6 m interior height, land aprons and scenery are authored. Selected approach levels are simplified; turn restrictions are not inferred.'}
    output = {'metadata':metadata,'bounds':[min(bounds[0],ISLAND_BOUNDS[0]-80),-1400,ISLAND_BOUNDS[2]+80,ISLAND_BOUNDS[3]+50], 'island_bounds':ISLAND_BOUNDS, 'roads':roads,
              'routes':routes,'tubes':tubes,'ground_triangles':ground_triangles,'water_triangles':water_triangles,'surface_triangles':surface_triangles}
    (ROOT/'Data/cross-harbour-source.geojson').write_text(json.dumps({'type':'FeatureCollection','metadata':metadata,'features':list(records.values())},ensure_ascii=False,separators=(',',':')))
    (ROOT/'Data/cross-harbour.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
    print('ANTILA_TUNNEL_DATA_OK:',len(roads),'source sections;',[(t['name'],round(t['length_m'],1)) for t in tubes],'; continuous routes',len(routes))


if __name__ == '__main__':
    build(Path(sys.argv[1]))
