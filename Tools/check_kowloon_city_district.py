"""Compare the bundled map with the official Kowloon City District boundary.

Run with .venv-geodata/bin/python Tools/check_kowloon_city_district.py.
Measurements use the game's approximate local metre projection and describe
coverage of the bundled datasets.
"""

import hashlib
import json
from collections import defaultdict

from shapely import get_parts, union_all
from shapely.geometry import LineString, Polygon, box, shape
from shapely.ops import transform

from import_map import ROOT, local
from import_tunnel import KOWLOON_CITY_NORTH_FILL_BOUNDS


def read(name):
    return json.loads((ROOT / 'Data' / name).read_text())


def project(x, y, z=None):
    return local((x, y))


def bounds_text(geometry):
    return ', '.join(f'{value:.1f}' for value in geometry.bounds)


def check():
    boundary = read('kowloon-city-district-boundary.geojson')
    features = boundary['features']
    if len(features) != 1 or features[0]['properties']['District'] != 'Kowloon City District':
        raise ValueError('Expected the official Kowloon City District boundary feature')
    canonical_feature = json.dumps(features[0], sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    if hashlib.sha256(canonical_feature.encode()).hexdigest() != boundary['metadata']['feature_sha256']:
        raise ValueError('Kowloon City District boundary does not match its recorded feature hash')
    district = transform(project, shape(features[0]['geometry']))
    if district.is_empty or not district.is_valid or district.geom_type not in ('Polygon', 'MultiPolygon'):
        raise ValueError('Invalid Kowloon City District boundary geometry')

    map_data = read('cross-harbour.json')
    ground = union_all([Polygon(triangle) for triangle in map_data['ground_triangles']])
    covered = district.intersection(ground)
    uncovered = district.difference(ground)
    x_min, z_min, x_max, z_max = KOWLOON_CITY_NORTH_FILL_BOUNDS
    north_fill = box(x_min, z_min, x_max, z_max)
    if north_fill.difference(ground).area > .01:
        raise AssertionError('The surveyed northern land extension has missing ground')
    old_cut = LineString([(x_min + 1, z_max), (x_max - 1, z_max)])
    walls = union_all([LineString(points) for points in map_data['kowloon_boundary']])
    if walls.distance(old_cut) < .5:
        raise AssertionError('A boundary wall still crosses the old northern seam')
    print(f'Official administrative extent including water: {district.area / 1e6:.3f} km²')
    print(f'Official extent local bounds (min X, min Z, max X, max Z), metres: {bounds_text(district)}')
    print(f'Mapped ground intersection: {covered.area / 1e6:.3f} km²')
    print(f'Administrative extent outside mapped ground, including water: {uncovered.area / 1e6:.3f} km²')
    for part in sorted(get_parts(uncovered), key=lambda geometry: geometry.area, reverse=True)[:4]:
        if part.area >= 1:
            print(f'  {part.area / 1e6:.5f} km² at ({bounds_text(part)})')
    print(f'Northern terrain extension: {north_fill.area:,.0f} m² of mainland with a clear former seam')

    road_parts = defaultdict(list)
    for feature in read('cross-harbour-source.geojson')['features']:
        line = LineString([local(point) for point in feature['geometry']['coordinates']])
        clipped = line.intersection(district)
        if clipped.length > 0:
            road_parts[feature['properties']['ROUTE_ID']].append(clipped)
    road_length = sum(union_all(parts).length for parts in road_parts.values())
    print(f'Bundled Transport Department road sections in district: {len(road_parts):,} unique ROUTE_IDs, '
          f'{road_length / 1000:.3f} km clipped centreline length')

    sites = defaultdict(list)
    for name in ('east-kowloon-open-spaces-source.geojson', 'mong-kok-open-spaces-source.geojson',
                 'kowloon-city-open-spaces-source.geojson'):
        for feature in read(name)['features']:
            props = feature['properties']
            if props['layer'] == 'Site':
                sites[props['SITEID']].append(transform(project, shape(feature['geometry'])))
    site_footprints = [union_all(parts) for parts in sites.values()]
    site_count = sum(footprint.intersection(district).area > footprint.area / 2
                     for footprint in site_footprints)
    print(f'Bundled government survey sites with most of their footprint in district: {site_count}')

    east_edge = map_data['east_kowloon_bounds'][2]
    _, min_z, max_x, max_z = district.bounds
    shore_east_in_district = (district.intersection(box(east_edge, min_z, max_x, max_z))
                             if east_edge < max_x else Polygon())
    shoreline = [LineString([local(point) for point in feature['geometry']['coordinates']])
                 for feature in read('east-kowloon-shoreline.geojson')['features']]
    east_fragments = [line.intersection(shore_east_in_district) for line in shoreline]
    east_fragments = [line for line in east_fragments if line.length > 0]
    east_length = union_all(east_fragments).length
    eastmost = max(line.bounds[2] for line in shoreline)
    print(f'Bundled eastern iB1000 shoreline reaches local X {eastmost:.1f} m. Within the district east of '
          f'the current map edge at X {east_edge:.1f} m: {len(east_fragments)} source fragments, '
          f'{east_length / 1000:.3f} km after union.')
    print('ANTILA_KOWLOON_CITY_DISTRICT_AUDIT_OK')


if __name__ == '__main__':
    check()
