"""Audit the mapped land and survey coverage of Wong Tai Sin District."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from shapely import union_all
from shapely.geometry import LineString, Polygon, box, shape

from import_map import ROOT, local
from import_shoreline import EAST_KOWLOON_BOUNDS, WONG_TAI_SIN_MARGIN_M, project_polygon


def read(name):
    return json.loads((ROOT / 'Data' / name).read_bytes())


def ground_geometry(map_data):
    return union_all([Polygon(triangle) for triangle in map_data['ground_triangles']])


def check(baseline_path=None):
    boundary_path = ROOT / 'Data/wong-tai-sin-district-boundary.geojson'
    boundary_bytes = boundary_path.read_bytes()
    boundary = json.loads(boundary_bytes)
    feature, = boundary['features']
    assert feature['properties']['District'] == 'Wong Tai Sin District'
    assert feature['properties']['地區號碼'] == 'H'
    canonical = json.dumps(feature, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    assert digest == boundary['metadata']['feature_sha256'], 'The official district feature changed'
    district = project_polygon(feature['geometry'])
    assert district.is_valid and district.geom_type == 'Polygon', 'Invalid Wong Tai Sin district geometry'

    coast = read('east-kowloon-coast.json')
    provenance = coast['metadata']['wong_tai_sin_district_land']
    assert provenance['district_source_sha256'] == hashlib.sha256(boundary_bytes).hexdigest()
    assert provenance['district_feature_sha256'] == digest
    assert provenance['margin_m'] == WONG_TAI_SIN_MARGIN_M
    mainland_source = read('east-kowloon-shoreline.geojson')['kai_tak_coast_sources']['reclamation']
    assert provenance['mainland_response_sha256'] == mainland_source['metadata']['response_sha256']
    mainland = union_all([project_polygon(row['geometry']) for row in mainland_source['features']])
    district_with_margin = district.buffer(WONG_TAI_SIN_MARGIN_M, quad_segs=4)
    assert mainland.covers(district_with_margin), 'The district margin leaves government-mapped land'
    assert district_with_margin.difference(shape(coast['land'])).area < .01, \
        'The eastern coast is missing surveyed inland terrain'

    map_data = read('cross-harbour.json')
    assert map_data['east_kowloon_bounds'] == coast['bounds']
    assert map_data['east_coast_metadata']['wong_tai_sin_district_land'] == provenance
    ground = ground_geometry(map_data)
    coverage = district.intersection(ground).area
    assert district_with_margin.difference(ground).area < .01, 'The compiled map has missing Wong Tai Sin ground'
    old_edge = box(*EAST_KOWLOON_BOUNDS).boundary.intersection(district)
    walls = union_all([LineString(path) for path in map_data['kowloon_boundary']])
    assert old_edge.intersection(walls).length < .01, 'An artificial wall remains across the old inland cut'
    print(f'Official Wong Tai Sin District: {district.area / 1e6:.5f} km², {coverage / 1e6:.5f} km² mapped')
    print(f'Inland terrain added: {provenance["added_ground_m2"]:,.0f} m², '
          f'{provenance["district_gap_filled_m2"]:,.0f} m² inside the district')
    print(f'Former map edge clear inside the district: {old_edge.length:,.1f} m')

    road_parts = defaultdict(list)
    for row in read('cross-harbour-source.geojson')['features']:
        line = LineString([local(point) for point in row['geometry']['coordinates']])
        clipped = line.intersection(district)
        if clipped.length > 0:
            road_parts[row['properties']['ROUTE_ID']].append(clipped)
    total_length = sum(union_all(parts).length for parts in road_parts.values())
    print(f'Transport Department road sections in district: {len(road_parts):,} distinct IDs, '
          f'{total_length / 1000:.3f} km of clipped centrelines')

    gardens = read('east-kowloon-open-spaces.json')['gardens']
    site_footprints = [union_all([Polygon(rings[0], rings[1:]) for rings in garden['rings']])
                       for garden in gardens]
    sites = sum(site.intersection(district).area > site.area / 2 for site in site_footprints)
    print(f'Government survey sites with most of their mapped footprint in the district: {sites}')

    if baseline_path:
        baseline = json.loads(baseline_path.read_bytes())
        prior_ground = ground_geometry(baseline)
        added = ground.difference(prior_ground)
        assert prior_ground.difference(ground).area < .01, 'Previously mapped ground was lost'
        assert added.symmetric_difference(district_with_margin.difference(prior_ground)).area < .01, \
            'New ground extends beyond the reviewed Wong Tai Sin footprint'
        assert baseline['kowloon_coastline'] == map_data['kowloon_coastline'], 'Surveyed shoreline changed'
        assert baseline['routes'] == map_data['routes'][:len(baseline['routes'])]
        assert baseline['tubes'] == map_data['tubes']
        print(f'Prior ground and surveyed coast preserved; {added.area:,.0f} m² added in the reviewed extent')

    print('ANTILA_WONG_TAI_SIN_TERRAIN_AUDIT_OK')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-map', type=Path, help='Compare a saved pre-expansion cross-harbour.json')
    check(parser.parse_args().baseline_map)
