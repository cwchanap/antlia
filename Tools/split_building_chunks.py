#!/usr/bin/env python3
"""Split authored building GLBs into lossless district chunks and collision proxies."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import shutil
import struct
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "Assets/Models"
OUTPUT_DIR = MODEL_DIR / "BuildingChunks"
TEXTURE_DIR = OUTPUT_DIR / "textures"
MANIFEST_PATH = ROOT / "Data/building-chunks.json"
MARKER = ".generated-by-split_building_chunks"
SOURCE_COUNT = 23
PAIR_COUNT = 3135
UNIQUE_IMAGE_COUNT = 3
GLB_JSON = 0x4E4F534A
GLB_BIN = 0x004E4942
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
TEXTURE_IMPORT_CONFIG = '[remap]\nimporter="texture"\ntype="CompressedTexture2D"\n\n[params]\ncompress/mode=2\ncompress/high_quality=false\nmipmaps/generate=true\n'
PROXY_MATERIAL = {
    "name": "Proxy neutral concrete",
    "pbrMetallicRoughness": {
        "baseColorFactor": [0.62, 0.61, 0.58, 1.0],
        "metallicFactor": 0.0,
        "roughnessFactor": 0.9,
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align4(data: bytearray) -> None:
    data.extend(b"\0" * (-len(data) % 4))


def read_glb(data: bytes) -> tuple[dict, bytes]:
    require(len(data) >= 20, "GLB is truncated")
    magic, version, total = struct.unpack_from("<4sII", data)
    require(magic == b"glTF" and version == 2, "expected a GLB 2.0 file")
    require(total == len(data), "GLB header length does not match file size")
    chunks = []
    offset = 12
    while offset < len(data):
        require(offset + 8 <= len(data), "truncated GLB chunk header")
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        require(offset + length <= len(data), "truncated GLB chunk")
        chunks.append((kind, data[offset:offset + length]))
        offset += length
    require([kind for kind, _ in chunks] == [GLB_JSON, GLB_BIN], "expected JSON and BIN GLB chunks")
    document = json.loads(chunks[0][1].decode("utf-8"))
    require(len(document.get("buffers", [])) == 1 and "uri" not in document["buffers"][0],
            "expected one embedded GLB buffer")
    binary = chunks[1][1]
    require(document["buffers"][0]["byteLength"] <= len(binary), "GLB buffer length exceeds BIN chunk")
    return document, binary


def write_glb(document: dict, binary: bytes) -> bytes:
    doc = dict(document)
    doc["buffers"] = [dict(buffer) for buffer in document["buffers"]]
    doc["buffers"][0]["byteLength"] = len(binary)
    json_bytes = json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    json_bytes += b" " * (-len(json_bytes) % 4)
    bin_bytes = binary + b"\0" * (-len(binary) % 4)
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    return (struct.pack("<4sII", b"glTF", 2, total)
            + struct.pack("<II", len(json_bytes), GLB_JSON) + json_bytes
            + struct.pack("<II", len(bin_bytes), GLB_BIN) + bin_bytes)


def view_payload(document: dict, binary: bytes, view_index: int) -> bytes:
    view = document["bufferViews"][view_index]
    require(view.get("buffer", 0) == 0, f"unsupported buffer index in bufferView {view_index}")
    start = view.get("byteOffset", 0)
    end = start + view["byteLength"]
    require(0 <= start <= end <= document["buffers"][0]["byteLength"] and end <= len(binary),
            f"invalid bufferView range {view_index}")
    return binary[start:end]


def image_payloads(document: dict, binary: bytes) -> tuple[dict[int, str], dict[str, tuple[str, bytes]], dict[int, str]]:
    uris: dict[int, str] = {}
    unique: dict[str, tuple[str, bytes]] = {}
    digests: dict[int, str] = {}
    for image_index, image in enumerate(document.get("images", [])):
        require(image.get("mimeType") == "image/png" and "bufferView" in image and "uri" not in image,
                f"source image {image_index} must be an embedded PNG")
        payload = view_payload(document, binary, image["bufferView"])
        require(payload.startswith(PNG_MAGIC), f"source image {image_index} is not a PNG")
        digest = hashlib.sha256(payload).hexdigest()
        stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", image.get("name", "image")).strip("_.") or "image"
        filename = f"{stem}-{digest}.png"
        if digest in unique:
            require(unique[digest][0] == filename and unique[digest][1] == payload,
                    "identical image payloads have inconsistent source names")
        unique[digest] = (filename, payload)
        uris[image_index] = f"textures/{filename}"
        digests[image_index] = digest
    return uris, unique, digests


def source_pairs(document: dict, source: Path) -> tuple[dict[str, int], dict[str, int]]:
    require(len(document.get("scenes", [])) == 1, f"{source.name}: expected one scene")
    nodes = document.get("nodes", [])
    scene_nodes = document["scenes"][document.get("scene", 0)].get("nodes", [])
    require(scene_nodes == list(range(len(nodes))), f"{source.name}: building nodes must be direct scene roots")
    visual: dict[str, int] = {}
    collision: dict[str, int] = {}
    meshes = set()
    for node_index, node in enumerate(nodes):
        name = node.get("name", "")
        require(not node.get("children"), f"{source.name}: unexpected nested building node {name}")
        if name.startswith("District_"):
            key, table = name[len("District_"):], visual
        elif name.startswith("Collision_"):
            key, table = name[len("Collision_"):], collision
        else:
            raise AssertionError(f"{source.name}: unexpected building node {name!r}")
        require(key not in table and "mesh" in node, f"{source.name}: duplicate or meshless node {name}")
        table[key] = node_index
        meshes.add(node["mesh"])
    require(visual.keys() == collision.keys(), f"{source.name}: District_/Collision_ suffixes do not pair")
    require(meshes == set(range(len(document.get("meshes", [])))),
            f"{source.name}: source contains unreferenced or shared meshes")
    return visual, collision


def accessor_refs(mesh: dict) -> set[int]:
    refs: set[int] = set()
    for primitive in mesh.get("primitives", []):
        refs.update(primitive.get("attributes", {}).values())
        if "indices" in primitive:
            refs.add(primitive["indices"])
        for target in primitive.get("targets", []):
            refs.update(target.values())
        require(not primitive.get("extensions"), "primitive accessor extensions are unsupported")
    return refs


def accessor_views(accessor: dict) -> set[int]:
    views = set()
    if "bufferView" in accessor:
        views.add(accessor["bufferView"])
    sparse = accessor.get("sparse")
    if sparse:
        views.add(sparse["indices"]["bufferView"])
        views.add(sparse["values"]["bufferView"])
    return views


def remap_accessor_refs(mesh: dict, mapping: dict[int, int]) -> dict:
    result = copy.deepcopy(mesh)
    for primitive in result.get("primitives", []):
        primitive["attributes"] = {key: mapping[value] for key, value in primitive.get("attributes", {}).items()}
        if "indices" in primitive:
            primitive["indices"] = mapping[primitive["indices"]]
        for target in primitive.get("targets", []):
            for key in target:
                target[key] = mapping[target[key]]
    return result


def remap_accessor_views(accessor: dict, mapping: dict[int, int]) -> dict:
    result = copy.deepcopy(accessor)
    if "bufferView" in result:
        result["bufferView"] = mapping[result["bufferView"]]
    if result.get("sparse"):
        result["sparse"]["indices"]["bufferView"] = mapping[result["sparse"]["indices"]["bufferView"]]
        result["sparse"]["values"]["bufferView"] = mapping[result["sparse"]["values"]["bufferView"]]
    return result


def subset_glb(document: dict, binary: bytes, node_indices: list[int],
               image_uris: dict[int, str], proxy: bool = False) -> bytes:
    selected_set = set(node_indices)
    selected_nodes = [index for index in document["scenes"][document.get("scene", 0)]["nodes"]
                      if index in selected_set]
    require(len(selected_nodes) == len(node_indices), "selected node is not in the active scene")
    source_meshes = sorted({document["nodes"][index]["mesh"] for index in selected_nodes})
    mesh_map = {old: new for new, old in enumerate(source_meshes)}
    accessors = sorted(set().union(*(accessor_refs(document["meshes"][index]) for index in source_meshes)))
    accessor_map = {old: new for new, old in enumerate(accessors)}
    views = sorted(set().union(*(accessor_views(document["accessors"][index]) for index in accessors)))
    view_map: dict[int, int] = {}
    out_binary = bytearray()
    out_views = []
    for old in views:
        align4(out_binary)
        view_map[old] = len(out_views)
        item = copy.deepcopy(document["bufferViews"][old])
        item["buffer"] = 0
        item["byteOffset"] = len(out_binary)
        out_views.append(item)
        out_binary.extend(view_payload(document, binary, old))
    out_accessors = [remap_accessor_views(document["accessors"][old], view_map) for old in accessors]
    out_meshes = []
    for old in source_meshes:
        mesh = remap_accessor_refs(document["meshes"][old], accessor_map)
        if proxy:
            suffix = mesh.get("name", "").removeprefix("Collision_")
            mesh["name"] = f"Proxy_{suffix}"
            for primitive in mesh.get("primitives", []):
                primitive["material"] = 0
        out_meshes.append(mesh)
    node_map = {old: new for new, old in enumerate(selected_nodes)}
    out_nodes = []
    for old in selected_nodes:
        node = copy.deepcopy(document["nodes"][old])
        node["mesh"] = mesh_map[node["mesh"]]
        if proxy:
            node["name"] = f"Proxy_{node.get('name', '').removeprefix('Collision_')}"
        out_nodes.append(node)

    result = dict(document)
    result["nodes"] = out_nodes
    result["meshes"] = out_meshes
    result["accessors"] = out_accessors
    result["bufferViews"] = out_views
    result["buffers"] = [dict(buffer) for buffer in document["buffers"]]
    result["buffers"][0]["byteLength"] = len(out_binary)
    result["scenes"] = copy.deepcopy(document["scenes"])
    result["scenes"][document.get("scene", 0)]["nodes"] = [node_map[index] for index in selected_nodes]
    if proxy:
        result["materials"] = [copy.deepcopy(PROXY_MATERIAL)]
        result["textures"] = []
        result["images"] = []
        result["samplers"] = []
        for key in ("extensionsUsed", "extensionsRequired"):
            if key in result:
                result[key] = [extension for extension in result[key] if not extension.startswith("KHR_materials_")]
    else:
        result["images"] = []
        for index, image in enumerate(document.get("images", [])):
            copied = copy.deepcopy(image)
            copied.pop("bufferView", None)
            copied["uri"] = image_uris[index]
            result["images"].append(copied)
    return write_glb(result, bytes(out_binary))


def node_matrix(node: dict) -> list[list[float]]:
    if "matrix" in node:
        values = node["matrix"]
        require(len(values) == 16, "node matrix must have 16 values")
        return [[values[row + column * 4] for column in range(4)] for row in range(4)]
    translation = node.get("translation", [0.0, 0.0, 0.0])
    scale = node.get("scale", [1.0, 1.0, 1.0])
    x, y, z, w = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
    rotation = [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ]
    return [[rotation[row][col] * scale[col] for col in range(3)] + [translation[row]]
            for row in range(3)] + [[0.0, 0.0, 0.0, 1.0]]


def world_bounds(document: dict, node_indices: list[int]) -> tuple[list[float], list[float], int]:
    lows = [math.inf, math.inf, math.inf]
    highs = [-math.inf, -math.inf, -math.inf]
    vertices = 0
    for node_index in node_indices:
        node = document["nodes"][node_index]
        matrix = node_matrix(node)
        mesh = document["meshes"][node["mesh"]]
        for primitive in mesh.get("primitives", []):
            accessor = document["accessors"][primitive["attributes"]["POSITION"]]
            require(accessor.get("type") == "VEC3" and accessor.get("componentType") == 5126,
                    f"{node.get('name')}: POSITION must be float VEC3")
            require("min" in accessor and "max" in accessor, f"{node.get('name')}: POSITION bounds are required")
            vertices += accessor["count"]
            for mask in range(8):
                point = [accessor["max"][axis] if mask & (1 << axis) else accessor["min"][axis]
                         for axis in range(3)]
                transformed = [sum(matrix[row][col] * point[col] for col in range(3)) + matrix[row][3]
                               for row in range(3)]
                for axis in range(3):
                    lows[axis] = min(lows[axis], transformed[axis])
                    highs[axis] = max(highs[axis], transformed[axis])
    require(vertices > 0 and all(math.isfinite(value) for value in lows + highs), "invalid building bounds")
    return ([math.nextafter(value, -math.inf) for value in lows],
            [math.nextafter(value, math.inf) for value in highs], vertices)


def clean_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.")
    require(cleaned, f"cannot make a path-safe identifier from {value!r}")
    return cleaned


def accessor_signature(document: dict, binary: bytes, accessor_index: int) -> tuple:
    accessor = copy.deepcopy(document["accessors"][accessor_index])
    views = []

    def replace(value):
        if isinstance(value, dict):
            if "bufferView" in value:
                index = value["bufferView"]
                view = document["bufferViews"][index]
                metadata = {key: item for key, item in view.items() if key not in ("buffer", "byteOffset")}
                views.append((metadata, view_payload(document, binary, index)))
                value["bufferView"] = "<view>"
            for child in value.values():
                replace(child)
        elif isinstance(value, list):
            for child in value:
                replace(child)

    replace(accessor)
    return json.dumps(accessor, sort_keys=True, separators=(",", ":")), tuple(views)


def mesh_signature(document: dict, binary: bytes, mesh_index: int, include_materials: bool = True,
                   ignore_name: bool = False) -> tuple:
    mesh = document["meshes"][mesh_index]
    metadata = {key: value for key, value in mesh.items() if key != "primitives"}
    if ignore_name:
        metadata.pop("name", None)
    primitives = []
    for primitive in mesh.get("primitives", []):
        shape = {key: copy.deepcopy(value) for key, value in primitive.items()
                 if key not in ("attributes", "indices", "targets", "material")}
        attributes = tuple((name, accessor_signature(document, binary, index))
                           for name, index in sorted(primitive.get("attributes", {}).items()))
        indices = accessor_signature(document, binary, primitive["indices"]) if "indices" in primitive else None
        targets = tuple(tuple((name, accessor_signature(document, binary, index))
                              for name, index in sorted(target.items()))
                        for target in primitive.get("targets", []))
        material = None
        if include_materials and "material" in primitive:
            material = document.get("materials", [])[primitive["material"]]
        primitives.append((json.dumps(shape, sort_keys=True, separators=(",", ":")), attributes, indices, targets,
                           json.dumps(material, sort_keys=True, separators=(",", ":")) if material is not None else None))
    return json.dumps(metadata, sort_keys=True, separators=(",", ":")), tuple(primitives)


def validate_output_refs(document: dict, binary: bytes) -> None:
    used_meshes = {node["mesh"] for node in document["nodes"] if "mesh" in node}
    require(used_meshes == set(range(len(document.get("meshes", [])))), "output contains an unreferenced mesh")
    used_accessors = set().union(*(accessor_refs(mesh) for mesh in document.get("meshes", [])))
    require(used_accessors == set(range(len(document.get("accessors", [])))), "output contains an unreferenced accessor")
    used_views = set().union(*(accessor_views(document["accessors"][index]) for index in used_accessors))
    require(used_views == set(range(len(document.get("bufferViews", [])))), "output contains an unreferenced bufferView")
    require(document["buffers"][0]["byteLength"] <= len(binary), "output BIN chunk is truncated")
    for index, view in enumerate(document.get("bufferViews", [])):
        view_payload(document, binary, index)
    for image in document.get("images", []):
        require("bufferView" not in image and "uri" in image, "output image is still embedded")


def compare_equivalence(source_doc: dict, source_bin: bytes, output_doc: dict, output_bin: bytes,
                        node_pairs: list[tuple[int, str]], proxy: bool = False) -> None:
    output_nodes = {node["name"]: node for node in output_doc["nodes"]}
    for source_index, output_name in node_pairs:
        source_node = source_doc["nodes"][source_index]
        output_node = output_nodes[output_name]
        expected_node = copy.deepcopy(source_node)
        expected_node.pop("mesh", None)
        expected_node["name"] = output_name
        actual_node = copy.deepcopy(output_node)
        actual_node.pop("mesh", None)
        require(actual_node == expected_node, f"node transform/metadata changed for {output_name}")
        source_mesh = source_node["mesh"]
        output_mesh = output_node["mesh"]
        if proxy:
            require(mesh_signature(source_doc, source_bin, source_mesh, False, True)
                    == mesh_signature(output_doc, output_bin, output_mesh, False, True),
                    f"proxy collision payload changed for {output_name}")
            require(all(primitive.get("material") == 0
                        for primitive in output_doc["meshes"][output_mesh]["primitives"]),
                    f"proxy {output_name} must use neutral concrete")
        else:
            require(mesh_signature(source_doc, source_bin, source_mesh)
                    == mesh_signature(output_doc, output_bin, output_mesh),
                    f"geometry or material payload changed for {output_name}")


def output_chunks(asset: dict, source_doc: dict, source_bin: bytes, visual: dict[str, int],
                  collision: dict[str, int], uris: dict[int, str], root: Path) -> tuple[list[dict], int, int]:
    stem = asset["stem"]
    proxy_rel = f"Assets/Models/BuildingChunks/{stem}-proxy.glb"
    proxy_nodes = [index for index, node in enumerate(source_doc["nodes"])
                   if node["name"].startswith("Collision_")]
    proxy_bytes = subset_glb(source_doc, source_bin, proxy_nodes, uris, proxy=True)
    (root / proxy_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / proxy_rel).write_bytes(proxy_bytes)
    chunks = []
    visual_total = 0
    collision_total = 0
    for suffix in sorted(visual):
        visual_index, collision_index = visual[suffix], collision[suffix]
        district_name = source_doc["nodes"][visual_index]["name"]
        identifier = clean_name(f"{stem}-{district_name}")
        proxy_name = f"Proxy_{suffix}"
        node_indices = [index for index in range(len(source_doc["nodes"]))
                        if index in (visual_index, collision_index)]
        detail_bytes = subset_glb(source_doc, source_bin, node_indices, uris)
        relative_path = f"Assets/Models/BuildingChunks/{identifier}.glb"
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(detail_bytes)
        both_nodes = [visual_index, collision_index]
        _, _, visual_vertices = world_bounds(source_doc, [visual_index])
        _, _, collision_vertices = world_bounds(source_doc, [collision_index])
        combined_min, combined_max, _ = world_bounds(source_doc, both_nodes)
        chunks.append({
            "id": identifier,
            "path": f"res://{relative_path}",
            "proxy_name": proxy_name,
            "source": stem,
            "min": combined_min,
            "max": combined_max,
            "visual_vertices": visual_vertices,
            "collision_vertices": collision_vertices,
        })
        visual_total += visual_vertices
        collision_total += collision_vertices
    require(len(chunks) == len(visual) == len(collision), f"{stem}: chunk pair count mismatch")
    asset["proxy"] = f"res://{proxy_rel}"
    asset["proxy_bytes"] = len(proxy_bytes)
    return chunks, visual_total, collision_total


def validate_images(unique_images: dict[str, tuple[str, bytes]], expected_count: int) -> None:
    require(len(unique_images) == expected_count,
            f"expected {expected_count} unique source PNGs, found {len(unique_images)}")


def write_texture_import(image_path: Path, existing_uid: str | None = None) -> None:
    import_path = Path(f"{image_path}.import")
    if existing_uid is None and import_path.is_file():
        existing_uid = godot_config_value(import_path.read_text(encoding="utf-8"), "remap", "uid")
    config = (TEXTURE_IMPORT_CONFIG.replace("[remap]\n", f"[remap]\nuid={existing_uid}\n")
              if existing_uid is not None else TEXTURE_IMPORT_CONFIG)
    import_path.write_text(config, encoding="utf-8")


def godot_config_value(contents: str, section: str, key: str) -> str | None:
    active_section = None
    value = None
    for line in contents.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            active_section = line[1:-1].strip()
        elif active_section == section and "=" in line:
            name, candidate = line.split("=", 1)
            if name.strip() == key:
                value = candidate.strip()
    return value


def check_texture_import(import_path: Path) -> None:
    require(import_path.is_file(), f"missing PNG import config: {import_path.name}")
    contents = import_path.read_text(encoding="utf-8")
    importer = (godot_config_value(contents, "remap", "importer") or "").strip().strip('"')
    resource_type = (godot_config_value(contents, "remap", "type") or "").strip().strip('"')
    require(importer == "texture" and resource_type == "CompressedTexture2D",
            f"{import_path.name}: expected a texture import for CompressedTexture2D")
    compression = godot_config_value(contents, "params", "compress/mode")
    require(compression is not None and compression.strip() == "2",
            f"{import_path.name}: [params] compress/mode must be 2 (found {compression!r})")
    high_quality = godot_config_value(contents, "params", "compress/high_quality")
    require(high_quality is not None and high_quality.strip().lower() == "false",
            f"{import_path.name}: [params] compress/high_quality must be false (found {high_quality!r})")
    mipmaps = godot_config_value(contents, "params", "mipmaps/generate")
    require(mipmaps is not None and mipmaps.strip().lower() == "true",
            f"{import_path.name}: [params] mipmaps/generate must be true (found {mipmaps!r})")


def generate() -> dict:
    sources = sorted(MODEL_DIR.glob("*-buildings.glb"))
    require(len(sources) == SOURCE_COUNT, f"expected {SOURCE_COUNT} source GLBs, found {len(sources)}")
    existing_texture_uids = {
        path.name: godot_config_value(path.read_text(encoding="utf-8"), "remap", "uid")
        for path in TEXTURE_DIR.glob("*.png.import")
    }
    if OUTPUT_DIR.exists():
        require((OUTPUT_DIR / MARKER).is_file(), f"refusing to replace unowned directory {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    (OUTPUT_DIR / MARKER).write_text("generated by Tools/split_building_chunks.py\n", encoding="utf-8")

    manifest_sources = []
    manifest_chunks = []
    unique_images: dict[str, tuple[str, bytes]] = {}
    source_bytes = 0
    proxy_bytes = 0
    visual_vertices = 0
    collision_vertices = 0
    for source in sources:
        source_data = source.read_bytes()
        source_bytes += len(source_data)
        source_doc, source_bin = read_glb(source_data)
        visual, collision = source_pairs(source_doc, source)
        image_uris, source_images, _ = image_payloads(source_doc, source_bin)
        for digest, value in source_images.items():
            if digest in unique_images:
                require(unique_images[digest] == value, "source PNG hash/name mismatch")
            unique_images[digest] = value
        asset = {"stem": source.stem}
        chunks, source_visual, source_collision = output_chunks(
            asset, source_doc, source_bin, visual, collision, image_uris, ROOT)
        manifest_chunks.extend(chunks)
        visual_vertices += source_visual
        collision_vertices += source_collision
        proxy_bytes += asset["proxy_bytes"]
        manifest_sources.append({
            "path": f"res://Assets/Models/{source.name}",
            "sha256": hashlib.sha256(source_data).hexdigest(),
            "proxy": asset["proxy"],
        })
    validate_images(unique_images, UNIQUE_IMAGE_COUNT)
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for filename, payload in sorted(unique_images.values()):
        texture_path = TEXTURE_DIR / filename
        texture_path.write_bytes(payload)
        write_texture_import(texture_path, existing_texture_uids.get(f"{filename}.import"))
    manifest = {"version": 1, "sources": manifest_sources, "chunks": manifest_chunks}
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "sources": len(manifest_sources),
        "chunks": len(manifest_chunks),
        "source_bytes": source_bytes,
        "detail_bytes": sum(path.stat().st_size for path in OUTPUT_DIR.glob("*.glb")) - proxy_bytes,
        "proxy_bytes": proxy_bytes,
        "texture_bytes": sum(path.stat().st_size for path in TEXTURE_DIR.glob("*.png")),
        "visual_vertices": visual_vertices,
        "collision_vertices": collision_vertices,
    }


def check() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    require(manifest.get("version") == 1, "unsupported building chunk manifest version")
    sources = sorted(MODEL_DIR.glob("*-buildings.glb"))
    require(len(sources) == SOURCE_COUNT and len(manifest.get("sources", [])) == SOURCE_COUNT,
            "manifest/source file count mismatch")
    manifest_source = {Path(item["path"]).name: item for item in manifest["sources"]}
    manifest_chunk = {item["id"]: item for item in manifest["chunks"]}
    require(len(manifest_chunk) == len(manifest["chunks"]), "duplicate manifest chunk id")
    unique_images: dict[str, tuple[str, bytes]] = {}
    expected_paths = set()
    expected_chunks = 0
    source_bytes = 0
    detail_bytes = 0
    proxy_bytes = 0
    visual_vertices = 0
    collision_vertices = 0
    for source in sources:
        source_data = source.read_bytes()
        source_bytes += len(source_data)
        require(source.name in manifest_source, f"source missing from manifest: {source.name}")
        source_entry = manifest_source[source.name]
        require(hashlib.sha256(source_data).hexdigest() == source_entry["sha256"],
                f"source hash changed: {source.name}")
        source_doc, source_bin = read_glb(source_data)
        visual, collision = source_pairs(source_doc, source)
        image_uris, source_images, source_image_digests = image_payloads(source_doc, source_bin)
        for digest, value in source_images.items():
            if digest in unique_images:
                require(unique_images[digest] == value, "source PNG hash/name mismatch")
            unique_images[digest] = value
        proxy_rel = f"Assets/Models/BuildingChunks/{source.stem}-proxy.glb"
        require(source_entry == {
            "path": f"res://Assets/Models/{source.name}",
            "sha256": hashlib.sha256(source_data).hexdigest(),
            "proxy": f"res://{proxy_rel}",
        }, f"manifest source record changed: {source.name}")
        proxy_path = ROOT / proxy_rel
        require(proxy_path.is_file(), f"missing proxy GLB: {proxy_rel}")
        expected_paths.add(f"{source.stem}-proxy.glb")
        proxy_expected = subset_glb(source_doc, source_bin,
                                    [i for i, node in enumerate(source_doc["nodes"])
                                     if node["name"].startswith("Collision_")], image_uris, proxy=True)
        proxy_data = proxy_path.read_bytes()
        require(proxy_data == proxy_expected, f"proxy GLB differs from deterministic source repack: {source.name}")
        proxy_doc, proxy_bin = read_glb(proxy_data)
        validate_output_refs(proxy_doc, proxy_bin)
        require(not proxy_doc.get("images") and not proxy_doc.get("textures") and not proxy_doc.get("samplers"),
                f"proxy contains textures: {source.name}")
        require(proxy_doc.get("materials") == [PROXY_MATERIAL], f"proxy material changed: {source.name}")
        proxy_pairs = []
        for suffix, node_index in collision.items():
            proxy_pairs.append((node_index, f"Proxy_{suffix}"))
        compare_equivalence(source_doc, source_bin, proxy_doc, proxy_bin, proxy_pairs, proxy=True)
        proxy_bytes += len(proxy_data)

        for suffix in sorted(visual):
            visual_index, collision_index = visual[suffix], collision[suffix]
            district_name = source_doc["nodes"][visual_index]["name"]
            identifier = clean_name(f"{source.stem}-{district_name}")
            entry = manifest_chunk.get(identifier)
            require(entry is not None, f"chunk missing from manifest: {identifier}")
            relative_path = f"Assets/Models/BuildingChunks/{identifier}.glb"
            expected_paths.add(f"{identifier}.glb")
            detail_path = ROOT / relative_path
            require(detail_path.is_file(), f"missing detail chunk: {relative_path}")
            expected = subset_glb(source_doc, source_bin, [visual_index, collision_index], image_uris)
            detail_data = detail_path.read_bytes()
            require(detail_data == expected, f"detail GLB differs from deterministic source repack: {identifier}")
            detail_doc, detail_bin = read_glb(detail_data)
            validate_output_refs(detail_doc, detail_bin)
            require(detail_doc.get("materials") == source_doc.get("materials", []),
                    f"material data changed: {identifier}")
            require(detail_doc.get("textures") == source_doc.get("textures", [])
                    and detail_doc.get("samplers") == source_doc.get("samplers", []),
                    f"texture/sampler data changed: {identifier}")
            for image_index, image in enumerate(source_doc.get("images", [])):
                output_image = detail_doc["images"][image_index]
                expected_image = {key: value for key, value in image.items() if key != "bufferView"}
                expected_image["uri"] = image_uris[image_index]
                require(output_image == expected_image, f"image reference changed: {identifier}")
                texture_path = OUTPUT_DIR / output_image["uri"]
                require(texture_path.is_file(), f"missing shared texture: {output_image['uri']}")
                require(output_image["uri"] == f"textures/{unique_images[source_image_digests[image_index]][0]}",
                        f"unexpected external texture reference: {output_image['uri']}")
            pairs = [(visual_index, source_doc["nodes"][visual_index]["name"]),
                     (collision_index, source_doc["nodes"][collision_index]["name"])]
            compare_equivalence(source_doc, source_bin, detail_doc, detail_bin, pairs)
            actual_min, actual_max, visual_count = world_bounds(source_doc, [visual_index])
            collision_min, collision_max, collision_count = world_bounds(source_doc, [collision_index])
            combined_min, combined_max, _ = world_bounds(source_doc, [visual_index, collision_index])
            require(entry == {
                "id": identifier,
                "path": f"res://{relative_path}",
                "proxy_name": f"Proxy_{suffix}",
                "source": source.stem,
                "min": combined_min,
                "max": combined_max,
                "visual_vertices": visual_count,
                "collision_vertices": collision_count,
            }, f"manifest bounds or vertex counts changed: {identifier}")
            require(all(combined_min[axis] <= min(actual_min[axis], collision_min[axis])
                        and combined_max[axis] >= max(actual_max[axis], collision_max[axis])
                        for axis in range(3)), f"chunk bounds exclude source geometry: {identifier}")
            visual_vertices += visual_count
            collision_vertices += collision_count
            detail_bytes += len(detail_data)
            expected_chunks += 1
    validate_images(unique_images, UNIQUE_IMAGE_COUNT)
    require(len(manifest["chunks"]) == expected_chunks == PAIR_COUNT,
            f"expected {PAIR_COUNT} district chunks, found {expected_chunks}")
    require(set(manifest_source) == {path.name for path in sources}, "manifest has unexpected source records")
    actual_paths = {path.name for path in OUTPUT_DIR.glob("*.glb")}
    require(actual_paths == expected_paths, "generated BuildingChunks directory has unexpected/missing GLBs")
    expected_textures = {filename for filename, _ in unique_images.values()}
    actual_textures = {path.name for path in TEXTURE_DIR.glob("*.png")}
    require(actual_textures == expected_textures, "shared texture directory has unexpected/missing PNGs")
    expected_imports = {f"{filename}.import" for filename in expected_textures}
    actual_imports = {path.name for path in TEXTURE_DIR.glob("*.png.import")}
    require(actual_imports == expected_imports, "shared texture directory has unexpected/missing PNG import configs")
    for digest, (filename, payload) in unique_images.items():
        path = TEXTURE_DIR / filename
        texture_data = path.read_bytes()
        require(texture_data == payload and hashlib.sha256(texture_data).hexdigest() == digest,
                f"shared texture changed: {filename}")
        check_texture_import(Path(f"{path}.import"))
    return {
        "sources": len(sources),
        "chunks": expected_chunks,
        "source_bytes": source_bytes,
        "detail_bytes": detail_bytes,
        "proxy_bytes": proxy_bytes,
        "texture_bytes": sum(path.stat().st_size for path in TEXTURE_DIR.glob("*.png")),
        "visual_vertices": visual_vertices,
        "collision_vertices": collision_vertices,
    }


def self_test() -> None:
    binary = bytearray()
    views = []

    def add_view(payload: bytes, target: int | None = None) -> int:
        align4(binary)
        view = {"buffer": 0, "byteOffset": len(binary), "byteLength": len(payload)}
        if target is not None:
            view["target"] = target
        views.append(view)
        binary.extend(payload)
        return len(views) - 1

    accessors = []

    def add_accessor(payload: bytes, count: int, kind: str, component: int, minimum=None, maximum=None) -> int:
        accessor = {"bufferView": add_view(payload), "componentType": component, "count": count, "type": kind}
        if minimum is not None:
            accessor["min"], accessor["max"] = minimum, maximum
        accessors.append(accessor)
        return len(accessors) - 1

    position_payloads = [
        (struct.pack("<9f", 0, 0, 0, 2, 0, 0, 0, 3, 1), [0, 0, 0], [2, 3, 1]),
        (struct.pack("<9f", -1, 0, 0, 1, 0, 0, 0, 2, 2), [-1, 0, 0], [1, 2, 2]),
        (struct.pack("<9f", 100, 0, 0, 102, 0, 0, 100, 2, 1), [100, 0, 0], [102, 2, 1]),
        (struct.pack("<9f", 99, 0, 0, 103, 0, 0, 100, 3, 2), [99, 0, 0], [103, 3, 2]),
    ]
    meshes = []
    nodes = []
    for index, (collision_name, district_name) in enumerate((("Collision_0_0", "District_0_0"),
                                                              ("Collision_9_9", "District_9_9"))):
        for offset, name in enumerate((collision_name, district_name)):
            base = index * 2 + offset
            position_payload, minimum, maximum = position_payloads[base]
            pos = add_accessor(position_payload, 3, "VEC3", 5126, minimum, maximum)
            normal = add_accessor(struct.pack("<9f", *([0, 1, 0] * 3)), 3, "VEC3", 5126)
            uv = add_accessor(struct.pack("<6f", 0, 0, 1, 0, 0, 1), 3, "VEC2", 5126)
            indices = add_accessor(struct.pack("<3H", 0, 1, 2), 3, "SCALAR", 5123)
            primitive = {"attributes": {"POSITION": pos, "NORMAL": normal, "TEXCOORD_0": uv},
                         "indices": indices}
            if name.startswith("District_"):
                primitive["material"] = 0
            mesh_index = len(meshes)
            meshes.append({"name": name, "primitives": [primitive]})
            nodes.append({"name": name, "mesh": mesh_index, "translation": [0, 0, -4]})
    image_payload = PNG_MAGIC + b"synthetic"
    image_view = add_view(image_payload)
    document = {
        "asset": {"version": "2.0"}, "scene": 0,
        "scenes": [{"nodes": [0, 1, 2, 3]}], "nodes": nodes, "meshes": meshes,
        "accessors": accessors, "bufferViews": views,
        "buffers": [{"byteLength": len(binary)}],
        "materials": [{"name": "facade", "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
        "textures": [{"source": 0}], "images": [{"name": "facade", "mimeType": "image/png", "bufferView": image_view}],
        "samplers": [],
    }
    source_bin = bytes(binary)
    uri = {0: "textures/facade-test.png"}
    detail, detail_bin = read_glb(subset_glb(document, source_bin, [0, 1], uri))
    require([node["name"] for node in detail["nodes"]] == ["Collision_0_0", "District_0_0"],
            "synthetic detail chunk retained unrelated nodes")
    require(len(detail["meshes"]) == 2 and len(detail["accessors"]) == 8,
            "synthetic detail chunk retained unrelated meshes/accessors")
    validate_output_refs(detail, detail_bin)
    require(detail["images"][0]["uri"] == uri[0] and "bufferView" not in detail["images"][0],
            "synthetic image was not externalized")
    compare_equivalence(document, source_bin, detail, detail_bin,
                        [(0, "Collision_0_0"), (1, "District_0_0")])
    proxy_data = subset_glb(document, source_bin, [0], uri, proxy=True)
    proxy, proxy_bin = read_glb(proxy_data)
    validate_output_refs(proxy, proxy_bin)
    require([node["name"] for node in proxy["nodes"]] == ["Proxy_0_0"]
            and len(proxy["meshes"]) == 1 and len(proxy["accessors"]) == 4,
            "synthetic proxy retained unrelated building data")
    require(not proxy.get("images") and not proxy.get("textures") and not proxy.get("samplers"),
            "synthetic proxy retained textures")
    require(proxy["materials"] == [PROXY_MATERIAL], "synthetic proxy concrete material changed")
    compare_equivalence(document, source_bin, proxy, proxy_bin, [(0, "Proxy_0_0")], proxy=True)
    conservative_min, conservative_max, _ = world_bounds(document, [1])
    require(conservative_min[0] < -1 and conservative_min[2] < -4
            and conservative_max[1] > 2 and conservative_max[2] > -2,
            "synthetic bounds did not include geometry overhang and node translation")
    with tempfile.TemporaryDirectory() as directory:
        texture_path = Path(directory) / "facade.png"
        import_path = Path(f"{texture_path}.import")
        import_path.write_text('[remap]\nimporter="texture"\ntype="CompressedTexture2D"\n'
                               'uid="uid://synthetic"\nmetadata={\n"vram_texture": false\n}\n\n'
                               '[params]\ncompress/mode=0\nmipmaps/generate=false\n', encoding="utf-8")
        existing_uid = godot_config_value(import_path.read_text(encoding="utf-8"), "remap", "uid")
        write_texture_import(texture_path)
        check_texture_import(import_path)
        require(godot_config_value(import_path.read_text(encoding="utf-8"), "remap", "uid") == existing_uid,
                "texture import writer did not preserve the UID after multiline metadata")
        import_path.unlink()
        write_texture_import(texture_path, existing_uid)
        require(godot_config_value(import_path.read_text(encoding="utf-8"), "remap", "uid") == existing_uid,
                "texture import writer did not preserve a UID after generated-directory cleanup")
        for key, expected, invalid in (("compress/mode", "2", "0"),
                                       ("compress/high_quality", "false", "true"),
                                       ("mipmaps/generate", "true", "false")):
            for value in (invalid, None):
                config = TEXTURE_IMPORT_CONFIG.replace(
                    f"{key}={expected}\n", "" if value is None else f"{key}={value}\n")
                import_path.write_text(config, encoding="utf-8")
                try:
                    check_texture_import(import_path)
                except AssertionError as error:
                    require(f"[params] {key} must be {expected}" in str(error),
                            f"invalid PNG import config did not report {key}")
                else:
                    raise AssertionError(f"PNG import check accepted {key}={value!r}")
    print("ANTILA_BUILDING_CHUNKS_SELF_TEST_OK: pair pruning, exact accessor payloads, external PNG, collision proxy and compressed mipmap import contract")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate generated chunks without writing")
    mode.add_argument("--self-test", action="store_true", help="run the synthetic assert self-check")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    stats = check() if args.check else generate()
    prefix = "ANTILA_BUILDING_CHUNKS_CHECK_OK" if args.check else "ANTILA_BUILDING_CHUNKS_PACKAGED"
    print(prefix + ": " + " ".join(f"{key}={value}" for key, value in stats.items()))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, KeyError, ValueError, struct.error) as error:
        print(f"ANTILA_BUILDING_CHUNKS_FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
