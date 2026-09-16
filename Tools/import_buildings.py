"""Offline CSDI building massing. Run with .venv-geodata/bin/python Tools/import_buildings.py.

Survey heights are datums: each touching building group shares its lowest base.
The flat game terrain preserves relative roof heights, not surveyed ground levels.
"""
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from shapely import constrained_delaunay_triangles, make_valid, STRtree, union_all
from shapely.geometry import Polygon, LineString, box
from shapely.geometry.polygon import orient
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


def build():
    raw = ROOT / "Data/buildings.geojson"
    features = json.loads(raw.read_text())["features"]
    roads = json.loads((ROOT / "Data/nathan-road.json").read_text())
    buffers = [LineString(roads["road_points"]).buffer(13.5, quad_segs=2, join_style="mitre")]
    for road in roads["side_roads"]:
        width = 18 if road["name"] in WIDE else 12
        buffers.append(LineString(road["points"]).buffer(width/2+3.5, quad_segs=2, join_style="mitre"))
    harbour = json.loads((ROOT/'Data/cross-harbour.json').read_text())
    for road in harbour['roads']:
        if not road['tunnel'] or road.get('ramp',False):
            buffers.append(LineString([(p[0],p[2]) for p in road['points']]).buffer(max(12,road['width'])/2+3.5,quad_segs=2,join_style='mitre').intersection(box(*roads['bounds'])))
    road_zone = union_all(buffers)
    # The prototype permits a bus turn into Granville: protect the long nose through that tight corner.
    turning_zone = LineString(roads["points"]).interpolate(503).buffer(32, quad_segs=8)
    turn_clearance = road_zone.buffer(2, quad_segs=2, join_style="mitre").intersection(turning_zone)
    exclusion = union_all([PARK, road_zone, turn_clearance])
    boundary = box(*roads["bounds"])
    source_polys = [make_valid(Polygon([local(p) for p in f["geometry"]["coordinates"][0]],
                      [[local(p) for p in ring] for ring in f["geometry"]["coordinates"][1:]])) for f in features]
    tree = STRtree(source_polys)
    parent = list(range(len(features)))

    def group(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, poly in enumerate(source_polys):
        for j in tree.query(poly, predicate="dwithin", distance=.25):
            parent[group(int(j))] = group(i)
    ground = {}
    for i, f in enumerate(features):
        base = f["properties"].get("BaseHeight")
        if isinstance(base, (float, int)) and math.isfinite(base):
            root = group(i)
            ground[root] = min(ground.get(root, base), base)

    candidates = []
    missing = clipped = 0
    for i, (f, poly) in enumerate(zip(features, source_polys)):
        props = f["properties"]
        top = props.get("TopHeight")
        if not isinstance(top, (int, float)) or top <= ground.get(group(i), 4):
            missing += 1
            height = max(3.2, (props.get("Storeys") or 3)*3.2)
        else:
            height = top - ground.get(group(i), props.get("BaseHeight") or 4)
        playable = poly.intersection(boundary).difference(exclusion)
        if poly.area - playable.area > .1:
            clipped += 1
        # Upper envelope removes duplicate/internal podium surfaces and overlapping collisions.
        candidates.append((round(height, 3), i, playable))
    candidates.sort(reverse=True)
    occupied = {}
    output = []
    for height, i, playable in candidates:
        root = group(i)
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
    assert pavement_patches and all(Polygon(p["polygon"]).is_valid for p in pavement_patches)
    names = {b["name"] for b in output}
    assert len(features) == 1718 and len(output) > 900 and area > 650000
    assert any("MASTERPIECE" in n.upper() for n in names)
    assert min(b["height"] for b in output) > 0 and max(b["height"] for b in output) > 240
    meta = {"provider": "Lands Department, HKSAR Government / CSDI Portal", "source": SOURCE,
            "terms": "https://portal.csdi.gov.hk/csdi-webpage/doc/TNC", "retrieved_utc": "2026-09-13",
            "source_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(), "bbox_wgs84": BBOX, "origin_wgs84": ORIGIN,
            "source_parts": len(features), "rendered_parts": len(output), "source_parts_retained": len({b["id"] for b in output}),
            "source_parts_clipped": clipped, "fallback_height_parts": missing, "footprint_area_m2": round(area),
            "volume_m3": round(sum(p.area*b["height"] for p,b in zip(actual,output))),
            "styles": dict(Counter(b["style"] for b in output)),
            "note": "Derived game massing, not survey-grade reconstruction. Flat ground; connected-part minimum base datum; upper-envelope podium/tower silhouettes. Road clearance 3.5m beyond authored carriageways including the Cross-Harbour surface approaches, plus 2m within 32m of the Nathan/Granville bus turn; authored park omitted. Missing heights use storeys x 3.2m or 9.6m. Facades are generated artwork, not surveyed photographs."}
    meta["small_pavement_gaps_filled"] = len(pavement_patches)
    (ROOT / "Data/building-layout.json").write_text(json.dumps({"metadata": meta, "buildings": output, "pavement_patches": pavement_patches}, ensure_ascii=False, separators=(",", ":")))
    print("BUILDING_LAYOUT_OK:", json.dumps(meta, ensure_ascii=False))


if __name__ == "__main__":
    build()
