# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Antila is a single-scene Godot 4.6 **.NET / C#** bus-driving prototype set in Tsim Sha Tsui / Jordan, Kowloon. Road alignments and building massing come from HK Government open data; everything else is authored. See `README.md` for the player-facing description and `docs/PLAN.md` for scope.

## Build, run, verify

```sh
./run.command                  # dotnet build → Godot asset import → launch
./run.command --headless -- --self-test    # full in-engine check suite; nonzero exit on failure
./run.command -- --capture                 # render evidence PNGs, then exit
```

`run.command` uses `GODOT_BIN`, defaulting to `/Applications/Godot_mono.app/Contents/MacOS/Godot`. **The plain `godot` on PATH is a non-Mono build and will not work.** Args after `--` are Godot *user* args, read via `OS.GetCmdlineUserArgs()`.

Godot user args (all defined in `Main._Ready`):

| Flag | Effect |
| --- | --- |
| `--self-test` | Everything: markings, buildings, footpaths, audio, regressions, signals, then a physically driven 1.08 km route through all three stops |
| `--road-check` / `--footpath-check` / `--building-check` / `--signal-check` | Early-exit subsets of the same `RunChecks` cascade — cheapest first |
| `--capture`, `--signal-capture`, `--audio-review` | Save rendered/recorded evidence, then quit |
| `--building-review`, `--footpath-review`, `--road-review` | Scenery capture sets; add `--before` to write `before-*` filenames |

There is no unit-test framework. `RunChecks` in `Scripts/Main.cs` **is** the test suite: it drives the real `BusController` through the real physics world and throws on failure. Add new checks there (or in the matching `Main.*.cs` partial) rather than introducing a test project. Checks print `ANTILA_*`-prefixed markers; `ANTILA_SELF_TEST_FAILED` accompanies exit code 1.

`python3 Tools/generate_audio.py --check-review` validates the recorded audio mix outside the engine.

## Architecture

**The scene is built entirely in code.** `Main.tscn` is a bare `Node3D` with one script attached; there are no other `.tscn` files, no editor-authored nodes, and no `[Export]` inspector wiring. `Main._Ready()` constructs the whole world in a fixed, order-dependent sequence:

```
RoadMap → PrepareParkEntrances → BuildEnvironment → BuildGovernmentBuildings → BuildStreet
→ BuildNeighborhoods → BuildStops → BuildTrafficLights → BuildRoads → BuildRoadDetails
→ BuildFootpaths → FinishStreetMeshes → BusController → Camera → BuildCab → Hud
```

Later stages read state accumulated by earlier ones (`_lots`, `_pavementPatches`, `_paint`, the terrain mask), so reordering these calls breaks placement. `FinishStreetMeshes` commits the batched `SurfaceTool` road paint — geometry added to `_paint` after it is lost.

`Main` is one `partial class` split by feature, all in `Scripts/`:

- `Main.cs` — lifecycle, terrain/street/neighborhood/stop construction, camera, service progression, captures, `RunChecks`
- `Main.Signals.cs` — `TrafficSignal`, `SignalAspect`, 48 approaches across 14 junctions
- `Main.RoadDetails.cs`, `Main.Footpaths.cs`, `Main.BuildingReview.cs`, `Main.AudioReview.cs`

Standalone types: `RoadMap` (plain C# class, not a Node), `BusController : CharacterBody3D`, `Hud : Control`.

**`RoadMap`** is the geometric authority. It parses `Data/nathan-road.json` at construction, joins same-name segments into polylines, and exposes the queries the rest of the build depends on: `At(distance, lane)`, `Forward`/`Heading`, `Project(position)`, `CanPaintLane`, `ClearOfRoads`, `LotClear`, `NearSideRoad`. It also generates the three-channel terrain surface mask (asphalt / paving / park) at 3 px per metre, consumed by `Assets/Materials/terrain.gdshader`. One blended terrain surface replaces stacked road meshes — do not add coplanar road geometry.

**Coordinates:** +X east, **−Z north**, 1 world unit = 1 metre, ground plane at Y = 0. Route positions are expressed as a distance along the H1 corridor plus a signed lane offset (the northbound driving lane is about −7.3).

**Physics layers:** layer 1 = world/static, layer 2 = bus. The bus is a kinematic `CharacterBody3D` with a bicycle steering model — no suspension or drivetrain sim.

`BusController` reports to `Main` through the `Notify` and `Moved` callbacks rather than signals, and exposes `AutomaticTest` / `TestThrottle` / `TestBrake` / `TestSteer` so checks can drive it physically. Input actions are registered programmatically in `Main.RegisterInput()`, not in `project.godot`.

Rendering is **GL Compatibility**, so avoid Forward+/Vulkan-only features.

`QuitGame()` forces `GC.Collect()` + `WaitForPendingFinalizers()` before `GetTree().Quit()`. This is a deliberate workaround for Godot 4.6 tearing down instance bindings while C# wrappers are still live — keep it.

## Asset and data pipeline

The game ships fully offline with **no Python, Shapely or network dependency at runtime**. Tools are regeneration-only:

- `Tools/import_map.py` (stdlib only) — TD `CENTERLINE.kmz` → `Data/roads.geojson` + `Data/nathan-road.json`
- `Tools/import_buildings.py` — needs `.venv-geodata` (`python3 -m venv .venv-geodata && .venv-geodata/bin/pip install -r Tools/requirements-geodata.txt`); CSDI footprints → `Data/building-layout.json`
- `Tools/model_*.py` / `import_passengers.py` — run **through Blender MCP**, not `python3`. Each creates its own isolated Blender scene, exports only its own objects to `Assets/Models/*.glb`, and restores the user's previous scene. Preserve that isolation in any new modeling script.

`Art/` holds editable `.blend` sources and is `.gdignore`d so Godot does not import them. `Art/Passengers/`, `Art/passengers.blend` and `Assets/Models/passenger_*` are git-excluded: the Renderpeople license permits game use but not asset redistribution.

Data files carry provenance (source URL, download timestamp, SHA-256, origin). Regenerating data means updating attribution in `README.md`, the relevant `docs/*.md` and the in-game HUD credit.

## Working conventions

- **Every change is verified in-engine and recorded.** `evidence/` holds the run logs and rendered PNGs referenced from `README.md` and `docs/`; `--*-review` flags with `--before` produce before/after pairs. `Art/before-*/` keeps prior asset states for comparison.
- Each feature area has a companion doc — `docs/TRAFFIC_LIGHTS.md`, `docs/GOVERNMENT_BUILDINGS.md`, `docs/FOOTPATH_POLISH.md`, `docs/ROAD_POLISH.md`, `docs/AUDIO_ASSETS.md`, `docs/DECORATION_ASSETS.md`, `docs/REALISM_ASSETS.md`, `docs/PASSENGER_ASSETS.md` — covering sources, exact generation prompts, approximations and check commands. Update the matching doc alongside code.
- C# is deliberately dense: compact one-line bodies, expression members, tuple lists as data tables, minimal spacing in the newer partials. `<Nullable>enable</Nullable>` is on; the codebase uses `= null!` for fields initialized in `_Ready`.
- Numeric constants in checks (231 map points, 1150 m, 437 sections, 26 passengers, 53 roof probes) are asserted, not incidental. Changing the data means updating those assertions.
- The build is expected to be **0 warnings / 0 errors**.
- Claims about the prototype stay honest: it is stylized, road widths/stops/traffic are authored, H1 is fictional, and no surveyed reconstruction or performance benchmark is claimed. Keep new documentation to that standard.
