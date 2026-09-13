# Antila — Kowloon Bus

A playable **Godot 4.6 .NET / C#** bus-driving scene across Tsim Sha Tsui and Jordan, Hong Kong. Drive an original cream-and-red double-decker north from Tsim Sha Tsui towards Jordan, serve three H1 stops, and finish the service.

![Kowloon map](evidence/map.png)

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
| M | Open / close the full Kowloon map; driving pauses while open |
| H | Horn |
| V | Mute / unmute all game audio |
| Escape | Pause / resume |
| R | Restart the service |
| F12 | Save the current view to `evidence/` |

Traffic lights control fourteen junctions: ten on Nathan Road from Peking Road to Jordan Road, plus Canton / Haiphong, Canton / Austin, Chatham / Granville and Chatham / Mody. Brake behind the white stop line on red or red-and-amber; amber means stop if safe. The next-signal panel shows the relevant approach and distance from the bus nose. Taxis wait at signals; the bus remains under your control, with red-light crossings recorded in the completion summary.

Turn onto side streets to explore the wider district; **M** shows your position and the H1 stops. The existing three-stop service stays on Nathan Road.

Follow the **leftmost northbound lane**. Pull into the green stop marker, align with the road, stop completely and open the doors. Boarding takes four seconds. Close the doors before accelerating. Complete Middle Road, Kowloon Park and Jordan Road to finish. H1 is a fictional prototype service, not an actual published bus route.

## What is built

- A **2.06 km east–west × 1.24 km north–south** map extract, 3.6 times the previous data width. A connected network of 58 named side streets reaches Canton Road and Kowloon Park Drive to the west, and Chatham Road, Granville Road and Science Museum Road to the east.
- The original 1.15 km Nathan Road H1 service, with markings, shopfronts, banyan trees, shelters, Chinese signs and ambient taxis.
- 1,762 visible building parts derived from HK Government footprints and height datums: irregular blocks, podiums, courtyards and towers up to 259 m. Four facade styles, cafe shopfronts and rooftop details cover 723,983 m² of ground; 131 spatial mesh chunks keep rendering and collision practical.
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

This is a **stylized prototype**. Road widths, elevations, streetscape, facade appearance, stop placements and traffic are authored approximations. Road alignments and building massing derive from government data, with pavement/park clearance adaptations; this is not a surveyed 3D reconstruction. Handling uses a flat-ground kinematic body, without suspension, drivetrain simulation or damage. Taxis follow a simple looping southbound path, waiting at red/amber lights and when their movement or loop destination is obstructed; there is no network routing, career saving or licensed operator livery. Traffic-light locations and timings are authored approximations; there are no pedestrian phases or turn-arrow phases. The scanned passengers use fixed poses without walking or boarding animations; cab instruments remain simple.

## Data and art

**Road geometry:** © Hong Kong SAR Government / Transport Department, via [DATA.GOV.HK — Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2). Reuse follows the portal's [Terms and Conditions](https://data.gov.hk/en/terms-and-conditions); ownership is acknowledged here, in the data files and in the game HUD. No government endorsement is implied.

`Data/roads.geojson` retains 596 clipped source features in WGS84. `Data/nathan-road.json` contains the unchanged 231 sampled service-route points, 244 samples covering the full Nathan Road surface and 437 connected side-street sections, extract bounds, source URL, original download timestamp, processing timestamp, SHA-256 and coordinate origin. +X is east, -Z is north, one world unit is one metre. This first slice averages carriageway centrelines at 5 m intervals. It does not infer real lane widths or turning permissions from the centreline data. The expansion uses named ground-level streets; unnamed links, pedestrian paths, highway/tunnel approaches and isolated fragments are excluded. Side streets are 12 or 18 m wide in the game. At runtime, unambiguous same-name segments join into 260 polylines; road geometry, pavement and building footprints generate a three-channel terrain mask at three pixels per metre. The original source features remain intact. The playable connected network spans about 1.75 km east–west inside the larger extract; no road is promised at every point within its bounds.

To regenerate using Python's standard library:

```sh
curl -L --fail https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz -o /tmp/CENTERLINE.kmz
python3 Tools/import_map.py /tmp/CENTERLINE.kmz
```

Google Maps imagery, tiles and 3D meshes are not included. The government extract is bundled so gameplay requires neither a map API key nor a network connection.

**Original models:** `Art/antila-assets.blend` is the editable Blender source for ten original GLBs. `Tools/model_assets.py` is the reproducible modeling script executed through Blender MCP. It creates a separate scene, exports only its selected objects and saves that scene's dependencies. The `.gdignore` keeps Godot from importing the source `.blend` as well as the GLBs.

**Government buildings:** Building data © HKSAR Government / Lands Department, via the [CSDI Portal](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC). `Data/buildings.geojson` retains 1,718 original building parts; `Tools/import_buildings.py` produces the playable layout. Blender MCP builds `Art/kowloon-buildings.blend` and `Assets/Models/kowloon-buildings.glb` from that layout and a new imagegen facade atlas. See `docs/GOVERNMENT_BUILDINGS.md` for attribution, source query, approximations, regeneration and checks. `Art/buildings.blend` and `docs/BUILDING_REVIEW.md` retain the superseded three-model grid.

**Traffic signals:** `Tools/model_traffic_signal.py` creates the original signal through Blender MCP, with separate red, amber and green lenses. The editable source is `Art/traffic-signal.blend`, exported as `Assets/Models/traffic-signal.glb`. See `docs/TRAFFIC_LIGHTS.md` for coverage, timing and checks.

**Passengers:** Four additional GLBs use free licensed scans from [Renderpeople](https://renderpeople.com/free-3d-people/), prepared through Blender MCP with `Tools/import_passengers.py`. The editable lineup is `Art/passengers.blend`. See `docs/PASSENGER_ASSETS.md` for source downloads, scale conversion, verification and licensing. These passenger assets are excluded from Git because their license permits game use but restricts distribution of the individual models; obtain them from the documented supplier downloads when preparing a fresh source checkout.

**Game audio:** An original instrumental track and nine SFX/ambience clips generated through ElevenLabs MCP replace the synthesized engine/horn and add event-driven SFX and city ambience. Original downloads and exact prompts are retained in `Art/Audio/`; `Tools/generate_audio.py` processes them locally without API calls. See `docs/AUDIO_ASSETS.md` and `evidence/game-audio-review.mp3` for mappings and a captured game mix. The 88-second stereo music loop plays quietly beneath the driving sounds, lowers while boarding, and follows pause, mute, reset and service-completion behavior.

**Generated poster:** `Assets/Textures/kowloon-poster.png`, made with the built-in imagegen tool. The exact prompt is in `docs/IMAGE_PROMPT.md`. It is decorative artwork, not a geographic reference.

**Photographic surface textures:** `Assets/Textures/weathered-tiles.png`, `cafe-storefront.png`, `asphalt.png` and `paving.png` add weathered walls, detailed shop interiors and street surfaces. They were generated with the built-in imagegen tool and applied through Blender materials and Godot UVs. See `docs/REALISM_ASSETS.md` for the exact prompts and mapping details.

**Vegetation and decoration:** `banyan-leaves.png`, `banyan-bark.png` and `park-ground.png` provide generated foliage, bark and lawn textures. The leaf image has actual transparency; Blender exports it with alpha cutouts. See `docs/DECORATION_ASSETS.md` for saved assets, prompts and simplifications. `evidence/decoration.png` shows the park and street furniture without the HUD.

**Pedestrian areas:** Stone pavement borders, tactile landing/boarding tiles, railings, drainage grates and two connected park entrances are documented in `docs/FOOTPATH_POLISH.md`. The new models were made through Blender MCP (`Art/footpaths.blend`, `Tools/model_footpaths.py`), with an imagegen stone texture at `Assets/Textures/pavement-stone.png`.

## Verification

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

The building review checks government-derived density, imported render/collision chunks, textured materials and 53 roof collision probes with `./run.command --headless -- --building-check`. `./run.command --disable-vsync -- --building-review` saves seven street/corner/block/skyline views; the full self-test includes the building audit.

The pedestrian-area checks run with `./run.command --headless -- --footpath-check` and as part of the full self-test. `./run.command --disable-vsync -- --footpath-review` saves seven pavement, crossing, bus-stop and park views.

Road-polish checks run with `./run.command --headless -- --road-check`; `./run.command --disable-vsync -- --road-review` saves eight road views. Findings, comparisons and verification are in `docs/ROAD_POLISH.md`.

Review findings and visual comparisons: `docs/POLISH_REVIEW.md`, `docs/SECOND_REVIEW.md` and `docs/BUILDING_REVIEW.md`. Implementation plan: `docs/PLAN.md`.
