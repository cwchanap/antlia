"""Offline CSDI building massing. Run with .venv-geodata/bin/python Tools/import_buildings.py.

Survey heights are datums: each touching building group shares its lowest base across regional extracts.
The flat game terrain preserves relative roof heights, not surveyed ground levels.
"""
import hashlib
import json
import math
import datetime
import sys
import tempfile
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from shapely import constrained_delaunay_triangles, make_valid, STRtree, union_all
from shapely.geometry import Polygon, LineString, Point, box, shape
from shapely.geometry.polygon import orient
from shapely.ops import polylabel
from import_map import local, BBOX, ORIGIN

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637211194312_35158/MapServer/0/query"
PARK = Polygon([(-26,-368),(-193,-361),(-378,-570),(-415,-903),(-63,-920)])
WIDE = {"CANTON ROAD", "CHATHAM ROAD SOUTH", "KOWLOON PARK DRIVE", "AUSTIN ROAD",
        "AUSTIN ROAD WEST", "JORDAN ROAD", "SALISBURY ROAD", "SCIENCE MUSEUM ROAD", "MODY ROAD"}


def polygons(geometry):
    if geometry.geom_type == "Polygon":
        if geometry.area >= 4:
            yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from polygons(part)


from import_tunnel import ISLAND_BOUNDS, KOWLOON_BOUNDS, WEST_BOUNDS, NORTHWEST_BOUNDS, KWAI_CHUNG_BOUNDS, TSUEN_WAN_BOUNDS, WEST_COAST_BOUNDS
ISLAND_BBOX = (ORIGIN[0]+ISLAND_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-ISLAND_BOUNDS[3]/111320,
               ORIGIN[0]+ISLAND_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-ISLAND_BOUNDS[1]/111320)

KOWLOON_BBOX = (ORIGIN[0]+KOWLOON_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-KOWLOON_BOUNDS[3]/111320,
                ORIGIN[0]+KOWLOON_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-KOWLOON_BOUNDS[1]/111320)
WEST_BBOX = (ORIGIN[0]+WEST_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-WEST_BOUNDS[3]/111320,
             ORIGIN[0]+WEST_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-WEST_BOUNDS[1]/111320)
NORTHWEST_BBOX = (ORIGIN[0]+NORTHWEST_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-NORTHWEST_BOUNDS[3]/111320,
                 ORIGIN[0]+NORTHWEST_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-NORTHWEST_BOUNDS[1]/111320)

KWAI_CHUNG_BBOX = (ORIGIN[0]+KWAI_CHUNG_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-KWAI_CHUNG_BOUNDS[3]/111320,
                   ORIGIN[0]+KWAI_CHUNG_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-KWAI_CHUNG_BOUNDS[1]/111320)

TSUEN_WAN_BBOX = (ORIGIN[0]+TSUEN_WAN_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-TSUEN_WAN_BOUNDS[3]/111320,
                   ORIGIN[0]+TSUEN_WAN_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-TSUEN_WAN_BOUNDS[1]/111320)

WEST_COAST_BBOX = (ORIGIN[0]+WEST_COAST_BOUNDS[0]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-WEST_COAST_BOUNDS[3]/111320,
                   ORIGIN[0]+WEST_COAST_BOUNDS[2]/(111320*math.cos(math.radians(ORIGIN[1]))), ORIGIN[1]-WEST_COAST_BOUNDS[1]/111320)

def download_island(north=False, west=False, northwest=False, kwai_chung=False, tsuen_wan=False, west_coast=False):
    bbox = WEST_COAST_BBOX if west_coast else TSUEN_WAN_BBOX if tsuen_wan else KWAI_CHUNG_BBOX if kwai_chung else NORTHWEST_BBOX if northwest else WEST_BBOX if west else KOWLOON_BBOX if north else ISLAND_BBOX
    query = dict(geometry=','.join(map(str,bbox)),geometryType='esriGeometryEnvelope',
                 inSR=4326,spatialRel='esriSpatialRelIntersects',where='1=1')
    def request(**params):
        with urllib.request.urlopen(SOURCE+'?'+urllib.parse.urlencode(query | params),timeout=60) as response:
            result=json.load(response)
        if not isinstance(result,dict): raise ValueError('Invalid building service response')
        if 'error' in result: raise ValueError(result['error'])
        return result
    count=request(f='json',returnCountOnly='true').get('count')
    if type(count) is not int or count<=0: raise ValueError('Expected a positive building count')
    features=[]
    while len(features)<count:
        page=request(f='geojson',outSR=4326,outFields='*',orderByFields='OBJECTID',resultOffset=len(features),resultRecordCount=3000)
        if page.get('type')!='FeatureCollection' or not isinstance(page.get('features'),list) or not page['features']:
            raise ValueError('Invalid or empty building page before count reached')
        features.extend(page['features'])
    ids=set()
    for feature in features:
        if not isinstance(feature,dict) or feature.get('type')!='Feature': raise ValueError('Invalid building feature')
        props=feature.get('properties');geometry=feature.get('geometry')
        if not isinstance(props,dict) or type(props.get('OBJECTID')) is not int:
            raise ValueError('Missing or invalid building OBJECTID')
        for field in ('BuildingCSUID','BuildingBlockType'):
            if not isinstance(props.get(field),str) or not props[field].strip(): raise ValueError(f'Missing building {field}')
        for field in ('BaseHeight','TopHeight','Storeys'):
            value=props.get(field)
            if value is not None and (type(value) not in (int,float) or not math.isfinite(value)):
                raise ValueError(f'Invalid building {field}')
        if props.get('BuildingNameEN') is not None and not isinstance(props['BuildingNameEN'],str):
            raise ValueError('Invalid building name')
        if not isinstance(geometry,dict) or geometry.get('type')!='Polygon': raise ValueError('Expected a building Polygon')
        rings=geometry.get('coordinates')
        if not isinstance(rings,list) or not rings: raise ValueError('Missing building polygon rings')
        for ring in rings:
            if not isinstance(ring,list) or len(ring)<4 or ring[0]!=ring[-1]: raise ValueError('Invalid building polygon ring')
            for point in ring:
                if not isinstance(point,list) or len(point) not in (2,3) or any(type(v) not in (int,float) or not math.isfinite(v) for v in point):
                    raise ValueError('Invalid building polygon coordinate')
                if not (-180<=point[0]<=180 and -90<=point[1]<=90): raise ValueError('Expected WGS84 building coordinates')
        # Match the builder's repair step; source polygons need not already be valid.
        polygon=make_valid(Polygon([local(p) for p in rings[0]],[[local(p) for p in ring] for ring in rings[1:]]))
        if polygon.is_empty or polygon.area<=0: raise ValueError('Empty building footprint')
        ids.add(props['OBJECTID'])
    if len(features)!=count or len(ids)!=count: raise ValueError('Incomplete or duplicate building extract')
    metadata=dict(source=SOURCE,bbox_wgs84=bbox,retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    target=ROOT/('Data/west-coast-buildings.geojson' if west_coast else 'Data/tsuen-wan-buildings.geojson' if tsuen_wan else 'Data/kwai-chung-buildings.geojson' if kwai_chung else 'Data/lai-chi-kok-buildings.geojson' if northwest else 'Data/west-kowloon-buildings.geojson' if west else 'Data/kowloon-north-buildings.geojson' if north else 'Data/island-buildings.geojson')
    contents=json.dumps(dict(type='FeatureCollection',metadata=metadata,features=features),ensure_ascii=False,separators=(',',':'),allow_nan=False)
    with tempfile.NamedTemporaryFile(dir=target.parent,prefix=target.name+'.',suffix='.part',delete=False) as staged:
        pending=Path(staged.name)
    try:
        pending.write_text(contents,encoding='utf-8')
        pending.replace(target)
    finally:pending.unlink(missing_ok=True)
    print('WEST_COAST_BUILDINGS_DOWNLOADED:' if west_coast else 'TSUEN_WAN_BUILDINGS_DOWNLOADED:' if tsuen_wan else 'KWAI_CHUNG_BUILDINGS_DOWNLOADED:' if kwai_chung else 'NORTHWEST_BUILDINGS_DOWNLOADED:' if northwest else 'WEST_BUILDINGS_DOWNLOADED:' if west else 'NORTH_BUILDINGS_DOWNLOADED:' if north else 'ISLAND_BUILDINGS_DOWNLOADED:',count,flush=True)


def build(island=False, north=False, west=False, northwest=False, kwai_chung=False, tsuen_wan=False, west_coast=False):
    raw = ROOT / ("Data/west-coast-buildings.geojson" if west_coast else "Data/tsuen-wan-buildings.geojson" if tsuen_wan else "Data/kwai-chung-buildings.geojson" if kwai_chung else "Data/lai-chi-kok-buildings.geojson" if northwest else "Data/west-kowloon-buildings.geojson" if west else "Data/kowloon-north-buildings.geojson" if north else "Data/island-buildings.geojson" if island else "Data/buildings.geojson")
    features = json.loads(raw.read_text())["features"]
    roads = json.loads((ROOT / "Data/nathan-road.json").read_text())
    boundary = box(*(KOWLOON_BOUNDS if north else ISLAND_BOUNDS if island else roads['bounds']))
    if island:boundary=shape(json.loads((ROOT/'Data/island-coast.json').read_text())['land'])
    if west:
        coast=json.loads((ROOT/'Data/west-kowloon-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    if northwest:
        coast=json.loads((ROOT/'Data/lai-chi-kok-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*WEST_BOUNDS),box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    if kwai_chung:
        coast=json.loads((ROOT/'Data/kwai-chung-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*WEST_BOUNDS),box(*NORTHWEST_BOUNDS),box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    if tsuen_wan:
        coast=json.loads((ROOT/'Data/tsuen-wan-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*KWAI_CHUNG_BOUNDS),box(*WEST_BOUNDS),box(*NORTHWEST_BOUNDS),box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    if west_coast:
        coast=json.loads((ROOT/'Data/west-coast-coast.json').read_text())
        boundary=shape(coast['land']).difference(union_all([box(*TSUEN_WAN_BOUNDS),box(*KWAI_CHUNG_BOUNDS),box(*WEST_BOUNDS),box(*NORTHWEST_BOUNDS),box(*roads['bounds']),box(*KOWLOON_BOUNDS)]))
    buffers = [LineString(roads["road_points"]).buffer(13.5, quad_segs=2, join_style="mitre")]
    for road in roads["side_roads"]:
        width = 18 if road["name"] in WIDE else 12
        buffers.append(LineString(road["points"]).buffer(width/2+3.5, quad_segs=2, join_style="mitre"))
    harbour = json.loads((ROOT/'Data/cross-harbour.json').read_text())
    for road in harbour['roads']:
        if not road['tunnel'] or road.get('ramp',False):
            buffers.append(LineString([(p[0],p[2]) for p in road['points']]).buffer(max(12,road['width'])/2+3.5,quad_segs=2,join_style='mitre').intersection(boundary))
    road_zone = union_all(buffers)
    # The prototype permits a bus turn into Granville: protect the long nose through that tight corner.
    turning_zone = LineString(roads["points"]).interpolate(503).buffer(32, quad_segs=8)
    turn_clearance = road_zone.buffer(2, quad_segs=2, join_style="mitre").intersection(turning_zone)
    exclusion = union_all([PARK, road_zone, turn_clearance])
    source_polys = [make_valid(Polygon([local(p) for p in f["geometry"]["coordinates"][0]],
                      [[local(p) for p in ring] for ring in f["geometry"]["coordinates"][1:]])) for f in features]
    base_sources = [raw] if island else [ROOT/'Data'/name for name in
        ('buildings.geojson','kowloon-north-buildings.geojson','west-kowloon-buildings.geojson','lai-chi-kok-buildings.geojson','kwai-chung-buildings.geojson','tsuen-wan-buildings.geojson','west-coast-buildings.geojson')]
    snapshots = [json.loads(path.read_text()) for path in base_sources]
    snapshots.sort(key=lambda data: datetime.datetime.fromisoformat(data.get('metadata',{}).get('retrieved_utc','2026-09-13T00:00:00+00:00')))
    base_features = [f for snapshot in snapshots for f in snapshot['features']]
    base_polys = source_polys if island else [make_valid(Polygon([local(p) for p in f['geometry']['coordinates'][0]],
        [[local(p) for p in ring] for ring in f['geometry']['coordinates'][1:]])) for f in base_features]
    tree = STRtree(base_polys)
    parent = list(range(len(base_features)))

    def group(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_csuid = {}
    for i, f in enumerate(base_features):
        csuid = f['properties']['BuildingCSUID']
        assert isinstance(csuid,str) and csuid, 'Missing persistent building identity'
        if csuid in by_csuid:parent[group(i)] = group(by_csuid[csuid])
        by_csuid[csuid] = i
    for i, poly in enumerate(base_polys):
        for j in tree.query(poly, predicate="dwithin", distance=.25):
            parent[group(int(j))] = group(i)
    ground = {}
    for i, f in enumerate(base_features):
        base = f["properties"].get("BaseHeight")
        if isinstance(base, (float, int)) and math.isfinite(base):
            root = group(i)
            ground[root] = min(ground.get(root, base), base)
    roots = [group(by_csuid[f['properties']['BuildingCSUID']]) for f in features]

    candidates = []
    missing = clipped = 0
    for i, (f, poly) in enumerate(zip(features, source_polys)):
        # The newest extract owns height inputs; regional footprints and IDs stay local.
        props = base_features[by_csuid[f['properties']['BuildingCSUID']]]["properties"]
        top = props.get("TopHeight")
        if not isinstance(top, (int, float)) or top <= ground.get(roots[i], 4):
            missing += 1
            height = max(3.2, (props.get("Storeys") or 3)*3.2)
        else:
            height = top - ground.get(roots[i], props.get("BaseHeight") or 4)
        playable = poly.intersection(boundary).difference(exclusion)
        if poly.area - playable.area > .1:
            clipped += 1
        # Upper envelope removes duplicate/internal podium surfaces and overlapping collisions.
        candidates.append((round(height, 3), i, playable))
    candidates.sort(reverse=True)
    occupied = {}
    output = []
    for height, i, playable in candidates:
        root = roots[i]
        visible = playable.difference(occupied[root]) if root in occupied else playable
        occupied[root] = union_all([occupied[root], playable]) if root in occupied else playable
        props = features[i]["properties"]
        source_id = props["OBJECTID"]
        style = 1 if height > 75 else 2 if props["BuildingBlockType"] == "Podium" else source_id % 3
        if style == 1 and height <= 75:
            style = 3
        for poly in polygons(visible):
            poly = orient(poly.simplify(.08, preserve_topology=True).intersection(visible), sign=1)
            if poly.geom_type != "Polygon":
                continue
            triangles = list(constrained_delaunay_triangles(poly).geoms)
            assert abs(sum(t.area for t in triangles)-poly.area) < .01
            point = poly.representative_point()
            # Difference operations can leave a narrow spur whose midpoint rounds outside the roof.
            if point.distance(poly.boundary)<.1:point=polylabel(poly,tolerance=.1)
            assert poly.contains(Point(round(point.x,4),round(point.y,4))), 'Rounded roof probe must remain inside its footprint'
            def coords(ring):
                return [[x, z] for x, z in list(ring.coords)[:-1]]
            output.append({"id": source_id, "name": props.get("BuildingNameEN") or "",
                           "type": props["BuildingBlockType"], "height": height, "style": style,
                           "center": [round(point.x, 4), round(point.y, 4)],
                           "roof_clearance": point.distance(poly.boundary),
                           "frontage": [LineString([a,b]).distance(road_zone)<1 for a,b in zip(list(poly.exterior.coords),list(poly.exterior.coords)[1:])],
                           "rings": [coords(poly.exterior), *[coords(r) for r in poly.interiors]],
                           "roof": [coords(orient(t, sign=1).exterior) for t in triangles]})

    actual = [Polygon(b["rings"][0], b["rings"][1:]) for b in output]
    assert all(p.is_valid and p.difference(boundary).area < .1 and p.intersection(exclusion).area < .1 for p in actual), "Invalid or obstructing footprint"
    actual_tree = STRtree(actual)
    for i, poly in enumerate(actual):
        assert all(poly.intersection(actual[int(j)]).area < .1 for j in actual_tree.query(poly) if j < i)
    area = union_all(actual).area
    # Close only small enclosed paving gaps; keep the park and larger open spaces intact.
    paved = union_all([road_zone.buffer(-.5), *[Polygon(p.exterior).buffer(3, join_style="bevel") for p in actual]])
    pavement_patches = []
    for part in polygons(paved):
        for ring in part.interiors:
            hole = Polygon(ring)
            if hole.area > 40 or hole.intersects(PARK):
                continue
            patch = hole.buffer(.4).intersection(boundary)
            if patch.geom_type != "Polygon" or patch.is_empty or patch.intersects(PARK):
                continue
            point = patch.representative_point()
            pavement_patches.append({"center": [point.x,point.y], "polygon": list(patch.exterior.coords)[:-1]})
    assert (west_coast or tsuen_wan or kwai_chung or northwest or west or north or island or pavement_patches) and all(Polygon(p["polygon"]).is_valid for p in pavement_patches)
    names = {b["name"] for b in output}
    if not (island or north or west or northwest or kwai_chung or tsuen_wan or west_coast):
        assert len(features) == 1718 and len(output) > 900 and area > 650000
        assert any("MASTERPIECE" in n.upper() for n in names)
        assert max(b["height"] for b in output) > 240
    else:
        assert len(output)>20 and area>10000, 'Island district extract is unexpectedly sparse'
    assert min(b["height"] for b in output) > 0
    meta = {"provider": "Lands Department, HKSAR Government / CSDI Portal", "source": SOURCE,
            "terms": "https://portal.csdi.gov.hk/csdi-webpage/doc/TNC", "retrieved_utc": json.loads(raw.read_text()).get('metadata',{}).get('retrieved_utc','2026-09-13'),
            "source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(), "bbox_wgs84": WEST_COAST_BBOX if west_coast else TSUEN_WAN_BBOX if tsuen_wan else KWAI_CHUNG_BBOX if kwai_chung else NORTHWEST_BBOX if northwest else WEST_BBOX if west else KOWLOON_BBOX if north else ISLAND_BBOX if island else BBOX, "origin_wgs84": ORIGIN,
            "source_parts": len(features), "rendered_parts": len(output), "source_parts_retained": len({b["id"] for b in output}),
            "source_parts_clipped": clipped, "fallback_height_parts": missing, "footprint_area_m2": round(area),
            "volume_m3": round(sum(p.area*b["height"] for p,b in zip(actual,output))),
            "styles": dict(Counter(b["style"] for b in output)),
            "note": "Derived game massing, not survey-grade reconstruction. Flat ground; connected-part minimum base datum; upper-envelope podium/tower silhouettes. Road clearance 3.5m beyond authored carriageways including the Cross-Harbour surface approaches, plus 2m within 32m of the Nathan/Granville bus turn; authored park omitted. Missing heights use storeys x 3.2m or 9.6m. Facades are generated artwork, not surveyed photographs."}
    meta["small_pavement_gaps_filled"] = len(pavement_patches)
    if island or north or west or northwest or kwai_chung or tsuen_wan or west_coast:
        meta['note'] = 'Derived expansion corridor massing on the authored land apron, not survey-grade reconstruction. Original WGS84 footprints and relative roof heights; flat ground; connected-part minimum base datum and upper-envelope podium/tower silhouettes. Buildings clipped to the land boundary and 3.5m beyond the surface carriageways. Missing heights use storeys x 3.2m or 9.6m. Facades, paving and vegetation are authored; selected street centrelines come from the Transport Department; the coastline remains authored.'
    if west or northwest or kwai_chung or tsuen_wan or west_coast:meta['note']=meta['note'].replace('authored land apron','government-derived land boundary').replace('the coastline remains authored','the western coastline comes from LandsD iB1000 Shoreline and CartoHydroLine seawall/high-water features, with recorded short gap repairs; prior building regions are excluded to avoid duplicate geometry')
    if west_coast:meta['note']=meta['note'].replace('with recorded short gap repairs','plus connected CartoLandCoverLine rock outlines and pier outlines, with recorded authored gap repairs up to 115.34 m')
    if island:
        meta['note']=meta['note'].replace('authored land apron','government-derived land boundary').replace('the coastline remains authored','the island shoreline comes from LandsD iB1000 with recorded authored ferry-terminal and tunnel-mouth joins')
        meta['coast_sha256']=hashlib.sha256((ROOT/'Data/island-coast.json').read_bytes()).hexdigest()
    else:
        meta['base_sources_sha256'] = {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in base_sources}
        meta['note'] += ' Base datums are reconciled across all seven Kowloon extracts before regional clipping; duplicate BuildingCSUID records share one group. TopHeight and fallback Storeys use the newest retrieved_utc record per BuildingCSUID (original undated extract: 2026-09-13 UTC; ties prefer west coast, Tsuen Wan, Kwai Chung, northwest, west, north, original). Each region retains its own source footprint and OBJECTID.'
    (ROOT / ("Data/west-coast-layout.json" if west_coast else "Data/tsuen-wan-layout.json" if tsuen_wan else "Data/kwai-chung-layout.json" if kwai_chung else "Data/lai-chi-kok-layout.json" if northwest else "Data/west-kowloon-layout.json" if west else "Data/kowloon-north-layout.json" if north else "Data/island-building-layout.json" if island else "Data/building-layout.json")).write_text(json.dumps({"metadata": meta, "buildings": output, "pavement_patches": pavement_patches}, ensure_ascii=False, separators=(",", ":")))
    print("BUILDING_LAYOUT_OK:", json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    if '--download' in sys.argv: download_island('--north' in sys.argv, '--west' in sys.argv, '--northwest' in sys.argv, '--kwai-chung' in sys.argv, '--tsuen-wan' in sys.argv, '--west-coast' in sys.argv)
    build('--island' in sys.argv, '--north' in sys.argv, '--west' in sys.argv, '--northwest' in sys.argv, '--kwai-chung' in sys.argv, '--tsuen-wan' in sys.argv, '--west-coast' in sys.argv)
