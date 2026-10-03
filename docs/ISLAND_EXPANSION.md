# Wan Chai / Causeway Bay expansion — 20 September 2026

The island district now spans 2.35 km east–west and 1 km north–south: an authored land area of 2.35 km², compared with the previous 1.02 × 0.79 km apron. The complete map bounds are about 3.14 × 3.55 km. Press **I while stopped** to start island free drive, **T** for the original tunnel approach, **M** for the map and **R** to return to H1. Island free drive is exploration, without additional passenger-service stops or turn-by-turn navigation.

## Road and building sources

The [Transport Department centreline KMZ](https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz) supplies the added road alignments. Its SHA-256 remains `936df4f37875a530d7862862ec5646e6ab2a5b7ef498d081084f9e4750c0ac1b`, matching the existing tunnel source snapshot. `Tools/import_tunnel.py` selects ground-level named streets and the explicit scenic-route connectors, then removes disconnected candidate components. It adds **429 source sections**, about **28.52 km of centreline geometry**, including parallel carriageways and junction branches. The complete crossing dataset has 478 sections. The original 49 sections, three trips and both tube definitions retain their coordinates and profiles exactly.

The added streets cover Wan Chai, Lockhart Road, Jaffe Road, Hennessy Road and the Causeway Bay / Yee Wo Street corridor. A fourth, 9.208 km scenic test trip connects the tunnel exit to both sides of the enlarged district and back to the original return connection. Source digitisation direction is followed; reversed sections are explicitly marked and must permit two-way travel. Source coordinates remain at one game metre per real metre. Widths, flat surface levels, land apron and shoreline remain authored; this does not reproduce every turn restriction, elevated road, tram line or junction control.

Building footprints and height datums come from the [Lands Department CSDI layer](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637211194312_35158/MapServer/0). The expanded WGS84 query bounds are `114.16940732297998,22.27613546532519,114.19222329297013,22.2851185770751`. Retrieved `2026-09-21T01:02:15.092513+00:00`; the independent count and unique record count both equal **2,048**. Raw SHA-256: `e658083b4319940a717131658ee019d12ad593c28c6631e3fa7508a841d3b3ad`.

The existing importer derives **2,180 island parts** from 1,996 retained source IDs, in 148 render/collision chunks. It preserves courtyard holes and relative height datums, clips clearances around selected streets, and fills 233 small paving gaps. There are 122 source records using the established height fallback. Combined with Kowloon: **3,944 parts, 279 chunks, 1,340,938 m² footprint coverage and 461 paving patches**, with heights up to 376.8 m. Generic facade artwork remains separate from the government geometry.

## Street detail

The expanded island has 122 trees, 170 lamp posts, 64 posed pedestrians and 18 news kiosks, plus planters, benches, street-name boards and the extended promenade. Placement rejects roads, building bounds and nearby props. People are decorative and do not board the H1 bus. Kiosks have collision bodies; smaller details retain the prototype's simplified collision treatment. Detail meshes stop rendering at 350 m, pedestrians at 100 m.

The driving HUD exposes the I shortcut, keeps the data credit clear of the controls and removes the old speed/gear overlay that duplicated the live cab instruments.

Blender MCP generated a compact street-tree variant from the existing bark/leaf materials and a news kiosk with shelves, a counter, canopy supports, striped roof and sign. Editable sources are in `Art/island-street-details.blend`; exports are `Assets/Models/street-tree.glb` and `Assets/Models/news-kiosk.glb`. The original user scene is restored after every model run. The built-in image-generation tool produced `Assets/Textures/kiosk-display.png` with this prompt:

> Use case: photorealistic-natural. Asset type: albedo texture for a small Hong Kong street news kiosk in a Godot bus driving simulator. Create one rectangular landscape image, 3:2 aspect ratio, an orthographic straight-on close-up of a densely stocked newspaper and magazine rack only. Three shallow horizontal shelves filled edge-to-edge with folded Chinese newspapers and colourful travel, gardening, food and general-interest magazines; worn off-white paper edges, muted red blue yellow magazine covers, fine realistic print-like detail with no readable headlines or named publications. Flat diffuse daylight, neutral exposure, no perspective, no cast shadows, no glossy baked highlights. No kiosk roof, no people, no street background, no logos, no watermarks, no frame. The artwork fills the entire canvas and will be mapped onto a 2.4 metre wide display.

## Regeneration and checks

```sh
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-centerline.kmz
.venv-geodata/bin/python Tools/import_buildings.py --island --download
# Later offline building regeneration omits --download.
# Through Blender MCP: Tools/model_tunnel.py;
# Tools/model_government_buildings.py with ISLAND=True;
# Tools/model_assets.py with ONLY_STREET_DETAIL=True.
./run.command --headless -- --self-test
./run.command --headless -- --island-check # focused scenic driving and crossing geometry checks
```

A narrow footprint spur exposed a roof-probe rounding problem in the larger extract. The importer now chooses a more interior point when boundary clearance is below 10 cm, and asserts that the rounded point remains inside the footprint. The real engine roof-ray test caught this before correction; the failure is retained in `evidence/island-expansion-2026-09-20/self-test.log`.

The new scenic route includes an approximately 80-degree Gloucester Road–Cannon Street turn. Its automatic test driver uses a roughly 12 m target lookahead and the left-side lane offset, anticipating the bend with the existing bicycle steering model. The original no-contact and 8 m route-deviation assertions remain in place. The earlier late-turn failure is retained in `self-test-final.log`.

Current checks cover 1,043 asphalt/pavement samples, 230 portal wall rays, 8,358 crossing/street bus-envelope probes, the original route checks and the new scenic drive. The island shortcut shares the stopped/map/pause guards with tunnel free drive. Final verification and rendered evidence are recorded below. Before-state data and models are saved under `Art/before-island-expansion-2026-09-20/`.

## Verification and rendered evidence

- The C# build completes with **0 warnings / 0 errors** on Godot 4.6.2 .NET / .NET 8.
- `evidence/island-expansion-2026-09-20/self-test-latest.log`: full suite exits 0 with `ANTILA_SELF_TEST_OK`. All building, asset, footpath, audio, map/camera and 14-junction signal checks pass. The ramp (218 m), exit bend (621 m), southbound crossing (2,933 m), original island loop (1,442 m), northbound crossing (3,721 m) and scenic drive (9,165 m) complete without contacts. Both tube drives reach −32 m. Haiphong Road (366 m), Granville Road (789 m) and H1 (1.08 km, three stops, 26 passengers) complete without unintended contacts; the separate boundary-impact test deliberately records a contact.
- `evidence/island-expansion-2026-09-20/island-drive-check.log`: focused check exits 0. The bus physically covers 9,164 m of the 9,208 m centreline itinerary, with no contacts or route departures; cornering and lane offsets account for the distance difference. The run also checks the shortcut guards, surface coverage, tunnel walls and bus envelopes.
- `evidence/island-expansion-2026-09-20/data-check.json`: the original 49 road sections, three trips and tube definitions are unchanged. Position/index streams for all 12 original tube floor/wall/ceiling/ledge meshes match the saved before-state, and the island source hash matches its layout metadata.
- `evidence/island-expansion-2026-09-20/capture-final.log`: native GL Compatibility rendering exits 0, with 17 PNGs covering both expanded districts, four street views, waterfront vegetation, three kiosks, a pedestrian, cab, HUD and full map. The [comparison page](../evidence/island-expansion-2026-09-20/compare.html) includes two matching-camera before/after pairs.

These checks use the real bus controller and collision world. Captures use the engine input-event path for I; physical keyboard input and performance benchmarks are outside this pass. Widths, ground levels, facade styles and the rectangular shoreline remain authored approximations.


## HUD review fixes — 21 September 2026 UTC

The expansion review found two HUD regressions: every frame resubmitted thousands of unchanged road strokes, and Nathan Road's lateral projection could display an oncoming-lane warning on correctly driven island streets.

`Hud` now renders the static Kowloon, island and tunnel road strokes into two transparent Godot `SubViewport` textures, one per map size. Each renders once and refreshes when its pixel dimensions change. Street labels, H1 progress/stops and the bus position/heading continue to draw live above the texture. The current-street search runs at most once per HUD draw. No map geometry, road scale or driving behavior changes.

The oncoming warning now requires the bus to be within 12 m of the bounded Nathan Road corridor in 3D, in addition to the existing lane and junction conditions. This prevents false warnings on Lockhart Road, Gloucester Road, beyond either corridor endpoint and deep below the surface, whether or not island free drive was selected. The existing warning remains a Nathan Road aid; it does not infer directional lanes throughout the island network.

```sh
./run.command --headless -- --hud-check
# Native rendered checks and local timing samples:
./run.command --disable-vsync --script evidence/hud-fixes-2026-09-21/hud-review.gd
./run.command --disable-vsync --script evidence/hud-fixes-2026-09-21/lane-warning.gd
./run.command --disable-vsync --script evidence/hud-fixes-2026-09-21/map-motion.gd
```

The focused C# check also runs inside the full self-test. It checks both reproduced island poses in both drive modes, a valid Nathan Road warning, correct-side driving, junction turns, tunnel depth and both corridor ends, followed by the existing map/pause, camera and taxi regression checks. The focused run passes with **0 build warnings / 0 errors**; the long driving suite was not repeated for these HUD-only changes.

Using the same stationary island cab, 1280 × 800 GL Compatibility renderer and M1 Pro as the review, two ordinary-render samples fell from median **36.044 / 35.805 ms** to **12.700 / 12.696 ms**. The after p95 values were 16.763 / 17.348 ms. Samples use 15 warm-up frames and 90 measured frames; these are local diagnostics, not a sustained or cross-device performance benchmark. Logs, harnesses and a [before/after comparison](../evidence/hud-fixes-2026-09-21/compare.html) are in `evidence/hud-fixes-2026-09-21/`.

Native verification also exits 0:

- `hud-runtime.log`: I shortcut, map-open driving lock and paused-shortcut guards; matching minimap/full-map captures.
- `lane-warning.log`: rendered Lockhart and Gloucester poses no longer warn; the Nathan Road control still displays the warning.
- `map-motion.log`: pixel checks find the bus marker at each new position and confirm the old marker clears on both maps; resize captures at 1024 × 640 retain marker alignment and road detail. Map close/resume and a map opened during an existing pause also pass.


## Driving guidance follow-up — 21 September 2026 UTC

The second HUD review found two remaining assumptions in the original H1 guidance. The lane warning treated the east carriageway as oncoming regardless of heading, and the service panel still used an unbounded lateral strip to decide whether to show stop distance. A bus on Lockhart Road could therefore see “55 m” to Middle Road despite being 1.92 km away.

The lane warning now compares the bus heading with the local Nathan Road tangent. Northbound traffic warns on the eastern carriageway; southbound traffic warns on the western carriageway. Headings more than 60 degrees from either road direction suppress the directional warning while turning. The existing centreline dead zone, junction exclusions and 12 m physical-corridor limit remain. This uses bus orientation, so briefly reversing for a manoeuvre does not switch its expected carriageway.

Both guidance paths share the same bounded, 3D corridor-distance query. The service panel uses its existing 20 m exploration margin with that physical distance, displaying **Exploring · M map / I island / T tunnel** when away from the corridor. It no longer presents along-route distance or missed-stop instructions from remote island positions. H1 approach distance, stopped/open-door boarding messages and missed-stop guidance remain live.

Verification:

- `evidence/guidance-fixes-2026-09-21/red-check.log`: the new checks fail against the previous guidance, reproducing both island distances and both southbound warning errors, plus perpendicular/depth/endpoint controls.
- `evidence/guidance-fixes-2026-09-21/hud-check.log`: `./run.command --headless -- --hud-check` passes after the fix, with **0 build warnings / 0 errors**. It includes both headings and both carriageways in service/free-drive modes, turning and junction guards, off-corridor island/depth/endpoints, normal H1 approach/boarding/missed-stop text, and the existing map/pause, camera and taxi regression checks. These checks also run within `--self-test`.

- `evidence/guidance-fixes-2026-09-21/runtime.log`: native GL Compatibility run exits 0 with `ANTILA_GUIDANCE_RENDER_OK`. The real bus drives all four direction/carriageway controls at about 9 km/h; both correct lanes suppress the warning and both wrong lanes show it. Lockhart/Gloucester exploration, normal H1 approach/boarding/missed-stop messages and map/Escape controls pass. Eleven fresh PNGs and two [before/after comparisons](../evidence/guidance-fixes-2026-09-21/compare.html) record the result.

The long driving suite was not repeated for these HUD guidance changes. The map cache, government geometry and vehicle handling are unchanged.

## Restart cleanup — 22 September 2026

The next review recorded 262 `Handle is not initialized` errors while `PackedScene.Instantiate` rebuilt government buildings after an R-key restart. Play resumed, but the reload was not clean. The stack matched Godot's managed/native resource-handle swap; a similar cached-resource lifetime issue is described in [Godot issue 112067](https://github.com/godotengine/godot/issues/112067).

Restart now performs `GC.Collect()` and `GC.WaitForPendingFinalizers()` before `ReloadCurrentScene`, matching the existing quit cleanup. This gives temporary C# resource wrappers a cleanup boundary before their native scene is replaced. It is a local workaround for the Godot/.NET lifetime problem, not an engine change.

`--restart-check` exercises the real restart input path from a paused map, island free drive and completed 26-passenger service. Each new scene must restore H1, closed doors, forward gear and active bus physics, preserve building mesh/collision counts, and pass the existing facade, paving and 107 roof-collision checks. A temporary Godot logger makes any engine error fail the run, even when scene creation recovers. Native runs also save four renders in `evidence/restart-check/`.

```sh
./run.command --headless -- --restart-check
./run.command --disable-vsync -- --restart-check
```

The original intermittent failure is retained in `evidence/restart-fix-2026-09-22/review-runtime-settled.log` and the shorter `review-restart-error-excerpt.log`. Baseline repeat checks also sometimes passed before the change, so this is not a deterministic red/green reproduction. The native check after the change passed all three reloads with 558 building mesh nodes and 279 collision shapes, no engine errors and a 0-warning/0-error build (`native-check.log`).

The headless check also passed all three reloads (`headless-check.log`). Replaying the original real-time boarding, map pause, completion and restart sequence passed without handle errors (`service-replay.log`), bringing the observed clean reloads after the change to seven. Captures are copied into `evidence/restart-fix-2026-09-22/`; the restarted H1 scene was inspected visually.

The full `--self-test` also exited 0 with no engine errors (`self-test.log`): road/building/footpath/audio/HUD/signal checks, both tunnel directions, the Wan Chai loop, the 9.165 km island scenic drive, both side-street turns and the physically driven 1.08 km H1 service with all 26 passengers and no unintended route contacts. These bounded clean runs do not establish that the upstream engine issue is fixed generally.
