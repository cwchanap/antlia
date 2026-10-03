# Government building layout — 13 September 2026

The repeated rectangular building grid has been replaced by derived Lands Department building footprints. The scene now has continuous street frontages, irregular block shapes, courtyards, podiums and towers, with four facade styles, subtle material tints, selected cafe shopfronts and rooftop plant rooms.

## Source and attribution

Building data © Hong Kong SAR Government / Lands Department, obtained through the [CSDI Portal](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC). Government ownership is acknowledged; no government endorsement is implied. See the [official Building dataset metadata](https://portal.csdi.gov.hk/csdi-webpage/metadata/landsd_rcd_1637211194312_35158/html) and [reuse terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC).

The source is a monthly updated polygon dataset with building names, types, base/top height datums and storeys. The extract was downloaded on 13 September 2026 UTC; its count query returned **1,718**, matching the downloaded feature count. No API key is needed for the bundled offline data. `Data/buildings.geojson` and `Data/building-layer-metadata.json` retain the original API responses; `Data/building-layout.json` contains the processed geometry, source IDs, names, provenance and SHA-256.

The query was made against `https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637211194312_35158/MapServer/0/query` with:

```text
where=1=1
geometry=114.1625,22.29455,114.1825,22.3057
geometryType=esriGeometryEnvelope
inSR=4326
spatialRel=esriSpatialRelIntersects
outFields=*
outSR=4326
f=geojson
resultRecordCount=3000
```

Google imagery, tiles and 3D models are not bundled. [Google Maps Platform terms](https://cloud.google.com/maps-platform/terms) restrict tracing building outlines and creating models from its content, so the openly reusable government source suits the game pipeline.

## Result and deliberate approximations

| Measure | Imported scene |
| --- | ---: |
| Source building parts | 1,718 |
| Source records retained after clipping/occlusion | 1,578 |
| Visible derived parts, including split polygons | 1,762 |
| Ground footprint coverage | 723,983 m² |
| Main building heights | 1.5–259.1 m |
| Parts above 75 m | 87 |
| Spatial render/collision chunks | 131 each |

These are building **parts**, not a count of individual addresses. Podiums and towers are separate source records. Heights are survey datums: the importer subtracts the lowest base in each connected group, preserving stepped podium/tower silhouettes on the game's flat ground. It takes the upper envelope of overlapping parts and retains courtyard holes in the rendered roofs and collision geometry. Decorative parapets and plant rooms extend slightly above the main roof datum.

The existing authored road widths receive 3.5 m of pavement clearance. The Nathan/Granville junction adds 2 m of setback within a 32 m radius to clear the bus nose during the right turn; this removes only 98 m² of coverage from the first imported layout. Map boundaries and the authored Kowloon Park are clipped out; 1,124 source parts are affected by those exclusions. The 64 source parts without a usable top height fall back to storeys × 3.2 m, or 9.6 m when storeys are missing. Boundary simplification is limited to 8 cm and clipped back inside the original visible footprint. This is geographically informed game massing, not a surveyed 3D reconstruction; generated facades do not reproduce the actual appearance or entrances of specific buildings. The government names remain in the data, rather than claiming visual identity for generic facades.

## Rebuild and checks

```sh
python3 -m venv .venv-geodata
.venv-geodata/bin/pip install -r Tools/requirements-geodata.txt
.venv-geodata/bin/python Tools/import_buildings.py
```

Run `Tools/model_government_buildings.py` through Blender MCP. It builds only the `CSDI_Kowloon` scene, exports `Assets/Models/kowloon-buildings.glb`, and writes the editable `Art/kowloon-buildings.blend`. The game has no Python or Shapely runtime dependency. Static collision meshes use unsplit walls and triangulated roofs, while visible walls repeat the atlas at approximately 6 m × 6.4 m per two-floor tile. Concave footprints and courtyard holes are preserved.

The importer asserts valid geometry, road/park clearance, absence of overlapping ground pieces, complete roof triangulation and landmark/density/height retention. The Godot checks verify material textures, chunk/collision parity and 53 physical roof probes, including the tallest parts:

```sh
./run.command --headless -- --building-check
./run.command --headless -- --self-test
./run.command --disable-vsync -- --building-review
./run.command --disable-vsync -- --road-review
```

Before images are retained in `evidence/before-government-buildings/`; updated images are in `evidence/building-review/`. Nathan Road and Haiphong street viewpoints are unchanged for comparison. Chatham/Granville viewpoints were moved out of the newly populated footprints, the block views were raised above the taller skyline, and a seventh district view was added. The earlier report `docs/BUILDING_REVIEW.md` describes the superseded rectangular grid.

## Verified result

The final C# build completed with **0 warnings and 0 errors**. `evidence/government-building-self-test.log` records an exit-0 full run: 53 roof probes, all building/material/chunk checks, pavement and park access, 14 junctions / 48 signal approaches, 3,110 bus-sized road clearance queries, camera and audio regressions, 366 m on Haiphong Road and 790 m on Granville Road, then the full 1.08 km service with three stops and 26 passengers. Both side-street drives and the service had no contacts. The deliberate outer-boundary impact remains part of the test.

Review fixes included a 40 cm building-edge margin for signal poles and the small Granville turning setback. The test logger now identifies any contact's position and collider. Seven building views and eight road views are captured with Godot's actual renderer. Godot still sometimes prints ObjectDB/resource-in-use diagnostics on shutdown (the final full test reported one resource); functional checks pass and the process returns 0. The launcher also emitted an editor-only Android SDK setting diagnostic during import. Verbose capture identifies the shutdown resources as the existing looping engine/road/city/music audio streams, not building meshes. These are recorded separately from the successful C# build and game checks.

## Generated facade atlas

`Assets/Textures/building-facades.png` was generated with the built-in imagegen tool. Output is 1,254 × 1,254 pixels; each quadrant is used directly by Blender UVs. The existing generated cafe texture supplies selected street-facing ground floors. Exact new prompt:

> Generate a photorealistic game building facade texture atlas, square 2048 by 2048, for a Hong Kong bus driving simulator. Asset, not a scene illustration. The image must be exactly four equal square panels in a 2 by 2 grid, filling the canvas with no margins, labels, gaps or dividers. Every panel is a perfectly orthographic straight-on facade surface, flat diffuse overcast lighting, no perspective, no sky, no roofs, no ground. Each panel represents 6 metres wide by 6.4 metres tall, with exactly two floors and two evenly spaced window bays per floor. TOP LEFT: older Kowloon off-white small ceramic tile residential facade, dark aluminium windows, slight grime and a few compact window air conditioners. TOP RIGHT: modern dark blue teal glass curtain wall office facade, subtle cloudy reflections, fine metal mullions. BOTTOM LEFT: warm buff stone hotel facade, four neatly recessed dark windows with pale stone sills and understated elegant stone joints. BOTTOM RIGHT: muted sage and dusty rose painted Hong Kong apartment facade, four windows, shallow balcony rails and subtle laundry-free lived-in wear. Each panel should tile cleanly left-to-right and top-to-bottom on its own, with building structure and repeated floor spacing meeting its panel boundaries. High resolution crisp material texture, believable scale, understated colours, no intense highlights or directional shadows. No writing, no logos, no signage, no people, no watermark.


## Follow-up visual polish — 13 September 2026

- Facades now use 6 m × 6.4 m tiles at a consistent world scale. Partial wall and roof-height panels crop the atlas instead of compressing several windows into narrow faces. The same correction applies to 10 m shopfront panels.
- Stone kerbs follow roads and park paths. The data importer fills 223 enclosed pavement gaps of at most 40 m² between padded building polygons, while retaining the park and larger open spaces. This removes both the unpaved patches and their false decorative borders.
- Reduced haze density and brightness restore contrast across the district while retaining atmospheric distance cues.

Rebuilt through Blender MCP and verified in Godot: C# build **0 warnings / 0 errors**, 232,443 sampled facade edges at consistent texture scale, 53 roof collision probes, 223 filled-gap pixel checks, road-marking checks and pavement/park-access checks. `./run.command --headless -- --building-check` runs these checks. `evidence/urban-polish-check.log` records the exit-0 run.

The building geometry and all 131 collision meshes match the pre-polish version exactly; the layout file only gains pavement-patch metadata. Fingerprints are in `evidence/before-urban-polish/collision-fingerprints.json` and `evidence/urban-polish-collision-parity.json`. This pass did not rerun the complete driving service; the earlier full-route result above belongs to the same collision geometry.

Before renders are in `evidence/before-urban-polish/`; the seven building, eight road and seven footpath views are refreshed in their usual review folders. Source backups are in `Art/before-urban-polish/`. The new facade-scale assertion in `Main.BuildingReview.cs` checks imported mesh geometry and UVs, so future Blender edits cannot silently stretch the windows again.


## Cross-Harbour approach clearance

The tunnel extension adds the selected surface approach roads to the existing building exclusion buffers. Original government features and height datums remain intact; approximately 246 m² of derived massing is removed around the new roads, including the previously obstructed Hong Chong Road exit bend. The current layout contains 1,764 visible parts from 1,577 source records, 131 chunks, 723,737 m² of footprint coverage and 228 small pavement patches. See [Cross-Harbour extension](CROSS_HARBOUR.md) for regeneration order and current runtime evidence.

## Street-front detail — 20 September 2026

The street-facing ground floors now alternate five storefront types: the existing cafe plus a new generated bakery/pharmacy/shutter/grocery atlas. Storefronts sit 18 cm inside the original footprint with modeled side reveals, sills and lintels. Upper-floor UV scale and the government layout data remain unchanged. `Tools/model_government_buildings.py` and `Art/kowloon-buildings.blend` contain the updated generation/source; [surface asset notes](REALISM_ASSETS.md) preserve the exact image prompt. This does not add surveyed shop identities or modeled upper-floor window interiors. [Review follow-up and evidence](ASSET_DETAIL_REVIEW.md).

## Island corridor — 20 September 2026

The same Lands Department layer now supplies the island return-loop surroundings. The query envelope is `114.17552394472202,22.27802191879267,114.18542704659008,22.2851185770751` in WGS84, using the parameters above with `orderByFields=OBJECTID` and pagination. A separate count query returned 731; the downloaded records match that count and have unique source IDs. Download time: `2026-09-20T23:41:34.518802+00:00`. Raw response plus query metadata: `Data/island-buildings.geojson`; SHA-256: `7d0aa077cab8befc7a6a7d5a02c5abb7730255d391bad2172604d6b0f4170a51`.

`Data/island-building-layout.json` retains 721 source IDs as 766 visible parts, 209,077 m² of coverage, heights up to 205.5 m, and 80 small pavement-gap patches. Forty-seven source parts need the existing height fallback. The pipeline uses the same upper-envelope and road-clearance rules as Kowloon, clipped to the existing authored island apron. It does not import additional street connections or surveyed coastline. Facades remain generated artwork.

```sh
.venv-geodata/bin/python Tools/import_buildings.py --island --download
# Offline regeneration after the initial download:
.venv-geodata/bin/python Tools/import_buildings.py --island
```

Through Blender MCP, execute the existing model script with `ISLAND=True` in its globals. This selects the isolated `CSDI_Island` scene, `Data/island-building-layout.json`, `Assets/Models/island-buildings.glb` and `Art/island-buildings.blend`. The previous Blender scene is restored in `finally`. Island geometry occupies 48 render/collision chunks. Kowloon files are unchanged by this import. Combined runtime totals are 2,530 parts, 179 chunks, 308 pavement patches and 72 sampled roof collision probes. [Area review and current evidence](AREA_REVIEW.md#implementation-follow-up).


## Expanded island district — 20 September 2026

The later Wan Chai / Causeway Bay pass expands the island query to 2,048 source records and derives 2,180 island parts. The combined scene has 3,944 parts, 279 chunks and 107 roof probes. Source bounds, hash, height fallbacks and the interior-point correction are recorded in [the expansion notes](ISLAND_EXPANSION.md).
