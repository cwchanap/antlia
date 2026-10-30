"""Offline source/geometry checks for the eastern expansion; run with .venv-geodata."""
import hashlib
import json
import math
from pathlib import Path
from shapely import STRtree, union_all
from shapely.geometry import LineString, Point, Polygon, box, shape
from import_map import local
from import_tunnel import EAST_KOWLOON, EAST_KOWLOON_BOUNDS, KOWLOON_BOUNDS, WEST_BOUNDS

ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/'Data'/name).read_text())


def check_roundabouts(roads,sources):
    rings=[('Hereford / Renfrew',('107211','107576','107598','107575','107601'),{'HEREFORD ROAD','RENFREW ROAD'}),
           ('Ho Tung / Oxford',('107564','107580','107235'),{'HO TUNG ROAD','OXFORD ROAD'})]
    for name,ids,approaches in rings:
        ids=['TD_'+i for i in ids]
        assert set(ids)<=roads.keys(),(name,'Missing government roundabout connections',set(ids)-roads.keys())
        for ident,next_id in zip(ids,ids[1:]+ids[:1]):
            road=roads[ident];feature=sources[ident]
            assert feature['properties']['ELEVATION']=='0' and feature['properties']['TRAVEL_DIRECTION']=='3'
            assert not road['tunnel'] and not road['elevated'] and road['width']==12
            source=LineString([local(p) for p in feature['geometry']['coordinates']])
            sampled=LineString([(p[0],p[2]) for p in road['points']])
            assert sampled.hausdorff_distance(source)<2.001 and all(source.distance(Point(p))<.0001 for p in sampled.coords)
            assert math.dist(road['points'][-1],roads[next_id]['points'][0])<.12,(name,'One-way ring is not closed')
        nodes=[Point(roads[i]['points'][0][0],roads[i]['points'][0][2]) for i in ids]
        approaches=[LineString([(p[0],p[2]) for p in r['points']]) for r in roads.values() if r['name'] in approaches]
        assert all(any(node.distance(line)<.12 for line in approaches) for node in nodes),(name,'Ring must meet its named approach streets')
    print('ANTILA_EAST_ROUNDABOUT_SOURCE_OK: eight directed source sections form two closed rings with named approaches')


def check_boundaries(data):
    ground=union_all([Polygon(t) for t in data['ground_triangles']])
    mainland=next(p for p in ground.geoms if p.contains(Point(0,-550)))
    perimeter=Polygon(mainland.exterior).boundary
    boundary=union_all([LineString(p) for p in data['kowloon_boundary']])
    walls=union_all([boundary,*[LineString(p) for p in data['kowloon_coastline']]])
    assert boundary.difference(mainland.boundary.buffer(.002)).length<.1,'Boundary wall must follow the actual mainland or water edge'
    missing=perimeter.difference(walls.buffer(.35)).length
    assert missing<1,('Mainland perimeter wall has unprotected gaps',missing)
    assert perimeter.distance(Point(3150,-2355.5))<.01,'Physical boundary fixture must remain on the outer edge'
    print('ANTILA_MAINLAND_BOUNDARY_SOURCE_OK: outer ground perimeter enclosed; no interior boundary wall')


def check():
    data=read('cross-harbour.json');coast=read('east-kowloon-coast.json')
    land=shape(coast['land']);raw=read('east-kowloon-shoreline.geojson')
    assert land.is_valid and 12e6<land.area<14e6
    assert coast['metadata']['source_sha256']==hashlib.sha256((ROOT/'Data/east-kowloon-shoreline.geojson').read_bytes()).hexdigest()
    assert len(raw['features'])==576 and coast['metadata']['max_gap_closure_m']<42
    # Hung Hom, Whampoa, To Kwa Wan and Kowloon City land; harbour and Kowloon Bay water.
    for p in [(1300,-1400),(1800,-1300),(1800,-2600),(1750,-3900)]:assert land.contains(Point(p)),p
    for p in [(1800,-300),(2500,-1500),(2600,-2400)]:assert not land.contains(Point(p)),p
    sources={f['properties']['source_id']:f for f in read('cross-harbour-source.geojson')['features']}
    roads={r['id']:r for r in data['roads']};route=data['routes'][12]
    assert len(roads)==len(data['roads'])==len(sources)==7227, 'Expected the complete current road/source set, including four reviewed additions'
    check_roundabouts(roads,sources)
    check_boundaries(data)
    assert len(data['routes'])==14 and route['source_ids']==EAST_KOWLOON
    assert route['points'][0]==data['routes'][0]['points'][0]
    distance=sum(math.dist(a,b) for a,b in zip(route['points'],route['points'][1:]))
    assert 6100<distance<6130
    for ident in EAST_KOWLOON:
        reverse=ident.startswith('-');id=ident.lstrip('-');r=roads[id];f=sources[id]
        assert f['properties']['TRAVEL_DIRECTION'] in (('1','2') if reverse else ('1','3'))
        source=LineString([local(p) for p in f['geometry']['coordinates']])
        sampled=LineString([(p[0],p[2]) for p in r['points']])
        # Four-metre sampling can cut source corners by at most half its interval.
        assert sampled.hausdorff_distance(source)<2.001,(id,'resampled route strays from source')
        assert all(source.distance(Point(p))<.0001 for p in sampled.coords),(id,'sample moved off source')
    barriers=union_all([LineString(p) for key in ('kowloon_boundary','kowloon_coastline') for p in data[key]])
    route_line=LineString([(p[0],p[2]) for p in route['points']])
    assert barriers.distance(route_line)>6.3,'Map edge or seawall crosses the exploration drive'
    prior=union_all([box(*WEST_BOUNDS),box(*KOWLOON_BOUNDS),box(*read('nathan-road.json')['bounds'])])
    new_roads=[r for r in roads.values() if land.covers(LineString([(p[0],p[2]) for p in r['points']]).buffer(6)) and LineString([(p[0],p[2]) for p in r['points']]).difference(prior).length>1]
    assert len(new_roads)>1400
    layout=read('east-kowloon-layout.json');lots=layout['buildings']
    assert layout['metadata']['source_parts']==8153 and len(lots)>3000
    assert len(layout['metadata']['base_sources_sha256'])==8
    polys=[Polygon(b['rings'][0],b['rings'][1:]) for b in lots]
    tree=STRtree(polys)
    assert all(p.is_valid and p.difference(land).area<.1 and p.intersection(prior).area<.1 for p in polys)
    road_zone=union_all([LineString([(p[0],p[2]) for p in r['points']]).buffer(max(12,r['width'])/2+3.5,quad_segs=2,join_style='mitre') for r in new_roads if not r['tunnel']])
    assert all(p.intersection(road_zone).area<.1 for p in polys),'Buildings obstruct authored road clearance'
    for i,p in enumerate(polys):assert all(p.intersection(polys[int(j)]).area<.1 for j in tree.query(p) if j<i)
    assert all(sum(Point(b['center']).within(box(*bounds)) for b in lots)>100 for bounds in [(900,-2000,2100,-650),(1400,-3200,2350,-2000),(1400,-4200,2200,-3300)])
    print(f'ANTILA_EAST_SOURCE_OK: {len(raw["features"])} shoreline fragments; {len(new_roads)} eastern roads; {distance:.1f} m directed drive; {len(lots)} building parts; land/sea, clearance, overlap and source checks')


if __name__=='__main__':check()
