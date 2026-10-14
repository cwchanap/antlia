# Antila — Kowloon Bus

A playable **Godot 4.6 .NET / C#** bus-driving scene across Tsim Sha Tsui and Jordan, Hong Kong. Drive an original cream-and-red double-decker north from Tsim Sha Tsui towards Jordan, serve three H1 stops, and finish the service. The map also reaches **West Kowloon, Tai Kok Tsui, Sham Shui Po, Cheung Sha Wan, Lai Chi Kok, Mei Foo, Lai King, Kwai Chung, Yau Ma Tei, Mong Kok, the Cross-Harbour Tunnel, Central, Admiralty, Wan Chai and Causeway Bay**, with both tunnel tubes and an expanded island street network.

![Expanded Kowloon and Cross-Harbour map](evidence/lai-chi-kok-expansion-2026-10-12/map.png)

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
| J | Start the Admiralty / Central loop while stopped |
| K | Start the Jordan / Yau Ma Tei / Mong Kok drive while stopped |
| L | Start West Kowloon / Tai Kok Tsui / Sham Shui Po free drive while stopped |
| N | Start Sham Shui Po / Cheung Sha Wan / Lai Chi Kok free drive while stopped |
| B | Start Mei Foo / Lai King / Kwai Chung free drive while stopped |
| T | Start a Cross-Harbour free drive while stopped in an active game |
| H | Horn |
| V | Mute / unmute all game audio |
| Escape | Pause / resume |
| R | Restart the service |
| F12 | Save the current view to `evidence/` |

Traffic lights control fourteen junctions: ten on Nathan Road from Peking Road to Jordan Road, plus Canton / Haiphong, Canton / Austin, Chatham / Granville and Chatham / Mody. Brake behind the white stop line on red or red-and-amber; amber means stop if safe. The next-signal panel shows the relevant approach and distance from the bus nose. Taxis wait at signals; the bus remains under your control, with red-light crossings recorded in the completion summary.

Press **T** while stopped to start at the tunnel approach in cab view. The tunnel follows government XY geometry at approximate metre scale, with approximately **1.857 km per tube**; its depth and interior dimensions are authored. **I** starts Wan Chai / Causeway Bay free drive; **J** starts the Admiralty / Central loop; **K** starts the northern Kowloon drive; **L** starts the 6.16 km western drive towards Sham Shui Po. **N** starts the 2.924 km Cheung Sha Wan / Lai Chi Kok drive. **B** starts the 5.358 km Mei Foo / Lai King / Kwai Chung drive. **M** shows the expanded map; **R** returns to H1. See [Cross-Harbour data, limits and verification](docs/CROSS_HARBOUR.md).

Turn onto side streets to explore the wider district; **M** shows your position and the H1 stops. The existing three-stop service stays on Nathan Road.

Follow the **leftmost northbound lane**. Pull into the green stop marker, align with the road, stop completely and open the doors. Boarding takes four seconds. Close the doors before accelerating. Complete Middle Road, Kowloon Park and Jordan Road to finish. H1 is a fictional prototype service, not an actual published bus route.

## What is built

- A **8.71 km east–west × 10.73 km north–south** overall map with 4,626 government road sections across northern Kowloon, the Cross-Harbour approaches and island streets, two driveable tubes, island return loop, ceramic walls, lamps and portal signs. The existing detailed Kowloon district remains a **2.06 km east–west × 1.24 km north–south** extract, 3.6 times the previous data width. A connected network of 58 named side streets reaches Canton Road and Kowloon Park Drive to the west, and Chatham Road, Granville Road and Science Museum Road to the east.
- A connected 5.358 km Mei Foo → Lai King → Kwai Chung drive, adding 1,191 government road sections and 3,422 building parts. Press **B while stopped**; [sources, terrain limits and checks](docs/KWAI_CHUNG_EXPANSION.md).
- A connected 2.924 km Sham Shui Po → Cheung Sha Wan → Lai Chi Kok exploration drive, with 445 added government road sections and three new building GLBs. See [sources, boundaries and checks](docs/LAI_CHI_KOK_EXPANSION.md).
- The original 1.15 km Nathan Road H1 service, with markings, shopfronts, banyan trees, shelters, Chinese signs and ambient taxis.
- Six restored flyover crossings with separate lower roads and connected ramps, plus the government-derived Central shoreline and restored Two IFC massing. See [map corrections and limits](docs/GOVERNMENT_MAP_FIXES.md); `--map-check` runs the focused crossing, IFC and island-coast collision checks.
- 24,250 visible building parts derived from HK Government footprints and height datums: 1,759 in the original Kowloon district, 5,102 around Yau Ma Tei / Mong Kok, 6,082 in the western / Sham Shui Po extension, 2,795 around Cheung Sha Wan / Lai Chi Kok, 3,422 around Lai King / Kwai Chung and 5,090 around the island corridor. Irregular blocks, podiums, courtyards and towers up to 485.3 m use four facade styles, five recessed shopfront types and rooftop details. Building coverage and the waterfront update are recorded in [the map-correction notes](docs/GOVERNMENT_MAP_FIXES.md).
- Modeled entrance steps and grab rails, transparent shelter glazing, live cab instruments and corrected tunnel lighting. The expansion streets have paving, trees, lamps, posed pedestrians, news kiosks and planters, plus a promenade following the island shoreline. Portals have exterior retaining shells; water has animated, distance-filtered ripples. The island apron is now 4.45 km wide, with a 9.2 km Wan Chai / Causeway Bay scenic drive and a 3.08 km Admiralty / Central loop. The western extension adds 1,367 sections, 6.59 km of government-derived coastline and streets reaching Sham Shui Po; see [West Kowloon expansion](docs/WEST_KOWLOON_EXPANSION.md). The northern extension added 673 sections and a 2.109 km Nathan Road drive; see [Yau Ma Tei / Mong Kok expansion](docs/KOWLOON_EXPANSION.md). The earlier westward expansion added 420 source sections; see [Central expansion and data handling](docs/CENTRAL_EXPANSION.md). See the [island expansion](docs/ISLAND_EXPANSION.md), [asset detail fixes](docs/ASSET_DETAIL_REVIEW.md) and [area review follow-up](docs/AREA_REVIEW.md#implementation-follow-up).
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

This is a **stylized prototype**. Road widths, elevations, streetscape, facade appearance, stop placements and traffic are authored approximations. Road alignments, building massing and the western/island coastlines derive from government data, with pavement/park clearance adaptations; this is not a surveyed 3D reconstruction. Handling uses a kinematic body that follows the road grade, without suspension, drivetrain simulation or damage. Taxis follow a simple looping southbound path, waiting at red/amber lights and when their movement or loop destination is obstructed; there is no network routing, career saving or licensed operator livery. Traffic-light locations and timings are authored approximations; there are no pedestrian phases or turn-arrow phases. The scanned passengers use fixed poses without walking or boarding animations; cab instruments remain simple.

## Data and art

**Road geometry:** © Hong Kong SAR Government / Transport Department, via [DATA.GOV.HK — Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2). Reuse follows the portal's [Terms and Conditions](https://data.gov.hk/en/terms-and-conditions); ownership is acknowledged here, in the data files and in the game HUD. No government endorsement is implied.

`Data/roads.geojson` retains 596 clipped source features in WGS84. `Data/nathan-road.json` contains the unchanged 231 sampled service-route points, 244 samples covering the full Nathan Road surface and 437 connected side-street sections, extract bounds, source URL, original download timestamp, processing timestamp, SHA-256 and coordinate origin. +X is east, -Z is north, one world unit is approximately one metre. The local projection stretches north–south distances by about 0.53%; see [the geographic review](docs/GOVERNMENT_MAP_REVIEW.md). This first slice averages carriageway centrelines at 5 m intervals. It does not infer real lane widths or turning permissions from the centreline data. The original district extract uses named ground-level streets; unnamed links, pedestrian paths, highway/tunnel approaches and isolated fragments are excluded. Side streets are 12 or 18 m wide in the game. At runtime, unambiguous same-name segments join into 260 polylines; road geometry, pavement and building footprints generate a three-channel terrain mask at three pixels per metre. The original source features remain intact. The playable connected network spans about 1.75 km east–west inside the larger extract; no road is promised at every point within its bounds.

The original Kowloon importer expects the WGS84 snapshot recorded in `Data/nathan-road.json`. The current TD KMZ needs an explicit datum conversion; regenerate the crossing/island expansion with:

```sh
curl -L --fail https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz -o /tmp/CENTERLINE.kmz
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/CENTERLINE.kmz --hk1980
```

**Cross-Harbour and Kowloon extensions:** `Data/cross-harbour-source.geojson` retains 4,626 selected TD features and their attributes. Earlier road sections are pinned to their snapshots; new roads use the October KMZ, converted from HK1980 geographic coordinates to WGS84. Stable `ROUTE_ID` values resolve changed KML identifiers. `Data/cross-harbour.json` adds approximately metre-scale geometry and provenance without changing the Nathan Road import. `Tools/import_tunnel.py` and Blender MCP `Tools/model_tunnel.py` regenerate it. The [Kwai Chung expansion](docs/KWAI_CHUNG_EXPANSION.md) adds 1,191 sections and a tenth drive while preserving all earlier roads/routes. The [Lai Chi Kok expansion](docs/LAI_CHI_KOK_EXPANSION.md) adds 445 sections and a ninth route while preserving all preceding roads and routes. The earlier [West Kowloon notes](docs/WEST_KOWLOON_EXPANSION.md) document the added 1,367 sections, two drives and retained earlier roads. The [map-correction follow-up](docs/GOVERNMENT_MAP_FIXES.md) restores elevated decks and documents the current checks.

**Kwai Chung coastline:** A 48-tile iB1000 extract adds the western mainland shoreline beyond the Lai Chi Kok rectangle, with 28 recorded gap repairs up to 5.37 m. Earlier coast/land geometry is retained. See [source metadata and limits](docs/KWAI_CHUNG_EXPANSION.md).

**Northwestern coastline:** A separate 40-tile iB1000 extract extends the coast by 903 m, preserving the preceding western land footprint and adding no gap repairs. The merged western mainland shoreline is 7.492 km; see [Lai Chi Kok source metadata](docs/LAI_CHI_KOK_EXPANSION.md).

**Western coastline:** Lands Department iB1000 Shoreline and CartoHydroLine seawall/high-water geometry supplies the western mainland edge, converted from HK1980 Grid to the game's metre coordinates. The bundled extract records 46 source tiles, archive hashes and 24 short straight gap repairs. This adds the West Kowloon peninsula and Yau Ma Tei typhoon-shelter shape. Inland terrain, map cuts, seawall height, and the earlier eastern Kowloon apron remain authored. The island coast now uses 34 additional/reused iB1000 tiles, pier outlines, a 10 cm topology weld and explicitly authored joins around ferry terminals and tunnel mouths (up to 115.15 m); see [map-correction sources and limitations](docs/GOVERNMENT_MAP_FIXES.md). See [shoreline sources and limits](docs/WEST_KOWLOON_EXPANSION.md#shoreline).

Google Maps imagery, tiles and 3D meshes are not included. The government extract is bundled so gameplay requires neither a map API key nor a network connection.

**Original models:** `Art/antila-assets.blend` is the editable Blender source for ten original GLBs. `Tools/model_assets.py` is the reproducible modeling script executed through Blender MCP. It creates a separate scene, exports only its selected objects and saves that scene's dependencies. The `.gdignore` keeps Godot from importing the source `.blend` as well as the GLBs.

**Government buildings:** Building data © HKSAR Government / Lands Department, via the [CSDI Portal](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC). `Data/buildings.geojson` retains 1,718 original Kowloon building parts; `Data/island-buildings.geojson` retains 4,838 island source records downloaded on 8 October 2026 UTC. `Data/kowloon-north-buildings.geojson` adds 4,868 northern records from 6 October 2026 UTC; `Data/west-kowloon-buildings.geojson` adds an 11,816-record extract from 7 October 2026 UTC, excluding earlier regions in its derived layout. `Data/lai-chi-kok-buildings.geojson` adds 4,504 records downloaded on 12 October 2026 UTC. `Data/kwai-chung-buildings.geojson` adds 4,690 records downloaded 13 October 2026 UTC. `Tools/import_buildings.py` produces the playable layouts, reconciling connected base heights across all five Kowloon extracts before regional clipping so shared buildings have level roofs. Shared building IDs use the newest extract's roof-height/storey inputs, preventing seams after a regional refresh. Each layout records the five input hashes. Blender MCP builds the corresponding `kowloon-buildings`, `island-buildings`, `central-buildings`, `yau-ma-tei-buildings`, `mong-kok-buildings` four western / Sham Shui Po GLBs, three Cheung Sha Wan / Lai Chi Kok GLBs, and three Lai King / Kwai Chung GLBs and editable blends using the existing imagegen facade atlases. See `docs/GOVERNMENT_BUILDINGS.md` for attribution, source queries, approximations, regeneration and checks. `Art/buildings.blend` and `docs/BUILDING_REVIEW.md` retain the superseded three-model grid.

**Traffic signals:** `Tools/model_traffic_signal.py` creates the original signal through Blender MCP, with separate red, amber and green lenses. The editable source is `Art/traffic-signal.blend`, exported as `Assets/Models/traffic-signal.glb`. See `docs/TRAFFIC_LIGHTS.md` for coverage, timing and checks.

**Passengers:** Four additional GLBs use free licensed scans from [Renderpeople](https://renderpeople.com/free-3d-people/), prepared through Blender MCP with `Tools/import_passengers.py`. The editable lineup is `Art/passengers.blend`. See `docs/PASSENGER_ASSETS.md` for source downloads, scale conversion, verification and licensing. These passenger assets are excluded from Git because their license permits game use but restricts distribution of the individual models; obtain them from the documented supplier downloads when preparing a fresh source checkout.

**Game audio:** An original instrumental track and nine SFX/ambience clips generated through ElevenLabs MCP replace the synthesized engine/horn and add event-driven SFX and city ambience. Original downloads and exact prompts are retained in `Art/Audio/`; `Tools/generate_audio.py` processes them locally without API calls. See `docs/AUDIO_ASSETS.md` and `evidence/game-audio-review.mp3` for mappings and a captured game mix. The 88-second stereo music loop plays quietly beneath the driving sounds, lowers while boarding, and follows pause, mute, reset and service-completion behavior.

**Generated poster:** `Assets/Textures/kowloon-poster.png`, made with the built-in imagegen tool. The exact prompt is in `docs/IMAGE_PROMPT.md`. It is decorative artwork, not a geographic reference.

**Photographic surface textures:** `Assets/Textures/weathered-tiles.png`, `cafe-storefront.png`, `asphalt.png` and `paving.png` add weathered walls, detailed shop interiors and street surfaces. They were generated with the built-in imagegen tool and applied through Blender materials and Godot UVs. See `docs/REALISM_ASSETS.md` for the exact prompts and mapping details.

**Vegetation and decoration:** `banyan-leaves.png`, `banyan-bark.png` and `park-ground.png` provide generated foliage, bark and lawn textures. The leaf image has actual transparency; Blender exports it with alpha cutouts. See `docs/DECORATION_ASSETS.md` for saved assets, prompts and simplifications. `evidence/decoration.png` shows the park and street furniture without the HUD.

**Pedestrian areas:** Stone pavement borders, tactile landing/boarding tiles, railings, drainage grates and two connected park entrances are documented in `docs/FOOTPATH_POLISH.md`. The new models were made through Blender MCP (`Art/footpaths.blend`, `Tools/model_footpaths.py`), with an imagegen stone texture at `Assets/Textures/pavement-stone.png`.

## Verification

The 13 October Mei Foo / Lai King / Kwai Chung expansion passes the full in-engine suite with all ten exploration routes and seven ramp/flyover drives, both side-street turns and the original three-stop / 26-passenger H1 service. The new route covers 5,323 m physically without contacts or departures. Final native images, B-key input, 16 coastline physics probes, government-data preservation, building seams and model-chunk checks pass. Build: **0 warnings / 0 errors**. Independent review found no actionable issues. Five scene reloads, including the new drive, restore H1 with all 1,842 collision chunks and no engine errors. See [sources, terrain limits and recorded evidence](docs/KWAI_CHUNG_EXPANSION.md) and [before/after views](evidence/kwai-chung-expansion-2026-10-13/compare.html). `--kwai-chung-check` runs the focused route/shortcut checks.

The 12–13 October Cheung Sha Wan / Lai Chi Kok expansion passes the full in-engine suite: all nine exploration routes, seven ramp/flyover drives, both side-street turns and the original three-stop / 26-passenger H1 service. The new route physically covers 2,910 m without contacts or departures. Build: **0 warnings / 0 errors**. Four scene reloads, including the new drive, restore H1 with no engine errors. Eight native views and N-key input pass; [compare before and after](evidence/lai-chi-kok-expansion-2026-10-12/compare.html). Source, preservation, shared-height and exact model-chunk audits pass. See [Lai Chi Kok sources and recorded checks](docs/LAI_CHI_KOK_EXPANSION.md); `--northwest-check` runs the focused route and shortcut checks.

The 8–11 October government-map correction is verified by the final `ANTILA_SELF_TEST_OK` marker: all eight complete routes, seven focused ramp/flyover drives, 50,337 bus-envelope queries and the original three-stop H1 service pass. The C# build reports 0 warnings / 0 errors; source/data checks and seven native comparison captures also pass. The earlier results below apply to their recorded snapshots. See [the correction results and evidence limits](docs/GOVERNMENT_MAP_FIXES.md).

The 11 October self-review follow-up caches HUD street lookups and refreshes shoreline archives before recording their source revisions. The HUD/input/camera regression suite and offline shoreline refresh/failure checks pass; the build has 0 warnings / 0 errors. The full route suite was not repeated for this follow-up. See [fixes and focused evidence](docs/GOVERNMENT_MAP_FIXES.md#self-review-fixes--11-october).

The West Kowloon / Sham Shui Po expansion passes the complete in-engine suite: all eight drives, both side-street turns and the original three-stop / 26-passenger H1 service. Both new routes complete without contacts or departures. Three scene reloads pass with no engine errors; native renders and the L-key input event pass. The final build has **0 warnings / 0 errors**. See [West Kowloon data, limitations and evidence](docs/WEST_KOWLOON_EXPANSION.md) and [before/after views](evidence/west-kowloon-expansion-2026-10-07/compare.html). `--west-check` runs the focused checks for both new drives.

Verified on 7 October 2026 (Hong Kong time): the northern Kowloon expansion passes the complete in-engine suite, including the 2.084 km physical Mong Kok drive, all five earlier routes, both Kowloon side-street turns and all three H1 stops. Three scene reloads pass with no engine errors; the build has **0 warnings / 0 errors**. Native renders and real K-key input also pass. See [Yau Ma Tei / Mong Kok data and evidence](docs/KOWLOON_EXPANSION.md) and [before/after views](evidence/kowloon-expansion-2026-10-06/compare.html). `--kowloon-check` provides a focused northern-route check.

Verified on 6 October 2026: the westward expansion passes the complete in-engine suite, including both tunnel directions, the 9.2 km island scenic drive, the new 3.08 km Central loop, both Kowloon side-street turns and all three H1 stops. The build has **0 warnings / 0 errors**; repeated scene reloads and native J/C keyboard checks also pass. See [Central / Admiralty expansion and evidence](docs/CENTRAL_EXPANSION.md). The new `--central-check` provides a focused western-loop check.

The second HUD follow-up makes Nathan Road lane warnings heading-aware and shows exploration guidance off the service corridor. The expanded `--hud-check` passes all four heading/carriageway combinations and preserves H1 service messages; see [guidance fixes and checks](docs/ISLAND_EXPANSION.md#driving-guidance-follow-up--21-september-2026-utc).

Restart now finishes pending C# resource cleanup before reloading the world. The new `--restart-check` verifies repeated reloads from map/pause, island drive, northwest drive, Kwai Chung drive and completed service, and fails on engine errors; see [restart cleanup and evidence](docs/ISLAND_EXPANSION.md#restart-cleanup--22-september-2026).

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
