"""Fit the pinned LandsD ground survey to a protected Wong Tai Sin hillside."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from pyproj import Transformer
from scipy.interpolate import LinearNDInterpolator
from shapely import constrained_delaunay_triangles, get_parts, union_all
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import polygonize

from import_map import ORIGIN, ROOT
from import_shoreline import project_polygon

STEP_M = 16
SURVEY_DATUM_M = 135
RELIEF_SCALE = .65
FEATHER_M = 140
MAX_RISE_PER_EDGE_METRE = .58


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def ground_triangles_sha256(triangles):
    # Replayed by the model exporter, which has no geodata dependencies.
    return hashlib.sha256(json.dumps(triangles, separators=(',', ':')).encode()).hexdigest()


def check_clearance(footprint, map_data):
    files = {}

    def read(name, *fields):
        payload = (ROOT / 'Data' / name).read_bytes()
        source = json.loads(payload)
        if fields:
            payload = json.dumps([source[key] for key in fields], ensure_ascii=False,
                                 separators=(',', ':'), sort_keys=True).encode()
        files[name] = {'fields': fields, 'sha256': digest(payload)}
        return source

    district = project_polygon(read('wong-tai-sin-district-boundary.geojson')['features'][0]['geometry'])
    if not district.covers(footprint):
        raise ValueError('Hillside footprint leaves the official district')
    bounds = box(*footprint.bounds).buffer(40)
    for row in map_data['roads']:
        if not row['tunnel']:
            line = LineString([(x, z) for x, _, z in row['points']])
            if line.intersects(bounds) and line.distance(footprint) < row['width'] / 2 + 25:
                raise ValueError(f"Hillside footprint overlaps road clearance {row['id']}")
    for line in map_data['kowloon_boundary']:
        if LineString(line).distance(footprint) < 20:
            raise ValueError('Hillside footprint reaches the outer wall')
    for name in ('east-kowloon-buildings.geojson', 'kowloon-north-buildings.geojson',
                 'kowloon-tong-buildings-source.geojson'):
        for row in read(name)['features']:
            if row['geometry'] is not None:
                lot = project_polygon(row['geometry'])
                if lot.intersects(bounds) and lot.distance(footprint) < 20:
                    raise ValueError(f'Hillside footprint overlaps a surveyed lot in {name}')
    for name in ('east-kowloon-layout.json', 'kowloon-north-layout.json'):
        for row in read(name, 'buildings')['buildings']:
            lot = Polygon(row['rings'][0], row['rings'][1:])
            if lot.intersects(bounds) and lot.distance(footprint) < 20:
                raise ValueError(f"Hillside footprint overlaps rendered lot {row['id']}")
    recreation = read('east-kowloon-open-spaces.json', 'gardens', 'paving')
    for garden in recreation['gardens']:
        for rings in garden['rings'] + garden['paths'] + garden['access']:
            if Polygon(rings[0], rings[1:]).distance(footprint) < 25:
                raise ValueError(f"Hillside footprint overlaps open space {garden['site']}")
    for triangle in recreation['paving']:
        paving = Polygon(triangle)
        if paving.intersects(bounds) and paving.distance(footprint) < 25:
            raise ValueError('Hillside footprint overlaps recreation paving')
    return files


def survey_heights(records, vertices):
    survey_points = []
    control_levels = []
    for row in records['layers']['393']:
        height = row['attributes']['CONTOURHEIGHT']
        for path in row['geometry']['paths']:
            survey_points.extend(point[:2] for point in path)
            control_levels.extend([height] * len(path))
    for row in records['layers']['382']:
        survey_points.append([row['geometry']['x'], row['geometry']['y']])
        control_levels.append(row['attributes']['HEIGHTVALUE'])
    east, north = np.array(survey_points).T
    longitude, latitude = Transformer.from_crs(2326, 4326, always_xy=True).transform(east, north)
    longitude_scale = 111320 * math.cos(math.radians(ORIGIN[1]))
    locations = np.column_stack(((longitude - ORIGIN[0]) * longitude_scale,
                                 -(latitude - ORIGIN[1]) * 111320))
    # Bucket duplicate close survey vertices before interpolating. Both sources are HKPD.
    _, first, group, counts = np.unique(np.round(locations / 2), axis=0, return_index=True,
                                        return_inverse=True, return_counts=True)
    heights = np.bincount(group, weights=control_levels) / counts
    result = LinearNDInterpolator(locations[first], heights)(vertices)
    if not np.isfinite(result).all():
        raise ValueError('Survey does not cover every hillside mesh vertex')
    return result


def mesh_grid(footprint):
    x0, z0, x1, z1 = footprint.bounds
    vertices = []
    by_point = {}
    faces = []
    for z in range(math.floor(z0 / STEP_M) * STEP_M, math.ceil(z1 / STEP_M) * STEP_M, STEP_M):
        for x in range(math.floor(x0 / STEP_M) * STEP_M, math.ceil(x1 / STEP_M) * STEP_M, STEP_M):
            cell = footprint.intersection(box(x, z, x + STEP_M, z + STEP_M))
            for part in get_parts(cell):
                if part.geom_type != 'Polygon' or part.area < 1e-5:
                    continue
                for triangle in get_parts(constrained_delaunay_triangles(part)):
                    if triangle.area < 1e-7:
                        continue
                    face = []
                    for x_at, z_at in list(triangle.exterior.coords)[:3]:
                        point = round(x_at, 8), round(z_at, 8)
                        if point not in by_point:
                            by_point[point] = len(vertices)
                            vertices.append(point)
                        face.append(by_point[point])
                    faces.append(face)
    return np.array(vertices), np.array(faces)


def replace_ground(footprint, raised_vertices, raised_faces, planar_triangles):
    edges = Counter(tuple(sorted((a, b))) for x, y, z in raised_faces
                    for a, b in ((x, y), (y, z), (z, x)))
    shared_edges = {tuple(sorted((tuple(raised_vertices[a, [0, 2]]), tuple(raised_vertices[b, [0, 2]]))))
                    for (a, b), count in edges.items() if count == 1}
    loops = polygonize([LineString(edge) for edge in sorted(shared_edges)])
    noded = union_all([p for p in loops if footprint.covers(p.representative_point())])
    if noded.geom_type != 'Polygon' or noded.symmetric_difference(footprint).area > .001:
        raise ValueError('Hillside grid does not cover the complete footprint')

    x0, z0, x1, z1 = footprint.bounds
    indices = []
    affected = []
    for i, tri in enumerate(planar_triangles):
        x, z = zip(*tri)
        if max(x) <= x0 or min(x) >= x1 or max(z) <= z0 or min(z) >= z1:
            continue
        poly = Polygon(tri)
        if poly.intersection(noded).area > 1e-7:
            indices.append(i)
            affected.append(poly)

    affected_land = union_all(affected)
    if noded.difference(affected_land).area > .001:
        raise ValueError('Hillside extends beyond the existing flat surface')
    flat = affected_land.difference(noded)
    if flat.union(noded).symmetric_difference(affected_land).area > .001:
        raise ValueError('Hillside replacement would change the existing land footprint')

    vertices = raised_vertices.tolist()
    by_point = {tuple(at): i for i, at in enumerate(vertices)}
    flat_faces = []
    flat_edges = set()
    for tri in get_parts(constrained_delaunay_triangles(flat)):
        ring = list(tri.exterior.coords)[:3]
        if tri.exterior.is_ccw:
            ring.reverse()
        face = []
        for x, z in ring:
            point = x, 0.0, z
            if point not in by_point:
                by_point[point] = len(vertices)
                vertices.append(list(point))
            face.append(by_point[point])
        a, b, c = ring
        flat_edges.update(tuple(sorted(edge)) for edge in ((a, b), (b, c), (c, a)))
        flat_faces.append(face)

    perimeter = Counter(tuple(sorted((a, b))) for triangle in affected
                        for a, b in zip(triangle.exterior.coords, list(triangle.exterior.coords)[1:]))
    retained_edges = {edge for edge, count in perimeter.items() if count == 1}
    if not (shared_edges | retained_edges).issubset(flat_edges):
        raise ValueError('Replacement must share fully noded edges with the hillside and the retained ground')
    combined_area = sum(Polygon([vertices[i][::2] for i in face]).area for face in flat_faces) + noded.area
    if abs(combined_area - affected_land.area) > .001:
        raise ValueError('Replacement contains missing or duplicate ground')
    replacement = {'old_triangles': indices, 'vertices': vertices, 'raised_faces': raised_faces.tolist(),
                   'planar_faces': flat_faces}
    return replacement, len(shared_edges)


def build(map_path, footprint_path, survey_path, manifest_path):
    source = survey_path.read_bytes()
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    footprint_bytes = footprint_path.read_bytes()
    uncompressed = gzip.decompress(source)
    if manifest['output']['sha256'] != digest(source) or \
            manifest['output']['uncompressed_sha256'] != digest(uncompressed) or \
            manifest['selection']['footprint_sha256'] != digest(footprint_bytes):
        raise ValueError('Pinned survey or reviewed footprint digest does not match its manifest')
    records = json.loads(uncompressed)
    survey_types = {'382': ('SHG',), '393': ('CNS', 'CIS')}
    if records.get('schema_version') != 1 or records.get('source_crs') != 'EPSG:2326' or \
            any(row['attributes']['FEATURETYPE'] not in survey_types[layer] for layer in survey_types
                for row in records['layers'][layer]):
        raise ValueError('Only the native government ground spot heights and certain contours are supported')
    footprint = shape(json.loads(footprint_bytes)['geometry'])
    if footprint.geom_type != 'Polygon' or not footprint.is_valid:
        raise ValueError('Expected a valid reviewed hillside polygon')
    map_data = json.loads(map_path.read_bytes())
    clearance_files = check_clearance(footprint, map_data)
    # Sign horizontal road geometry and wall lines, independently of processing metadata and grades.
    surface_roads = [(road['width'], [(x, z) for x, _, z in road['points']])
                     for road in sorted(map_data['roads'], key=lambda road: road['id']) if not road['tunnel']]
    clearance_map = encoded([surface_roads, sorted(map_data['kowloon_boundary'])])
    vertices, faces = mesh_grid(footprint)
    levels = survey_heights(records, vertices)
    distance = np.array([footprint.boundary.distance(Point(*at)) for at in vertices])
    taper = np.minimum(1, distance / FEATHER_M)
    taper = taper * taper * (3 - 2 * taper)
    height = np.minimum(np.maximum(0, (levels - SURVEY_DATUM_M) * RELIEF_SCALE) * taper,
                        distance * MAX_RISE_PER_EDGE_METRE)
    height[distance < 1e-6] = 0
    x, z = vertices.T
    xyz = np.column_stack((x, np.round(height, 6), z))
    corners = xyz[faces]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    area = np.abs(normals[:, 1]).sum() / 2
    if np.min(np.abs(normals[:, 1])) <= 0 or abs(area - footprint.area) > .05:
        raise ValueError('The height mesh is incomplete or has degenerate faces')
    flip = normals[:, 1] < 0
    faces[flip] = faces[flip][:, [0, 2, 1]]
    slope = np.arctan2(np.linalg.norm(normals[:, [0, 2]], axis=1), np.abs(normals[:, 1])) * 180 / math.pi
    replacement, seam_edges = replace_ground(footprint, xyz, faces, map_data['ground_triangles'])
    return {'metadata': {
        'source': 'Lands Department iB1000 ground spot heights and contours via the CEDD Basemap',
        'survey_archive_sha256': digest(source), 'survey_manifest_sha256': digest(manifest_bytes),
        'reviewed_footprint_sha256': digest(footprint_bytes), 'source_crs': records['source_crs'],
        'datum': 'HKPD', 'survey_contours': len(records['layers']['393']), 'survey_ground_spots': len(records['layers']['382']),
        'ground_triangles_sha256': ground_triangles_sha256(map_data['ground_triangles']),
        'clearance_map_sha256': digest(clearance_map), 'clearance_files_sha256': clearance_files,
        'grid_m': STEP_M, 'source_height_m_hkpd': [round(float(levels.min()), 3), round(float(levels.max()), 3)],
        'game_height_m': [0, round(float(height.max()), 3)], 'game_height_origin_hkpd_m': SURVEY_DATUM_M,
        'game_relief_scale': RELIEF_SCALE, 'feather_m': FEATHER_M,
        'maximum_rise_per_edge_metre': MAX_RISE_PER_EDGE_METRE, 'maximum_slope_deg': round(float(slope.max()), 3),
        'area_m2': round(footprint.area, 3), 'bounds': footprint.bounds, 'seam_edges': seam_edges,
        'terms': 'https://portal.csdi.gov.hk/csdi-webpage/doc/TNC',
    }, **replacement}


if __name__ == '__main__':
    data = ROOT / 'Data'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, default=data / 'cross-harbour.json')
    parser.add_argument('--footprint', type=Path, default=data / 'wong-tai-sin-relief-footprint.geojson')
    parser.add_argument('--survey', type=Path, default=data / 'wong-tai-sin-relief-survey.json.gz')
    parser.add_argument('--manifest', type=Path, default=data / 'wong-tai-sin-relief-survey.manifest.json')
    parser.add_argument('--output', type=Path, default=data / 'wong-tai-sin-relief.json')
    args = parser.parse_args()
    result = build(args.map, args.footprint, args.survey, args.manifest)
    temporary = NamedTemporaryFile(dir=args.output.parent, delete=False)
    stage = Path(temporary.name)
    try:
        with temporary:
            temporary.write(encoded(result))
        stage.replace(args.output)
    finally:
        stage.unlink(missing_ok=True)
    print('ANTILA_WONG_TAI_SIN_RELIEF_READY', json.dumps(result['metadata']))
