"""Refresh the reviewed Kowloon, Wong Tai Sin and western New Territories sites from iB1000 sheets.

Offline rebuild: .venv-geodata/bin/python Tools/import_east_open_spaces.py
Verified source refresh: --extract CACHE_DIR TILE_MANIFEST_JSON. Downloads are staged separately.
"""
import hashlib
import json
import math
import random
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely import constrained_delaunay_triangles, make_valid, union_all
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import nearest_points, polylabel

from import_map import ORIGIN, ROOT, local
from import_open_spaces import encoded, replace_outputs

SOURCE = ROOT / 'Data/east-kowloon-open-spaces-source.geojson'
TARGET = ROOT / 'Data/east-kowloon-open-spaces.json'
SITES = {
    '1503005871': 'Hutchison Park', '1503005901': 'Tai Wan Shan Park',
    '1503005881': 'Hoi Sham Park', '1503005751': 'Ko Shan Road Park',
    '1503005870': 'To Kwa Wan Recreation Ground', '1503005863': 'Kowloon Walled City Park',
    '1503005866': 'Carpenter Road Park', '1503005714': 'Kowloon Tsai Park',
    '1910071209': 'Hung Hom Harbourfront', '1503005853': 'Morse Park',
    '1503005716': 'Junction Road Park', '1503005939': 'Choi Hung Road Playground',
    '1503005718': 'Lion Rock Park', '1910059822': 'Diamond Hill Water Feature Park',
    '1503005810': 'Ma Chai Hang Recreation Ground', '1503005961': 'Fung Tak Park',
    '1910064509': 'Hoi Fan Road Park', '1503000381': 'Central Kwai Chung Park',
    '1503005413': 'Shek Kip Mei Park', '1503000390': 'Lai Chi Kok Park',
    '1503005076': 'Nam Cheong Park', '1503000414': 'Shing Mun Valley Park',
    '1910069198': 'Kwai Chung Park', '1503000199': 'Tsuen Wan Park',
    '1810011761': 'Tsuen Wan Riviera Park'
}
SITE_BOUNDS = {
    '1503005871': [1826.7959910512027, -1521.0092856069375, 1997.8916879763524, -1306.9636430950327],
    '1503005901': [2037.6486812819355, -1278.063228570602, 2173.1167578527516, -1175.2341889791328],
    '1503005881': [1871.9432176891537, -2313.0317466918095, 2098.9824712245095, -1907.50746359212],
    '1503005751': [1150.5355297886654, -2311.348484227767, 1488.8607329272077, -1980.592032698378],
    '1503005870': [1776.6033510928078, -2791.75414020496, 1989.0173508778378, -2584.594445656426],
    '1503005863': [1713.639059908951, -4257.891011711707, 1980.2293124785942, -4037.4259302626224],
    '1503005866': [1532.3517004685953, -4161.18955329226, 2063.6765085864463, -3965.8787816273525],
    '1503005714': [1017.1909054534431, -4443.349740243774, 1358.1608900809742, -3849.1581288892426],
    '1910071209': [996.1195523483505, -509.6529589592727, 1104.5937895171367, -250.0385285930514],
    '1503005853': [1760.3173751329005, -5119.457393558613, 2288.845400516954, -4427.280784936417],
    '1503005716': [1111.5256304827312, -4950.948383086019, 1362.970881793604, -4737.835897821695],
    '1503005939': [2383.6107490413233, -4923.582929906242, 2702.2700728422237, -4616.948406871777],
    '1503005718': [970.8043299925458, -5773.7397669791135, 1328.0121736031258, -5398.5069190814365],
    '1910059822': [2677.233575864375, -5076.5110562881055, 3118.7957031399997, -4844.495887636024],
    '1503005810': [1596.190587643832, -5569.804171876455, 1779.3897064693133, -5405.642652004627],
    '1503005961': [2579.047443432498, -5372.188813796862, 2689.693166883958, -5229.831197913318],
    '1910064509': [-1732.3521805766952, -3082.8655755309037, -1595.4998534662866, -2860.294866206161],
    '1503000381': [-4224.798083177408, -7272.529653382138, -3844.879898541535, -6308.095521732379],
    '1503005413': [-377.5248763264252, -4941.30469055476, -58.370218496456424, -4328.298200843563],
    '1503000390': [-3848.078468328502, -5148.89470854557, -3078.5897515369866, -4167.693809688551],
    '1503005076': [-1734.542226475257, -3399.3829735405134, -1385.123684107868, -3024.9134984630628],
    '1503000414': [-4962.622008269732, -9275.338028197904, -4251.971198185875, -8693.337462672245],
    '1910069198': [-5738.491640333387, -6589.061843381081, -5436.021150340948, -6399.916456318958],
    '1503000199': [-6528.625296719309, -8184.949144270538, -5964.900747322041, -7708.218422287199],
    '1810011761': [-6275.605829581109, -7799.665424696743, -6056.081895757306, -7284.462980134114]
}
SITE_AREAS = {
    '1503005870': 24129.94, '1503005866': 57783.76, '1503005714': 151727.3,
    '1503005863': 30698.27, '1503005901': 9752.8, '1503005871': 24977.52,
    '1910071209': 13430.51, '1503005751': 51213.79, '1503005881': 32665.73,
    '1503005853': 138311.6389966884, '1503005716': 34258.67063764957,
    '1503005939': 40047.64332197038, '1503005718': 63997.520086180004,
    '1910059822': 28530.14636659569, '1503005810': 20193.488710215668,
    '1503005961': 10929.43612446799,
    '1910064509': 16418.810903934194, '1503000381': 105755.54982705388,
    '1503005413': 79801.42638753576, '1503000390': 221549.941513457,
    '1503005076': 47091.25146438434, '1503000414': 150237.2351947325,
    '1910069198': 15853.528033861303, '1503000199': 69395.69676229537,
    '1810011761': 43016.26394057317
}
SHORELINE = json.loads((ROOT / 'Data/east-kowloon-shoreline.geojson').read_text())['metadata']
INDEX_URL = SHORELINE['source']
# The official iB1000 query extends north beyond the current terrain coast bounds.
BBOX = (114.1, 22.295, 114.204, 22.38)
CACHE = Path('/tmp/antila-western-map-fixes-2026-10-28')
INDEX_RESPONSE = ROOT / 'evidence/western-map-fixes-2026-10-28/official-index-response.json'
INDEX_SHA256 = 'cb6b0f3a75b5f6fa4f32c09f89539ca552f95f29804520abb5245ab062d92adf'
COAST_FILES = (
    ROOT / 'Data/east-kowloon-coast.json', ROOT / 'Data/west-kowloon-coast.json',
    ROOT / 'Data/lai-chi-kok-coast.json', ROOT / 'Data/kwai-chung-coast.json',
    ROOT / 'Data/tsuen-wan-coast.json'
)
NS = {'g': 'http://www.opengis.net/gml', 'f': 'http://www.safe.com/gml/fme'}
LAYERS = ('Site', 'BuiltStructurePolygon')
KINDS = {'FOF': 'field', 'BAC': 'court', 'TEC': 'court', 'RAT': 'track'}
EXPECTED_SPORT_FRAGMENTS = {
    '1500001706': ('11-NE-21A', '11-NE-21C'),
    '1500004972': ('11-NE-21C',), '1500004971': ('11-NE-21C',),
    '1910087164': ('11-NE-16C',), '1910087165': ('11-NE-16C',),
    '1910087166': ('11-NE-16C',), '1910087167': ('11-NE-16C',),
    '1500001704': ('11-NE-16C',), '1500001702': ('11-NE-16C',),
    '1500001703': ('11-NE-16C',), '1500002363': ('11-NW-20D',),
    '1500001700': ('11-NE-16A',), '1500001701': ('11-NE-16A',),
    '1500001698': ('11-NE-16A',), '1500001699': ('11-NE-16A',),
    '1500001652': ('11-NE-11A',), '1500001648': ('11-NE-11A',),
    '1500001649': ('11-NE-11A',), '1500001650': ('11-NE-11A',),
    '1500001651': ('11-NE-11A',), '1810060612': ('11-NW-15B',),
    '1500001950': ('11-NW-10D', '11-NW-15B'),
    '1500001887': ('11-NW-15B',),
    '1500001948': ('11-NW-10D', '11-NW-15B'),
    '1500001949': ('11-NW-10D', '11-NW-15B'),
    '1500001881': ('11-NW-15B',), '1500001883': ('11-NW-15B',),
    '1500001874': ('11-NW-15B',),
    '1500001891': ('11-NW-10D',), '1500001892': ('11-NW-10D',),
    '1500001893': ('11-NW-10D',), '1500001894': ('11-NW-10D',),
    '1500001896': ('11-NW-10D',), '1500001897': ('11-NW-10D',),
    '1500001898': ('11-NW-10D',), '1500001899': ('11-NW-10D',),
    '1500001900': ('11-NW-10D',), '1500001901': ('11-NW-10D',),
    '1910085624': ('11-NE-1C', '11-NE-6A', '11-NW-10B', '11-NW-5D'),
    '1810000218': ('11-NE-6A', '11-NE-6C'),
    '1500001593': ('11-NE-6A',), '1500001585': ('11-NE-6A',),
    '1500001584': ('11-NE-6A',), '1500001583': ('11-NE-6A',),
    '1910084728': ('11-NE-6C',), '1810000220': ('11-NE-6C',),
    '1810000219': ('11-NE-6C',), '1810000217': ('11-NE-6C',),
    '1810000193': ('11-NE-6C',), '1500001608': ('11-NE-6C',),
    '1500001607': ('11-NE-6C',), '1500001606': ('11-NE-6C',),
    '1500001605': ('11-NE-6C',), '1500001604': ('11-NE-6C',),
    '1500001603': ('11-NE-6C',),
    '1500001622': ('11-NE-6B', '11-NE-6D'),
    '1500001621': ('11-NE-6B', '11-NE-6D'),
    '1500004960': ('11-NE-6D',), '1500004959': ('11-NE-6D',),
    '1500001618': ('11-NE-6D',), '1500001617': ('11-NE-6D',),
    '1500001616': ('11-NE-6D',),
    '1500002747': ('11-NW-10D',), '1500001940': ('11-NW-10D',),
    '1500001939': ('11-NW-10D',), '1500001938': ('11-NW-10D',),
    '1500001937': ('11-NW-10D',), '1500001936': ('11-NW-10D',),
    '1500001935': ('11-NW-10D',), '1500001934': ('11-NW-10D',),
    '1500001932': ('11-NW-10D',),
    '1500000750': ('6-SE-20D',), '1500000753': ('6-SE-20D',),
    '1500000756': ('6-SE-25B',), '1500000757': ('6-SE-25B',),
    '1500000760': ('6-SE-25B',), '1500001283': ('7-SW-16B',),
    '1500001285': ('7-SW-16B',), '1500001287': ('7-SW-11D',),
    '1500001289': ('7-SW-11D',), '1500001358': ('7-SW-22C',),
    '1500001359': ('7-SW-22C',), '1500001360': ('7-SW-22C',),
    '1500001361': ('7-SW-22C',), '1500001811': ('11-NW-7C',),
    '1500001812': ('11-NW-7C',), '1500001813': ('11-NW-7C',),
    '1500001817': ('11-NW-7C',), '1500001822': ('11-NW-7C',),
    '1500001823': ('11-NW-7A',), '1500001906': ('11-NW-9D',),
    '1500001913': ('11-NW-9D',), '1500001923': ('11-NW-9D',),
    '1500001924': ('11-NW-9D',), '1500001925': ('11-NW-9D',),
    '1500001926': ('11-NW-9D',), '1500001927': ('11-NW-9D',),
    '1500001928': ('11-NW-9D',), '1500001929': ('11-NW-9D',),
    '1500001930': ('11-NW-9D',), '1500004915': ('6-SE-20D',),
    '1500004916': ('6-SE-20D',), '1500004917': ('6-SE-25B',),
    '1500004918': ('6-SE-25B',), '1500004927': ('7-SW-16B',),
    '1500004928': ('7-SW-11D', '7-SW-12C'), '1500004937': ('11-NW-7C',),
    '1500004938': ('11-NW-7C',), '1500004939': ('11-NW-7C',),
    '1500004985': ('11-NW-9D',), '1500004986': ('11-NW-9D',),
    '1810018589': ('7-SW-11D', '7-SW-16B'),
    '1810061752': ('7-SW-11D', '7-SW-16B'),
    '1910085685': ('6-SE-25B', '6-SE-25D'),
    '1910085686': ('6-SE-25B', '6-SE-25D'),
    '1910086770': ('6-SE-25B',), '1910088624': ('11-NW-18B',),
    '1910088625': ('11-NW-18B',), '1910088626': ('11-NW-18B',),
    '1910088666': ('6-SE-25B',),
}
EXPECTED_SPORTS = frozenset(EXPECTED_SPORT_FRAGMENTS)
EXPECTED_SITE_FRAGMENTS = {
    '1503005714': ('11-NW-10D', '11-NW-15B'),
    '1503005716': ('11-NW-10B', '11-NW-10D'),
    '1503005718': ('11-NW-10B', '11-NW-5D'),
    '1503005751': ('11-NW-20D',),
    '1503005810': ('11-NE-1C', '11-NE-6A', '11-NW-10B', '11-NW-5D'),
    '1503005853': ('11-NE-6A', '11-NE-6C', '11-NE-6C', '11-NE-6C', '11-NE-6C'),
    '1503005863': ('11-NE-11A',),
    '1503005866': ('11-NE-11A', '11-NW-15B'),
    '1503005870': ('11-NE-16A',), '1503005871': ('11-NE-21A',),
    '1503005881': ('11-NE-16C',),
    '1503005901': ('11-NE-21A', '11-NE-21C'),
    '1503005939': ('11-NE-6B', '11-NE-6C', '11-NE-6D'),
    '1503005961': ('11-NE-6B',),
    '1810011761': ('6-SE-25B', '6-SE-25D'),
    '1910059822': ('11-NE-6B', '11-NE-6D'), '1910071209': ('11-SW-5B',),
    '1910064509': ('11-NW-13D', '11-NW-18B'),
    '1503000381': ('11-NW-2A', '7-SW-22C'),
    '1503005413': ('11-NW-9B', '11-NW-9D'),
    '1503000390': ('11-NW-12B', '11-NW-7A', '11-NW-7B', '11-NW-7C', '11-NW-7D', '11-NW-7D'),
    '1503005076': ('11-NW-13D', '11-NW-18B'),
    '1503000414': ('7-SW-11D', '7-SW-12C', '7-SW-16B'),
    '1910069198': ('11-NW-1A',),
    '1503000199': ('6-SE-20D', '6-SE-25B', '6-SE-25B'),
}
EXPECTED_SITE_IDS = frozenset(SITES)
WESTERN_SITE_COAST = {
    '1910064509': 'west-kowloon', '1503005413': 'lai-chi-kok',
    '1503000390': 'lai-chi-kok', '1503005076': 'west-kowloon',
    '1503000414': 'tsuen-wan', '1503000381': 'kwai-chung',
    '1910069198': 'kwai-chung', '1503000199': 'tsuen-wan',
    '1810011761': 'tsuen-wan'
}
EASTERN_SITE_IDS = EXPECTED_SITE_IDS - WESTERN_SITE_COAST.keys()
SHEET_CACHE_EXPECTED = 230
WIP_LABEL = 'WIP Sep 2026'
FOOTBALL_REFERENCE = 'https://www.lcsd.gov.hk/clpss/en/webApp/PhoneAddress.do?ftid=4'
HOI_SHAM_REFERENCE = 'https://www.lcsd.gov.hk/clpss/en/webApp/PhoneAddress.do?ftid=42'
TO_KWA_WAN_REFERENCE = 'https://www.info.gov.hk/gia/general/201306/30/P201306280790_print.htm'
SOURCE_TO_WGS84 = Transformer.from_crs(2326, 4326, always_xy=True)


def priority_boxes():
    scale_x = 111320 * math.cos(math.radians(ORIGIN[1]))
    return {uid: box(ORIGIN[0] + b[0] / scale_x, ORIGIN[1] - b[3] / 111320,
                     ORIGIN[0] + b[2] / scale_x, ORIGIN[1] - b[1] / 111320)
            for uid, b in SITE_BOUNDS.items()}


def index_polygon(geometry):
    if 'rings' in geometry:
        rings = geometry['rings']
        if not rings:
            raise ValueError('Empty iB1000 index tile geometry')
        return make_valid(Polygon(rings[0], rings[1:]))
    if all(key in geometry for key in ('xmin', 'ymin', 'xmax', 'ymax')):
        return box(geometry['xmin'], geometry['ymin'], geometry['xmax'], geometry['ymax'])
    raise ValueError('Unrecognized iB1000 index tile geometry')


def validate_index(index):
    if index.get('error') or index.get('exceededTransferLimit') or not index.get('features'):
        raise ValueError('Incomplete or empty official iB1000 index response')
    rows = []
    seen = set()
    for feature in index['features']:
        props = feature.get('attributes', {})
        tile = str(props.get('SHEETNO', '')).removeprefix('T')
        url = props.get('GML', '')
        revision = props.get('REVISIONDATE')
        geom = feature.get('geometry')
        if not tile or tile in seen or not url.startswith('https://open.hkmapservice.gov.hk/OpenData/directDownload?'):
            raise ValueError('Missing, duplicate, or unexpected official iB1000 tile row')
        if revision is None or not geom:
            raise ValueError('iB1000 index row is missing revision or whole-sheet geometry: ' + tile)
        polygon = index_polygon(geom)
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError('Invalid iB1000 tile geometry: ' + tile)
        seen.add(tile)
        rows.append(dict(tile=tile, url=url, revision_date=revision, geometry=geom))
    return rows


def select_tiles(index_tiles):
    boxes = priority_boxes()
    site_union = union_all(list(boxes.values()))
    selected = []
    candidates = []
    for row in index_tiles:
        tile = index_polygon(row['geometry'])
        candidates.append(tile)
        if tile.intersects(site_union):
            selected.append(row)
    if not selected:
        raise ValueError('No complete iB1000 sheets cover the reviewed site bounds')
    coverage = union_all([index_polygon(row['geometry']) for row in selected])
    for uid, site_box in boxes.items():
        if site_box.difference(coverage).area > 1e-10:
            raise ValueError('Selected whole-sheet tiles do not cover the reviewed bounds: ' + uid)
    return sorted(selected, key=lambda row: row['tile'])


def validate_manifest(manifest):
    if manifest.get('index_url') != INDEX_URL or tuple(manifest.get('bbox_wgs84', ())) != BBOX:
        raise ValueError('Unexpected iB1000 index source or extent')
    expected_bounds = {uid: list(bounds) for uid, bounds in SITE_BOUNDS.items()}
    if manifest.get('site_bounds') != expected_bounds:
        raise ValueError('Tile manifest does not use the reviewed 25 site bounds')
    if manifest.get('index_sha256') != INDEX_SHA256:
        raise ValueError('Tile manifest is not backed by the reviewed complete official index')
    index_sources = manifest.get('index_sources', [])
    response_path = str(INDEX_RESPONSE.relative_to(ROOT))
    matching_sources = [row for row in index_sources if row.get('kind') == 'expanded_25_site_official_index']
    if len(matching_sources) != 1 or matching_sources[0].get('path') != response_path or \
            matching_sources[0].get('sha256') != INDEX_SHA256 or matching_sources[0].get('bbox_wgs84') != list(BBOX):
        raise ValueError('Tile manifest is missing the reviewed expanded official-index response')
    response = INDEX_RESPONSE.read_bytes()
    if hashlib.sha256(response).hexdigest() != INDEX_SHA256:
        raise ValueError('The saved complete official iB1000 index response changed')
    official_rows = validate_index(json.loads(response))
    if len(official_rows) != SHEET_CACHE_EXPECTED:
        raise ValueError('The saved official iB1000 index response is incomplete')
    index_tiles = manifest.get('index_tiles')
    if (not isinstance(index_tiles, list) or len(index_tiles) != SHEET_CACHE_EXPECTED or
            len({row.get('tile') for row in index_tiles}) != SHEET_CACHE_EXPECTED):
        raise ValueError('Missing or incomplete whole-sheet iB1000 index selection')
    official_by_tile = {row['tile']: row for row in official_rows}
    for row in index_tiles:
        official = official_by_tile.get(row.get('tile'))
        if official is None or any(row.get(key) != official.get(key)
                                   for key in ('tile', 'url', 'revision_date', 'geometry')):
            raise ValueError('Cached index rows differ from the reviewed official response: ' + str(row.get('tile')))
    expected = select_tiles(official_rows)
    rows = manifest.get('tiles', [])
    names = [row.get('tile') for row in rows]
    if names != [row['tile'] for row in expected]:
        raise ValueError('Incomplete, duplicate, or unexpected whole-sheet tile selection')
    index_by_tile = official_by_tile
    for row in rows:
        source = index_by_tile[row['tile']]
        if row.get('url') != source.get('url') or row.get('revision_date') != source.get('revision_date'):
            raise ValueError('Selected tile provenance differs from official index: ' + row['tile'])
        if row.get('index_source') != matching_sources[0]['kind']:
            raise ValueError('Selected tile index vintage is inconsistent: ' + row['tile'])
        digest = row.get('sha256', '')
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest.lower()):
            raise ValueError('Invalid iB1000 tile SHA-256: ' + row['tile'])
    return rows


def regional_land():
    land_parts = []
    regions = []
    for path in COAST_FILES:
        data = json.loads(path.read_text())
        region = box(*data['bounds'])
        land_parts.append(make_valid(shape(data['land']).intersection(region)))
        regions.append(region)
    return union_all(land_parts), union_all(regions)


def site_land_geometries():
    east_path = ROOT / 'Data/east-kowloon-coast.json'
    east_data = json.loads(east_path.read_text())
    east_bounds = box(*east_data['bounds'])
    east_land = shape(east_data['land']).intersection(east_bounds)
    result = {uid: east_land for uid in EASTERN_SITE_IDS}
    for uid, region_name in WESTERN_SITE_COAST.items():
        path = next(path for path in COAST_FILES if path.stem == region_name + '-coast')
        data = json.loads(path.read_text())
        bounds = box(*data['bounds'])
        result[uid] = make_valid(shape(data['land']).intersection(bounds))
    return result


def fragment_counter(features, layer, id_field):
    return Counter((str(feature.get('properties', {}).get(id_field)),
                    str(feature.get('properties', {}).get('tile')))
                   for feature in features
                   if feature.get('properties', {}).get('layer') == layer)


def validate_source_fragments(source):
    raw = json.loads(source)
    if raw.get('type') != 'FeatureCollection' or not isinstance(raw.get('features'), list):
        raise AssertionError('Missing government feature collection')
    features = raw['features']
    site_features = [feature for feature in features if feature.get('properties', {}).get('layer') == 'Site']
    sport_features = [feature for feature in features
                      if feature.get('properties', {}).get('layer') == 'BuiltStructurePolygon']
    if len(site_features) + len(sport_features) != len(features) or any(
            feature.get('properties', {}).get('USAGETYPE') not in KINDS for feature in sport_features):
        raise AssertionError('Government source contains an unexpected layer or sport category')
    site_ids = {str(feature.get('properties', {}).get('SITEID')) for feature in site_features}
    sport_ids = {str(feature.get('properties', {}).get('BUILTSTRUCTUREPOLYGONID')) for feature in sport_features}
    if site_ids != EXPECTED_SITE_IDS:
        raise AssertionError(f'Raw source Site IDs differ from reviewed IDs; missing={sorted(EXPECTED_SITE_IDS-site_ids)}; unexpected={sorted(site_ids-EXPECTED_SITE_IDS)}')
    if sport_ids != EXPECTED_SPORTS:
        raise AssertionError(f'Raw source sports IDs differ from reviewed IDs; missing={sorted(EXPECTED_SPORTS-sport_ids)}; unexpected={sorted(sport_ids-EXPECTED_SPORTS)}')
    expected_sites = Counter((site_id, tile) for site_id, tiles in EXPECTED_SITE_FRAGMENTS.items()
                             for tile in tiles)
    actual_sites = fragment_counter(features, 'Site', 'SITEID')
    if actual_sites != expected_sites:
        raise AssertionError('Raw source Site geometry differs from reviewed fragments; missing=' +
                             repr(sorted((expected_sites-actual_sites).elements())) +
                             '; unexpected=' + repr(sorted((actual_sites-expected_sites).elements())))
    expected_sports = Counter((source_id, tile) for source_id, tiles in EXPECTED_SPORT_FRAGMENTS.items()
                              for tile in tiles)
    actual_sports = fragment_counter(features, 'BuiltStructurePolygon', 'BUILTSTRUCTUREPOLYGONID')
    if actual_sports != expected_sports:
        raise AssertionError('Raw source sports differ from reviewed fragments; missing=' +
                             repr(sorted((expected_sports-actual_sports).elements())) +
                             '; unexpected=' + repr(sorted((actual_sports-expected_sports).elements())))
    if len(features) != 189:
        raise AssertionError('The reviewed source must contain exactly 189 Site and sport fragments')
    metadata = raw.get('metadata', {})
    if set(metadata.get('site_revisions', {})) != EXPECTED_SITE_IDS or \
            set(metadata.get('sports_revisions', {})) != EXPECTED_SPORTS:
        raise AssertionError('Government source is missing complete Site or sports revision provenance')
    return raw


def source_ring(element):
    result = []
    for node in element.findall('.//g:posList', NS):
        values = list(map(float, node.text.split()))
        if len(values) < 6 or len(values) % 3 or not all(math.isfinite(v) for v in values):
            raise ValueError(f'Invalid iB1000 polygon ring: {len(values)} ordinates')
        points = [list(SOURCE_TO_WGS84.transform(values[i + 1], values[i]))
                  for i in range(0, len(values), 3)]
        if result:
            if math.dist(result[-1], points[0]) > 1e-8:
                raise ValueError('Disconnected iB1000 polygon ring')
            points = points[1:]
        result.extend(points)
    if len(result) < 4 or math.dist(result[0], result[-1]) > 1e-8:
        raise ValueError('Open iB1000 polygon ring')
    return result


def parse_polygon(item, tile, layer):
    props = {e.tag.split('}')[-1]: e.text for e in item if e.tag.startswith('{' + NS['f'] + '}')}
    if layer == 'Site' and props.get('SITEID') not in SITES:
        return []
    if layer == 'BuiltStructurePolygon' and props.get('USAGETYPE') not in KINDS:
        return []
    if props.get('STATUS') != 'E':
        return []
    ident = props.get('SITEID' if layer == 'Site' else 'BUILTSTRUCTUREPOLYGONID')
    if not ident:
        raise ValueError('iB1000 polygon feature is missing its source identifier: ' + tile)
    features = []
    for patch in item.findall('.//g:PolygonPatch', NS):
        exterior = patch.find('g:exterior', NS)
        if exterior is None:
            raise ValueError('iB1000 polygon is missing its exterior ring: ' + ident)
        rings = [source_ring(exterior), *[source_ring(h) for h in patch.findall('g:interior', NS)]]
        if Polygon(rings[0], rings[1:]).is_empty:
            raise ValueError('Empty iB1000 source polygon: ' + ident)
        features.append({'type': 'Feature', 'properties': props | {'layer': layer, 'tile': tile},
                         'geometry': {'type': 'Polygon', 'coordinates': rings}})
    if not features:
        raise ValueError('Recognized iB1000 polygon has no PolygonPatch: ' + ident)
    return features


def parse_annotations(archive, tile):
    result = []
    for layer in ('SiteAnno', 'SubSiteAnno'):
        name = f'{tile}/Layers/Buildings/{layer}.gml'
        if name not in archive.namelist():
            continue
        doc = ET.fromstring(archive.read(name))
        if doc.tag != '{' + NS['g'] + '}FeatureCollection':
            raise ValueError('Invalid iB1000 annotation layer: ' + name)
        for member in doc.findall(f'g:featureMember/f:{layer}', NS):
            text = member.find('f:TextString', NS)
            pos = member.find('.//g:pos', NS)
            if text is None or not text.text or pos is None:
                continue
            values = list(map(float, pos.text.split()))
            if len(values) < 2 or not all(math.isfinite(v) for v in values):
                raise ValueError('Invalid iB1000 site annotation position: ' + tile)
            lon, lat = SOURCE_TO_WGS84.transform(values[1], values[0])
            props = {e.tag.split('}')[-1]: e.text for e in member if e.tag.startswith('{' + NS['f'] + '}')}
            result.append({'text': ' '.join(text.text.split()), 'tile': tile, 'layer': layer,
                           'last_updated': props.get('LASTUPDATEDATE'), 'position_wgs84': [lon, lat]})
    return result


def extract(cache, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    tile_rows = validate_manifest(manifest)
    found = []
    annotations = []
    for row in tile_rows:
        path = Path(cache) / (row['tile'] + '.zip')
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != row['sha256']:
            raise ValueError('Government ZIP checksum mismatch: ' + row['tile'])
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('Corrupt iB1000 archive: ' + row['tile'])
            for layer in LAYERS:
                name = f"{row['tile']}/Layers/Buildings/{layer}.gml"
                expected_fragments = EXPECTED_SITE_FRAGMENTS if layer == 'Site' else EXPECTED_SPORT_FRAGMENTS
                has_expected = any(row['tile'] in tiles for tiles in expected_fragments.values())
                if name not in archive.namelist():
                    if has_expected:
                        raise ValueError('Missing required government layer: ' + name)
                    continue
                doc = ET.fromstring(archive.read(name))
                if doc.tag != '{' + NS['g'] + '}FeatureCollection':
                    raise ValueError('Invalid government layer: ' + name)
                systems = [e.get('srsName') for e in doc.iter() if e.get('srsName')]
                if not systems or any(crs != 'EPSG:2326' for crs in systems):
                    raise ValueError('Unexpected iB1000 CRS: ' + name)
                members = doc.findall(f'g:featureMember/f:{layer}', NS)
                if not members and has_expected:
                    raise ValueError('Empty or unrecognized required government layer: ' + name)
                for item in members:
                    found.extend(parse_polygon(item, row['tile'], layer))
            annotations.extend(parse_annotations(archive, row['tile']))

    sites = defaultdict(list)
    for feature in found:
        if feature['properties']['layer'] == 'Site':
            uid = feature['properties']['SITEID']
            sites[uid].append(source_local(feature))
    if set(sites) != set(SITES):
        raise ValueError('Incomplete source Site geometry: ' + ', '.join(sorted(set(SITES) - set(sites))))
    land, region = regional_land()
    site_geometries = {uid: union_all(parts).intersection(land).intersection(region) for uid, parts in sites.items()}
    site_union = union_all(list(site_geometries.values()))
    source_features = [feature for feature in found if feature['properties']['layer'] == 'Site']
    for feature in found:
        if feature['properties']['layer'] != 'BuiltStructurePolygon':
            continue
        if source_local(feature).intersection(site_union).area > 1:
            source_features.append(feature)
    if not any(f['properties']['layer'] == 'BuiltStructurePolygon' for f in source_features):
        raise ValueError('The selected iB1000 sheets contain no source sports surfaces')

    site_revisions = {uid: sorted({f['properties'].get('LASTUPDATEDATE') for f in source_features
                                   if f['properties']['layer'] == 'Site' and f['properties']['SITEID'] == uid})
                      for uid in SITES}
    sport_revisions = {uid: sorted({f['properties'].get('LASTUPDATEDATE') for f in source_features
                                    if f['properties']['layer'] == 'BuiltStructurePolygon' and
                                    f['properties']['BUILTSTRUCTUREPOLYGONID'] == uid})
                       for uid in sorted({f['properties']['BUILTSTRUCTUREPOLYGONID'] for f in source_features
                                          if f['properties']['layer'] == 'BuiltStructurePolygon'})}
    relevant_annotations = []
    for annotation in annotations:
        point = Point(local(annotation['position_wgs84']))
        for uid, site in site_geometries.items():
            if site.covers(point):
                relevant_annotations.append(annotation | {'site': uid})
                break
    metadata = {
        'provider': 'Lands Department, HKSAR Government', 'source': INDEX_URL,
        'index_url': INDEX_URL, 'bbox_wgs84': list(BBOX),
        'retrieved_utc': manifest['retrieved_utc'], 'source_crs': 'EPSG:2326',
        'axis_order': 'GML northing,easting,height; converted to WGS84',
        'terms': SHORELINE.get('terms'), 'origin_wgs84': ORIGIN,
        'index_sha256': manifest['index_sha256'], 'index_sources': manifest.get('index_sources', []),
        'source_manifests': manifest.get('source_manifests', []),
        'tile_manifest_sha256': hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
        'tiles': [{k: row[k] for k in ('tile', 'url', 'revision_date', 'sha256')} |
                  {'retrieved_utc': row.get('retrieved_utc', manifest['retrieved_utc']),
                   'index_source': row.get('index_source') or 'official_index'} for row in tile_rows],
        'site_revisions': site_revisions, 'sports_revisions': sport_revisions,
        'source_annotations': relevant_annotations,
        'known_wip_annotations': [a for a in relevant_annotations if WIP_LABEL.lower() in a['text'].lower()],
        'note': 'Government Site and BuiltStructurePolygon geometries are retained from complete selected iB1000 sheets. Sports and site source dates vary; Carpenter Road has a WIP Sep 2026 source annotation. Paths, access, surface styling, planting and furniture are authored approximations.'
    }
    if not metadata['known_wip_annotations']:
        # Retain the reviewed warning if the annotation label is absent from a selected sheet.
        metadata['known_wip_annotations'] = [{'site': '1503005866', 'text': WIP_LABEL,
                                               'source': 'reviewed priority-site annotation; see selected sheet revision metadata'}]
    return encoded({'type': 'FeatureCollection', 'metadata': metadata, 'features': source_features})


def source_local(feature):
    geometry = feature['geometry']
    parts = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
    return make_valid(union_all([Polygon([local(p) for p in coords[0]],
                                        [[local(p) for p in ring] for ring in coords[1:]])
                                 for coords in parts]))


def geometry_rings(poly):
    return [list(poly.exterior.coords)[:-1], *[list(ring.coords)[:-1] for ring in poly.interiors]]


def geometry_polygons(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if hasattr(geom, 'geoms'):
        return [part for item in geom.geoms for part in geometry_polygons(item)]
    return []


def polygon_triangles(poly):
    faces = list(constrained_delaunay_triangles(poly).geoms)
    if abs(sum(face.area for face in faces) - poly.area) > .01:
        raise ValueError('Polygon triangulation lost source area')
    return [list(face.exterior.coords)[:-1] for face in faces]


def safe_site_polygons():
    layout_paths = sorted(ROOT.glob('Data/*layout.json'))
    if len(layout_paths) != 9:
        raise ValueError(f'Expected all nine loaded building layouts; found {len(layout_paths)}')
    buildings = []
    pavement_patches = []
    inputs = {}
    for path in layout_paths:
        inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        data = json.loads(path.read_text())
        buildings.extend(Polygon(b['rings'][0], b['rings'][1:]) for b in data['buildings'])
        pavement_patches.extend(Polygon(p['polygon']) for p in data['pavement_patches'])
    lots = union_all(buildings)
    road_path = ROOT / 'Data/cross-harbour.json'
    inputs[str(road_path.relative_to(ROOT))] = hashlib.sha256(road_path.read_bytes()).hexdigest()
    for coast_path in COAST_FILES:
        inputs[str(coast_path.relative_to(ROOT))] = hashlib.sha256(coast_path.read_bytes()).hexdigest()
    east_path = ROOT / 'Data/east-kowloon-coast.json'
    east_data = json.loads(east_path.read_text())
    east_land = shape(east_data['land'])
    east_bounds = box(*east_data['bounds'])
    roads = []
    prop_roads = []
    street_targets = []
    carriageways = []
    network = json.loads(road_path.read_text())
    for road in network['roads']:
        if road['tunnel'] and not road.get('ramp', False):
            continue
        line = LineString([(p[0], p[2]) for p in road['points']])
        if not line.intersects(east_bounds):
            continue
        roads.append(line.buffer(max(12, road['width']) / 2 + 3.5, join_style='mitre'))
        prop_roads.append(line.buffer(max(12, road['width']) / 2 + 8, join_style='mitre'))
        street_targets.append(line.buffer(max(12, road['width']) / 2 + 3, join_style='mitre'))
        carriageways.append(line.buffer(max(12, road['width']) / 2, join_style='mitre'))
    ground = union_all([Polygon(triangle) for triangle in network['ground_triangles']])
    bounds = network['bounds']
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    resolution = min(2, 16384 / max(width, height))
    pixels_x, pixels_y = min(16384, math.ceil(width * resolution)), min(16384, math.ceil(height * resolution))
    pixel_radius = math.hypot(width / pixels_x, height / pixels_y) / 2
    paving_margin = pixel_radius + math.hypot(width / pixels_x, height / pixels_y)
    east = (union_all(roads), union_all(prop_roads), east_land.intersection(east_bounds),
            union_all(street_targets), union_all(carriageways))

    west_regions = {}
    for coast_path in COAST_FILES:
        region_name = coast_path.stem.removesuffix('-coast')
        if region_name == 'east-kowloon' or region_name not in set(WESTERN_SITE_COAST.values()):
            continue
        data = json.loads(coast_path.read_text())
        bounds = box(*data['bounds'])
        region_roads = []
        region_prop_roads = []
        region_street_targets = []
        region_carriageways = []
        for road in network['roads']:
            if road['tunnel'] and not road.get('ramp', False):
                continue
            line = LineString([(p[0], p[2]) for p in road['points']])
            regional_line = line.intersection(bounds)
            if regional_line.is_empty:
                continue
            region_roads.append(regional_line.buffer(max(12, road['width']) / 2 + 3.5, join_style='mitre'))
            region_prop_roads.append(regional_line.buffer(max(12, road['width']) / 2 + 8, join_style='mitre'))
            region_street_targets.append(regional_line.buffer(max(12, road['width']) / 2 + 3, join_style='mitre'))
            region_carriageways.append(regional_line.buffer(max(12, road['width']) / 2, join_style='mitre'))
        west_regions[region_name] = (
            union_all(region_roads), union_all(region_prop_roads),
            make_valid(shape(data['land']).intersection(bounds)),
            union_all(region_street_targets), union_all(region_carriageways))
    return (inputs, lots, *east[:2], east[2], east[3], east[4], ground, west_regions,
            union_all(pavement_patches), paving_margin)


def publicly_connected_path_components(paths, access, street_targets, lots, pavement_patches, paving_margin):
    if paths.is_empty or street_targets.is_empty:
        return []
    context = paths.envelope.buffer(250 + paving_margin)
    local_targets = street_targets.intersection(context)
    local_lots = lots.intersection(context)
    local_patches = pavement_patches.intersection(context)
    paved = make_valid(union_all([
        paths.buffer(paving_margin), access.buffer(paving_margin),
        local_targets.buffer(paving_margin), local_lots.buffer(3 + paving_margin),
        local_patches.buffer(paving_margin)
    ]).difference(local_lots))
    return [part for part in geometry_polygons(paved) if part.intersects(local_targets)]


def path_network(site_id, site, safe, sports, street_targets, carriageways, land, building_clearance,
                 lots, pavement_patches, paving_margin):
    blocked = sports.buffer(3.5) if not sports.is_empty else Polygon()
    free = make_valid(safe.difference(blocked))
    linework = []
    path_parts = []
    access_parts = []
    for part in geometry_polygons(free):
        if part.area < 80:
            continue
        inset = part.buffer(-4, join_style='mitre')
        if inset.is_empty:
            inset = part.buffer(-1.5, join_style='mitre')
        if inset.is_empty:
            continue
        for inset_part in geometry_polygons(inset):
            if inset_part.area < 40:
                continue
            centre = polylabel(inset_part, tolerance=.25)
            rectangle = list(inset_part.minimum_rotated_rectangle.exterior.coords)[:4]
            edges = [(rectangle[(i + 1) % 4][0] - rectangle[i][0],
                      rectangle[(i + 1) % 4][1] - rectangle[i][1]) for i in range(4)]
            lengths = [math.hypot(*v) for v in edges]
            primary_index = max(range(4), key=lambda i: lengths[i])
            secondary_index = (primary_index + 1) % 4
            primary = edges[primary_index]
            primary_len = lengths[primary_index]
            secondary = edges[secondary_index]
            secondary_len = lengths[secondary_index]
            a = (primary[0] / primary_len, primary[1] / primary_len)
            b = (secondary[0] / secondary_len, secondary[1] / secondary_len)
            lines = [LineString([(centre.x - a[0] * primary_len, centre.y - a[1] * primary_len),
                                 (centre.x + a[0] * primary_len, centre.y + a[1] * primary_len)]),
                     LineString([(centre.x - b[0] * secondary_len, centre.y - b[1] * secondary_len),
                                 (centre.x + b[0] * secondary_len, centre.y + b[1] * secondary_len)])]
            if primary_len > 45:
                for offset in (-primary_len / 3, primary_len / 3):
                    x, z = centre.x + a[0] * offset, centre.y + a[1] * offset
                    lines.append(LineString([(x - b[0] * secondary_len, z - b[1] * secondary_len),
                                             (x + b[0] * secondary_len, z + b[1] * secondary_len)]))
            perimeter = inset_part.boundary
            linework.extend(lines)
            linework.extend([LineString(ring.coords) for ring in (inset_part.exterior, *inset_part.interiors)])
            path_parts.append(perimeter.buffer(1.8, join_style='round'))
            path_parts.extend(line.buffer(1.8, cap_style='round') for line in lines)
    paths = make_valid(union_all(path_parts).intersection(free)) if path_parts else Polygon()
    # Join separated loops across clear garden ground; existing public paving can serve the rest.
    parts = [part for part in geometry_polygons(paths) if part.area >= 1]
    path_samples = []
    for part in parts:
        point = polylabel(part, tolerance=.1)
        if part.boundary.distance(point) > 1.1:
            path_samples.append([point.x, point.y])
    while len(parts) > 1:
        candidates = sorted((parts[i].distance(parts[j]), i, j)
                            for i in range(len(parts)) for j in range(i + 1, len(parts)))
        for _, i, j in candidates:
            start, end = nearest_points(parts[i], parts[j])
            centerline = LineString([start, end])
            corridor = centerline.buffer(1.8)
            if corridor.difference(free.buffer(.01)).area > .01:
                continue
            joined = union_all([parts[i], parts[j], corridor])
            parts = [part for k, part in enumerate(parts) if k not in (i, j)] + [joined]
            linework.append(centerline)
            break
        else:
            break
    paths = union_all(parts)
    # Safe-area clipping can leave isolated scraps too narrow for a clearance-safe connectivity probe.
    retained = []
    discarded_component = False
    sampled = [Point(sample) for sample in path_samples]
    for part in geometry_polygons(paths):
        if part.area < 1:
            discarded_component = True
            continue
        if any(part.covers(sample) for sample in sampled):
            retained.append(part)
            continue
        point = polylabel(part, tolerance=.1)
        if part.boundary.distance(point) <= 1.1:
            discarded_component = True
            continue
        retained.append(part)
        path_samples.append([point.x, point.y])
        sampled.append(point)
    # Keep the original geometry serialization when every component is usable; re-union only
    # when clipping left a component that cannot safely retain a connectivity probe.
    if discarded_component:
        paths = union_all(retained) if retained else Polygon()

    # Connect interior paths to the existing street paving edge. The authored corridor may
    # leave the government site boundary, but it must stay on mainland land and clear buildings.
    access_reason = 'no nearby street paving'
    if not paths.is_empty and not street_targets.is_empty:
        start, end = nearest_points(paths, street_targets.boundary)
        toward_street = (end.x - start.x, end.y - start.y)
        distance = math.hypot(*toward_street)
        start_inside = Point(start.x - toward_street[0] / max(distance, .01) * 2.5,
                             start.y - toward_street[1] / max(distance, .01) * 2.5)
        approach = LineString([start_inside, start])
        centerline = LineString([start_inside, end])
        # Do not draw an entrance across a carriageway, seawall or building footprint.
        if centerline.length <= 250 and free.buffer(.01).covers(approach):
            corridor = centerline.buffer(1.8, cap_style='flat')
            inside_land = corridor.difference(land.buffer(.01)).area <= .01
            clear_buildings = corridor.intersection(building_clearance).area <= .01
            clear_carriageway = corridor.intersection(carriageways).area <= .01
            clear_sports = corridor.intersection(blocked).area <= .01
            joins_path = corridor.intersection(paths).area > .1
            if inside_land and clear_buildings and clear_carriageway and clear_sports and joins_path:
                access_parts.append(corridor)
                linework.append(centerline)
            else:
                access_reason = f'land={inside_land}, buildings={clear_buildings}, road={clear_carriageway}, sports={clear_sports}, path={joins_path}'
        else:
            access_reason = f'entrance route is {centerline.length:.1f} m or does not begin on an interior path'

    access = union_all(access_parts) if access_parts else Polygon()
    rejected_components = []
    if site_id in WESTERN_SITE_COAST and not paths.is_empty:
        connected = publicly_connected_path_components(paths, access, street_targets, lots,
                                                      pavement_patches, paving_margin)
        retained = []
        extra_access = []
        for index, component in enumerate(geometry_polygons(paths)):
            if any(public.intersects(component) for public in connected):
                retained.append(component)
                continue
            reason = 'no street target'
            if not street_targets.is_empty:
                start, end = nearest_points(component, street_targets.boundary)
                toward_street = (end.x - start.x, end.y - start.y)
                distance = math.hypot(*toward_street)
                start_inside = Point(start.x - toward_street[0] / max(distance, .01) * 2.5,
                                     start.y - toward_street[1] / max(distance, .01) * 2.5)
                approach = LineString([start_inside, start])
                centerline = LineString([start_inside, end])
                corridor = centerline.buffer(1.8, cap_style='flat')
                reasons = []
                if centerline.length > 250:
                    reasons.append(f'length={centerline.length:.2f}m exceeds 250m')
                if not free.buffer(.01).covers(approach):
                    reasons.append('approach leaves the safe site')
                if corridor.difference(land.buffer(.01)).area > .01:
                    reasons.append('corridor leaves mainland ground')
                if corridor.intersection(building_clearance).area > .01:
                    reasons.append('corridor enters building clearance')
                if corridor.intersection(carriageways).area > .01:
                    reasons.append('corridor enters a carriageway')
                if corridor.intersection(blocked).area > .01:
                    reasons.append('corridor enters a sports clearance')
                if corridor.intersection(component).area <= .1:
                    reasons.append('corridor misses the path component')
                if not reasons:
                    retained.append(component)
                    extra_access.append(corridor)
                    linework.append(centerline)
                    continue
                reason = '; '.join(reasons)
            rejected_components.append(dict(site=site_id, component=f'{site_id}:{index:02d}',
                                            area_m2=round(component.area, 2), reason=reason))
        if rejected_components:
            paths = union_all(retained) if retained else Polygon()
            path_samples = [sample for sample in path_samples
                            if any(part.covers(Point(sample)) for part in retained)]
            linework = [line for line in linework if line.intersects(paths)]
        if extra_access:
            access = union_all([access, *extra_access])
        connected = publicly_connected_path_components(paths, access, street_targets, lots,
                                                      pavement_patches, paving_margin)
        if any(not any(public.intersects(component) for public in connected)
               for component in geometry_polygons(paths)):
            raise ValueError(f'{site_id}: retained western paths do not connect to public paving')
    if paths.is_empty or paths.area < 80:
        raise ValueError('Could not create useful connected paths in source site')
    if access.is_empty:
        raise ValueError(f'{site_id}: could not connect site paths to existing street paving ({access_reason})')
    return paths, access, linework, path_samples, rejected_components


def football_style(site_id, source_id, source_area):
    if source_id in ('1500001948', '1500001949'):
        return 'court', 'LCSD lists two hard-surface seven-a-side pitches at Kowloon Tsai Park.'
    if source_id in ('1500001881', '1500001883', '1500001874'):
        return 'field', 'LCSD lists three turf football pitches at Kowloon Tsai Park.'
    if source_id in ('1500001702', '1500001703'):
        return 'court', 'LCSD lists five-a-side football at Hoi Sham Park.'
    if source_id in ('1500001706', '1500002363', '1500001698', '1500001699', '1500001652') and source_area < 4000:
        return 'court', 'Small iB1000 FOF surfaces are styled as hard football courts; surface finish is an authored approximation.'
    return 'field', 'iB1000 FOF source geometry retained; field finish is an authored approximation.'


def build(source):
    raw = validate_source_fragments(source)
    inputs, lots, roads, prop_roads, land, street_targets, carriageways, ground, west_regions, \
        pavement_patches, paving_margin = safe_site_polygons()
    building_clearance = lots.buffer(4)
    east_region = (roads, prop_roads, land, street_targets, carriageways)
    site_regions = {uid: west_regions[WESTERN_SITE_COAST[uid]] if uid in WESTERN_SITE_COAST else east_region
                    for uid in SITES}
    site_lands = {uid: region[2] for uid, region in site_regions.items()}
    site_parts = defaultdict(list)
    sports_parts = defaultdict(list)
    attributes = {}
    source_features = raw['features']
    for feature in source_features:
        props = feature.get('properties', {})
        if feature.get('geometry', {}).get('type') not in ('Polygon', 'MultiPolygon'):
            raise ValueError('Unexpected government source geometry')
        poly = source_local(feature)
        if poly.is_empty or not poly.is_valid:
            raise ValueError('Invalid government source polygon')
        if props.get('layer') == 'Site' and props.get('SITEID') in SITES:
            site_parts[props['SITEID']].append(poly)
        elif props.get('layer') == 'BuiltStructurePolygon' and props.get('USAGETYPE') in KINDS:
            source_id = props.get('BUILTSTRUCTUREPOLYGONID')
            if not source_id:
                raise ValueError('Sports source feature is missing its source ID')
            sports_parts[source_id].append(poly)
            attributes[source_id] = props
    sites = {uid: union_all(parts).intersection(site_lands[uid]) for uid, parts in site_parts.items()}
    if set(sites) != set(SITES):
        raise ValueError('Government source is missing one or more reviewed sites')
    for uid, site in sites.items():
        if site.is_empty or not site.is_valid or abs(site.area - SITE_AREAS[uid]) > max(1, SITE_AREAS[uid] * .002):
            raise ValueError('Source site differs from reviewed bounds or mainland clipping: ' + uid)
    assignment = defaultdict(list)
    for source_id, parts in sports_parts.items():
        raw_poly = union_all(parts)
        overlaps = sorted(((raw_poly.intersection(site).area, uid) for uid, site in sites.items()), reverse=True)
        area, uid = overlaps[0]
        if area > 20:
            poly = raw_poly.intersection(site_lands[uid])
            if poly.area > 20:
                assignment[uid].append((source_id, poly, attributes[source_id]))

    sites_out = []
    surfaces = []
    sports = []
    paving = []
    fixtures = []
    gardens = []
    path_component_rejections = []
    global_fixture_points = []
    source_sport_ids = set()
    for uid, name in SITES.items():
        site = sites[uid]
        site_roads, site_prop_roads, site_land, site_street_targets, site_carriageways = site_regions[uid]
        safe = make_valid(site.difference(union_all([building_clearance, site_roads])))
        if safe.is_empty or safe.area < 100:
            raise ValueError('Building and road clearance removed the usable area: ' + uid)
        site_sports = assignment[uid]
        # A running track's inner ring encloses its athletics infield, not garden space.
        source_union = union_all([(union_all([Polygon(p.exterior) for p in geometry_polygons(poly)])
            if props['USAGETYPE']=='RAT' else poly).intersection(site) for _,poly,props in site_sports]) if site_sports else Polygon()
        paths, access, linework, path_samples, rejected = path_network(
            uid, site, safe, source_union, site_street_targets, site_carriageways, ground,
            building_clearance, lots, pavement_patches, paving_margin)
        path_component_rejections.extend(rejected)
        for access_part in geometry_polygons(access):
            point = polylabel(access_part, tolerance=.1)
            if access_part.boundary.distance(point) > 1.1:
                path_samples.append([point.x, point.y])
        if not path_samples:
            raise ValueError('Garden path lacks an interior paving-mask sample: ' + uid)
        for source_id, poly, props in site_sports:
            clipped = make_valid(poly.intersection(site).intersection(safe))
            if clipped.is_empty or clipped.area < 20:
                raise ValueError('Source sports outline was lost during safe-area clipping: ' + source_id)
            style, style_note = (football_style(uid, source_id, poly.area) if props['USAGETYPE'] == 'FOF'
                                 else (KINDS[props['USAGETYPE']], 'Source sport category from iB1000.'))
            source_sport_ids.add(source_id)
            for part in geometry_polygons(clipped):
                sample = polylabel(part, tolerance=.1)
                surfaces.append(dict(site=uid, source_id=source_id, usage=props['USAGETYPE'], kind=style,
                                     rings=geometry_rings(part), triangles=polygon_triangles(part),
                                     sample=[sample.x, sample.y]))
            # The Blender script receives only intact, source-contained rectangles.
            if clipped.symmetric_difference(poly.intersection(site)).area < .01 and site.covers(poly) and safe.covers(poly):
                rectangle = poly.minimum_rotated_rectangle
                if poly.area / rectangle.area > .9 and props['USAGETYPE'] != 'RAT' and poly.covers(rectangle.buffer(-.2, join_style='mitre')):
                    coords = list(rectangle.exterior.coords)[:-1]
                    if math.dist(coords[0], coords[1]) > math.dist(coords[1], coords[2]):
                        coords = coords[1:] + coords[:1]
                    center = rectangle.centroid
                    axis = (coords[2][0] - coords[1][0], coords[2][1] - coords[1][1])
                    length = math.hypot(*axis)
                    if length > 1:
                        sports.append(dict(site=uid, source_id=source_id, usage=props['USAGETYPE'], kind=style,
                                           classification=style_note, center=[center.x, center.y],
                                           forward=[axis[0] / length, axis[1] / length],
                                           width=math.dist(coords[0], coords[1]), length=length))
        sport_block = source_union.buffer(4) if not source_union.is_empty else Polygon()
        planting = safe.difference(union_all([sport_block, paths.buffer(3.5), access.buffer(3.5), site_prop_roads]))
        rng = random.Random(int(uid))
        props_out = []
        xmin, zmin, xmax, zmax = site.bounds
        spacing = 13 if site.area < 30000 else 19
        jitter = min(3, spacing * .16)
        for x in range(math.ceil(xmin / spacing) * spacing, math.floor(xmax), spacing):
            for z in range(math.ceil(zmin / spacing) * spacing, math.floor(zmax), spacing):
                point = Point(x + rng.uniform(-jitter, jitter), z + rng.uniform(-jitter, jitter))
                radius = 1.6
                if planting.covers(point.buffer(radius)):
                    if any(point.distance(existing) < radius + existing_radius + 2 for existing, existing_radius in global_fixture_points):
                        continue
                    item = dict(site=uid, asset='banyan' if len(props_out) % 4 == 0 else 'street-tree',
                                position=[point.x, point.y], yaw=rng.uniform(0, math.tau), radius=radius,
                                scale=.52 if len(props_out) % 4 == 0 else .62)
                    props_out.append(item)
                    global_fixture_points.append((point, radius))

        # Benches sit off path edges with clear approach corridors and source/building/road clearance.
        for line in linework:
            for segment in (line,) if line.geom_type == 'LineString' else getattr(line, 'geoms', ()):
                if segment.length < 24:
                    continue
                for d in range(12, int(segment.length), 26):
                    centre = segment.interpolate(d)
                    before = segment.interpolate(max(0, d - 1))
                    after = segment.interpolate(min(segment.length, d + 1))
                    dx, dz = after.x - before.x, after.y - before.y
                    length = math.hypot(dx, dz)
                    if length < .01:
                        continue
                    normal = (-dz / length, dx / length)
                    for side in (-1, 1):
                        point = Point(centre.x + normal[0] * side * 3.5, centre.y + normal[1] * side * 3.5)
                        radius = 1.05
                        if not safe.covers(point.buffer(radius)) or paths.distance(point) < 1.1 or access.distance(point) < 2.5:
                            continue
                        if source_union.distance(point) < 5 or prop_roads.distance(point) < radius:
                            continue
                        if any(point.distance(existing) < radius + existing_radius + 4 for existing, existing_radius in global_fixture_points):
                            continue
                        item = dict(site=uid, asset='bench', position=[point.x, point.y],
                                    yaw=math.atan2(-dx, -dz), radius=radius, scale=1)
                        props_out.append(item)
                        global_fixture_points.append((point, radius))
                        break

        if not any(f['asset'] in ('street-tree', 'banyan') for f in props_out):
            # Narrow court-side beds can miss the tree grid; fit a planter to usable planting ground.
            for part in geometry_polygons(planting):
                point = polylabel(part, tolerance=.1)
                radius = 1.1
                if not part.covers(point.buffer(radius)):
                    continue
                if any(point.distance(existing) < radius + existing_radius + 2 for existing, existing_radius in global_fixture_points):
                    continue
                props_out.append(dict(site=uid, asset='planter', position=[point.x, point.y], yaw=0,
                                      radius=radius, scale=1))
                global_fixture_points.append((point, radius))
                break
        if len(props_out) < 3 or not any(f['asset'] in ('street-tree', 'banyan', 'planter') for f in props_out):
            raise ValueError('Site has too few clear planting or furniture fixtures: ' + uid)
        fixtures.extend(props_out)
        paved = make_valid(union_all([paths, access]))
        for part in geometry_polygons(paved):
            paving.extend(polygon_triangles(part))
        path_rings = [geometry_rings(part) for part in geometry_polygons(paths)]
        access_rings = [geometry_rings(part) for part in geometry_polygons(access)]
        gardens.append(dict(site=uid, rings=[geometry_rings(part) for part in geometry_polygons(site)],
                            paths=path_rings, access=access_rings, samples=path_samples,
                            paving_area_m2=round(paved.area, 2)))
        sites_out.append(dict(id=uid, name=name, source_area_m2=round(site.area, 2),
                              bounds=list(site.bounds), fixtures=len(props_out)))

    if len(gardens) != len(SITES) or len({s['source_id'] for s in sports}) != len(sports):
        raise ValueError('Every reviewed site must have one garden and unique sports fittings')
    surface_shapes = [Polygon(s['rings'][0], s['rings'][1:]) for s in surfaces]
    for item, poly in zip(surfaces, surface_shapes):
        if poly.intersection(lots).area > .01 or poly.intersection(site_regions[item['site']][0]).area > .01:
            raise ValueError('Source sports surface overlaps a building or road: ' + item['source_id'])
    if source_sport_ids != EXPECTED_SPORTS or len(surfaces) < len(EXPECTED_SPORTS) or \
            len(fixtures) < len(SITES) * 3 or not paving:
        raise ValueError('East recreation source geometry or authored details are incomplete')
    all_x = [site['bounds'][i] for site in sites_out for i in (0, 2)]
    all_z = [site['bounds'][i] for site in sites_out for i in (1, 3)]
    min_x, min_z = math.floor(min(all_x)), math.floor(min(all_z))
    max_x, max_z = math.ceil(max(all_x)), math.ceil(max(all_z))
    classification = {
        'note': 'Government iB1000 outlines are retained. Surface finish is game styling; small football outlines are styled as hard courts, while identified turf fields remain fields.',
        'references': [HOI_SHAM_REFERENCE, TO_KWA_WAN_REFERENCE, FOOTBALL_REFERENCE],
        'hard_football_ids': ['1500001702', '1500001703', '1500001706', '1500002363',
                             '1500001698', '1500001699', '1500001652', '1500001948', '1500001949'],
        'turf_football_ids': ['1500001881', '1500001883', '1500001874']
    }
    source_metadata = raw['metadata']
    metadata = dict(provider=source_metadata['provider'], source=source_metadata['source'],
                    retrieved_utc=raw['metadata']['retrieved_utc'], source_sha256=hashlib.sha256(source).hexdigest(),
                    inputs_sha256=inputs, origin_wgs84=ORIGIN, source_revisions=raw['metadata']['site_revisions'],
                    sports_revisions=raw['metadata']['sports_revisions'],
                    index_url=source_metadata['index_url'], bbox_wgs84=source_metadata['bbox_wgs84'],
                    index_sha256=source_metadata['index_sha256'], index_sources=source_metadata['index_sources'],
                    tile_manifest_sha256=source_metadata['tile_manifest_sha256'],
                    source_manifests=source_metadata['source_manifests'], source_tiles=source_metadata['tiles'],
                    source_feature_count=len(raw['features']),
                    source_site_fragment_count=sum(len(tiles) for tiles in EXPECTED_SITE_FRAGMENTS.values()),
                    source_sport_fragment_count=sum(len(tiles) for tiles in EXPECTED_SPORT_FRAGMENTS.values()),
                    known_wip_annotations=raw['metadata']['known_wip_annotations'],
                    western_path_component_rejections=path_component_rejections,
                    source_classification=classification,
                    note='Twenty-five source-bounded Kowloon and western New Territories open spaces. Source sports are clipped clear of current building layouts and roads. Paths, access, paving, planting, benches, planters and surface finish are authored approximations; source dates do not establish current access or venue status.')
    return encoded({'metadata': metadata, 'bounds': [min_x, min_z, max_x - min_x, max_z - min_z],
                         'sites': sites_out, 'surfaces': surfaces, 'paving': paving, 'fixtures': fixtures,
                         'sports': sports, 'gardens': gardens, 'play_areas': []})


def validate_layout(source, target):
    raw = validate_source_fragments(source)
    data = json.loads(target)
    layout_sports = {str(surface.get('source_id')) for surface in data.get('surfaces', [])}
    if layout_sports != EXPECTED_SPORTS:
        raise AssertionError(f'Derived surfaces differ from reviewed source IDs; missing={sorted(EXPECTED_SPORTS-layout_sports)}; unexpected={sorted(layout_sports-EXPECTED_SPORTS)}')
    if set(s['id'] for s in data.get('sites', [])) != EXPECTED_SITE_IDS or len(data.get('gardens', [])) != len(SITES):
        raise AssertionError('Expected all 25 reviewed Kowloon and western New Territories open spaces')
    if data.get('play_areas') != [] or len({g['site'] for g in data['gardens']}) != len(SITES):
        raise AssertionError('Unexpected authored play areas or duplicate garden IDs')
    if len(data.get('surfaces', [])) < len(EXPECTED_SPORTS) or len(data.get('fixtures', [])) < len(SITES) * 3:
        raise AssertionError('Missing source sports or authored garden details')
    expected_source = defaultdict(list)
    for feature in raw.get('features', []):
        props = feature['properties']
        if props.get('layer') == 'Site':
            expected_source[props['SITEID']].append(source_local(feature))
    if set(expected_source) != set(SITES):
        raise AssertionError('Source GeoJSON is missing a complete site boundary')
    inputs = data.get('metadata', {}).get('inputs_sha256', {})
    expected_inputs = {str(path.relative_to(ROOT)) for path in ROOT.glob('Data/*layout.json')}
    expected_inputs.update(str(path.relative_to(ROOT)) for path in COAST_FILES)
    expected_inputs.add('Data/cross-harbour.json')
    if set(inputs) != expected_inputs or len([p for p in inputs if p.endswith('layout.json')]) != 9:
        raise AssertionError('All nine building layouts, current roads and five coastal land inputs must be hashed')
    if not data['metadata'].get('known_wip_annotations'):
        raise AssertionError('Known Carpenter Road WIP annotation was lost')

    def polygons(rings_list):
        return union_all([Polygon(rings[0], rings[1:]) for rings in rings_list])

    land_by_site = site_land_geometries()
    source_sites = {uid: union_all(parts).intersection(land_by_site[uid]) for uid, parts in expected_source.items()}
    gardens = {g['site']: g for g in data['gardens']}
    surface_ids = [s['source_id'] for s in data['surfaces']]
    sport_ids = [s['source_id'] for s in data['sports']]
    if len(set(sport_ids)) != len(sport_ids):
        raise AssertionError('A source sport outline is fitted more than once')
    for uid in SITES:
        garden = gardens[uid]
        site = polygons(garden['rings'])
        if site.symmetric_difference(source_sites[uid]).area > .02:
            raise AssertionError(uid + ': source site geometry differs from retained iB1000')
        paths = polygons(garden['paths'])
        access = polygons(garden['access']) if garden['access'] else Polygon()
        paved = union_all([paths, access])
        if paths.area < 80 or paths.difference(site).area > .01 or garden['paving_area_m2'] != round(paved.area, 2):
            raise AssertionError(uid + ': missing source-bounded interior paving')
        if not garden['samples'] or any(not paved.covers(Point(sample)) or paved.boundary.distance(Point(sample)) <= 1.1 for sample in garden['samples']):
            raise AssertionError(uid + ': paving samples are too close to a path edge')
        for part in geometry_polygons(paved):
            if part.area >= 1 and not any(part.covers(Point(sample)) for sample in garden['samples']):
                raise AssertionError(uid + ': retained paving component has no connectivity probe')
        if access.is_empty or access.intersection(paths).area < .1:
            raise AssertionError(uid + ': missing connected site access polygons')
        if len([f for f in data['fixtures'] if f['site'] == uid]) < 3:
            raise AssertionError(uid + ': useful garden fixtures missing')
        if not any(f['site'] == uid and f['asset'] == 'bench' for f in data['fixtures']):
            raise AssertionError(uid + ': bench missing')
        if not any(f['site'] == uid and f['asset'] in ('street-tree', 'banyan', 'planter') for f in data['fixtures']):
            raise AssertionError(uid + ': planting missing')
    for source_id in set(surface_ids):
        patches = [Polygon(s['rings'][0], s['rings'][1:]) for s in data['surfaces'] if s['source_id'] == source_id]
        if sum(p.area for p in patches)-union_all(patches).area > .01:
            raise AssertionError('A government sports surface is duplicated: ' + source_id)
    site_fragments = sum(len(tiles) for tiles in EXPECTED_SITE_FRAGMENTS.values())
    sport_fragments = sum(len(tiles) for tiles in EXPECTED_SPORT_FRAGMENTS.values())
    print(f'ANTILA_EAST_OPEN_SPACE_DATA_OK: {len(data["sites"])} government sites; '
          f'{site_fragments} Site fragments; {len(EXPECTED_SPORTS)} source sports across {sport_fragments} sheet fragments; '
          f'{len(data["surfaces"])} rendered surfaces; {len(data["sports"])} intact rectangle fittings; '
          f'{len(data["fixtures"])} authored fixtures')


def refresh(cache=None, manifest=None, source_path=SOURCE, target_path=TARGET):
    source = extract(cache, manifest) if cache is not None else source_path.read_bytes()
    validate_source_fragments(source)
    layout = build(source)
    validate_layout(source, layout)
    outputs = ([(source_path, source)] if cache is not None else []) + [(target_path, layout)]
    replace_outputs(outputs)
    data = json.loads(layout)
    print('ANTILA_EAST_OPEN_SPACE_IMPORT_OK:', len(data['surfaces']), 'source surfaces;',
          len(data['sports']), 'intact sport fittings;', len(data['fixtures']), 'fixtures;',
          len(data['paving']), 'paving triangles')


if __name__ == '__main__':
    if '--extract' in sys.argv:
        refresh(Path(sys.argv[sys.argv.index('--extract') + 1]), Path(sys.argv[sys.argv.index('--extract') + 2]))
    else:
        refresh()
