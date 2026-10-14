# Government map corrections — 8–11 October 2026

Follow-up to [the government map review](GOVERNMENT_MAP_REVIEW.md). The island now follows a government-derived harbour edge, Two IFC's massing is restored, and the six crossings identified in the review have separate road decks and ground surfaces. Existing road XY coordinates, tunnel depth profiles and the eight route sequences are preserved.

## Road levels

The TD `ELEVATION` attribute identifies relative road levels, not heights in metres. All six imported level-1 sections now have 7 m decks. Connected approaches use a cosine transition over 150 m of road outside junction aprons, producing 85 raised road sections in total. Shared junctions remain level until adjoining branches separate by 7.5 m, preventing overlapping ramp meshes at shallow merges. These heights, ramp lengths and carriageway widths are authored for the prototype: generally 6 m on raised roads, with 12 m at the three low Hung Hing / Convention Avenue junction sections for bus turning room. The first 12 m-wide ramp mesh overlapped the adjacent Harbour Road carriageway; the bus-envelope check caught this and the raised carriageways were narrowed. The clearance probe follows the road pitch, as the actual bus does, and uses ±1.4 m lane offsets on the narrower ramps. Physical route checks use the same offsets and reject a bus more than 1.5 m from the intended road height.

Four restored crossings are Hoi Fai Road over Lin Cheung Road; two are the Tonnochy/Gloucester connection used by the island return and scenic routes. Decks have separate asphalt, concrete soffits, edge faces and physics surfaces. The underlying ground roads remain available. Raised sections no longer paint asphalt onto the ground below them. Roadside furniture is kept clear of the elevated approaches.

Short links between raised junctions interpolate between their endpoint heights rather than dipping below both. Ramp slab edges blend into ground near their entries, and Blender asserts upward-facing road and shoulder triangles. These corrections address the Sham Mong clearance failure and the physical Lin Cheung ramp-entry contact found during testing.

Road and deck-edge physics use the same 3.5 cm visual-surface offset. This prevents an invisible lip at merges while keeping the rendered asphalt above the terrain surface. The targeted Lin Cheung drive covers both its ramp entry and raised junction. Separate Hung Hing and Wan Chai bend drives cover both lane offsets. The three low junction sections retain 12 m of turning room and level end aprons, preventing a turning bus from climbing the shoulder or hitting the edge of a higher adjoining surface.

The road source is the Transport Department [Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2), downloaded as [CENTERLINE.kmz](https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz). SHA-256: `108319d165d1059522db6e7506d888c9da78a2c8777b2b42f6f09fbf67bdd568`. HK1980 geographic coordinates are converted to WGS84; retained sections are pinned by `ROUTE_ID`. The correction preserves all 2,938 previously imported road polylines and adds 52 connected island sections, for 2,990 total. The eight route XY paths remain unchanged.

## Island coast and buildings

`Data/island-shoreline.geojson` records 506 line features from 34 Lands Department iB1000 tiles: shoreline, seawall/high-water lines, and jetty/pier/wharf outlines. Source tile URLs, revision dates and archive hashes are retained. The [iB1000 catalogue](https://portal.csdi.gov.hk/geoportal/rest/metadata/item/landsd_rcd_1637223748322_25497/html) and [feature definitions](https://www.hkmapmeta.gov.hk/mcs/home/web/data/lands/iB1000.html) describe those government inputs.

`Tools/import_shoreline.py --island` converts HK1980 Grid coordinates to the existing world projection and derives the connected mainland polygon. It uses a 1 mm topology grid, a 10 cm weld and simplification within 25 cm. The result contains approximately 4,632,343 square world metres of land and 9.63 km of shore before the tunnel portal cutouts. Terrain, water, physical seawalls, promenade paving and the HUD coastline all use this boundary.

**Gap repairs are authored:** 60 recorded line joins, including repeated endpoint matches, bridge incomplete source fragments; the longest is 115.15 m around ferry-terminal/tunnel-mouth geometry. These are documented closures, not surveyed coast segments. Pier interiors, map cuts, seawall height and flat inland terrain remain approximations. The earlier western Kowloon coast is unchanged.

The island building extract was refreshed from the Lands Department [Building layer](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637211194312_35158/MapServer/0) on 8 October 2026 at 10:41 UTC. It contains 4,838 source records; SHA-256: `995215dd40513d94a7f759996d6b7d7dc9b165cd3893426f30ba6674a51a8ff2`. The regenerated layout has 5,090 visible building parts, 663 more than before, bringing the complete world to 18,035. The original, northern and western Kowloon layouts remain byte-identical to the pre-fix snapshot.

Two IFC now retains **99.91%** of its source tower footprint. Its podium area retains **99.97%** when the towers above it are included, as required by the existing upper-envelope mesher. The remaining fractions come from footprint simplification. The IFC roof is at 402.5 world metres using the existing connected-part minimum-base convention. This is massing derived from government records; facade textures, roof details and flattened ground elevations are authored.

## Scale boundary

The shared local projection is unchanged to preserve road, building and authored-placement continuity. Its approximately **0.53% north–south stretch** remains a known limitation. README and HUD measurements now explicitly say approximate. A projected-grid migration must move the whole world together; this correction does not claim surveyed metric accuracy.

## Regeneration and checks

```sh
.venv-geodata/bin/python Tools/import_shoreline.py --island --download
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/CENTERLINE.kmz --hk1980
.venv-geodata/bin/python Tools/import_buildings.py --island --download
# Execute through Blender MCP, preserving the user's scene:
# Tools/model_tunnel.py
# Tools/model_government_buildings.py with ISLAND=True
./run.command --headless -- --map-check
./run.command --headless --disable-render-loop --fixed-fps 60 -- --self-test
```

Both Blender exports were performed through MCP and restored the original active scene. Editable `.blend` files and runtime GLBs are updated. No new dependency or runtime network access was introduced.

Evidence is in `evidence/government-map-fixes-2026-10-08/`; the pre-fix assets and data are in `Art/before-government-map-fixes-2026-10-08/`. Both follow the project's local evidence/backup convention.

- `before-check.log` records the expected failed regression on the old assets: six missing decks and the missing IFC roof.
- `map-check.log` records the initial passing deck/IFC regression. The full suite also checks four island land/sea locations and 14 physical seawall locations.
- `check-data.py`, `data-check.log` and `data-check.json` validate preserved XY, original tunnel profiles, unchanged regional layouts, source level attributes, crossing clearance, ramp continuity, all island carriageways staying on land and restored IFC massing matched by persistent CSUID.
- `self-test.log` reaches `ANTILA_SELF_TEST_OK`: all eight complete routes, seven focused ramp/flyover drives, 50,337 bus-envelope queries, both original side-street turns and the three-stop H1 service complete. H1 carries 26 passengers over 1.08 km without route contacts. The sole `ANTILA_TEST_CONTACT` is the deliberate outer-barrier collision check. The build has 0 warnings / 0 errors and the log has no engine error markers.
- `verification.json` records the results and log hashes. The prior shell session was no longer available when work resumed, so its final process exit status is not claimed; the complete in-engine success marker is preserved. The native capture process exited 0.
- Native before/after views cover Central waterfront, IFC, Hoi Fai and Gloucester Road. The seven final native captures also include the Hoi Fai underpass, Hung Hing approach and updated HUD map; `compare.html` presents the before/after views.

Bridge support/guardrail detailing, terrain elevation, surveyed deck dimensions, vehicle/time-dependent turn restrictions and an end-to-end projection migration were not added in this correction.

## Self-review fixes — 11 October

The street-name HUD lookup now caches its result until the bus moves 3 m from its last lookup position. This avoids scanning 56,493 harbour road segments on every redraw. The cache uses three-dimensional displacement, refreshes immediately across the below-ground cutoff, and belongs to the scene instance so a restart starts empty. Route jumps refresh on their first lookup. The label can lag a junction by up to 3 m; road geometry and driving behavior are unchanged.

`Tools/import_shoreline.py --download` now refreshes every requested tile before recording the server's revision metadata, even when a ZIP already exists. Replacement happens after ZIP and GML validation; download, invalid-ZIP and malformed-XML failures preserve the previous archive and raw source output. Running without `--download` remains an offline rebuild from the shipped GeoJSON. No government data or assets were regenerated for these fixes.

The new `Tools/check_shoreline.py` uses isolated synthetic tiles and mocked network calls for both western Kowloon and island modes. It verifies changed geometry, revision and SHA-256 on a repeated download, plus preservation on failed refreshes. `CheckHud` covers stationary reuse, accumulated movement, vertical relocation, returning to Nathan Road and the below-ground cutoff. Both regressions were observed failing before their fixes. The HUD and existing input/camera/traffic regression suite then exited 0 with 0 build warnings / errors; both offline modes also exited 0.

```sh
.venv-geodata/bin/python Tools/check_shoreline.py
./run.command --headless --disable-render-loop --fixed-fps 60 -- --hud-check
```

Logs and the lookup microbenchmark are in `evidence/review-fixes-2026-10-11/`. The original 200-call measurement averaged 8.395 ms per lookup. After this fix, 200 cached calls averaged 0.002945 ms; 200 alternating relocations averaged 4.575 ms; 600 position updates at the equivalent of 50 km/h and 60 lookups/second averaged 0.349 ms. The benchmark process exited 0. These are synchronous lookup measurements including the script-to-C# call overhead, not overall FPS or a physical drive. Nine map/data/model hashes still match the completed correction snapshot. The full driving suite and native captures were not repeated for these two fixes; the completed map-correction results above remain their recorded evidence.


## Regional seams and Hong Chong ground — 11 October

The follow-up review found 108.381 m² of Hong Chong Road section `ID_021368` outside the authored original-district ground apron. Its north edge now extends 10 m farther, from Z = −1311.124 to −1321.124. The full 12 m carriageway and roughly 4.8 m beyond its northern edge have ground collision. This is an inland map-edge correction, not a surveyed coastline change. `Tools/import_tunnel.py` now rejects any non-tunnel carriageway extending outside the land polygon. All 2,990 road XYZ polylines, eight routes, both tube profiles and government-derived western/island coast boundaries are unchanged.

Building base datums now reconcile connected parts across the three Kowloon source extracts. The [building notes](GOVERNMENT_BUILDINGS.md#regional-height-correction--11-october-2026) describe the retained source identities and hashes. All 109 cross-region building identities now agree on height; 26 previously differed. No footprint, building count, paving patch or road clearance is changed. Island layouts and assets remain byte-identical.

The new `CheckGovernmentMap` regressions cast physical rays at Hong Chong's centre, outer lane and shoulder, and compare roof collisions on both sides of the Ping An Tower and One IGC region seams. They run under both `--map-check` and `--self-test`. On the old assets the check exited 1 with two unsupported-ground probes and both mismatched roofs. The importer assertion independently failed on `ID_021368`.

Local backups: `Art/before-map-correctness-fixes-2026-10-11/`. Evidence: `evidence/map-correctness-fixes-2026-10-11/`, including the before-failure logs, before/after data reports, Blender regeneration logs and native captures. The data audit checks all shared building identities, footprint preservation/containment, region overlaps, road XYZ/routes/tubes, road ground support and hashes of retained island/coast data and assets.

The regenerated terrain and seven Kowloon building GLBs were exported through Blender MCP; the user's original scene, objects and selection were restored. The data audit exited 0 with zero unsupported Hong Chong carriageway area, zero regional height disagreements, zero footprint changes and zero cross-region overlaps. Native rendering exited 0: all seven physical probes passed, giving 141.5 m on both Ping An roof halves, 111.7 m on both One IGC halves and Y = 0 at all three Hong Chong probes. Matching before/after views are in `compare.html`; both corrected captures were visually inspected.

The C# build completed with 0 warnings / 0 errors. The headless editor's import startup emitted one `EditorSettings not instantiated yet` diagnostic for `export/android/android_sdk_path`; the native capture log has no error markers. Android export is outside this verification.

The complete `--self-test` run exited **0** and reached `ANTILA_SELF_TEST_OK`. It passed all eight routes and seven focused ramp/flyover drives, 50,337 bus-envelope queries, 450 building roof probes, 1,981,905 facade-edge checks, both side-street turns, and the 1.08 km / three-stop / 26-passenger H1 service. The only contact marker is the deliberate outer-barrier test. Audio, HUD/cache, input/camera, footpaths and all 48 signal approaches also passed. `verification.json` records both process exit statuses and source/model/log hashes.

No Android export, performance benchmark or survey-grade terrain reconstruction was performed. Authored eastern ground edges, road widths, flattened building bases, regional facade/parapet joints and the existing approximately 0.53% north–south projection stretch remain limitations.

## Building refresh and tunnel entrance corrections — 11 October

Both findings from `evidence/map-self-review-2026-10-11/report.md` are addressed. The building importer now chooses one record's height inputs per persistent `BuildingCSUID`, ordered by extract retrieval timestamp, before deriving regional heights. The shared connected-part base calculation and regional source footprints/IDs are retained. [Snapshot precedence and regeneration instructions](GOVERNMENT_BUILDINGS.md#regional-height-correction--11-october-2026) include the original undated extract's known date and deterministic ties.

The tunnel ground importer removes the extra 5 cm buffer around already flat-ended portal cutouts. Their 5.4 m half-width still clears the exterior walls; their ends now meet the tunnel floors. The existing checks for unobstructed portal interiors remain active. `CheckGovernmentMap` adds four physical entrance probes, included in both `--map-check` and `--self-test`.

Godot vertex compression is disabled specifically for `cross-harbour.glb` in its `.import` settings. The terrain mesh spans 4.75 × 6.9 km; compression moved its portal vertices by centimetres, leaving the two Kowloon probes unsupported even after the GLB was corrected. `import-probe.gd` isolates the imported terrain and two tunnel floors: the same four rays all hit ground after compression is disabled. Keep this setting when reimporting because runtime collision is created from the imported visual meshes. The first full-suite attempt with compression enabled is retained as `compressed-self-test.log` (exit 1).

Evidence and scripts are in `evidence/map-regeneration-fixes-2026-10-11/`; originals are in `Art/before-map-regeneration-fixes-2026-10-11/`. Before the fixes, both regressions exited 1: the synthetic building refresh retained an old regional height, and the in-engine map check found two unsupported entrances. The corrected building regression exits 0, checking both a revised `TopHeight` and a missing-height/storeys fallback across separately rebuilt layouts. Its synthetic newer northern extract is confined to a temporary directory.

No new government download was made. All three Kowloon layouts were regenerated from the retained extracts; their 12,945 building parts and paving patches are byte-for-byte equal as parsed arrays. Only their provenance notes change. All nine building GLBs, the island layout, Nathan Road and coast inputs retain their hashes. The Cross-Harbour terrain asset and editable blend were regenerated through Blender MCP, restoring the user's scene, objects and selection.

`check-data.py` exits 0 and confirms all 2,990 road XYZ polylines, eight routes, both tube profiles, rendered asphalt/water triangles, coast boundaries and source features are unchanged. Comparing actual GLB ground and tunnel-floor triangles reduces the four inner-carriageway gaps from 0.186–0.223 m² to 0–0.000218 m². The remaining sub-millimetre export slivers are floating-point mesh precision; this is not a claim of mathematically watertight exported geometry.

```sh
.venv-geodata/bin/python Tools/check_buildings.py
.venv-geodata/bin/python evidence/map-regeneration-fixes-2026-10-11/check-data.py
./run.command --headless --disable-render-loop --fixed-fps 60 -- --self-test
```

The native capture process exits 0. All four entrance rays hit `HarbourGround` at Y ≈ 0; `runtime-probes.json` records the colliders. Three inspected captures show both island portals and the two Kowloon entrances: `island-portals.png`, `kowloon-portal-east.png` and `kowloon-portal-west.png`.

The final full `--self-test` exits **0** and reaches `ANTILA_SELF_TEST_OK`: all eight routes and seven focused ramp drives, 50,337 bus-envelope queries, 450 roof probes, both side-street turns, and the 1.08 km / three-stop / 26-passenger H1 service pass. The only contact marker is the deliberate barrier test. The build reports 0 warnings / 0 errors; the final self-test and native capture logs have no engine error markers. `verification.json` records process results and source, model, import-setting and evidence hashes.

No fresh government download, performance benchmark or Android export was performed. The existing authored terrain/widths and projection limits remain; these fixes do not make the prototype a surveyed reconstruction.

## Raised-road joins — 12 October

The six open deck wedges found in the latest review are closed. `Tools/model_tunnel.py` now gives connected, equal-width raised-road pairs a shared mitered cross-section. The floor, soffit, side walls and lane paint use that same section. All 18 above-ground two-section joins are stitched; resampling retains the original endpoints. Unequal widths and excessively sharp turns fail regeneration instead of producing an invalid miter. Existing floor-triangle and ramp-shoulder checks remain active.

The harbour GLB and editable blend were regenerated through Blender MCP, restoring the user's scene, objects, active object and selection. All 26 retained data/building-asset hashes still match, including all 2,990 road polylines, eight routes, both tunnel profiles and every building GLB. Of the 2,828 exported meshes, 2,701 retain identical geometry; changes are confined to raised-road floors, slab sides/soffits and their paint. Ground, coastline and tunnel geometry are unchanged.

`CheckGovernmentMap` adds six physical lane-support probes, used by both `--map-check` and `--self-test`. They all failed on the old asset (`map-before.log`, exit 1), then passed after regeneration. `check-data.py` independently confirms matching exported border vertices at all 18 joins and reduces the missing floor area in all six measured 1 m neighbourhoods to zero. A 508,437-ray scan now has eight misses, down from 31. The remaining samples lie within 0.409 mm of an exported floor boundary; local grid probes and `remaining-boundaries.json` retain the precision evidence. This is not a claim that every exported mesh edge is mathematically watertight.

The complete `--self-test` exited **0** with `ANTILA_SELF_TEST_OK`: all 15 harbour drives, 50,337 bus-envelope queries, both side-street turns and the 1.08 km / three-stop / 26-passenger H1 service passed. No route contacts occurred; the sole contact marker is the deliberate barrier test. The C# build reports 0 warnings / 0 errors. The native capture process also exited 0, and all 12 targeted rays hit road decks at their expected heights. Matching Tonnochy and Sham Mong before/after captures were visually inspected. The final native and self-test logs have no engine error markers.

Evidence and reproduction scripts: [`evidence/deck-join-fixes-2026-10-12/`](../evidence/deck-join-fixes-2026-10-12/), including [before/after views](../evidence/deck-join-fixes-2026-10-12/compare.html), `data-check.json` and `verification.json`. Originals are in `Art/before-deck-joins-2026-10-12/`.

No fresh government download, performance benchmark or platform export was performed. Authored road widths/heights, flattened terrain and the existing projection limits remain.
