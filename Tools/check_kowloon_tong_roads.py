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
PRIOR_ROAD_COUNT = 7273
TOTAL_ROAD_COUNT = 7275
PRIOR_SOURCE_FEATURES_SHA256 = '325ca42495500a92445bcdcd64b8e7481610a05eedaa7955bd74f3809bf1e26b'
PRIOR_ROADS_SHA256 = 'a126778701b58e88a99d67ae970e67cfdcc61412b2092e3ef4e52e4d8f8e76d0'
PRIOR_ROUTES_SHA256 = '12cf83fdf66246566f2f1aafbea6014531770b2b8d111fc0d47540854fa3cb11'
PRESERVED_MAP_SHA256 = '6fd9fa47503f31157aede62b047c93065d10b7890425883b4ffba596a5fc9bfc'

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

PRESERVED_FIELDS = (
    'bounds', 'island_bounds', 'kowloon_north_bounds', 'island_land',
    'island_coastline', 'island_boundary', 'island_coast_metadata',
    'kowloon_east_land', 'east_kowloon_bounds', 'east_coast_metadata',
    'kowloon_west_land', 'kowloon_coastline', 'kowloon_boundary', 'coast_metadata',
    'kowloon_northwest_bounds', 'northwest_coast_metadata', 'kwai_chung_bounds',
    'kwai_chung_coast_metadata', 'tsuen_wan_bounds', 'tsuen_wan_coast_metadata',
    'west_coast_bounds', 'west_coast_metadata', 'ground_triangles',
    'water_triangles', 'harbour_paving_triangles', 'tubes',
)


def read(path):
    return json.loads(path.read_text())


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def check():
    source = read(ROOT / 'Data/cross-harbour-source.geojson')
    data = read(ROOT / 'Data/cross-harbour.json')
    runtime = read(ROOT / 'Data/cross-harbour-runtime.json')
    features = source['features']
    roads = data['roads']
    source_by_id = {feature['properties']['source_id']: feature for feature in features}
    roads_by_id = {road['id']: road for road in roads}

    assert source['metadata']['source_sha256'] == SOURCE_SHA256, 'Kowloon Tong roads must use the reviewed TD archive'
    assert len(features) == len(source_by_id) == len(roads) == len(roads_by_id) == TOTAL_ROAD_COUNT
    assert len(data['routes']) == 14, 'The local street restoration must not add a drive route'
    assert set(source_by_id) == set(roads_by_id), 'Source and runtime road inventory must be one-to-one'
    assert digest(features[:PRIOR_ROAD_COUNT]) == PRIOR_SOURCE_FEATURES_SHA256, \
        'The previous 7,253 source records changed or were reordered'
    assert digest(roads[:PRIOR_ROAD_COUNT]) == PRIOR_ROADS_SHA256, \
        'The previous 7,253 road objects changed or were reordered'
    assert set(EXPECTED_ROADS) <= set(source_by_id), 'A reviewed Kowloon Tong section is missing'
    assert set(source_by_id) - {feature['properties']['source_id'] for feature in features[:PRIOR_ROAD_COUNT]} == LEVEL_ONE_STREET_CROSSINGS, \
        'Only the two reviewed Cornwall Street connectors may be added to the 7,273-road stage'
    assert digest(data['routes']) == PRIOR_ROUTES_SHA256, 'Existing drive route arrays changed'
    assert digest({field: data[field] for field in PRESERVED_FIELDS}) == PRESERVED_MAP_SHA256, \
        'Existing land, coast, bounds, ground, water or harbour paving changed'
    assert runtime['roads'] == roads and runtime['routes'] == data['routes'], \
        'Runtime road or route data is stale'
    assert not any('rail' in key.lower() or 'pier' in key.lower() for key in data), \
        'Kowloon Tong road restoration must not add rail or pier data'

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

    print('ANTILA_KOWLOON_TONG_ROADS_OK: 7,273 prior roads preserved; 22 reviewed roads present; '
          'flat rail-crossing connectors, traversable joins, routes and land/coast invariants checked')


if __name__ == '__main__':
    check()
