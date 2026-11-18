"""Offline preservation and source-geometry checks for the Kwai Chung junction."""
import json
import math
from collections import Counter
from pathlib import Path

from shapely import union_all
from shapely.geometry import LineString, Polygon, box

from import_map import local


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'evidence/western-map-fixes-2026-10-28/before/Data'
SOURCE_SHA256 = '3df2c43b6f19bf7b34e0022d60d7cf5bd148ae0e0f001191879333d46ba66e52'
ROUNDABOUT = ('TD_8457', 'TD_9137', 'TD_9138')
ADDED_IDS = {*ROUNDABOUT, 'TD_57333'}
PRESERVED_FIELDS = (
    'bounds', 'island_bounds', 'kowloon_north_bounds', 'island_land',
    'island_coastline', 'island_boundary', 'island_coast_metadata',
    'kowloon_east_land', 'east_kowloon_bounds', 'east_coast_metadata',
    'coast_metadata', 'kowloon_northwest_bounds', 'northwest_coast_metadata',
    'kwai_chung_bounds', 'kwai_chung_coast_metadata', 'tsuen_wan_bounds',
    'tsuen_wan_coast_metadata', 'west_coast_bounds', 'west_coast_metadata',
)


def read(path):
    return json.loads(path.read_text())


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def local_line(feature):
    return [local(point) for point in feature['geometry']['coordinates']]


def point_segment_distance(point, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dz * dz
    if length2 == 0:
        return distance(point, a)
    t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dz) / length2))
    return distance(point, (a[0] + t * dx, a[1] + t * dz))


def check():
    data = read(ROOT / 'Data/cross-harbour.json')
    source = read(ROOT / 'Data/cross-harbour-source.geojson')
    baseline = read(BASELINE / 'cross-harbour.json')
    baseline_source = read(BASELINE / 'cross-harbour-source.geojson')
    source_features = source['features']
    source_by_id = {feature['properties']['source_id']: feature for feature in source_features}
    roads = {road['id']: road for road in data['roads']}
    baseline_roads = {road['id']: road for road in baseline['roads']}
    baseline_source_ids = {feature['properties']['source_id'] for feature in baseline_source['features']}

    assert len(baseline_roads) == 7223 and len(baseline_source_ids) == 7223, 'Unexpected reviewed road baseline'
    assert len(baseline['routes']) == 14, 'Unexpected reviewed route baseline'
    assert data['routes'] == baseline['routes'], 'Existing route arrays changed'
    assert data['tubes'] == baseline['tubes'], 'Existing tunnel profiles changed'
    assert len(data['routes']) == 14, 'The restored junction must not create a service or itinerary route'
    for field in PRESERVED_FIELDS:
        assert data[field] == baseline[field], f'Existing coast/ground/bounds field changed: {field}'
    # Shore changes elsewhere in Kowloon can retriangulate the whole map.
    kwai_extent = box(*data['kwai_chung_bounds'])
    for field, geometry in (('ground_triangles', Polygon), ('water_triangles', Polygon),
                            ('kowloon_coastline', LineString), ('kowloon_boundary', LineString)):
        old, new = (union_all([p.intersection(kwai_extent) for points in snapshot[field]
                               if (p := geometry(points)).intersects(kwai_extent)]) for snapshot in (baseline, data))
        difference = old.symmetric_difference(new)
        size = difference.area if geometry is Polygon else difference.length
        assert size < .01, f'Kwai Chung {field} changed'

    assert baseline_roads.keys() <= roads.keys(), 'An existing road object was removed'
    assert all(roads[ident] == road for ident, road in baseline_roads.items()), \
        'An existing road object changed'
    assert source_features[:len(baseline_source['features'])] == baseline_source['features'], \
        'Existing source records changed or were reordered'
    assert baseline_source_ids <= source_by_id.keys(), 'An existing source record was removed'
    assert set(roads) == set(source_by_id), 'Road and source sections must have one-to-one IDs'
    additions = set(roads) - set(baseline_roads)
    assert ADDED_IDS <= additions, 'Expected all four reviewed junction and approach roads'
    assert Counter(roads[ident]['name'] for ident in additions - ADDED_IDS) == {
        'WYLIE ROAD': 23, "KING'S PARK RISE": 3,
        'CORNWALL STREET': 17, 'TAT CHEE AVENUE': 3,
        'YORK ROAD': 1, 'NORFOLK ROAD': 1,
    }, 'Unexpected road additions outside the reviewed junction, King’s Park access and Kowloon Tong'
    assert len(data['roads']) == len(source_features) == 7275, 'Expected the complete current road/source set'

    for metadata in (data['metadata'], source['metadata']):
        assert metadata['source_crs'] == 'EPSG:4326', 'The fresh WGS84 archive must not use HK1980 conversion'
        assert metadata['coordinate_processing'] == 'WGS84 coordinates used directly', \
            'The fresh WGS84 archive must be projected directly'
    assert all(source_by_id[ident]['properties']['source_sha256'] == SOURCE_SHA256 for ident in ADDED_IDS), \
        'Each new source feature must cite the fresh reviewed archive hash'

    for ident in ROUNDABOUT:
        feature = source_by_id[ident]
        properties = feature['properties']
        assert properties['ELEVATION'] == '0' and properties['TRAVEL_DIRECTION'] == '3', \
            f'{ident} must remain a ground-level, source-directed roundabout section'
        assert properties['ALIAS_ENAME'] == 'Roundabout', f'{ident} roundabout alias changed'
        assert roads[ident]['source_level'] == 0 and not roads[ident]['elevated'] and not roads[ident]['tunnel'], \
            f'{ident} must remain on ground level'

    for ident in ADDED_IDS:
        feature = source_by_id[ident]
        road = roads[ident]
        line = local_line(feature)
        points = road['points']
        assert points and distance((points[0][0], points[0][2]), line[0]) < .001, \
            f'{ident} runtime path must begin in source direction'
        assert distance((points[-1][0], points[-1][2]), line[-1]) < .001, \
            f'{ident} runtime path must end in source direction'
        assert max(min(point_segment_distance((point[0], point[2]), a, b)
                       for a, b in zip(line, line[1:])) for point in points) < .001, \
            f'{ident} runtime samples must stay on source geometry'
        assert all(abs(point[1]) < .001 for point in points), f'{ident} must remain at ground height'

    for ident, next_id in zip(ROUNDABOUT, ROUNDABOUT[1:] + ROUNDABOUT[:1]):
        assert distance(local_line(source_by_id[ident])[-1], local_line(source_by_id[next_id])[0]) < .12, \
            f'{ident} does not connect in the reviewed one-way ring order to {next_id}'
    assert distance(local_line(source_by_id['TD_9097'])[-1], local_line(source_by_id['TD_8457'])[0]) < .12, \
        'Kwai Yue Street must enter the roundabout in its source direction'
    assert distance(local_line(source_by_id['TD_8457'])[-1], local_line(source_by_id['TD_57784'])[0]) < .12, \
        'The roundabout must connect to Kwai Hei Street in its source direction'
    assert distance(local_line(source_by_id['TD_9137'])[-1], local_line(source_by_id['TD_57333'])[0]) < .12, \
        'The reviewed roundabout exit must connect to Wing Shun Street'
    assert source_by_id['TD_57333']['properties']['STREET_ENAME'] == 'WING SHUN STREET'
    assert source_by_id['TD_57333']['properties']['TRAVEL_DIRECTION'] == '1', \
        'Wing Shun must retain its bidirectional source classification; sampled points follow source coordinate order'

    service_routes = read(ROOT / 'Data/routes.json')
    assert service_routes == read(BASELINE / 'routes.json'), 'Scheduled service route data changed'

    for baseline_path in BASELINE.glob('*layout.json'):
        if baseline_path.name not in {'kwai-chung-layout.json','building-layout.json','kowloon-north-layout.json'}:
            assert (ROOT / 'Data' / baseline_path.name).read_bytes() == baseline_path.read_bytes(), \
                f'Unrelated building layout changed: {baseline_path.name}'
    old_layout = read(BASELINE / 'kwai-chung-layout.json')
    layout = read(ROOT / 'Data/kwai-chung-layout.json')
    old_buildings = {building['id']: building for building in old_layout['buildings']}
    buildings = {building['id']: building for building in layout['buildings']}
    assert len(layout['buildings']) == len(old_layout['buildings']) == 3425
    assert buildings.keys() == old_buildings.keys(), 'Road clearance rebuild changed the Kwai Chung building set'
    assert layout['metadata']['source_sha256'] == old_layout['metadata']['source_sha256'], \
        'Kwai Chung government building source changed during the offline clearance rebuild'
    assert layout['metadata']['base_sources_sha256'] == old_layout['metadata']['base_sources_sha256'], \
        'Kwai Chung shared building-height sources changed during the offline clearance rebuild'
    clearance_checks = 0
    for ident in ADDED_IDS:
        road = roads[ident]
        line = LineString([(point[0], point[2]) for point in road['points']])
        for building in layout['buildings']:
            footprint = Polygon(building['rings'][0], building['rings'][1:])
            clearance = footprint.distance(line) - road['width'] / 2
            assert clearance >= 3.49, \
                f'{ident} building clearance below the 3.5 m margin: {building["id"]} at {clearance:.3f} m'
        clearance_checks += len(layout['buildings'])
    assert all(Polygon(patch['polygon']).is_valid and Polygon(patch['polygon']).area > 0
               for patch in layout['pavement_patches']), 'Kwai Chung pavement patches must remain valid polygons'
    print('ANTILA_WESTERN_JUNCTION_OK: four reviewed roads; one-way ring and Wing Shun connectivity; '
          f'7,223 old road/source objects, 14 route arrays, tunnel profiles and unrelated layouts preserved; '
          f'{clearance_checks} building-clearance probes retain the 3.5 m margin')


if __name__ == '__main__':
    check()
