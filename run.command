#!/bin/sh
set -eu
cd "$(dirname "$0")"
GODOT_BIN="${GODOT_BIN:-/Applications/Godot_mono.app/Contents/MacOS/Godot}"
dotnet build --nologo -p:UseSharedCompilation=false
"$GODOT_BIN" --headless --editor --path "$PWD" --import --quit >/dev/null
exec "$GODOT_BIN" --path "$PWD" "$@"
