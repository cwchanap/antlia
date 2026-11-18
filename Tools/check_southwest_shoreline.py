"""Focused source and geometry checks for the southwest harbour correction."""
import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import transform, unary_union

from import_map import ORIGIN, local
from import_tunnel import MUSEUM_WATER_BOUNDS, SOUTHWEST_CHART_GAP_BOUNDS, SOUTHWEST_EDIT_BOUNDS, SOUTHWEST_PROMENADE_BOUNDS

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_geometry(geometry):
    scale_x=111320*math.cos(math.radians(ORIGIN[1]))
    return transform(lambda x,y,z=None:((x-ORIGIN[0])*scale_x,-(y-ORIGIN[1])*111320),geometry)


def check():
    output=read(ROOT/'Data/cross-harbour.json')
    metadata=output['metadata']
    water_data=read(ROOT/'Data/southwest-water-source.geojson')
    shoreline_data=read(ROOT/'Data/southwest-shoreline-source.geojson')
    building_data=read(ROOT/'Data/southwest-building-ground-source.geojson')
    cultural_path=ROOT/'Data/southwest-public-spaces-source.geojson'
    cultural_data=read(cultural_path)
    water=unary_union([shape(feature['geometry']) for feature in water_data['features']])
    decks=unary_union([local_geometry(shape(feature['geometry'])) for feature in shoreline_data['features']
                       if feature['properties'].get('source_type') in ('JPW','FFL')])
    buildings=unary_union([local_geometry(shape(feature['geometry'])) for feature in building_data['features']])
    cultural_site=unary_union([local_geometry(shape(feature['geometry'])) for feature in cultural_data['features']
                       if feature['properties'].get('layer')=='Site' and feature['properties'].get('SITEID')=='1503005422'])
    site_ground=cultural_site.difference(water)
    ground=unary_union([Polygon(triangle) for triangle in output['ground_triangles']])
    assert output['kowloon_west_land']['type']=='Polygon', 'Preserved west-land provenance schema changed'
    assert metadata['southwest_water_source_sha256']==sha256(ROOT/'Data/southwest-water-source.geojson')
    assert metadata['southwest_shoreline_source_sha256']==sha256(ROOT/'Data/southwest-shoreline-source.geojson')
    assert metadata['southwest_building_source_sha256']==sha256(ROOT/'Data/southwest-building-ground-source.geojson')
    assert metadata['southwest_cultural_site_source_sha256']==sha256(cultural_path)
    assert metadata['southwest_cultural_site_source']=='Data/southwest-public-spaces-source.geojson'
    assert metadata['southwest_edit_bounds']==list(SOUTHWEST_EDIT_BOUNDS)
    assert metadata['southwest_chart_gap_bounds']==list(SOUTHWEST_CHART_GAP_BOUNDS)
    assert metadata['southwest_promenade_bounds']==list(SOUTHWEST_PROMENADE_BOUNDS)
    assert metadata['museum_water_bounds']==list(MUSEUM_WATER_BOUNDS)
    assert metadata['southwest_water_correction_area_m2']>470000

    for point in [(-1000,-500),(-700,-170),(-550,100)]:
        assert not ground.covers(Point(point)), f'Open harbour water remains solid at {point}'
    art_park=Point(-1550,-550)
    assert ground.covers(art_park), 'West Kowloon Art Park ground was cut'
    assert site_ground.difference(ground).area<.1, 'Cultural Centre Site non-water support is incomplete'
    assert box(*SOUTHWEST_PROMENADE_BOUNDS).difference(water).difference(ground).area<.1, 'Charted public promenade is missing ground'
    tst_sites=unary_union([shape(f['geometry']) for f in read(ROOT/'Data/tst-shoreline-source.geojson')['features']])
    museum_water=water.intersection(box(*MUSEUM_WATER_BOUNDS)).difference(unary_union([decks,buildings,tst_sites]))
    assert museum_water.intersection(ground).area<.1, 'Mapped water east of the Museum of Art must be open'
    assert ground.covers(Point(82.35,152.97)) and not ground.covers(Point(86.35,152.97)), 'The museum wall must separate land and water'

    landmark_source=read(ROOT/'Data/southwest-landmarks-source.geojson')
    for feature in landmark_source['features']:
        footprint=local_geometry(shape(feature['geometry']))
        assert footprint.difference(ground).area<.1, feature['properties']['BuildingNameEN']+' lacks ground support'

    stable_decks=[]
    for source_id in ('1513000311','1108329108'):
        geometries=[local_geometry(shape(feature['geometry'])) for feature in shoreline_data['features']
                    if feature['properties'].get('source_id')==source_id and feature['properties'].get('source_type') in ('JPW','FFL')]
        deck=unary_union(geometries)
        probe=deck.representative_point()
        assert ground.covers(probe), f'Public ferry deck {source_id} is not solid'
        stable_decks.append((source_id,tuple(round(value,3) for value in probe.coords[0])))
    deck_paving=unary_union([Polygon(t) for t in output['harbour_paving_triangles']])
    assert deck_paving.symmetric_difference(decks.intersection(ground)).area<.1, 'Paving must match supported surveyed deck footprints'

    roads_ok=0
    southwest_area=box(*SOUTHWEST_EDIT_BOUNDS)
    for road in output['roads']:
        if road['tunnel']:
            continue
        carriageway=LineString([(point[0],point[2]) for point in road['points']]).buffer(road['width']/2)
        assert carriageway.intersection(southwest_area).difference(ground).area<.01, f"Road {road['id']} lost southwest ground support"
        roads_ok+=1

    survey=Point(-332.27,169.64)
    swa=[local_geometry(shape(feature['geometry'])) for feature in shoreline_data['features']
         if feature['properties'].get('source_type')=='SWA' and feature['properties'].get('source_id')=='1101166503']
    assert swa and min(line.distance(survey) for line in swa)<.01, 'Surveyed TST seawall probe moved'
    coast=unary_union([LineString(line) for line in output['kowloon_coastline']])
    assert coast.distance(survey)<.01, 'Surveyed TST seawall is absent from the canonical coastline'
    museum_probe=Point(84.35,152.97)
    assert coast.intersection(ground.boundary.buffer(.002)).distance(museum_probe)<.1, 'Museum seawall must coincide with the terrain edge'
    gap=box(*SOUTHWEST_CHART_GAP_BOUNDS)
    assert coast.intersection(gap.boundary).length<.1, 'Artificial chart-gap edge was emitted as coastline'

    runtime=read(ROOT/'Data/cross-harbour-runtime.json')
    for key,value in output.items():
        if key not in ('ground_triangles','water_triangles','surface_triangles'):
            assert runtime.get(key)==value, f'Runtime field {key} differs from canonical JSON'

    print('ANTILA_SOUTHWEST_SHORELINE_OK:',
          f"water_cut={metadata['southwest_water_correction_area_m2']:.1f}m2;",
          f"CulturalCentreSite={site_ground.area:.1f}m2;",
          f'roads={roads_ok};',
          'water_probes=(-1000,-500),(-700,-170),(-550,100);',
          f'decks={stable_decks};',
          f'seawall_distance={coast.distance(survey):.4f}m; no chart-gap edge wall')


if __name__=='__main__':
    check()
