"""Offline road inventory, preservation and direction checks for Wong Tai Sin District."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

from shapely import union_all
from shapely.geometry import LineString, Point, Polygon

from check_kowloon_tong_roads import digest
from import_map import NS, SOURCE, local
from import_tunnel import (
    CHOI_HUNG_SIDE_LOOP, CHOI_HUNG_TO_HAMMER_HILL, HAMMER_HILL_DECKS,
    HAMMER_HILL_EAST_ENTRY, HAMMER_HILL_MERGE, HAMMER_HILL_WEST_EXIT, LUNG_CHEUNG_UNDERPASS,
    WONG_TAI_SIN_DEFERRED_ROADS,
    WONG_TAI_SIN_DISTRICT_ROADS, WONG_TAI_SIN_NARROW_CARRIAGEWAYS, WONG_TAI_SIN_NETWORK_ROADS,
)

DATA = Path(__file__).resolve().parents[1] / 'Data'
PRIOR_ROAD_COUNT = 7489
PRIOR_SOURCES_SHA256 = 'bd56d1920d9897cada40434800cd9563586fba1037181c5b33b1eeb7685a5a1a'
PRIOR_ROADS_SHA256 = 'ed71f53419438cc46ede04230085fe4a52eeca729544988125876ea7347ddfc8'
PRIOR_ROUTES_SHA256 = '5fd69e9dc1acd1a18ff6e4a9876adba6d253ab6ae8caa7eb7e36c843477d415d'
DIAMOND_HILL_ROUTE_SHA256 = '80448f3c05a0cb6a5dddc45cc08579ac546cce03062aabe9c4829f56ab990894'
DIAMOND_HILL_ROAD_COUNT = 7571
DIAMOND_HILL_ROADS_SHA256 = '76a245f61112acf122a39be717aa8ed628c6359cf466fbeb191f45b235c7d852'
DIAMOND_HILL_SOURCES_SHA256 = 'cb6d508524361a7792cbf50083afbdd4969ab909f7b618764a1a3fbba8b0bd8f'
DIAMOND_HILL_DRIVES_SHA256 = '69eb50ec641c280601384f8bbd7bc8ef02bfce5c11f7e5e743ffd10104bd89a4'
CENTERLINE_SHA256 = 'ebdc7052bbd07fbc3f6f068012ba8354e62c9f3c21c080d6cd43f334b1169adf'
TURN_SHA256 = 'b6911192e9cfc9c719ec317d3a5c2a7e6db01fc27d751af952546203ac7a9bc4'
HAMMER_HILL_RING = ('TD_103019', 'TD_103025', 'TD_103024', 'TD_103020', 'TD_103027', 'TD_103026')
CHOI_HUNG_RETURN = ('TD_102872', 'TD_102843', 'TD_102926', 'TD_102871', 'TD_283007')


def check_turns(archive_path, *drives):
    with archive_path.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == TURN_SHA256
    restricted_sequences = {
        tuple(route_ids[i:i + count])
        for route_ids in drives
        for count in range(2, 9)
        for i in range(len(route_ids) - count + 1)
    }
    pattern = re.compile(r'<td>([A-Za-z0-9_]+)</td>\s*<td>(.*?)</td>')
    records = 0
    with zipfile.ZipFile(archive_path) as archive, archive.open('doc.kml') as stream:
        for _, element in ET.iterparse(stream, events=('end',)):
            if element.tag != f"{{{NS['k']}}}Placemark":
                continue
            properties = dict(pattern.findall(element.findtext('k:description', '', NS)))
            edges = [properties.get(f'Edge{i}FID', '') for i in range(1, 9)]
            turn = tuple(edge for edge in edges if edge.isdigit())
            assert not (properties.get('NO_TURN', '').startswith('-') and turn in restricted_sequences), \
                ('TD turn restriction matches the itinerary', properties.get('TURN_ID'), turn)
            records += 1
            element.clear()
    assert records > 1000
    print(f'ANTILA_DIAMOND_HILL_TURN_SOURCE_OK: {records:,} official turn records checked')


def drive_points(roads, features, members, *, surface_only=True):
    points = []
    route_ids = []
    for member in members:
        ident = member.lstrip('-')
        reverse = member.startswith('-')
        road = roads[ident]
        feature = features[ident]
        properties = feature['properties']
        assert properties['TRAVEL_DIRECTION'] in (('1', '2') if reverse else ('1', '3')), ident
        assert not road['tunnel'] and (not surface_only or not road['elevated']), ident
        line = LineString([local(point) for point in feature['geometry']['coordinates']])
        assert all(line.distance(Point(x, z)) < .0001 for x, _, z in road['points']), ident
        segment = road['points'][::-1] if reverse else road['points']
        assert not points or math.dist(points[-1], segment[0]) < .12, ident
        points.extend(segment[bool(points):])
        route_ids.append(properties['ROUTE_ID'])
    for a, b, c in zip(points, points[1:], points[2:]):
        direction = sum((b[i] - a[i]) * (c[i] - b[i]) for i in range(3))
        assert direction / (math.dist(a, b) * math.dist(b, c)) > -.5
    return points, route_ids


def check_hammer_hill_merge(roads, merge):
    assert merge == HAMMER_HILL_MERGE, 'The Hammer Hill apron metadata must identify the reviewed junction'
    height = merge['height_m']
    junction = roads[merge['departure']]['points'][0]
    assert junction[1] == height
    for ident in (*merge['approaches'], merge['departure']):
        road = roads[ident]
        incoming = ident in merge['approaches']
        points = road['points'][::-1] if incoming else road['points']
        assert road['elevated'] and points[0] == junction
        first_ramp = next((i for i, point in enumerate(points) if point[1] != height), len(points))
        level_end = points[:first_ramp]
        flat_span = sum(math.dist(a, b) for a, b in zip(level_end, level_end[1:]))
        assert 1 < first_ramp < len(points) and flat_span >= (16 if incoming else 7.9), \
            (ident, 'The Hammer Hill apron needs a level span on each arm', flat_span)


def check(data_path=DATA, turn_archive=None):
    data = json.loads((data_path / 'cross-harbour.json').read_text())
    source = json.loads((data_path / 'cross-harbour-source.geojson').read_text())
    assert len(data['routes']) >= 16, 'The Diamond Hill drive must append to the 15 existing drives'
    assert digest(data['routes'][:15]) == PRIOR_ROUTES_SHA256, 'An existing itinerary changed'
    assert digest(data['roads'][:PRIOR_ROAD_COUNT]) == PRIOR_ROADS_SHA256, 'Existing road objects changed'
    assert digest(source['features'][:PRIOR_ROAD_COUNT]) == PRIOR_SOURCES_SHA256, 'Existing source records changed'
    assert digest(data['roads'][:DIAMOND_HILL_ROAD_COUNT]) == DIAMOND_HILL_ROADS_SHA256, 'Reviewed Diamond Hill road objects changed'
    assert digest(source['features'][:DIAMOND_HILL_ROAD_COUNT]) == DIAMOND_HILL_SOURCES_SHA256, 'Reviewed Diamond Hill source records changed'
    assert digest(data['routes'][:16]) == DIAMOND_HILL_DRIVES_SHA256, 'A reviewed Diamond Hill edition drive changed'
    assert source['metadata']['source'] == SOURCE and source['metadata']['source_sha256'] == CENTERLINE_SHA256
    assert source['metadata']['source_crs'] == 'EPSG:4326'
    boundary_path = data_path / 'wong-tai-sin-district-boundary.geojson'
    boundary = json.loads(boundary_path.read_text())
    feature, = boundary['features']
    feature_bytes = json.dumps(feature, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    feature_sha256 = hashlib.sha256(feature_bytes).hexdigest()
    assert feature_sha256 == boundary['metadata']['feature_sha256']
    assert feature_sha256 == data['east_coast_metadata']['wong_tai_sin_district_land']['district_feature_sha256']
    assert hashlib.sha256(boundary_path.read_bytes()).hexdigest() == source['metadata']['wong_tai_sin_district_boundary_sha256']

    roads = {road['id']: road for road in data['roads']}
    features = {feature['properties']['source_id']: feature for feature in source['features']}
    assert list(roads) == list(features) and len(roads) == len(data['roads']) == len(source['features'])
    assert {'TD_267096', 'TD_266963', 'TD_274787'}.isdisjoint(roads), 'The deferrals around Kai Tak Bridge were lost'
    network_ids = set(source['metadata'].get('wong_tai_sin_network_sections', ()))
    assert network_ids == set(list(roads)[DIAMOND_HILL_ROAD_COUNT:]), 'The additional district sections do not match the source inventory'
    deferred = WONG_TAI_SIN_DEFERRED_ROADS - network_ids
    assert deferred.isdisjoint(roads), 'A deferred Choi Hung link was added without a reviewed exit'
    assert set(source['metadata']['wong_tai_sin_deferred_roads']) == deferred
    new_roads = data['roads'][PRIOR_ROAD_COUNT:DIAMOND_HILL_ROAD_COUNT]
    new_ids = {road['id'] for road in new_roads}
    assert new_ids == WONG_TAI_SIN_DISTRICT_ROADS and len(new_ids) == 82
    assert {'FUNG TAK ROAD', 'PO KONG VILLAGE ROAD', 'TSZ WAN SHAN ROAD', 'HAMMER HILL ROAD'} <= {
        road['name'] for road in new_roads
    }
    ground = union_all([Polygon(triangle) for triangle in data['ground_triangles']])
    for road in new_roads:
        properties = features[road['id']]['properties']
        assert properties['source_sha256'] == CENTERLINE_SHA256 and properties['ELEVATION'] == '0'
        assert properties['TRAVEL_DIRECTION'] in ('1', '2', '3')
        assert not road['tunnel'] and not road['elevated']
        sampled = LineString([(x, z) for x, _, z in road['points']])
        assert sampled.buffer(road['width'] / 2).difference(ground).area < .01, road['id']

    for first, second in zip(HAMMER_HILL_RING, HAMMER_HILL_RING[1:] + HAMMER_HILL_RING[:1]):
        assert features[first]['properties']['TRAVEL_DIRECTION'] == '3'
        assert math.dist(roads[first]['points'][-1], roads[second]['points'][0]) < .12, (first, second)

    route = data['routes'][15]
    assert route['name'] == 'Wong Tai Sin → Diamond Hill'
    assert digest(route) == DIAMOND_HILL_ROUTE_SHA256, 'The existing Diamond Hill drive changed'
    assert len(route['source_ids']) == 58 and len(route['points']) == 817
    assert route['points'][0] == data['routes'][13]['points'][-1]
    assert math.dist(route['points'][-1], [2953.5226, 0, -5124.4027]) < .002
    assert roads[route['source_ids'][-1]]['name'] == 'LUNG POON STREET'
    points, route_ids = drive_points(roads, features, route['source_ids'])
    assert points == route['points'] and len(set(route_ids)) == len(route_ids)
    distance = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    assert 3100 < distance < 3160
    assert set(CHOI_HUNG_RETURN[:-1]) <= new_ids and CHOI_HUNG_RETURN[-1] not in new_ids
    _, return_ids = drive_points(roads, features, CHOI_HUNG_RETURN)
    turn_paths = [route_ids, return_ids]
    if network_ids:
        assert network_ids == WONG_TAI_SIN_NETWORK_ROADS - set(list(roads)[:DIAMOND_HILL_ROAD_COUNT])
        assert len(data['routes']) == 17
        for ident in network_ids:
            road, feature = roads[ident], features[ident]
            props = feature['properties']
            assert props['source_sha256'] == CENTERLINE_SHA256 and props['TRAVEL_DIRECTION'] in ('1', '2', '3'), ident
            assert road['source_level'] == int(props['ELEVATION']) and not road['tunnel'], ident
            if ident in WONG_TAI_SIN_NARROW_CARRIAGEWAYS:
                assert road['width'] == WONG_TAI_SIN_NARROW_CARRIAGEWAYS[ident], ident
            line = LineString([(x, z) for x, _, z in road['points']])
            assert line.buffer(road['width'] / 2).difference(ground).area < .01, ident
        for ident in HAMMER_HILL_DECKS:
            assert roads[ident]['source_level'] == 1 and roads[ident]['elevated'], ident
            assert {point[1] for point in roads[ident]['points']} == {7}, ident
        merge = data['metadata']['wong_tai_sin_decks']['merge']
        assert merge == source['metadata']['wong_tai_sin_decks']['merge']
        check_hammer_hill_merge(roads, merge)
        route = data['routes'][16]
        assert route['name'] == 'Choi Hung → Hammer Hill' and route['source_ids'] == CHOI_HUNG_TO_HAMMER_HILL
        points, choi_hung_turn_path = drive_points(roads, features, route['source_ids'], surface_only=False)
        assert points == route['points']
        turn_paths.append(choi_hung_turn_path)
        for members, surface_only in ((CHOI_HUNG_SIDE_LOOP, True), (LUNG_CHEUNG_UNDERPASS, True),
                                      (HAMMER_HILL_WEST_EXIT, False), (HAMMER_HILL_EAST_ENTRY, False)):
            _, path = drive_points(roads, features, members, surface_only=surface_only)
            turn_paths.append(path)
        route_length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
        print(f'ANTILA_CHOI_HUNG_DISTRICT_DRIVE_OK: {len(network_ids)} additional roads; '
              f'{len(route["source_ids"])} directed sections and {route_length:.1f} m')
    else:
        assert len(data['routes']) == 16
    if turn_archive is not None:
        check_turns(turn_archive, *turn_paths)
    print('ANTILA_CHOI_HUNG_RETURN_OK:', ' → '.join(CHOI_HUNG_RETURN))
    print(f'ANTILA_WONG_TAI_SIN_DISTRICT_ROADS_OK: {len(new_roads)} new sections; '
          f'{len(route_ids)} directed itinerary sections and {distance:.1f} m to Diamond Hill')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--turn-archive', type=Path, help='Original Transport Department TURN.kmz')
    check(turn_archive=parser.parse_args().turn_archive)
