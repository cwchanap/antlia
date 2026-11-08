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

The native `--map-buffer-check` passed at the initial size and after resizing the window to **2880 × 1800**; map textures refreshed at the larger presentation scale. `RenderingServer` reported **220.2 MiB** of buffers initially and **246.2 MiB** after resize. These are global mesh/canvas buffer counters for the whole scene, rather than a HUD-only allocation. A previous red run reported **1,180.2 MiB**; its [result](../evidence/building-streaming-2026-10-30/map-red-result.json) is retained. The final check's [log](../evidence/building-streaming-2026-10-30/map-budget-final.log) and [result](../evidence/building-streaming-2026-10-30/map-budget-final-result.json) are also recorded. These allocations overlap process physical footprint and must not be added to it.

## Follow-up — 31 October 2026

The Mong Kok builder now leaves recreation-texture creation to the immediately following eastern builder, which merges both datasets. This removes an unused 3,500 × 3,100 RGB image and its mipmaps (about 41.4 MiB of image payload), raster scratch data and upload work. A native comparison found all three final terrain images and every mip level byte-identical: 44 matching image/mip records. Steady renderer texture memory remained unchanged, as expected.

Fresh normal-recipe observations before/after this small cleanup measured 5,451.43 / 5,462.88 MiB peak and 4,201.86 / 4,238.88 MiB at the live idle menu. This does not demonstrate an overall process-memory reduction; the improvement is the avoided initialization work. The same native viewport and temporary screen-edge placement were used.

Managed-collection and macOS allocator-relief experiments were discarded: collection reduced the managed heap but did not reliably reduce startup peak, and native allocator relief returned zero bytes. No forced startup GC or platform-specific allocator code is retained. Larger gains should first target pre-baking the static terrain masks to avoid runtime raster buffers, then area-based terrain and prop residency. Savings from those changes have not been measured. Records are in `evidence/allocator-memory-2026-10-31/`.


## Baked terrain masks

Normal play uses lossless baked terrain data from `Assets/Textures/TerrainMasks/`, avoiding large managed raster buffers and repeated polygon/stroke work on every launch. Surface and harbour masks remain RGB PNG imports; the [7 November recreation follow-up](#sparse-recreation-mask--7-november-2026) stores occupied mask pages in a compact atlas. `RoadMap.CreateSurfaceMask` remains the sole generator; the existing builders supply the same ordered lots, pavement, park paths, roads and recreation triangles. World bounds, channels and source-image budgets are preserved. All terrain data remains resident; pages are not streamed.

The PNG import settings retain mipmaps, disable lossy compression and disable automatic 3D compression detection. `Data/terrain-masks.json` records each image's bounds, dimensions, format, mip count and full pixel/mip SHA-256. Ordinary startup checks bounds and dimensions without reading the large images back from the renderer. There is no runtime generation fallback.

When changing road/building/open-space data, mask inputs or rasterizer behavior, regenerate and verify with the Mono engine:

```sh
./run.command --headless -- --bake-terrain
./run.command --headless -- --terrain-mask-check
./run.command -- --building-check
```

The first command assembles the usual source geometry and writes all three canonical PNGs, metadata and the compact recreation derivative, then exits before bus/HUD construction. The next invocation imports the saved PNGs before the check runs. `--terrain-mask-check` regenerates the current expected images and checks exact RGB pixels, every mip level and world bounds against the imported assets, then exits. The full `--self-test` includes this asset comparison and the sparse recreation CPU round-trip/binding checks. The native filtering gate is a separate `--sparse-recreation-check` invocation. `--surface-check` continues to test the synthetic rasterizer cases independently. Regeneration and checking need only the existing C# build and Godot; no Python or network dependency is added to play.


### Local measurements — 31 October 2026

Two normal-recipe comparisons used the same 1280 × 800 native viewport and temporary unfocused screen-edge placement. Each recorded a live menu snapshot after at least 20 seconds, then intentionally terminated the game (exit 143). The first optimized sample used the direct-load prototype; the second used the final bounds/metadata-validated loader.

| Sample | Ready, seconds | Peak physical footprint, MiB | Live menu, MiB |
| --- | ---: | ---: | ---: |
| Runtime generation, first | 48.59 | 4,827.02 | 4,448.35 |
| Saved textures, prototype | 36.19 | 4,826.49 | 4,014.57 |
| Runtime generation, repeat | 45.52 | 4,922.18 | 4,375.64 |
| Saved textures, final loader | 40.06 | 4,635.47 | 4,014.52 |

Menu physical footprint fell by **361–434 MiB (8.25–9.75%)**. Startup peak improvement ranged from negligible to about 287 MiB, so these observations do not establish a consistent large peak reduction. The below-4 GiB peak goal remains unmet. Renderer texture telemetry stays at 888,412,266 bytes: the terrain remains resident, and the saving comes from avoiding runtime generation work and buffers. The three source PNGs total 3,684,289 bytes (3.51 MiB), with derived import caches stored separately.

These are local observations, not a formal benchmark, steady-driving measurement or ordinary foreground/manual-play result. Detailed process-tree samples, live `vmmap` snapshots and ready times are in `evidence/prebaked-terrain-2026-10-31/startup-comparison.json`. Functional checks allocate image references/readbacks and must not be used as normal-play memory measurements.

The checker validates the full CPU image/mip digest against metadata, then compares fresh and imported textures through the same rendering backend. Native readback differs from CPU bytes at mip level 1; using a fresh reference upload preserves an exact comparison without a tolerance. The original and imported native textures matched in all 44 image/mip records, including every base pixel.

Final verification passed all six functional gates: headless generation, headless and native exact asset checks, the native image/mip proof, native building/terrain checks, and nine headless reloads restoring ten validated world states. The native check passed 985 roof and 72 rendered boundary probes, park coverage and footpaths. The final C# build has 0 warnings / 0 errors, functional engine logs have no warnings/errors, and all 36 recorded runtime input/DLL hashes stayed unchanged. Missing metadata, changed bounds, a stale digest and a one-pixel PNG change each produced the expected exit 1; original files were restored. A fresh code review and independent measurement/prose check found no actionable issues. Full driving, manual keyboard play and export packaging were not rerun. See the [trial report](../evidence/prebaked-terrain-2026-10-31/REPORT.md) and [validation record](../evidence/prebaked-terrain-2026-10-31/validation.json).

## Resource cleanup and allocation trace — 31 October–1 November 2026

The carriageway index used to fit scheduled routes is released after `LoadRoutes`; its measured backing-array capacity was **75.85 MiB**, plus containers. The Wong Tai Sin geometry check rebuilds and releases its own temporary index. Fitted lanes remain on the route paths. This removes retained managed references without adding forced collection or platform-specific allocator calls.

Godot skips the already-hidden, non-colliding harbour `RoadSurface` during import. A shared scene post-import hook also redirects eight albedo references in five models to the byte-identical canonical bark, leaf, pavement and asphalt PNGs. Tints, UVs, sampling and other material parameters stay on the imported materials. The GLBs, PNGs and Blender sources are unchanged; the saved imported scenes refer directly to the canonical textures. `CheckAssetDetails`, reached by `--building-check` and `--self-test`, checks the absent mesh and shared texture paths/identities.

Native renderer counters fell by **39.98 MiB of textures** and **31.61 MiB of buffers**, **71.59 MiB combined**. These are confirmed resource allocations within the process budget. The index capacity, engine counters and OS physical footprint overlap and cannot be added into a total RAM saving; managed garbage collection and native allocator retention also affect when memory returns to the OS.

Allocation/free histories identify large empty-labelled native heap regions previously used for WebP terrain decoding, decoded mip data, OpenGL uploads and temporary JSON strings. A separate **280.5 MiB** live allocation group matches Godot's retained renderer instance-pair pages. Their growth can be triggered by flushing queued scene updates during a node free; it is not the size of the three tiny footpath templates themselves. Terrain residency, decoder scratch, UTF-8 JSON loading and renderer pairing remain further candidates, with no additional change shipped here. See the [breakdown](../evidence/memory-breakdown-2026-10-31/REPORT.md), [cleanup trace and results](../evidence/memory-cleanups-2026-10-31/REPORT.md) and [validation record](../evidence/memory-cleanups-2026-10-31/validation.json).

The full headless self-test passed with 25 exploration/approach drives, 133,749 clearance queries, H1/H2/H3 (15 stops / 119 passengers) and the original 1.08 km service. This includes the cache-release assertion after the Wong Tai Sin check's temporary rebuild. The native building check passed 985 roof and 72 rendered boundary probes, shared-texture identity and footpath checks; seven native footpath captures were reviewed. All four final functional gates exited 0 without engine warnings/errors. C# builds had 0 warnings / 0 errors, and the fresh code/evidence review has no outstanding findings. Export packaging, manual keyboard play and steady-driving memory were not checked.

Two final normal launches measured **4,160.46 / 3,945.69 MiB** at the live menu and **4,809.97 / 4,785.85 MiB** peak process-tree footprint. The fresh baseline was **5,715.99 MiB** at the menu, but older unchanged launches were already about 3.9–4.9 GiB. Much of the spread tracks empty-labelled native heap regions, so the full observed difference is not a proven saving from these small resource changes. Final peaks remain about 4.7 GiB; the below-4 GiB peak target is unmet. These local observations use the same temporary screen-edge viewport and are not steady-driving measurements or a formal benchmark.


## Renderer allocations during construction — 7 November 2026

The three off-tree footpath templates now use `QueueFree()` after their meshes are assigned to the existing MultiMesh batches. Immediate `Free()` flushed global renderer updates during world construction. Deferring their deletion lets SceneTree flush pending transforms first and avoids about **281 MiB of retained native allocations** in the instrumented menu runs. The three templates are deleted at the end of the frame; their meshes remain owned by the MultiMesh resources.

H2/H3 replays also initialize the bus directly at the remembered service’s route start. The former H1-first reset could load and immediately evict a detailed chunk before `BuildScene` returned, triggering a similar renderer flush. The later `BeginRoute` still performs the normal trip setup. Building eviction and synchronous collision preparation retain their existing behavior.

Four fresh native runs used Mono Godot 4.6.2, the same imported assets and 1280 × 800 viewport, and the same temporary unfocused screen-edge placement. Baseline runs measured **814.22 / 814.31 MiB** on the native allocation counter; deferred-deletion runs measured **533.66 / 533.29 MiB**. All retained the same **846,491,906 texture bytes**, **199,917,220 buffer bytes** and **52,572 scene nodes**. A local 650 MiB native-allocation diagnostic failed before the change and passed afterward; it is not a portable process-memory limit.

Live menu physical footprints were **3,945.49 / 3,945.16 MiB** before and **3,639.08 / 3,630.97 MiB** afterward, about **306–315 MiB lower** in these observations. Sampled whole-run peaks were **4,836.63 / 4,716.00 MiB** before and **4,684.46 / 4,414.83 MiB** afterward. These direct native runs use cached build/import; peaks are sampled with gaps for `vmmap`, and capture work follows the menu snapshot. Earlier unchanged launches varied substantially, so these are local observations rather than a general RAM-saving guarantee or a `just run` benchmark. The below-4 GiB peak goal remains unmet in these samples.

The normal tunnel captures retain the earlier small brightness differences: four of six views are exact, one differs by at most 1/255 per channel and one by at most 10/255. The Compatibility renderer truncates insertion-ordered per-mesh light lists. Immediate deletion and deferred deletion produce different pairing histories. A diagnostic reset of all 123 existing lights after construction makes all six baseline/candidate captures exact, supporting pairing order as the explanation. The reset is not part of the game; light configuration and scene construction order stay as authored. The exact lamps responsible for the original pixel differences were not instrumented.

See [startup measurements](../evidence/template-lifecycle-2026-11-07/startup-measurements.json), [normal captures](../evidence/template-lifecycle-2026-11-07/normal-comparison.json), [normalized control](../evidence/template-lifecycle-2026-11-07/normalized-comparison.json) and the [investigation hypothesis](../evidence/template-lifecycle-2026-11-07/HYPOTHESIS.md). The final native lifecycle probe physically drove H3 for **3,385 m**, served **four stops / 33 passengers**, reached **−32 m**, and recorded **6,242 naturally drawn frames**, with no contacts or red-light violations. H3 and H2 scene replays restored a fresh active service at the matching route start. Native counters remained **549.03 / 550.58 MiB** after those replays; the template-only experiment had returned to **810.23 MiB** on H3 replay. Post-reload tunnel lighting/daylight and pavement/park-collision checks passed.

The matched H3 samples measured **4,104.57 / 4,002.27 / 3,986.58 MiB** at roughly 0.9 / 2.1 / 3.2 km before and **3,803.14 / 3,674.93 / 3,680.79 MiB** after, about **301–327 MiB lower** in this pair. The completed-drive samples were **3,991.80 / 3,683.55 MiB**, and H3 replay samples **4,260.22 / 3,920.02 MiB**. These are live process observations from one drive per source variant, not a formal benchmark. The later H2 replay reached **4,194.75 MiB**, and the final drive-plus-two-reloads sequence sampled a **4,903.91 MiB** peak. Native allocation improvements therefore do not establish a sub-4 GiB lifecycle peak or the 2–3 GiB driving target.

See [lifecycle measurements](../evidence/template-lifecycle-2026-11-07/lifecycle-measurements.json) and [physical comparison](../evidence/template-lifecycle-2026-11-07/physical-comparison.json). The temporary diagnostics were removed; the production build passed with zero warnings/errors. The final full headless `--self-test` exited 0 in **1,080.54 seconds**, covering 25 exploration drives, 133,749 clearance queries, H1/H2/H3 (15 stops / 119 passengers), both side-street turns and the original 1.08 km service. It used fixed physics timing with the headless render loop disabled; native rendering was verified by the separate lifecycle/capture probes. The early `--terrain-mask-check` exited 0 in **38.72 seconds**, including queued-template shutdown before bus construction. All nine game runs had no engine warnings/errors, and code/evidence reviews had no actionable findings. The [validation record](../evidence/template-lifecycle-2026-11-07/validation.json) also confirms unchanged runtime data/import inputs and cleanup. Export packaging, manual keyboard play and longer reload stress were not checked.


## Runtime harbour data — 7 November 2026

`BuildHarbour` now reads the compact runtime harbour export instead of parsing three offline-only triangle arrays. The canonical authoring file remains byte-identical. The derivative preserves all other fields, including source provenance, and is regenerated by `Tools/export_runtime_harbour.py` or the existing tunnel importer. [Regeneration and data-equivalence checks](CROSS_HARBOUR.md#runtime-data-export--7-november-2026).

The input falls from **41,118,951 to 5,685,005 bytes (86.17%)**. This avoids unused parsing/string work; it does not reduce the authoritative road arrays or the resident terrain/GLB payload. The full canonical comparison runs only for the explicit data check or self-test.

A controlled native pair used the same cached imports, 1280 × 800 viewport and H3 drive/reload harness. Automatic rendering was disabled and the harness manually drew every process frame without swapping buffers, avoiding macOS occlusion pauses. Completed manual draws increased **1,704 → 8,187 → 9,507** before and **1,750 → 8,936 → 10,338** afterward; both reported **1,380 / 2,439 / 4,925** draw calls at menu, drive completion and reload. These are local manually rendered observations, not ordinary foreground play or a `just run` benchmark.

Startup cumulative managed allocation fell from **1,666,195,192 to 1,528,140,544 bytes**, **131.66 MiB less allocation traffic**. This is not a retained-RAM saving. Texture/buffer, node and detailed-chunk counts matched at all three checkpoints. The initial renderer counters remained **846,491,906 texture bytes**, **199,917,220 buffer bytes** and **52,572 nodes**.

| Physical footprint, MiB | Canonical loader | Runtime loader |
| --- | ---: | ---: |
| Live menu | 3,623.75 | 3,691.72 |
| Completed H3 drive | 3,672.79 | 3,720.10 |
| After H3 reload | 3,641.68 | 3,722.77 |
| Sampled whole-lifecycle peak | 4,511.74 | 4,740.43 |

**Overall RAM reduction is not demonstrated.** The candidate's matched physical samples were higher, despite lower startup allocation traffic. Earlier unchanged baseline menu observations varied from **3,647.63 to 5,193.29 MiB**. The original drive pair also had unequal natural rendering activity, so its lower candidate samples cannot support a memory-saving claim. The retained heap, engine counters and OS footprint overlap and must not be added together. Peaks are sampled every 0.2 seconds with gaps for `vmmap`; the below-4 GiB peak target remains unmet.

The engine data check confirms all **26 retained fields** match. Missing output, changed retained values and extra authoring fields fail with exit 1; normal startup fails clearly when the runtime file is missing even while canonical data is present. Standalone export/check/recovery regressions pass. The tunnel importer can import the shared exporter; full geodata regeneration was not run.

Both native H3 drive/reload probes passed **3,385 m**, four stops and 33 passengers with no contacts or red-light violations, plus post-reload tunnel lighting/daylight and footpath checks. Five of six normal tunnel views are exact; the sixth differs in **134 pixels**, at most **1/255** per channel. A PCK smoke check loaded the normal world with both loose JSON files absent and verified the packed runtime hash. This does not validate a complete exported executable.

The final production build has **0 warnings / 0 errors**. The full headless `--self-test` exited 0 in **1,151.48 seconds**, covering 25 exploration/approach drives, 133,749 clearance queries, H1/H2/H3 (15 stops / 119 passengers), both side-street turns and the original 1.08 km service. Headless-only render skips are recorded in the log; native tunnel views and lifecycle checks are separate above. All six completed native probe/capture runs and the full suite have no engine warnings/errors. Nine recorded source/data/DLL hashes stayed unchanged, canonical data still matches Git HEAD, and temporary game diagnostics, window settings and the owned test process were cleaned up. Code/evidence reviews found no outstanding issues. Full geodata regeneration was not checked; subsequent native/export and keyboard verification follows below.

Measurements and raw logs are recorded in [the trial report](../evidence/runtime-harbour-2026-11-07/REPORT.md), [measurement record](../evidence/runtime-harbour-2026-11-07/measurements.json) and [validation record](../evidence/runtime-harbour-2026-11-07/validation.json).

### Native and standalone follow-up

The source game's native `--building-check` passed in **123.07 seconds**, including 985 roof probes and the 72 rendered terrain-edge probes skipped by headless checks. A local universal macOS .NET export then passed packed harbour-data equivalence, building streaming with six teleports, the native building/render check and a filtered H3 service drive (**3,385 m, four stops, 33 passengers**, no contacts or red-light violations). The exported app ran from `/private/tmp` without a source-project path argument. Its isolated terrain-check PNG is byte-identical to the source game's. All completed automated data, streaming, building and route checks have no engine warnings/errors.

The export used verified official 4.6.2 Mono templates, a temporary solution/preset and a temporary ETC2/ASTC import setting required by the Apple Silicon exporter. Apple's signing tool corrected malformed DER entitlements emitted by Godot's built-in signer; the original four .NET entitlements were preserved. The app starts successfully and passes final deep/strict signature verification. This validates a local development export; distribution/notarization was not tested. All nine recorded production hashes and 3,328 import metadata files remain unchanged, and temporary project files/settings are removed.

After the user unlocked the Mac, the standalone app passed a native keyboard smoke check with a visible always-on-top test window: H3 selection/briefing/start, acceleration, braking to zero, cab camera, doors, map, pause, a fresh H3 restart and clean quit. An earlier background/non-top window remained on its splash image under automation despite world readiness; that behavior was not isolated or fixed. The visible source-engine probe recorded 5,022 naturally drawn frames with drawing enabled. The keyboard run's initial F12 save failed because the export omits its evidence directory; preparing the output folder allowed captures, which were archived and removed from the app before final signature verification. No project window preference was changed.

These functional runs do not establish a new memory result. Full human route driving and distribution/notarization remain unchecked. See the [follow-up report](../evidence/runtime-harbour-2026-11-07/followup/REPORT.md) and [validation record](../evidence/runtime-harbour-2026-11-07/followup/validation.json).


### Ordinary foreground window check

Two subsequent source-game probes ran without always-on-top or forced redraw. Drawn frames advanced **24 → 76** and **59 → 225**, with rendering enabled throughout. Hidden/unfocused samples generally reported `can_draw=false`; a focused/drawable state was observed in each run. Native keyboard input selected H3 in the ordinary foreground route menu. No game window/focus policy was changed: normal drawing is demonstrated, while the exact historical exported background-window cause remains unproven. See [window-state evidence](../evidence/window-startup-2026-11-07/REPORT.md).


## Sparse recreation mask — 7 November 2026

The canonical 8,192 × 7,664 RGB8 recreation mask retains all 14 authored mip levels and its original world bounds. Normal play replaces its 239.499 MiB dense pixel/mip payload with 196 occupied 128-pixel pages. Every stored page has a one-texel gutter copied from its original global mip; absent pages are exactly zero. A 2,048 × 2,048 mipless atlas and nearest-filtered lookup preserve the original NPOT mip dimensions. The power-of-two backing avoids additional coordinate rounding at page seams. The three compact textures total **12,672,828 decoded bytes (12.09 MiB)**, including the LOD helper, and remain globally resident.

Native filtering on this Mac does not use the continuous blend weights of the initial manual sampler. A 65,532-byte RGBA8 helper encodes each mip number as a four-bit Gray code. Its per-mip colors are constant, so implicit sampling with the original texel footprint exposes the native integer levels and blend weight without a device-specific rounding rule. Zero-weight upper mips are not sampled. The native gate compares against the original imported texture at a channel-error threshold of 1/255, including integer/fractional transitions, occupied seams, borders, Y-dominant and rotated views, and tilted perspective. The authored CPU chain is used as the byte authority because native readback of mip 1 differs from shader sampling on this Mac.

`Data/sparse-recreation.json` records schema/source bounds, image and source-JSON SHA-256 digests, per-mip page layout, decoded payload and hashes of the three binary resources. Startup validates the source linkage, layout, resource hashes and the 32 MiB payload cap before binding the material. Missing, stale or corrupt resources fail clearly; normal play does not generate a dense reference. The canonical source PNG remains available for authoring, while bake/check paths reuse the same C# generator and bundled JSON so checks also work in an exported PCK.

```sh
./run.command --headless -- --sparse-recreation-bake
./run.command -- --sparse-recreation-check
./run.command --headless -- --terrain-mask-check
```

The first command refreshes only the sparse derivative. The full `--bake-terrain` workflow also refreshes it. The native checker saves its paired captures under `user://sparse-recreation-check/` and prints the resolved directory, allowing export checks without writing into the signed app. CPU image/page checks run in `--terrain-mask-check` and `--self-test`; native filtering is checked separately.

Measurements and validation are recorded in `evidence/sparse-filtering-2026-11-07/`. Functional image checks allocate dense references and are separate from normal-play memory measurements. The visible, unfocused window uses the ordinary render loop at 1,280 × 800, temporary always-on-top placement, and the same automated H3/reload sequence. All measured frames reported drawable windows and nonzero draw calls. The H3 driver uses 4× simulation time; frame intervals are observations between engine-drawn frames, not hardware GPU timings.

| Physical-footprint checkpoint | Dense baseline, MiB | Sparse integration, MiB |
| --- | ---: | ---: |
| Menu | 3,592.13 | 3,472.78 |
| Completed H3 | 3,740.21 | 3,431.60 |
| After reload | 4,971.60 | 4,550.83 |
| Sampled lifecycle peak | 5,482.79 | 4,570.91 |

In this local pair, the integration was 119 MiB lower at the menu, 309 MiB lower after H3 and 421 MiB lower after reload. The sampled peak was 912 MiB lower; **the below-4 GiB peak goal remains unmet**. H3 median frame interval changed from 13.484 to 14.122 ms, and p95 from 28.740 to 30.696 ms. Menu/reload medians changed from 12.874/21.051 to 13.601/21.389 ms. These observations show a small rendering cost, not a frame-rate improvement or a formal cross-device benchmark; see `production-comparison.json` and raw phase samples.

Allocator retention makes exact RAM savings variable. An earlier sparse run held more memory at its first menu checkpoint, then released about 1.1 GiB while texture/buffer counts stayed stable. Matched menu holds identified the changing charge as `MALLOC_LARGE (empty)` mappings, not growing graphics residency. In the repeated hold the sparse game settled near 3.21 GiB, but baseline retained-empty regions differed substantially between runs. Do not generalize an individual checkpoint or add renderer counters to physical footprint. See `menu-retention-comparison.json` and the timed `vmmap` snapshots.

The final source and standalone native checks each passed **83,710,983 exact authored mip pixels** and **214,433,792 GPU comparisons**. Standalone captures are byte-identical to the source check, and the packed harbour-data check passes. The local universal macOS .NET export ran from `/private/tmp` without a source-project path and completed the filtered H3 route: **3,385 m, four stops, 33 passengers**, no contacts, red-light violations, engine warnings or errors. Its supported `--print-fps` output reported 38–97 project-loop FPS (median 69 across 108 one-second observations); this is not a paired frame-time or hardware GPU benchmark. The sampled standalone peak was **4,172.71 MiB**, still above 4 GiB. The exported player does not support the external `--script` timing probe, so that interrupted attempt is excluded.

The full terrain bake regenerated the derivative while preserving all seven canonical PNG/import/manifest files byte-for-byte. The terrain-mask check passes, and invalid schema, source linkage and atlas hashes each fail with exit 1. All 3,328 import metadata files and temporary export settings were restored. The local app uses the same four .NET entitlements as the previous export, with Apple's ad-hoc signature and final deep/strict verification. Cross-GPU filtering, manual driving and distribution/notarization were not checked for this change.

The final build has **0 warnings / 0 errors**. The complete fixed-60 headless `--self-test` exited 0 in **1,052.17 seconds**, including 25 regional/approach drives, 133,749 bus-envelope queries, H1/H2/H3 (15 stops / 119 passengers), both side-street turns and the original 1.08 km service. Headless terrain-edge render skips remain recorded separately from the native comparison and normal-window lifecycle checks above. The suite has no engine warnings or errors. Final validation confirms all 11 recorded runtime input hashes, seven canonical mask files and 3,328 import metadata files are unchanged, with temporary diagnostics/settings removed. Code and evidence reviews found no outstanding issues. See `evidence/sparse-filtering-2026-11-07/validation.json` and `REPORT.md`.
