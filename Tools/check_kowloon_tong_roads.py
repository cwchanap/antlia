"""Offline regressions for the reviewed Kowloon Tong road restoration."""
import collections
import hashlib
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Point

from import_map import local

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA256 = '34b8dbd0a7d5c99f60461886303b2e21f1fb3d00369a3e0c46b41b233e205c22'
PRIOR_ROAD_COUNT = 7275
PRIOR_ROUTE_COUNT = 14
PRIOR_SOURCE_FEATURES_SHA256 = 'c9e995a9f3c5d6a589a7c48b6185bf4f31a74833ce1339a11cbf2d385b3be03d'
PRIOR_ROADS_SHA256 = '981f2c960b9c4b48a563c9d3f8afb86d614273e35a944e5306cffd55dcfb2584'
PRIOR_ROUTES_SHA256 = '12cf83fdf66246566f2f1aafbea6014531770b2b8d111fc0d47540854fa3cb11'
PRESERVED_REGIONAL_FIELDS_SHA256 = 'dd7fb635be12beeccd3e167e0dcb7dabd9d9b57f5e5954b81966c7f4b5f8b3f3'

EXPECTED_ROADS = {
    'TD_108064': ('CORNWALL STREET', '3'),
    'TD_108061': ('CORNWALL STREET', '3'),
    'TD_108062': ('CORNWALL STREET', '3'),
    'TD_108063': ('CORNWALL STREET', '3'),
    'TD_107934': ('CORNWALL STREET', '3'),
    'TD_107935': ('CORNWALL STREET', '3'),
    'TD_107715': ('CORNWALL STREET', '1'),
    'TD_107716': ('CORNWALL STREET', '3'),
    'TD_107718': ('CORNWALL STREET', '1'),
    'TD_107719': ('CORNWALL STREET', '3'),
    'TD_107656': ('CORNWALL STREET', '3'),
    'TD_107657': ('CORNWALL STREET', '3'),
    'TD_110086': ('CORNWALL STREET', '3'),
    'TD_107620': ('CORNWALL STREET', '1'),
    'TD_107621': ('CORNWALL STREET', '1'),
    'TD_107623': ('CORNWALL STREET', '3'),
    'TD_107624': ('CORNWALL STREET', '3'),
    'TD_108065': ('TAT CHEE AVENUE', '3'),
    'TD_108066': ('TAT CHEE AVENUE', '3'),
    'TD_107747': ('TAT CHEE AVENUE', '3'),
    'TD_107225': ('YORK ROAD', '3'),
    'TD_107587': ('NORFOLK ROAD', '3'),
}
LEVEL_ONE_STREET_CROSSINGS = {'TD_107934', 'TD_107935'}

PRESERVED_REGIONAL_FIELDS = (
    'island_bounds', 'kowloon_north_bounds', 'island_land',
    'island_coastline', 'island_boundary', 'island_coast_metadata',
    'kowloon_west_land', 'coast_metadata',
    'kowloon_northwest_bounds', 'northwest_coast_metadata', 'kwai_chung_bounds',
    'kwai_chung_coast_metadata', 'tsuen_wan_bounds', 'tsuen_wan_coast_metadata',
    'west_coast_bounds', 'west_coast_metadata', 'tubes',
)


def read(path):
    return json.loads(path.read_text())


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def preserved_roads(roads, routes):
    itinerary_ids = {ident.lstrip('-') for route in routes for ident in route['source_ids']}
    for road in roads:
        if road['name'] != 'SHING FUNG ROAD' or road['id'] in itinerary_ids:
            yield road
            continue
        # The new Shing Fung Road deck can change approach heights and widths.
        assert road['width'] in (6, 12) and all(0 <= y <= 7 for _, y, _ in road['points'])
        normalized = {**road, 'points': [(x, z) for x, _, z in road['points']]}
        normalized.pop('width')
        normalized.pop('elevated')
        yield normalized


def check():
    source = read(ROOT / 'Data/cross-harbour-source.geojson')
    data = read(ROOT / 'Data/cross-harbour.json')
    runtime = read(ROOT / 'Data/cross-harbour-runtime.json')
    features = source['features']
    roads = data['roads']
    source_by_id = {feature['properties']['source_id']: feature for feature in features}
    roads_by_id = {road['id']: road for road in roads}

    assert len(features) == len(source_by_id) == len(roads) == len(roads_by_id)
    assert list(source_by_id) == list(roads_by_id), 'Source and sampled road order must match'
    prior_routes = data['routes'][:PRIOR_ROUTE_COUNT]
    assert digest(features[:PRIOR_ROAD_COUNT]) == PRIOR_SOURCE_FEATURES_SHA256, \
        'The previous 7,275 source records changed or were reordered'
    assert digest(list(preserved_roads(roads[:PRIOR_ROAD_COUNT], prior_routes))) == PRIOR_ROADS_SHA256, \
        'The previous 7,275 road objects changed or were reordered'
    assert set(EXPECTED_ROADS) <= set(source_by_id), 'A reviewed Kowloon Tong section is missing'
    assert digest(prior_routes) == PRIOR_ROUTES_SHA256, 'Existing drive route arrays changed'
    assert digest({field: data[field] for field in PRESERVED_REGIONAL_FIELDS}) == PRESERVED_REGIONAL_FIELDS_SHA256, \
        'Existing western or island regions or harbour tunnel tubes changed'
    assert runtime['roads'] == roads and runtime['routes'] == data['routes'], \
        'Runtime road or route data is stale'

    lengths = collections.Counter()
    distances = collections.Counter()
    endpoint_nodes = collections.defaultdict(list)
    source_lines = {}
    for feature in features:
        ident = feature['properties']['source_id']
        line = LineString([local(point) for point in feature['geometry']['coordinates']])
        source_lines[ident] = line
        if ident in EXPECTED_ROADS:
            name, direction = EXPECTED_ROADS[ident]
            props = feature['properties']
            road = roads_by_id[ident]
            assert props['STREET_ENAME'] == name and props['TRAVEL_DIRECTION'] == direction, \
                f'{ident} source name or direction changed'
            expected_level = 1 if ident in LEVEL_ONE_STREET_CROSSINGS else 0
            assert props['ELEVATION'] == str(expected_level) and props['source_sha256'] == SOURCE_SHA256, \
                f'{ident} source level or provenance changed'
            assert road['name'] == name and road['source_level'] == expected_level and road['width'] == 12, \
                f'{ident} runtime road definition changed'
            assert not road['elevated'] and not road['tunnel'], f'{ident} must remain at ground level'
            points = road['points']
            assert all(abs(point[1]) < .001 and line.distance(Point(point[0], point[2])) < .001
                       for point in points), f'{ident} must follow its surveyed flat centreline'
            assert math.dist((points[0][0], points[0][2]), line.coords[0]) < .001 and \
                   math.dist((points[-1][0], points[-1][2]), line.coords[-1]) < .001, \
                f'{ident} runtime endpoints must retain source direction'
            lengths[name] += line.length
        for side, point in enumerate((line.coords[0], line.coords[-1])):
            endpoint_nodes[tuple(round(value, 1) for value in point)].append((ident, side, point))

    assert {name: round(lengths[name], 1) for name in ('CORNWALL STREET', 'TAT CHEE AVENUE', 'YORK ROAD', 'NORFOLK ROAD')} == {
        'CORNWALL STREET': 1268.8, 'TAT CHEE AVENUE': 430.6,
        'YORK ROAD': 189.0, 'NORFOLK ROAD': 135.9,
    }, 'Reviewed source street lengths changed'
    joined_sides = collections.Counter()
    for ident in EXPECTED_ROADS:
        line = source_lines[ident]
        for side, point in enumerate((line.coords[0], line.coords[-1])):
            if any(other != ident and math.dist(point, other_point) < .12
                   for other, _, other_point in endpoint_nodes[tuple(round(value, 1) for value in point)]):
                joined_sides[ident] += 1
        assert joined_sides[ident] > 0, f'{ident} must connect to another surveyed road section'
    assert joined_sides['TD_107225'] == joined_sides['TD_107587'] == 2, \
        'York Road and Norfolk Road must connect at both ends'
    for chain in (('TD_108064', 'TD_107935', 'TD_108062'),
                  ('TD_108061', 'TD_107934', 'TD_108063')):
        for first, second in zip(chain, chain[1:]):
            a, b = roads_by_id[first]['points'], roads_by_id[second]['points']
            assert math.dist((a[-1][0], a[-1][2]), (b[0][0], b[0][2])) < .12, \
                f'{first} does not connect to {second}'
            assert abs(a[-1][1] - b[0][1]) < .001, f'{first}/{second} pavement height discontinuity'

    print('ANTILA_KOWLOON_TONG_ROADS_OK: 7,275 prior roads retained; 22 reviewed roads present; '
          'flat rail-crossing connectors, traversable joins and retained routes checked')


if __name__ == '__main__':
    check()
