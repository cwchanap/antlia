"""Project the canonical cross-harbour data for the runtime loader."""
import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Data/cross-harbour.json"
TARGET = ROOT / "Data/cross-harbour-runtime.json"
EXCLUDED = {"surface_triangles", "ground_triangles", "water_triangles"}


def project(data):
    assert isinstance(data, dict), "Canonical harbour data must be a JSON object"
    assert EXCLUDED <= data.keys(), "Canonical harbour data is missing a runtime-excluded field"
    return {key: value for key, value in data.items() if key not in EXCLUDED}


def encode(data):
    return json.dumps(project(data), ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def check():
    assert TARGET.is_file(), f"Missing {TARGET}; run Tools/export_runtime_harbour.py"
    canonical = json.loads(SOURCE.read_bytes())
    runtime_bytes = TARGET.read_bytes()
    runtime = json.loads(runtime_bytes)
    assert set(canonical) - set(runtime) == EXCLUDED, "Runtime harbour must omit exactly the three triangle fields"
    assert runtime == project(canonical), "Runtime harbour fields differ from the canonical projection"
    assert runtime_bytes == encode(canonical).encode("utf-8"), "Runtime harbour export is stale or not compactly encoded"
    return len(runtime_bytes)


def generate():
    payload = encode(json.loads(SOURCE.read_bytes())).encode("utf-8")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=TARGET.parent, prefix=TARGET.name + ".", suffix=".part", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        temporary.replace(TARGET)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return len(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the runtime projection without writing")
    args = parser.parse_args()
    size = check() if args.check else generate()
    action = "CHECK_OK" if args.check else "EXPORTED"
    print(f"ANTILA_RUNTIME_HARBOUR_{action}: {size} bytes")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, OSError, ValueError) as error:
        print(f"ANTILA_RUNTIME_HARBOUR_FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
