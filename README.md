# Antila — Kowloon Bus

A playable **Godot 4.6 .NET / C#** bus-driving scene across Tsim Sha Tsui and Jordan, Hong Kong. Drive an original cream-and-red double-decker north from Tsim Sha Tsui towards Jordan, serve three H1 stops, and finish the service. The map also reaches the **Cross-Harbour Tunnel, Wan Chai and Causeway Bay**, with both tunnel tubes and an expanded island street network.

![Expanded Cross-Harbour map](evidence/island-expansion-2026-09-20/expanded-map.png)

![Government-derived Nathan Road buildings](evidence/building-review/nathan-front.png)

## Play

Open `project.godot` in **Godot_mono** and press **F5** after building C#, or double-click **run.command**. The launcher builds C#, imports assets and starts the game. This Mac has Godot .NET 4.6.2 and .NET 8; the ordinary `godot` command points to a different, non-Mono installation.

```sh
./run.command
```

On another machine set `GODOT_BIN` to a Godot 4.6 .NET executable. The SDK may require an initial NuGet restore; the game runs offline once built.

| Key | Action |
| --- | --- |
| W / Up | Accelerate |
| S / Down | Brake |
| A, D / Left, Right | Steer |
| Space | Handbrake, held |
| E | Open / close left-side doors, while stopped |
| Q | Drive / reverse, while stopped |
| C | Chase / right-hand cab camera |
| M | Open / close the full crossing map; driving pauses while open |
| I | Start island free drive through Wan Chai / Causeway Bay while stopped |
| T | Start a Cross-Harbour free drive while stopped in an active game |
| H | Horn |
| V | Mute / unmute all game audio |
| Escape | Pause / resume |
| R | Restart the service |
| F12 | Save the current view to `evidence/` |

Traffic lights control fourteen junctions: ten on Nathan Road from Peking Road to Jordan Road, plus Canton / Haiphong, Canton / Austin, Chatham / Granville and Chatham / Mody. Brake behind the white stop line on red or red-and-amber; amber means stop if safe. The next-signal panel shows the relevant approach and distance from the bus nose. Taxis wait at signals; the bus remains under your control, with red-light crossings recorded in the completion summary.

Press **T** while stopped to start at the tunnel approach in cab view. The tunnel follows government XY geometry at metre scale, with approximately **1.857 km per tube**; its depth and interior dimensions are authored. **I** starts island free drive. **M** shows the crossing and expanded island streets; **R** returns to H1. See [Cross-Harbour data, limits and verification](docs/CROSS_HARBOUR.md).

Turn onto side streets to explore the wider district; **M** shows your position and the H1 stops. The existing three-stop service stays on Nathan Road.

Follow the **leftmost northbound lane**. Pull into the green stop marker, align with the road, stop completely and open the doors. Boarding takes four seconds. Close the doors before accelerating. Complete Middle Road, Kowloon Park and Jordan Road to finish. H1 is a fictional prototype service, not an actual published bus route.

## What is built

- A **3.14 km east–west × 3.55 km north–south** overall map with 478 government road sections across the Cross-Harbour approaches and island streets, two driveable tubes, island return loop, ceramic walls, lamps and portal signs. The existing detailed Kowloon district remains a **2.06 km east–west × 1.24 km north–south** extract, 3.6 times the previous data width. A connected network of 58 named side streets reaches Canton Road and Kowloon Park Drive to the west, and Chatham Road, Granville Road and Science Museum Road to the east.
- The original 1.15 km Nathan Road H1 service, with markings, shopfronts, banyan trees, shelters, Chinese signs and ambient taxis.
- 3,944 visible building parts derived from HK Government footprints and height datums: 1,764 in Kowloon and 2,180 around the island corridor. Irregular blocks, podiums, courtyards and towers up to 377 m use four facade styles, five recessed shopfront types and rooftop details. Combined ground coverage is 1,340,938 m² across 279 spatial render/collision chunks.
- Modeled entrance steps and grab rails, transparent shelter glazing, live cab instruments and corrected tunnel lighting. The island loop has continuous paving, 122 trees, 170 lamps, 64 posed pedestrians, 18 news kiosks, planters and a waterfront promenade. Portals have exterior retaining shells; water has animated, distance-filtered ripples. The island apron is now 2.35 km wide, with 429 additional government road sections and a 9.2 km scenic test drive. See the [island expansion](docs/ISLAND_EXPANSION.md), [asset detail fixes](docs/ASSET_DETAIL_REVIEW.md) and [area review follow-up](docs/AREA_REVIEW.md#implementation-follow-up).
- One terrain surface blends asphalt, paving, park lawns and paths from a generated data mask, avoiding stacked road meshes. Stone kerbs follow roads and park paths, while facade textures keep a consistent window scale. Softer haze improves skyline contrast. Lane paint is batched and stops at crossing roads.
- Clearer road paint, arterial lane guides, left-hand traffic arrows, three yellow box junctions and labelled bus bays. Parallel source carriageways share a lane layout and crossings span the combined road width. Kowloon Park's bay sits clear of the Granville crossing; road and path edges use fractional pixel coverage.
- Scattered park trees, connected park paths, and physical outer boundaries. Nathan Road now connects through both former internal barriers to the surrounding junctions.
- A 10.7 m double-decker modeled through Blender MCP, with moving door panels, wheel rotation and a simple right-hand driving cab.
- A C# bicycle steering model with acceleration, braking, reverse, collision response and a door movement interlock.
- Forty-eight traffic-light approaches at fourteen junctions, with Blender-modeled poles, lit lenses, stop lines, coordinated phases and taxi stopping.
- A chase camera that pulls forward at physical walls, plus map controls that keep driving, doors, gear and traffic paused.
- Sequential boarding, 26 passengers, a fitted district minimap and full M-key overview, pause/restart and completion summary.
- An original imagegen poster on the shelters; nine ElevenLabs-generated engine, road, city, door, brake, horn, boarding and contact clips, plus an original instrumental background track, with driving-dependent mixing and a V-key mute control.
- Textured banyan trees with branching trunks, roots and leaf cutouts, park lawns, planters, benches and orange litter bins.
- Four detailed scanned passenger groups at each stop, including a parent carrying a child; queues disappear when boarding completes.

This is a **stylized prototype**. Road widths, elevations, streetscape, facade appearance, stop placements and traffic are authored approximations. Road alignments and building massing derive from government data, with pavement/park clearance adaptations; this is not a surveyed 3D reconstruction. Handling uses a kinematic body that follows the road grade, without suspension, drivetrain simulation or damage. Taxis follow a simple looping southbound path, waiting at red/amber lights and when their movement or loop destination is obstructed; there is no network routing, career saving or licensed operator livery. Traffic-light locations and timings are authored approximations; there are no pedestrian phases or turn-arrow phases. The scanned passengers use fixed poses without walking or boarding animations; cab instruments remain simple.

## Data and art

**Road geometry:** © Hong Kong SAR Government / Transport Department, via [DATA.GOV.HK — Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2). Reuse follows the portal's [Terms and Conditions](https://data.gov.hk/en/terms-and-conditions); ownership is acknowledged here, in the data files and in the game HUD. No government endorsement is implied.

`Data/roads.geojson` retains 596 clipped source features in WGS84. `Data/nathan-road.json` contains the unchanged 231 sampled service-route points, 244 samples covering the full Nathan Road surface and 437 connected side-street sections, extract bounds, source URL, original download timestamp, processing timestamp, SHA-256 and coordinate origin. +X is east, -Z is north, one world unit is one metre. This first slice averages carriageway centrelines at 5 m intervals. It does not infer real lane widths or turning permissions from the centreline data. The original district extract uses named ground-level streets; unnamed links, pedestrian paths, highway/tunnel approaches and isolated fragments are excluded. Side streets are 12 or 18 m wide in the game. At runtime, unambiguous same-name segments join into 260 polylines; road geometry, pavement and building footprints generate a three-channel terrain mask at three pixels per metre. The original source features remain intact. The playable connected network spans about 1.75 km east–west inside the larger extract; no road is promised at every point within its bounds.

To regenerate using Python's standard library:

```sh
curl -L --fail https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz -o /tmp/CENTERLINE.kmz
python3 Tools/import_map.py /tmp/CENTERLINE.kmz
```

**Cross-Harbour extension:** `Data/cross-harbour-source.geojson` retains 478 selected TD features and their original attributes, including the original 49 crossing sections. `Data/cross-harbour.json` adds the metre-scale crossing geometry and provenance without changing the Nathan Road import. `Tools/import_tunnel.py` and Blender MCP `Tools/model_tunnel.py` regenerate it; see `docs/CROSS_HARBOUR.md` and `docs/ISLAND_EXPANSION.md` for sources, authored depth/width/shoreline limits, texture prompts and checks.

Google Maps imagery, tiles and 3D meshes are not included. The government extract is bundled so gameplay requires neither a map API key nor a network connection.

**Original models:** `Art/antila-assets.blend` is the editable Blender source for ten original GLBs. `Tools/model_assets.py` is the reproducible modeling script executed through Blender MCP. It creates a separate scene, exports only its selected objects and saves that scene's dependencies. The `.gdignore` keeps Godot from importing the source `.blend` as well as the GLBs.

**Government buildings:** Building data © HKSAR Government / Lands Department, via the [CSDI Portal](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC). `Data/buildings.geojson` retains 1,718 original Kowloon building parts; `Data/island-buildings.geojson` retains 2,048 island source records downloaded on 21 September 2026 UTC. `Tools/import_buildings.py` produces the playable layouts. Blender MCP builds the corresponding `kowloon-buildings` and `island-buildings` GLBs and editable blends using the existing imagegen facade atlases. See `docs/GOVERNMENT_BUILDINGS.md` for attribution, source queries, approximations, regeneration and checks. `Art/buildings.blend` and `docs/BUILDING_REVIEW.md` retain the superseded three-model grid.

**Traffic signals:** `Tools/model_traffic_signal.py` creates the original signal through Blender MCP, with separate red, amber and green lenses. The editable source is `Art/traffic-signal.blend`, exported as `Assets/Models/traffic-signal.glb`. See `docs/TRAFFIC_LIGHTS.md` for coverage, timing and checks.

**Passengers:** Four additional GLBs use free licensed scans from [Renderpeople](https://renderpeople.com/free-3d-people/), prepared through Blender MCP with `Tools/import_passengers.py`. The editable lineup is `Art/passengers.blend`. See `docs/PASSENGER_ASSETS.md` for source downloads, scale conversion, verification and licensing. These passenger assets are excluded from Git because their license permits game use but restricts distribution of the individual models; obtain them from the documented supplier downloads when preparing a fresh source checkout.

**Game audio:** An original instrumental track and nine SFX/ambience clips generated through ElevenLabs MCP replace the synthesized engine/horn and add event-driven SFX and city ambience. Original downloads and exact prompts are retained in `Art/Audio/`; `Tools/generate_audio.py` processes them locally without API calls. See `docs/AUDIO_ASSETS.md` and `evidence/game-audio-review.mp3` for mappings and a captured game mix. The 88-second stereo music loop plays quietly beneath the driving sounds, lowers while boarding, and follows pause, mute, reset and service-completion behavior.

**Generated poster:** `Assets/Textures/kowloon-poster.png`, made with the built-in imagegen tool. The exact prompt is in `docs/IMAGE_PROMPT.md`. It is decorative artwork, not a geographic reference.

**Photographic surface textures:** `Assets/Textures/weathered-tiles.png`, `cafe-storefront.png`, `asphalt.png` and `paving.png` add weathered walls, detailed shop interiors and street surfaces. They were generated with the built-in imagegen tool and applied through Blender materials and Godot UVs. See `docs/REALISM_ASSETS.md` for the exact prompts and mapping details.

**Vegetation and decoration:** `banyan-leaves.png`, `banyan-bark.png` and `park-ground.png` provide generated foliage, bark and lawn textures. The leaf image has actual transparency; Blender exports it with alpha cutouts. See `docs/DECORATION_ASSETS.md` for saved assets, prompts and simplifications. `evidence/decoration.png` shows the park and street furniture without the HUD.

**Pedestrian areas:** Stone pavement borders, tactile landing/boarding tiles, railings, drainage grates and two connected park entrances are documented in `docs/FOOTPATH_POLISH.md`. The new models were made through Blender MCP (`Art/footpaths.blend`, `Tools/model_footpaths.py`), with an imagegen stone texture at `Assets/Textures/pavement-stone.png`.

## Verification

The second HUD follow-up makes Nathan Road lane warnings heading-aware and shows exploration guidance off the service corridor. The expanded `--hud-check` passes all four heading/carriageway combinations and preserves H1 service messages; see [guidance fixes and checks](docs/ISLAND_EXPANSION.md#driving-guidance-follow-up--21-september-2026-utc).

Restart now finishes pending C# resource cleanup before reloading the world. The new `--restart-check` verifies repeated reloads from map/pause, island drive and completed service, and fails on engine errors; see [restart cleanup and evidence](docs/ISLAND_EXPANSION.md#restart-cleanup--22-september-2026).

The 21 September HUD follow-up fixes the island lane warnings and caches static map roads. `./run.command --headless -- --hud-check` passes the new warning checks and existing map/camera/taxi regressions with **0 warnings / 0 errors**. Local cab-view median frame time fell from about 36 ms to 12.7 ms; see [checks, limits and rendered comparisons](docs/ISLAND_EXPANSION.md#hud-review-fixes--21-september-2026-utc).

Verified on 20 September 2026: the expanded Wan Chai / Causeway Bay scene passes the full in-engine suite, including 8,358 crossing/street clearance probes, both tunnel directions, the 9.2 km scenic drive, both Kowloon side-street turns and all three H1 stops. The C# build has **0 warnings / 0 errors**. Seventeen native renders include the expanded districts, street details, island shortcut, HUD and map. See [expansion verification](docs/ISLAND_EXPANSION.md#verification-and-rendered-evidence) and [before/after views](evidence/island-expansion-2026-09-20/compare.html).

Verified on 13 September 2026: the full self-test passes both tunnel directions, the island return loop, all original city checks, both side-street turns and the complete H1 service without unintended contacts. The crossing has a focused physics check (`./run.command --headless -- --harbour-check`) and a native render review (`./run.command --disable-vsync -- --harbour-review`). Current logs and six renders are under `evidence/harbour/`; see [Cross-Harbour verification and limits](docs/CROSS_HARBOUR.md).

```sh
./run.command --headless -- --self-test
./run.command -- --capture
./run.command -- --signal-capture
./run.command -- --audio-review
python3 Tools/generate_audio.py --check-review
```

The first command runs the C# in-engine checks and returns a nonzero exit code on failure. It checks audio imports, loop lengths, overlapping effects, pause/resume, mute and reset cleanup, terrain-mask placement, junction marking rules, 3,110 bus-sized physics queries across the road network, map loading, acceleration, braking, reverse, moving-door rejection, outer-boundary collision, wrong-side boarding rejection, passenger model groups, map-open controls and nested pause, chase-camera obstruction/smoothing and cab placement, taxi stop/resume and occupied loop destinations, physical turns from Nathan Road onto Haiphong Road and Granville Road beyond the former lateral boundaries, and a complete physically driven route through all three stops, including the removal of boarded queues. The second saves actual rendered chase, cab, park-stop, bus/shelter, decoration, passenger, camera-near-wall, west/east street, full-map, aerial, Salisbury/Chatham junction and block-density views (the aerial survey capture disables distance fog for readability), then exits. See `evidence/self-test.log`, `evidence/capture.log` and the PNGs for the recorded run.

Verified on 12 September 2026: the launcher built with **0 warnings / 0 errors**, imported the assets, and passed the complete 1.08 km driving check with all three stops and no route contacts. The expansion checks additionally drove 366 m west on Haiphong Road (to x = −355 m) and 790 m east on Granville Road (to x = 636 m), including turns from Nathan Road, without contacts. Map-open pause/resume also passed. Earlier native keyboard checks separately confirmed C, E, Q, Escape, R and F12. The second review verified native M/E/Q/Escape controls, including blocked bus controls under the map and preservation of an existing pause, after desktop access became available. C and F12 also worked in the reviewed build; the final cab image shows the corrected notification layout. Sustained throttle/steering were exercised by the in-engine controller check; the UI automation tool sends short key taps. The expanded scene is rendered at 1280 × 800 on this M1 Pro; no performance benchmark is claimed. Some earlier headless runs printed shutdown or Android SDK settings warnings; the final game capture loaded and exited successfully.

The traffic-light expansion covers fourteen junctions and 48 approaches. `docs/TRAFFIC_LIGHTS.md` lists the locations, phase timings and final placement/route evidence; `./run.command --headless -- --signal-check` runs the focused checks.

The government-building layout was verified on 13 September 2026 UTC: the full driving checks pass with the new footprints, including both side-street turns and all three service stops. See `docs/GOVERNMENT_BUILDINGS.md` and `evidence/government-building-self-test.log` for the current scene results and shutdown diagnostics.

The 20 September surrounding-area pass passed the full service suite, followed by a final crossing check after the portal cladding correction: **0 build warnings / errors**, both tunnel directions and the island loop without contacts. It adds 112 surface/pavement samples and 230 interior-wall probes. See the [28 runtime captures and verification notes](docs/AREA_REVIEW.md#verification-of-the-follow-up) and [before/after comparison](evidence/area-fixes-2026-09-20/compare.html).

The building review checks government-derived density, imported render/collision chunks, textured materials and 107 roof collision probes with `./run.command --headless -- --building-check`. `./run.command --disable-vsync -- --building-review` saves seven street/corner/block/skyline views; the full self-test includes the building audit.

The pedestrian-area checks run with `./run.command --headless -- --footpath-check` and as part of the full self-test. `./run.command --disable-vsync -- --footpath-review` saves seven pavement, crossing, bus-stop and park views.

Road-polish checks run with `./run.command --headless -- --road-check`; `./run.command --disable-vsync -- --road-review` saves eight road views. Findings, comparisons and verification are in `docs/ROAD_POLISH.md`.

Review findings and visual comparisons: `docs/POLISH_REVIEW.md`, `docs/SECOND_REVIEW.md` and `docs/BUILDING_REVIEW.md`. Implementation plan: `docs/PLAN.md`.
