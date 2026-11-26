"""Offline source and geometry checks for the Kai Tak Cruise Terminal drive."""
import json
import math
from pathlib import Path

from shapely import union_all
from shapely.geometry import LineString, Point, Polygon

from import_map import SOURCE, local
from import_tunnel import KAI_TAK, KAI_TAK_NETWORK

DATA = Path(__file__).resolve().parents[1] / 'Data'
SOURCE_SHA256 = 'ebdc7052bbd07fbc3f6f068012ba8354e62c9f3c21c080d6cd43f334b1169adf'
ROUTE_START = (2279.2831, 0, -3017.2665)
ROUTE_FINISH = (4051.1208, 0, -1510.4505)


def check(data_path=DATA):
    data = json.loads((data_path / 'cross-harbour.json').read_text())
    source = json.loads((data_path / 'cross-harbour-source.geojson').read_text())
    metadata = source['metadata']
    assert metadata['source'] == SOURCE and metadata['source_sha256'] == SOURCE_SHA256
    assert metadata['source_crs'] == 'EPSG:4326', 'The November TD archive is already in WGS84'

    routes = data['routes']
    has_diamond_hill = 'wong_tai_sin_district_boundary_sha256' in metadata
    has_choi_hung = 'wong_tai_sin_network_sections' in metadata
    assert len(routes) == 15 + has_diamond_hill + has_choi_hung
    route = routes[14]
    assert route['name'] == 'Kai Tak → Kai Tak Cruise Terminal'
    assert route['source_ids'] == KAI_TAK and len(KAI_TAK) == 34
    assert math.dist(route['points'][0], ROUTE_START) < .002
    assert math.dist(route['points'][-1], ROUTE_FINISH) < .002
    assert any(math.dist(route['points'][0], point) < .002 for point in routes[12]['points']), \
        'The Cruise Terminal drive must start at a surveyed junction on the eastern drive'

    roads = {road['id']: road for road in data['roads']}
    sources = {feature['properties']['source_id']: feature for feature in source['features']}
    chi_man = roads['TD_105191']
    bridge_stub = {'TD_267096', 'TD_266963', 'TD_274787'} & (roads.keys() | sources.keys())
    assert chi_man['width'] == 5.0 and not bridge_stub, (
        'Expected a 5 m Chi Man Street and no approach to the unmodeled Kai Tak Bridge',
        chi_man['width'], sorted(bridge_stub),
    )
    properties = sources['TD_105191']['properties']
    assert chi_man['name'] == properties['STREET_ENAME'] == 'CHI MAN STREET'
    assert chi_man['source_level'] == 0 and not chi_man['elevated'] and not chi_man['tunnel']
    assert properties['TRAVEL_DIRECTION'] == '3' and properties['source_sha256'] == SOURCE_SHA256
    ground = union_all([Polygon(triangle) for triangle in data['ground_triangles']])
    water = union_all([Polygon(triangle) for triangle in data['water_triangles']])
    barriers = union_all([LineString(path) for key in ('kowloon_coastline', 'kowloon_boundary')
                          for path in data[key]])
    for coords in [(4200, -1360), (3050, -2700)]:
        point = Point(coords)
        assert ground.covers(point) and not water.covers(point), (coords, 'Expected runway land')
    for coords in [(2600, -2400), (3650, -2210), (4050, -2000), (4700, -1200)]:
        point = Point(coords)
        assert water.covers(point) and not ground.covers(point), (coords, 'Expected Kowloon Bay water')

    itinerary = []
    new_sections = 0
    for member in KAI_TAK:
        ident = member.lstrip('-')
        reverse = member.startswith('-')
        road = roads[ident]
        feature = sources[ident]
        properties = feature['properties']
        new_sections += properties['source_sha256'] == SOURCE_SHA256
        assert road['name'] == properties['STREET_ENAME'], ident
        assert properties['TRAVEL_DIRECTION'] in (('1', '2') if reverse else ('1', '3')), ident

        source_line = LineString([local(point) for point in feature['geometry']['coordinates']])
        sampled = LineString([(x, z) for x, _, z in road['points']])
        assert sampled.hausdorff_distance(source_line) < 2.001, ident
        assert all(source_line.distance(Point(point)) < .0001 for point in sampled.coords), ident
        carriageway = sampled.buffer(road['width'] / 2)
        assert carriageway.difference(ground).area < .01, (ident, 'Carriageway lacks ground support')
        assert barriers.distance(sampled) > 1.5, (ident, 'A seawall or map edge blocks the drive')

        points = road['points'][::-1] if reverse else road['points']
        assert not itinerary or math.dist(itinerary[-1], points[0]) < .12, (ident, 'Disconnected carriageway')
        itinerary.extend(points[1:] if itinerary else points)

    assert itinerary == route['points'], 'Route samples must follow the directed source sections'
    assert new_sections == 25, 'Every new itinerary section must identify the November TD archive'
    for ident in ('TD_284207', *KAI_TAK_NETWORK):
        road = roads[ident]
        assert road['name'] == 'SHING FUNG ROAD' and road['source_level'] == 1
        assert road['elevated'] and not road['tunnel'], ident

    distance = sum(math.dist(start, finish) for start, finish in zip(itinerary, itinerary[1:]))
    assert 3000 < distance < 3050
    print(f'ANTILA_KAI_TAK_SOURCE_OK: {len(KAI_TAK)} directed sections, {new_sections} new; '
          f'{distance:.1f} m to the Cruise Terminal; surveyed land and water checks')


if __name__ == '__main__':
    check()
