# Startup memory and scenery placement — 30–31 October 2026

The earlier sections document the eager-world terrain and scenery fixes. The [building-streaming change](BUILDING_STREAMING.md) bounds detailed-building residency; the final combined-source startup measurement and verification are recorded below.

The 29 October native `just run` investigation reproduced a menu that had not appeared after three minutes. Scenery placement took 154.22 seconds and allocated 12.83 GiB cumulatively in C#. Terrain construction later raised the process's macOS physical footprint to 9.83 GiB before the diagnostic monitor stopped it. Those were bounded diagnostic runs, not an observed out-of-memory crash or a steady-state measurement. [Investigation](../evidence/startup-memory-investigation-2026-10-29/REPORT.md).

## Fix

Scenery clearance uses conservative spatial bounds to select nearby candidates before applying the existing exact geometry checks. Placement order and the seeded random sequence remain part of the contract: 1,271 trees, 4,523 lamps, 544 pedestrians and 138 kiosks. Clearance still accounts for already-placed scenery and the reserved recreation fixtures.

`RoadMap.CreateSurfaceMask` now bounds every RGB8 image to **192 MiB of base pixels**, approximately **256 MiB including mipmaps**, as well as the existing 16,384-pixel axis limit. The budget is the same as the existing recreation-mask contract. The current Nathan Road and recreation masks already fit; the large outer-map road/paving mask uses lower sampling density. World coordinates and physics geometry retain their existing interpretation. GPU texture copies and other world assets consume additional memory; this is an image budget, not a total-process limit.

The budgeted outer-map mask conservatively covers paving by half a texel diagonal so bilinear sampling retains both roadside strips. This can broaden its visible outer paving edge; asphalt geometry, physics, and the higher-density district/recreation masks are not rescaled by this change. Two real failing roadside locations are pinned in the isolated check, and the full suite retains its existing coverage thresholds.

Generated boxes now share a `BoxMesh` by exact size, matching the existing material-cache pattern. The 4,523 harbour lamps alone previously created 13,569 meshes at just three sizes. Each instance retains its own material override and transform; solid boxes keep their own collision shapes.

Building instantiation disposes its one-shot `PackedScene` wrappers, releases hidden render meshes after creating their physics shapes, and shares the three imported facade/shopfront texture families across districts. All 23 building GLBs embed the same three byte-identical PNGs; tints, UVs and material sampling stay on the existing materials. Collision nodes remain available for chunk parity, roof probes and reload checks.

The original terrain/scenery changes needed no dependency or government-data update. Building streaming later added derived chunk assets while retaining source GLBs for offline regeneration. Detailed building residency is now bounded around the bus; props, pedestrians, terrain masks and other world assets still load globally. See [building streaming](BUILDING_STREAMING.md) for the asset and residency details.

## Checks

```sh
./run.command --headless -- --surface-check
./run.command --headless --fixed-fps 60 -- --self-test
./run.command --headless -- --streaming-check
./run.command --headless -- --streaming-loader-check
./run.command -- --map-buffer-check             # native renderer only; do not use --headless
just run
```

`--surface-check` exits before constructing the world. It exercises the actual image generator with a large two-dimensional extract, thin horizontal/vertical extracts, distant road coordinates, and road/pavement/park samples, then checks shared box geometry, independent materials and collision dimensions. It fails with exit code 1 if the budget or placement is wrong. The full self-test also runs these checks, scenery filtering regressions, all existing terrain probes, and the driving suite.

The earlier fix's verification and startup measurements are recorded under `evidence/startup-fix-2026-10-30/`.

## Eager-world measurement before building streaming

Before building streaming, the normal `just run` recipe reached `ANTILA_READY` in **54.49 seconds**, including build/import. The monitor then allowed at least 20 seconds of menu rendering. On the same M1 Pro / 32 GiB system, that run reached a peak macOS physical footprint of **8,519.63 MiB**, with **8,053.16 MiB** at the idle menu. The largest road/paving mask changed from 16,384 × 12,861 (602.86 MiB base / 803.81 MiB with mipmaps) to 9,246 × 7,258 (under 192 MiB base / 256 MiB with mipmaps).

The older eager-world baseline was deliberately stopped before menu completion, so its 9.83 GiB footprint is a lower bound, not a comparable full-startup peak. These local observations are not a performance benchmark. See `shared-boxes-summary.json`, `shared-boxes-memory.csv` and `shared-boxes-vmmap.txt` for the earlier completed startup measurement.

## Earlier fix verification results

At that earlier source snapshot, the C# build had **0 warnings / 0 errors**. The full headless `--self-test` exited 0: 25 exploration/approach drives, 133,749 full-bus clearance queries, H1/H2/H3 (15 stops / 119 passengers), both side-street turns, and the original 1.08 km service all passed. Scenery totals remained 1,271 trees / 4,523 lamps / 544 pedestrians / 138 kiosks; terrain probes retained the original thresholds, including both previously failing paving locations.

The native `--building-check` exited 0, including 72 rendered play-boundary probes, final terrain/asphalt priority, shared textures, roof collision and footpath checks. A separate native eastern capture exited 0; all eight district/street/stop/map views were inspected. Prior capture files were preserved and restored after the new views were copied into this fix's evidence folder.

The headless `--restart-check` exited 0 after **nine reloads / ten validated world states**, each with 6,270 building mesh nodes and 3,135 collision shapes. The final code review has no outstanding findings. Its independent numeric check covered all 34,368 roadside paving probes with a minimum coverage of 0.978 (required greater than 0.9); this is separate from the actual engine checks.

`validation.json`, the per-gate result JSONs and their logs record these checks; C# SHA-256 values match the source used for the completed native startup measurement. All verification game copies are stopped. Direct desktop keyboard interaction was not checked because the Mac was locked; the real-physics input/route checks and native renderer/captures were completed.

## Final combined-source startup measurement

On the same M1 Pro / 32 GiB system, the final normal `just run` recipe reached `ANTILA_READY` in **42.44 seconds**. Peak process-tree physical footprint was **5,481.55 MiB (5.35 GiB)**; the live idle game measured **5,479.90 MiB (5.35 GiB)** after at least 20 seconds. The previous eager-world measurement was **8,519.63 MiB peak / 8,053.16 MiB idle**. Peak fell **35.66%** and idle fell **31.95%**. The below-4 GiB peak goal remains unmet; the 2–3 GiB steady-driving budget has not been demonstrated.

The run used the normal recipe with cached build/import. It rendered at the same 1280 × 800 native viewport in a temporary unfocused, always-on-top screen-edge position; a separate probe verified 20 natural draw frames and `can_draw=true`. The temporary override was removed and all verification game copies were stopped. This is a local observation, not a formal benchmark or a measurement in the ordinary foreground presentation. The monitor recorded the live idle snapshot and `vmmap`, then intentionally terminated the process with signal 15 (exit 143). Manual desktop keyboard play was not checked. See `evidence/building-streaming-2026-10-30/startup-comparison.json`, `startup-measured-final-result.json`, and `startup-measured-final-vmmap.txt`.

All seven final gates passed without engine errors. The final headless self-test completed 25 exploration/approach drives and 133,749 clearance probes, H1/H2/H3 (15 stops / 119 passengers), the original 1.08 km service and both side-street turns. The restart check passed nine reloads and ten validated states. Native building and map checks passed; all 19 final captures were reviewed. Build: **0 warnings / 0 errors**. Full records are in `evidence/building-streaming-2026-10-30/validation.json` and `REPORT.md`.

Functional-test final footprint samples can be taken during teardown, so they do not demonstrate steady-driving memory. Do not use them to infer the 2–3 GiB driving target.

## HUD map drawing and final verification

The minimap, expanded M map and route-select map simplify and cull only their drawn road-background linework. Polyline endpoints are preserved exactly, and simplified linework stays within **0.35 physical output pixel** of its source; viewport culling retains segments that can touch the padded canvas. Lines are batched by road class for `DrawMultiline`, and a viewport resize redraws the map canvases and refreshes their textures. RoadMap data, route geometry, collision and driving physics are unchanged. `Hud.MapGeometry.cs` owns the drawing geometry; `Main.MapChecks.cs` runs the geometry and native resize checks.

The native `--map-buffer-check` passed at the initial size and after resizing the window to **2880 × 1800**; map textures refreshed at the larger presentation scale. `RenderingServer` reported **220.2 MiB** of render buffers initially and **246.2 MiB** after resize. A previous red run reported **1,180.2 MiB**; its [result](../evidence/building-streaming-2026-10-30/map-red-result.json) is retained. The final check's [log](../evidence/building-streaming-2026-10-30/map-budget-final.log) and [result](../evidence/building-streaming-2026-10-30/map-budget-final-result.json) are also recorded. Render-buffer telemetry is separate from process physical footprint.
