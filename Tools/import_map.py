"""Extract public TD KML into offline GeoJSON and a wider Kowloon driving scene.

Usage: python3 Tools/import_map.py /path/to/CENTERLINE.kmz
Download: https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz
Only Python's standard library is required. Coordinates are local metres,
east = +X, north = -Z. Road widths and H1 stop locations are game design.
"""
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = (114.17232, 22.2950)
BBOX = (114.1625, 22.29455, 114.1825, 22.3057)
NS = {"k": "http://www.opengis.net/kml/2.2"}
SOURCE = "https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz"


def local(p):
    return ((p[0] - ORIGIN[0]) * 111320 * math.cos(math.radians(ORIGIN[1])),
            -(p[1] - ORIGIN[1]) * 111320)


def clip(a, b):
    """Liang-Barsky clipping preserves segments crossing the extract boundary."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    lo, hi = 0.0, 1.0
    for p, q in zip((-dx, dx, -dy, dy),
                    (a[0]-BBOX[0], BBOX[2]-a[0], a[1]-BBOX[1], BBOX[3]-a[1])):
        if p == 0:
            if q < 0:
                return None
        elif p < 0:
            lo = max(lo, q/p)
        else:
            hi = min(hi, q/p)
    if lo > hi:
        return None
    return [(a[0]+lo*dx, a[1]+lo*dy), (a[0]+hi*dx, a[1]+hi*dy)]


def extract(path):
    features = []
    with zipfile.ZipFile(path) as archive, archive.open("doc.kml") as stream:
        for _, element in ET.iterparse(stream, events=("end",)):
            if element.tag != f"{{{NS['k']}}}Placemark":
                continue
            name = element.findtext("k:name", "", NS)
            description = element.findtext("k:description", "", NS)
            props = dict(re.findall(r"<td>([A-Z_]+)</td>\s*<td>(.*?)</td>", description))
            if props.get("ELEVATION", "0") != "0" or name == "-99":
                element.clear()
                continue
            for coords in element.findall(".//k:coordinates", NS):
                points = [tuple(map(float, word.split(",")[:2])) for word in coords.text.split()]
                lines = []
                for a, b in zip(points, points[1:]):
                    part = clip(a, b)
                    if part and math.dist(*part) > 1e-10:
                        if lines and math.dist(lines[-1][-1], part[0]) < 1e-9:
                            lines[-1].append(part[1])
                        else:
                            lines.append(part)
                for line in lines:
                    features.append({"type": "Feature", "properties": {
                        "name": name, "name_zh": props.get("STREET_CNAME", ""),
                        "source_id": element.get("id"), "travel_direction": props.get("TRAVEL_DIRECTION")},
                        "geometry": {"type": "LineString", "coordinates": line}})
            element.clear()
    return features


def build(path):
    features = extract(path)
    nathan = [[local(p) for p in f["geometry"]["coordinates"]]
              for f in features if f["properties"]["name"] == "NATHAN ROAD"]
    road_points = []
    for distance in range(-25, 1191, 5):
        z = -float(distance)
        crossings = []
        for line in nathan:
            for a, b in zip(line, line[1:]):
                if min(a[1], b[1]) <= z < max(a[1], b[1]):
                    crossings.append(a[0] + (b[0]-a[0]) * (z-a[1])/(b[1]-a[1]))
        if not crossings:
            raise ValueError(f"Nathan Road centreline has a gap at {distance} metres")
        # ponytail: midpoint of carriageway extremes; use lane topology for junction routing.
        road_points.append([round((min(crossings)+max(crossings))/2, 3), round(z, 3)])
    route = [p for p in road_points if -1150 <= p[1] <= 0]
    # Exclude unnamed links, pedestrian paths and grade-separated highway approaches.
    excluded = {"NULL", "CROSS HARBOUR TUNNEL", "HUNG HOM BYPASS", "HONG CHONG ROAD",
                "RAILWAY APPROACH", "METROPOLIS DRIVE"}
    streets = [f for f in features if f["properties"]["name"] not in excluded
               and not f["properties"]["name"].endswith((" PATH", " SQUARE", " TERRACE"))]
    lines = [[local(p) for p in f["geometry"]["coordinates"]] for f in streets]
    # Follow shared/nearby source vertices; omit isolated fragments of flyovers at the clip edge.
    cells, neighbors = {}, [set() for _ in lines]
    for i, line in enumerate(lines):
        for x, z in line:
            cell = (math.floor(x / 12), math.floor(z / 12))
            for dx in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j, px, pz in cells.get((cell[0]+dx, cell[1]+dz), []):
                        if i != j and math.hypot(x-px, z-pz) <= 12:
                            neighbors[i].add(j)
                            neighbors[j].add(i)
            cells.setdefault(cell, []).append((i, x, z))
    connected = {i for i, f in enumerate(streets) if f["properties"]["name"] == "NATHAN ROAD"}
    pending = list(connected)
    while pending:
        for i in neighbors[pending.pop()] - connected:
            connected.add(i)
            pending.append(i)
    side_roads = [{"name": f["properties"]["name"],
                   "points": [[round(x, 3), round(z, 3)] for x, z in lines[i]]}
                  for i, f in enumerate(streets)
                  if i in connected and f["properties"]["name"] != "NATHAN ROAD"]
    assert {"CANTON ROAD", "CHATHAM ROAD SOUTH", "SCIENCE MUSEUM ROAD"} <= {r["name"] for r in side_roads}
    source_hash = hashlib.file_digest(open(path, "rb"), "sha256").hexdigest()
    old_metadata = json.loads((ROOT / "Data/nathan-road.json").read_text())["metadata"] if (ROOT / "Data/nathan-road.json").exists() else {}
    processed = datetime.datetime.now(datetime.timezone.utc).isoformat()
    metadata = {"source": SOURCE, "provider": "Transport Department, HKSAR Government / DATA.GOV.HK",
                "terms": "https://data.gov.hk/en/terms-and-conditions",
                "retrieved_utc": old_metadata.get("retrieved_utc", processed) if old_metadata.get("source_sha256") == source_hash else processed,
                "processed_utc": processed, "source_sha256": source_hash,
                "bbox_wgs84": BBOX, "origin_wgs84": ORIGIN,
                "note": "Original clipped WGS84 geometry. Game corridor averages carriageways; widths, elevations and H1 stops are fictional."}
    (ROOT / "Data/roads.geojson").write_text(json.dumps({"type": "FeatureCollection", "metadata": metadata, "features": features}, ensure_ascii=False, separators=(",", ":")))
    output = {"metadata": metadata, "bounds": [round(local(BBOX[:2])[0], 3), round(local(BBOX[2:])[1], 3),
                         round(local(BBOX[2:])[0], 3), round(local(BBOX[:2])[1], 3)],
              "points": route, "road_points": road_points, "side_roads": side_roads,
              "stops": [{"name": "Middle Road", "zh": "中間道", "distance": 55, "passengers": 8},
                        {"name": "Kowloon Park", "zh": "九龍公園", "distance": 535, "passengers": 12},
                        {"name": "Jordan Road", "zh": "佐敦道", "distance": 1100, "passengers": 6}]}
    (ROOT / "Data/nathan-road.json").write_text(json.dumps(output, ensure_ascii=False, indent=2))
    assert len(route) == 231 and 80 < len(features) < 1000
    assert abs(route[0][0]) < 15 and -100 < route[-1][0] < 0
    print(f"MAP_OK: {len(features)} government road features; {len(side_roads)} connected street sections; {len(route)} corridor points; 1150 m")


if __name__ == "__main__":
    assert clip((114, 22.30), (115, 22.30)) is not None
    assert clip((114, 22), (115, 22)) is None
    build(Path(sys.argv[1]))
