"""Verify the source-bounded Tsim Sha Tsui apron cut and its generated land."""
import hashlib
import json
import math
from pathlib import Path
import sys

from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Tools'))
from import_tunnel import build_tst_shoreline_geometry


def read(name):
    return json.loads((ROOT/'Data'/name).read_text())


def check():
    source=read('tst-shoreline-source.geojson')
    east=read('east-kowloon-shoreline.geojson')['features']
    west=read('west-kowloon-shoreline.geojson')['features']
    east_land=shape(read('east-kowloon-coast.json')['land'])
    bounds=read('nathan-road.json')['bounds']
    district=box(bounds[0]-110,bounds[1]-130,bounds[2]+110,bounds[3]+120)
    sites,cut,frontier,east_cut=build_tst_shoreline_geometry(
        district,east_land,source['features'],east,west)

    assert sites.is_valid and sites.geom_type in ('Polygon','MultiPolygon')
    assert abs(cut.area-383956.36)<.05, cut.area
    assert abs(east_cut.area-338329.85)<.05, east_cut.area
    assert cut.is_valid and cut.intersection(sites).area<.05
    apron_join=LineString([(550,-1220),(550,district.bounds[3])])
    assert cut.boundary.intersection(apron_join).length<.01, 'The old x=550 notch must dissolve into the sourced coast'
    assert math.dist(frontier.coords[0],(47.98794,195.51219))<.02
    assert math.dist(frontier.coords[-1],(851.64857,-447.83297))<.02
    assert 1100<frontier.length<1180
    for feature in source['features']:
        properties=feature['properties']
        assert properties['layer']=='Site' and properties['status']=='E'
        assert set(properties['source_tiles'])==set(properties['source_tile_sha256'])
        assert all(len(value)==64 for value in properties['source_tile_sha256'].values())

    output=read('cross-harbour.json')
    assert output['metadata']['tst_shoreline_source_sha256']==hashlib.sha256(
        (ROOT/'Data/tst-shoreline-source.geojson').read_bytes()).hexdigest()
    ground=unary_union([Polygon(t) for t in output['ground_triangles']])
    assert sites.difference(ground).area<.05, 'The generated ground must retain complete reviewed TST Site land'
    for road in output['roads']:
        if road['tunnel']:
            continue
        line=LineString([(p[0],p[2]) for p in road['points']])
        buffer=line.buffer(road['width']/2+1)
        assert buffer.intersection(cut).area<.01, (road['id'],'road envelope intersects TST water cut')
    for road in read('nathan-road.json')['side_roads']:
        envelope=LineString(road['points']).buffer(11)
        assert envelope.intersection(cut).area<.01, (road['name'],'side-road envelope intersects cut')
        assert ground.covers(LineString(road['points']).buffer(9)), (road['name'],'side-road ground was lost')

    coast=unary_union([LineString(line) for line in output['kowloon_coastline']])
    assert coast.distance(frontier)<.01, 'The source Site/SWA waterfront must remain a coastline barrier'
    print(f"ANTILA_TST_SHORELINE_OK: {cut.area:.2f} m2 removed; {east_cut.area:.2f} m2 eastern cut; "
          f"{frontier.length:.2f} m joined Site/SWA frontage; {len(output['roads'])} roads and all Sites supported")


if __name__=='__main__':
    check()
