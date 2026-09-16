"""TD centreline KMZ -> metre-scale Cross-Harbour extension. Regeneration needs Shapely.

Run: .venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-centerline.kmz
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


def build(source):
    ids = set(SOUTH+ISLAND+NORTH)
    records = {}
    with zipfile.ZipFile(source) as archive, archive.open('doc.kml') as stream:
        for _, element in ET.iterparse(stream, events=('end',)):
            if element.tag != f"{{{NS['k']}}}Placemark":
                continue
            ident = element.get('id')
            if ident in ids:
                props = dict(re.findall(r'<td>([A-Z_]+)</td>\s*<td>(.*?)</td>', element.findtext('k:description','',NS)))
                coords = [list(map(float,w.split(','))) for w in element.find('.//k:coordinates',NS).text.split()]
                records[ident] = {'type':'Feature','properties':dict(props, source_id=ident),
                                  'geometry':{'type':'LineString','coordinates':coords}}
            element.clear()
    assert records.keys() == ids, 'Source road IDs changed; review the extract before rebuilding.'
    original = {i:LineString([local(p) for p in f['geometry']['coordinates']]) for i,f in records.items()}
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
    for name,members in [('Hung Hom → Hong Kong Island',SOUTH),('Wan Chai return loop',ISLAND),('Hong Kong Island → Kowloon',NORTH)]:
        points = []
        for ident in members:
            p = by_id[ident]['points']
            assert not points or math.dist(points[-1],p[0]) < .02, (name,ident,'gap')
            points.extend(p if not points else p[1:])
        routes.append({'name':name,'source_ids':members,'points':points})
    for a,b in zip(routes,routes[1:]):
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
    island = box(330,1100,1350,1890)
    land = unary_union([district,island])
    ground = land.difference(unary_union(cutouts).buffer(.05))
    for street in district_data['side_roads']:
        assert ground.covers(LineString(street['points']).buffer(9)), (street['name'],'portal cut breaks the existing street')
    water = box(-2250,-550,2550,2350).difference(land)
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
        'source_sha256':hashlib.file_digest(open(source,'rb'),'sha256').hexdigest(),
        'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'origin_wgs84':ORIGIN,
        'terms':'https://data.gov.hk/en/terms-and-conditions', 'world_units_per_metre':1,
        'dictionary':'https://static.data.gov.hk/td/road-network-v2/dataspec/rdnet_dataspec.zip',
        'tunnel_reference':'https://www.td.gov.hk/en/transport_in_hong_kong/tunnels_and_bridges_n/location_map/index_t.html',
        'note':'Original XY preserved. ELEVATION is a relative road level, not metres. Depth 32 m, widths, 5.6 m interior height, land aprons and scenery are authored. Selected approach levels are simplified; turn restrictions are not inferred.'}
    output = {'metadata':metadata,'bounds':[bounds[0],-1400,1430,1940], 'roads':roads,
              'routes':routes,'tubes':tubes,'ground_triangles':ground_triangles,'water_triangles':water_triangles,'surface_triangles':surface_triangles}
    (ROOT/'Data/cross-harbour-source.geojson').write_text(json.dumps({'type':'FeatureCollection','metadata':metadata,'features':list(records.values())},ensure_ascii=False,separators=(',',':')))
    (ROOT/'Data/cross-harbour.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')))
    print('ANTILA_TUNNEL_DATA_OK:',len(roads),'source sections;',[(t['name'],round(t['length_m'],1)) for t in tubes],'; continuous routes',len(routes))


if __name__ == '__main__':
    build(Path(sys.argv[1]))
