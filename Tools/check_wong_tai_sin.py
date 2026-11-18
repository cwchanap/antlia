"""Offline source/preservation checks for the Wong Tai Sin extension."""
import hashlib
import json
import math
from pathlib import Path

from shapely import union_all
from shapely.geometry import LineString, Point, Polygon, box, shape

from import_map import local

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'evidence/wong-tai-sin-expansion-2026-10-24/baseline/Data'


def read(root, name):
    return json.loads((root / name).read_text())


def bus_lane_offset(width, elevated, tunnel=False):
    half_width = 3.65 if tunnel else width / 2
    cap = 2.15 if tunnel else 1.4 if elevated else 1.8
    return max(0, min(cap, half_width - 1.24 - .25))


def _add(a, b): return tuple(x + y for x, y in zip(a, b))
def _sub(a, b): return tuple(x - y for x, y in zip(a, b))
def _mul(a, n): return tuple(x * n for x in a)
def _dot(a, b): return sum(x * y for x, y in zip(a, b))
def _cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def _length(a): return math.sqrt(_dot(a, a))
def _unit(a): return _mul(a, 1 / _length(a))


def _box_hits_triangle(center, axes, half, triangle):
    edges = [_sub(triangle[1], triangle[0]), _sub(triangle[2], triangle[1]),
             _sub(triangle[0], triangle[2])]
    test_axes = axes + [_cross(edges[0], edges[1])]
    test_axes += [_cross(axis, edge) for axis in axes for edge in edges]
    for axis in test_axes:
        if _dot(axis, axis) < 1e-18:
            continue
        projections = [_dot(point, axis) for point in triangle]
        middle = _dot(center, axis)
        radius = sum(half[i] * abs(_dot(axes[i], axis)) for i in range(3))
        if min(projections) > middle + radius + 1e-7 or max(projections) < middle - radius - 1e-7:
            return False
    return True


def _model_raised_triangles(data, target_roads):
    target_points = [p for road in target_roads for p in road['points']]
    bounds = (min(p[0] for p in target_points)-16, min(p[2] for p in target_points)-16,
              max(p[0] for p in target_points)+16, max(p[2] for p in target_points)+16)

    def local(road):
        xs = [p[0] for p in road['points']]; zs = [p[2] for p in road['points']]
        return road['elevated'] and not road['tunnel'] and max(xs) >= bounds[0] and min(xs) <= bounds[2] and \
            max(zs) >= bounds[1] and min(zs) <= bounds[3]

    roads = [r for r in data['roads'] if local(r)]
    join_points = {tuple(r['points'][end]) for r in roads for end in (0, -1)}
    join_ids = {r['id'] for r in data['roads'] if r['elevated'] and not r['tunnel'] and
                any(tuple(r['points'][end]) in join_points for end in (0, -1))}
    model_roads = [r for r in data['roads'] if r['id'] in join_ids]

    def resample(road):
        points = [tuple(map(float, p)) for p in road['points']]
        arc = [0.0]
        for a, b in zip(points, points[1:]): arc.append(arc[-1] + _length(_sub(b, a)))
        count = math.ceil(arc[-1] / 4)
        sampled = []
        for i in range(count + 1):
            distance = i * arc[-1] / count
            j = min(len(points)-2, max(0, next((k-1 for k, d in enumerate(arc) if d > distance), len(arc)-1)))
            t = (distance - arc[j]) / max(.000001, arc[j+1] - arc[j])
            sampled.append(_add(points[j], _mul(_sub(points[j+1], points[j]), t)))
        sampled[0], sampled[-1] = points[0], points[-1]
        rights = []
        for i in range(len(sampled)):
            direction = _sub(sampled[min(i+1, len(sampled)-1)], sampled[max(0, i-1)])
            rights.append(_unit((-direction[2], 0, direction[0])))
        return sampled, rights

    sections = {r['id']: (r, *resample(r)) for r in model_roads}
    raised_ends = {}
    for road, points, rights in sections.values():
        for i, sign in ((0, 1), (-1, -1)):
            if points[i][1] > .01:
                raised_ends.setdefault(tuple(points[i]), []).append((road, rights, i, sign))
    for endpoints in raised_ends.values():
        if len(endpoints) != 2:
            continue
        (road_a, ra, ia, sa), (road_b, rb, ib, sb) = endpoints
        assert road_a['width'] == road_b['width'], ('model raised join width mismatch', road_a['id'], road_b['id'])
        a, b = _mul(ra[ia], sa), _mul(rb[ib], sb)
        axis = _unit(_sub(a, b))
        assert _dot(axis, a) > .5, ('model raised join turns too sharply', road_a['id'], road_b['id'])
        miter = _mul(axis, 1 / _dot(axis, a))
        ra[ia], rb[ib] = _mul(miter, sa), _mul(miter, -sb)

    triangles = []
    for road in roads:
        road, points, rights = sections[road['id']]
        half = road['width'] / 2
        strips = [((-half, .035), (half, .035)),
                  ((-half, -.65), (half, -.65)),
                  ((-half, .035), (-half, -.65)),
                  ((half, -.65), (half, .035))]
        for i in range(len(points)-1):
            for strip_index, offsets in enumerate(strips):
                vertices = []
                for point, right in ((points[i], rights[i]), (points[i+1], rights[i+1])):
                    for x, y in offsets:
                        if strip_index >= 2 and y == -.65 and point[1] < .65:
                            x += math.copysign(1 - point[1] / .65, x); y = -point[1]
                        vertex = _add(point, _add(_mul(right, x), (0, y - .035, 0)))
                        vertices.append(vertex)
                # Strip face order is (near-left, near-right, far-right, far-left).
                triangles.extend((road['id'], triangle) for triangle in (
                    (vertices[0], vertices[1], vertices[3]),
                    (vertices[0], vertices[3], vertices[2])))
    return triangles


def check_wong_tai_sin_bus_envelope(data, roads):
    branches = [roads[i] for i in ('TD_103438', 'TD_103954')]
    crossing = roads['TD_103801']
    triangles = _model_raised_triangles(data, branches + [crossing])
    triangle_bounds = [(road_id, triangle, tuple(min(p[k] for p in triangle) for k in range(3)),
                        tuple(max(p[k] for p in triangle) for k in range(3))) for road_id, triangle in triangles]
    query_roads = branches + [crossing]
    hits = []; query_count = 0
    for road in query_roads:
        points = road['points']
        lane = bus_lane_offset(road['width'], road['elevated'], road['tunnel'])
        assert abs(lane) + 1.24 + .25 <= road['width'] / 2 + 1e-6, (road['id'], lane, road['width'])
        for i in range(2, len(points)-2, 3):
            p = points[i]
            forward = _unit(_sub(points[i+1], p))
            horizontal = _unit((forward[0], 0, forward[2]))
            right = (-horizontal[2], 0, horizontal[0])
            pitch = math.asin(max(-1, min(1, forward[1])))
            up = (-horizontal[0]*math.sin(pitch), math.cos(pitch), -horizontal[2]*math.sin(pitch))
            back = (-horizontal[0]*math.cos(pitch), -math.sin(pitch), -horizontal[2]*math.cos(pitch))
            axes = [right, up, back]
            half = (1.24, 2.1, 5.275)
            for lateral in (-lane, 0, lane):
                center = _add(p, _add(_mul(right, lateral), _mul(up, 2.55)))
                radius = tuple(sum(half[k] * abs(axes[k][component]) for k in range(3))
                               for component in range(3))
                query_count += 1
                for triangle_road, triangle, low, high in triangle_bounds:
                    if any(low[k] > center[k] + radius[k] + 1e-7 or high[k] < center[k] - radius[k] - 1e-7
                           for k in range(3)):
                        continue
                    if _box_hits_triangle(center, axes, half, triangle):
                        hits.append((road['id'], i, round(lateral, 3), triangle_road,
                                     tuple(tuple(round(value, 4) for value in vertex) for vertex in triangle)))
                        break
    assert not hits, f'Full bus OBB intersects raised-strip triangles: {hits}'
    print(f'ANTILA_WTS_BUS_ENVELOPE_OK: {query_count} full bus OBBs clear of {len(triangles)} raised-strip triangles; ' \
          'single-lane branches and TD_103801 low crossing remain supported')


def check():
    data = read(ROOT / 'Data', 'cross-harbour.json')
    source = read(ROOT / 'Data', 'cross-harbour-source.geojson')
    coast = read(ROOT / 'Data', 'east-kowloon-coast.json')
    baseline = read(BASELINE, 'cross-harbour.json')
    baseline_source = read(BASELINE, 'cross-harbour-source.geojson')
    baseline_coast = read(BASELINE, 'east-kowloon-coast.json')

    assert len(data['routes']) == 14, 'Expected route index 13 for Kowloon City → Wong Tai Sin'

    assert data['routes'][:13] == baseline['routes'], 'Existing routes 0–12 changed'
    assert data['tubes'] == baseline['tubes'], 'Existing tunnel profiles changed'
    assert data['bounds'] == baseline['bounds'], 'World bounds changed'
    assert source['features'][:len(baseline_source['features'])] == baseline_source['features'], \
        'Existing source records changed or were reordered'
    old_roads = {road['id']: road for road in baseline['roads']}
    roads = {road['id']: road for road in data['roads']}
    assert len(roads) == len(data['roads']) == len(source['features']) == 7275, \
        'Expected the complete road/source set, including the reviewed Kowloon Tong links'
    assert old_roads.keys() <= roads.keys(), 'An existing road record was removed'
    assert all(roads[ident] == road for ident, road in old_roads.items()), \
        'An existing road geometry or property changed'

    raw_path = ROOT / 'Data/east-kowloon-shoreline.geojson'
    baseline_raw_path = BASELINE / 'east-kowloon-shoreline.geojson'
    raw_bytes = raw_path.read_bytes()
    assert raw_bytes == baseline_raw_path.read_bytes(), 'Government shoreline source changed'
    assert coast['metadata']['source_sha256'] == hashlib.sha256(raw_bytes).hexdigest()
    assert coast['bounds'] == [550, -6400, 3150, -100], 'Eastern land cut has the wrong bounds'
    land = shape(coast['land'])
    previous_land = shape(baseline_coast['land'])
    old_clip = box(*baseline_coast['bounds'])
    assert land.is_valid and land.covers(previous_land), 'The old eastern land was not retained'
    assert land.intersection(old_clip).symmetric_difference(previous_land).area < .01, \
        'Land inside the old eastern cut changed'
    assert coast['coastline'] == baseline_coast['coastline'], 'Existing shoreline fragments changed'

    route = data['routes'][13]
    assert route['name'] == 'Kowloon City → Wong Tai Sin'
    assert 'TD_103731' in [ident.lstrip('-') for ident in route['source_ids']], \
        'The source-connected Fung Mo Street deck is required to join the eastern road components'
    assert math.dist(route['points'][0], data['routes'][12]['points'][-1]) < .001, \
        'New drive does not start at the old eastern endpoint'
    source_by_id = {f['properties']['source_id']: f for f in source['features']}
    assert len(source_by_id) == len(source['features']) == len(roads) == len(data['roads']), \
        'Road and source IDs must be unique and one-to-one'
    single_lane_widths = {'TD_103438':3.2, 'TD_103954':3.0}
    assert {ident:road['width'] for ident, road in roads.items() if ident in single_lane_widths} == single_lane_widths, \
        'Fung Mo single-lane widths must match their source-specific authored clearances'
    for ident, width in single_lane_widths.items():
        road=roads[ident];feature=source_by_id[ident]
        assert road['width'] == width and road['source_level'] == 0 and \
               feature['properties']['ELEVATION'] == '0' and feature['properties']['TRAVEL_DIRECTION'] == '3', \
            (ident, 'approach must retain its government level and forward one-way direction')
        source_line=LineString([local(p) for p in feature['geometry']['coordinates']])
        assert all(source_line.distance(Point(p[0],p[2])) < .0001 for p in road['points']), \
            (ident, 'width edit must not move sampled source centerline coordinates')
        assert math.dist((road['points'][0][0],road['points'][0][2]),source_line.coords[0]) < .0001 and \
               math.dist((road['points'][-1][0],road['points'][-1][2]),source_line.coords[-1]) < .0001, \
            (ident, 'runtime path order must follow the legal forward source direction')
    check_wong_tai_sin_bus_envelope(data, roads)
    route_line = LineString([(p[0], p[2]) for p in route['points']])
    route_parts = []
    for signed_id in route['source_ids']:
        reverse = signed_id.startswith('-')
        ident = signed_id.lstrip('-')
        feature = source_by_id[ident]
        direction = feature['properties']['TRAVEL_DIRECTION']
        assert direction in (('1', '2') if reverse else ('1', '3')), \
            (ident, 'source direction forbids this itinerary')
        road_points = roads[ident]['points']
        part = road_points[::-1] if reverse else road_points
        assert not roads[ident]['tunnel'], (ident, 'new drive must not enter a tunnel')
        source_line = LineString([local(p) for p in feature['geometry']['coordinates']])
        sampled = LineString([(p[0], p[2]) for p in part])
        assert sampled.hausdorff_distance(source_line) < 2.001, (ident, 'route leaves source centerline')
        assert all(source_line.distance(Point(p[0], p[2])) < .0001 for p in part), \
            (ident, 'sample is not on source centerline')
        assert not route_parts or math.dist(route_parts[-1][-1], part[0]) < .12, \
            (ident, 'source itinerary has a join gap')
        route_parts.append(part)
    joined = route_parts[0][:]
    for part in route_parts[1:]:
        joined.extend(part[1:])
    assert joined == route['points'], 'Route samples differ from its directed source itinerary'
    assert roads['TD_103731']['source_level'] == 1 and roads['TD_103731']['elevated'], \
        'The TD relative-level connector must retain its authored deck profile'
    companion = roads['TD_103730']
    assert companion['source_level'] == 1 and companion['elevated'], \
        'The source-paired Fung Mo Street deck must be modeled alongside the selected carriageway'
    companion_source = source_by_id['TD_103730']
    assert companion_source['properties']['TRAVEL_DIRECTION'] == '3' and \
           companion_source['properties']['ELEVATION'] == '1', \
        'The companion deck must retain its government direction and relative level'
    for deck_id, deck_end, ground_id, ground_end in (
        ('TD_103730', 0, 'TD_103485', -1), ('TD_103730', -1, 'TD_103487', 0)):
        deck_coords=[local(p) for p in source_by_id[deck_id]['geometry']['coordinates']]
        ground_coords=[local(p) for p in source_by_id[ground_id]['geometry']['coordinates']]
        assert math.dist(deck_coords[deck_end],ground_coords[ground_end]) < .12, \
            (deck_id,ground_id,'government source endpoints do not join')
        deck_point,ground_point=roads[deck_id]['points'][deck_end],roads[ground_id]['points'][ground_end]
        assert math.dist((deck_point[0],deck_point[2]),(ground_point[0],ground_point[2])) < .12, \
            (deck_id,ground_id,'source endpoint does not meet its ground approach')
        assert abs(deck_point[1]-ground_point[1]) < .01, \
            (deck_id,ground_id,'paired-deck approach profile has a height discontinuity')
    assert max(abs(b[1] - a[1]) for a, b in zip(route['points'], route['points'][1:])) < .35, \
        'The source-level bridge or its approach ramps have a height discontinuity'
    final_id = route['source_ids'][-1].lstrip('-')
    assert source_by_id[final_id]['properties']['STREET_ENAME'] == 'WONG TAI SIN ROAD', \
        'The route must finish on Wong Tai Sin Road'
    assert 1000 < route_line.length < 10000, route_line.length
    for a, b, c in zip(route['points'], route['points'][1:], route['points'][2:]):
        dot = sum((b[i] - a[i]) * (c[i] - b[i]) for i in range(3)) / \
              (math.dist(a, b) * math.dist(b, c))
        assert dot > -.5, 'New drive turns back sharply'

    ground = union_all([Polygon(t) for t in data['ground_triangles']])
    assert ground.covers(route_line.buffer(5.9)), 'New drive lacks continuous ground support'
    barriers = union_all([LineString(p) for key in ('kowloon_boundary', 'kowloon_coastline')
                          for p in data[key]])
    assert barriers.distance(route_line) > 6.3, 'New drive crosses the map edge or seawall'
    distance = sum(math.dist(a, b) for a, b in zip(route['points'], route['points'][1:]))
    print(f'ANTILA_WONG_TAI_SIN_SOURCE_OK: {len(roads)} roads; '
          f'{len(source["features"])} source records; {distance:.1f} m directed drive; '
          f'{len(route["source_ids"])} source sections; old routes/roads/tubes/shoreline preserved')


if __name__ == '__main__':
    check()
