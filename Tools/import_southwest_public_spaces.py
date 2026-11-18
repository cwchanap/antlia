"""Add the two source-verified Tsim Sha Tsui public-space records."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from shapely import constrained_delaunay_triangles, make_valid, union_all
from shapely.geometry import LineString, Point, Polygon, box, shape
from shapely.ops import transform
from import_buildings import WIDE
from import_tunnel import SOUTHWEST_PROMENADE_BOUNDS


ORIGIN = (114.17232, 22.295)
CULTURAL_ID = "1503005422"
WONDERLAND_ID = "1910058892"
SITE_NAMES = {
    CULTURAL_ID: "Hong Kong Cultural Centre",
    WONDERLAND_ID: "Wonderland",
}
WONDERLAND_PROBE = (-1697.86, -824.37)
CULTURAL_CONTROL_POINTS = (
    (-145.618, 210.401), (-155.970, 211.367), (-240.051, 164.957),
    (-264.530, 201.097), (-268.811, 183.603), (-295.585, 169.459),
    (-298.846, 159.739), (-318.150, 154.798),
)


def _local_geometry(geometry):
    scale_x = 111320 * math.cos(math.radians(ORIGIN[1]))

    def project(x, y, z=None):
        if hasattr(x, "__iter__"):
            return ([(value - ORIGIN[0]) * scale_x for value in x],
                    [-(value - ORIGIN[1]) * 111320 for value in y])
        return ((x - ORIGIN[0]) * scale_x, -(y - ORIGIN[1]) * 111320)

    return make_valid(transform(project, geometry))


def _source_local(feature):
    return _local_geometry(shape(feature["geometry"]))


def _polygons(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if hasattr(geometry, "geoms"):
        return [part for item in geometry.geoms for part in _polygons(item)]
    return []


def _rings(polygon):
    return [list(polygon.exterior.coords)[:-1],
            *[list(interior.coords)[:-1] for interior in polygon.interiors]]


def _triangles(polygon):
    faces = list(constrained_delaunay_triangles(polygon).geoms)
    if abs(sum(face.area for face in faces) - polygon.area) > .01:
        raise ValueError("Paving triangulation lost source area")
    return [list(face.exterior.coords)[:-1] for face in faces]


def _district_road_buffers(site, district_roads):
    hard = []
    targets = []

    def add(points, width):
        line = LineString(points)
        if line.is_empty or site.distance(line) > 250:
            return
        half_width = width / 2
        hard.append(line.buffer(half_width + 3.5, quad_segs=2, join_style="mitre"))
        targets.append(line.buffer(half_width + 3, quad_segs=2, join_style="mitre"))

    if len(district_roads.get("road_points", [])) >= 2:
        add(district_roads["road_points"], 20)
    for road in district_roads.get("side_roads", []):
        add(road.get("points", []), 18 if road.get("name") in WIDE else 12)
    return (union_all(hard) if hard else Polygon(),
            union_all(targets) if targets else Polygon())


def _site_and_lines(source_path):
    raw = json.loads(Path(source_path).read_text())
    site_parts = {key: [] for key in SITE_NAMES}
    line_features = {key: [] for key in SITE_NAMES}
    for feature in raw["features"]:
        props = feature.get("properties", {})
        if props.get("layer") == "Site" and props.get("SITEID") in site_parts:
            site_parts[props["SITEID"]].append(_source_local(feature))
        elif props.get("layer") == "CartoPedLine" and props.get("PEDESTRIANTYPE") in ("PA", "CWY"):
            for site_id in props.get("related_SITEID", []):
                if site_id in line_features:
                    line_features[site_id].append((props, _source_local(feature)))
    if any(not values for values in site_parts.values()):
        raise ValueError("Supplement is missing an exact iB1000 Site polygon")
    sites = {key: make_valid(union_all(values)) for key, values in site_parts.items()}
    return raw, sites, line_features


def _source_metadata(raw, source_path):
    metadata = raw["metadata"]
    source_path = Path(source_path)
    return {
        "source": metadata["source"],
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "feature_count": len(raw["features"]),
        "site_fragment_count": sum(feature["properties"].get("layer") == "Site"
                                    for feature in raw["features"]),
        "site_ids": sorted({feature["properties"].get("SITEID") for feature in raw["features"]
                             if feature["properties"].get("layer") == "Site"}),
        "tile_manifest_sha256": metadata["tile_manifest_sha256"],
        "tiles": metadata["tiles"],
        "cartopedline_codes": metadata["cartopedline_codes"],
    }


def add_southwest_public_spaces(data, source_path, ground, lots, road_hard,
                                street_targets, district_roads, inputs_sha256):
    """Append Site 1503005422 and Site 1910058892 to a fresh open-spaces dict.

    `ground`, `lots`, `road_hard`, and `street_targets` use the existing importer’s
    local map coordinates. Existing data is only appended to; it is never rebuilt.
    """
    raw, source_sites, line_features = _site_and_lines(source_path)
    if len(raw["features"]) != 193 or _source_metadata(raw, source_path)["site_ids"] != sorted(SITE_NAMES):
        raise ValueError("The supplemental source differs from the reviewed 193-feature pair")
    if {item["id"] for item in data["sites"]} & set(SITE_NAMES):
        raise ValueError("Supplemental Site ID already exists in output")
    if {item["site"] for item in data["gardens"]} & set(SITE_NAMES):
        raise ValueError("Supplemental garden ID already exists in output")

    culture_source = source_sites[CULTURAL_ID]
    event_source = source_sites[WONDERLAND_ID]
    if culture_source.intersection(event_source).area > .01:
        raise ValueError("Supplemental government Sites overlap")
    culture_site = make_valid(culture_source.intersection(ground))
    event_site = make_valid(event_source.intersection(ground))
    if culture_site.is_empty or event_site.is_empty or min(culture_site.area, event_site.area) < 100:
        raise ValueError("A supplemental Site has insufficient shared ground support")

    district_hard, district_targets = _district_road_buffers(culture_site, district_roads)
    site_roads = union_all([road_hard, district_hard])
    site_targets = union_all([street_targets, district_targets])
    building_clearance = lots.buffer(4)

    official_lines = [line for _, line in line_features[CULTURAL_ID]]
    if not official_lines:
        raise ValueError("Cultural Centre has no source PA/CWY pavement lines")
    walkway = union_all(official_lines).buffer(
        3, quad_segs=2, cap_style="round", join_style="round")
    promenade = box(*SOUTHWEST_PROMENADE_BOUNDS).intersection(ground)
    # The venue plan shows an open paved piazza between its buildings and the waterfront.
    candidate = make_valid(culture_site.union(walkway.intersection(ground)).difference(
        union_all([building_clearance, site_roads])))
    paths = make_valid(candidate.intersection(culture_site))
    access = make_valid(candidate.difference(culture_site))
    if paths.is_empty or paths.area < 100:
        raise ValueError("Cultural Centre source paths have no safe paved area")
    if not access.is_empty:
        # Surveyed exterior paths connect the piazza to streets and the promenade.
        connected = [part for part in _polygons(access)
                     if part.distance(paths) <= 2.1 and
                     (part.distance(site_targets) <= 2.1 or part.intersection(promenade).area > .1)]
        access = union_all(connected) if connected else Polygon()
    paved = make_valid(union_all([paths, access]))

    samples = []
    for part in _polygons(paths):
        point = part.representative_point()
        if part.boundary.distance(point) > .1:
            samples.append([point.x, point.y])
    if not samples or not all(paved.covers(Point(point)) for point in CULTURAL_CONTROL_POINTS):
        raise ValueError("Cultural Centre paving must cover the reviewed pedestrian connections")
    samples.extend([list(point) for point in CULTURAL_CONTROL_POINTS])

    probe = Point(-1697.86, -824.37)
    if not event_site.covers(probe):
        raise ValueError("Wonderland open-center probe is outside supported source Site")

    data["sites"].extend([
        dict(id=CULTURAL_ID, name=SITE_NAMES[CULTURAL_ID],
             source_area_m2=round(culture_source.area, 2),
             supported_area_m2=round(culture_site.area, 2),
             bounds=list(culture_source.bounds), fixtures=0, public_space_kind="piazza"),
        dict(id=WONDERLAND_ID, name=SITE_NAMES[WONDERLAND_ID],
             source_area_m2=round(event_source.area, 2),
             supported_area_m2=round(event_site.area, 2),
             bounds=list(event_source.bounds), fixtures=0, public_space_kind="open_event_ground"),
    ])
    data["gardens"].extend([
        dict(site=CULTURAL_ID, rings=[_rings(part) for part in _polygons(culture_site)],
             paths=[_rings(part) for part in _polygons(paths)],
             access=[_rings(part) for part in _polygons(access)], samples=samples,
             paving_area_m2=round(paved.area, 2), surface_mode="piazza_and_access"),
        dict(site=WONDERLAND_ID, rings=[_rings(part) for part in _polygons(event_site)],
             paths=[], access=[], samples=[], paving_area_m2=0, event_ground=True,
             vegetation_reserved=True, fixtures_reserved=True, center_probe=list(WONDERLAND_PROBE)),
    ])
    paving_triangles = []
    for part in _polygons(paved):
        paving_triangles.extend(_triangles(part))
    data["paving"].extend(paving_triangles)

    metadata = data["metadata"]
    path_key = "Data/southwest-public-spaces-source.geojson"
    inputs_sha256[path_key] = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
    metadata["inputs_sha256"] = {
        key.replace("\\", "/"): value for key, value in inputs_sha256.items()
    }
    if any(Path(key).is_absolute() for key in metadata["inputs_sha256"]):
        raise ValueError("inputs_sha256 keys must be project-relative")
    metadata["supplemental_site_source"] = _source_metadata(raw, source_path) | {
        "line_features_by_site": {key: len(value) for key, value in line_features.items()},
        "cultural_source_line_types": {
            kind: sum(props.get("PEDESTRIANTYPE") == kind
                      for props, _ in line_features[CULTURAL_ID]) for kind in ("PA", "CWY")
        },
        "access_half_width_m": 3,
        "paved_triangle_count": len(paving_triangles),
    }
    expected_site_count = len(data["metadata"].get("source_revisions", {})) + len(SITE_NAMES)
    if len(data["sites"]) != expected_site_count or len(data["gardens"]) != expected_site_count:
        raise ValueError("Supplement did not retain the full source-site inventory")
    if len(data["fixtures"]) != sum(item["fixtures"] for item in data["sites"]):
        raise ValueError("Fixture counts changed or do not match Site metadata")
    return {
        "source_sites": source_sites,
        "supported_sites": {CULTURAL_ID: culture_site, WONDERLAND_ID: event_site},
        "paths": paths,
        "access": access,
        "paved": paved,
        "paving_triangles": paving_triangles,
        "road_targets": site_targets,
        "building_clearance": building_clearance,
        "site_roads": site_roads,
    }


def validate_southwest_public_spaces(data, source_path, ground, lots, road_hard,
                                     street_targets, district_roads=None):
    """Validate the supplemental pair alongside the complete surveyed site inventory."""
    expected_site_count = len(data.get("metadata", {}).get("source_revisions", {})) + len(SITE_NAMES)
    if len(data.get("sites", [])) != expected_site_count or len(data.get("gardens", [])) != expected_site_count:
        raise AssertionError("Expected all surveyed Sites plus the two supplemental Sites")
    sites = [item for item in data["sites"] if item.get("id") in SITE_NAMES]
    gardens = [item for item in data["gardens"] if item.get("site") in SITE_NAMES]
    if {item["id"] for item in sites} != set(SITE_NAMES) or len(sites) != 2:
        raise AssertionError("Supplemental source Site IDs are missing or duplicated")
    if {item["id"]: item.get("name") for item in sites} != SITE_NAMES \
            or any(item.get("fixtures") != 0 for item in sites):
        raise AssertionError("Supplemental display names or fixture counts changed")
    if {item["site"] for item in gardens} != set(SITE_NAMES) or len(gardens) != 2:
        raise AssertionError("Supplemental garden records are missing or duplicated")
    source, source_sites, line_features = _site_and_lines(source_path)
    metadata = data.get("metadata", {}).get("supplemental_site_source", {})
    if len(source["features"]) != 193 or metadata.get("feature_count") != 193 \
            or metadata.get("site_fragment_count") != 2:
        raise AssertionError("Supplemental source feature/Site counts do not match the audited pair")
    if metadata.get("site_ids") != sorted(SITE_NAMES):
        raise AssertionError("Supplemental source IDs differ from the audited pair")
    source_counts = data["metadata"]
    if source_counts.get("source_feature_count") != source_counts.get("source_site_fragment_count", 0) \
            + source_counts.get("source_sport_fragment_count", 0):
        raise AssertionError("Integrated government source feature counts are inconsistent")

    culture_garden = next(item for item in gardens if item["site"] == CULTURAL_ID)
    event_garden = next(item for item in gardens if item["site"] == WONDERLAND_ID)
    if culture_garden.get("surface_mode") != "piazza_and_access":
        raise AssertionError("Cultural Centre piazza and access treatment is missing")
    if event_garden.get("event_ground") is not True or event_garden.get("paths") \
            or event_garden.get("access") or event_garden.get("paving_area_m2") != 0 \
            or event_garden.get("fixtures_reserved") is not True \
            or event_garden.get("center_probe") != list(WONDERLAND_PROBE):
        raise AssertionError("Wonderland event ground has authored paths or lost its reservation")

    cultural_site = make_valid(source_sites[CULTURAL_ID].intersection(ground))
    event_site = make_valid(source_sites[WONDERLAND_ID].intersection(ground))
    probe = Point(*WONDERLAND_PROBE)
    if not event_site.covers(probe):
        raise AssertionError("Wonderland center probe is not supported by the current ground")

    paths = union_all([Polygon(item[0], item[1:]) for item in culture_garden["paths"]]) \
        if culture_garden.get("paths") else Polygon()
    access = union_all([Polygon(item[0], item[1:]) for item in culture_garden["access"]]) \
        if culture_garden.get("access") else Polygon()
    paved = union_all([paths, access])
    buildings = lots.buffer(4)
    targets = street_targets
    if district_roads is None:
        road_path = Path(source_path).with_name("nathan-road.json")
        district_roads = json.loads(road_path.read_text()) if road_path.exists() else {}
    district_hard, district_targets = _district_road_buffers(cultural_site, district_roads)
    roads = union_all([road_hard, district_hard])
    targets = union_all([targets, district_targets])
    if paths.is_empty or not cultural_site.buffer(.01).covers(paths):
        raise AssertionError("Cultural source paths escape the exact supported Site")
    if not ground.buffer(.01).covers(paved) or paved.intersection(buildings).area > .01 \
            or paved.intersection(roads).area > .01:
        raise AssertionError("Cultural paving is outside supported ground or intersects clearance")
    if paths.distance(targets) > 2.5:
        raise AssertionError("Cultural source paths no longer connect to a reviewed street target")
    if not all(paved.covers(Point(point)) for point in CULTURAL_CONTROL_POINTS):
        raise AssertionError("A reviewed Cultural Centre pedestrian connection lost paving")
    if any(item.get("site") in SITE_NAMES for item in data["fixtures"]):
        raise AssertionError("Supplement added unsupported fixtures")
    expected_hash = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
    if data["metadata"].get("inputs_sha256", {}).get("Data/southwest-public-spaces-source.geojson") != expected_hash:
        raise AssertionError("Supplemental source hash is missing from inputs_sha256")
    if any(Path(key).is_absolute() for key in data["metadata"].get("inputs_sha256", {})):
        raise AssertionError("inputs_sha256 contains a non-project-relative path")
    if not line_features[CULTURAL_ID]:
        raise AssertionError("Cultural source path lines are missing")
    return True
