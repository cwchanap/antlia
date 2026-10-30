# Mong Kok open spaces — updated 21 October 2026

The 24 October [Wong Tai Sin extension](WONG_TAI_SIN_EXPANSION.md) refreshes input provenance and deterministically regenerates 324 fixtures (193 trees, 125 benches, six planters). The one fewer school bench is authored reflow; park/path geometry and source sports remain unchanged. Older counts below describe their recorded snapshots.

The empty-area review found both missing building components and genuine open sites. The importer repair restores 24 previously dropped building sections across northern and western Kowloon. The scenery work now details nine confirmed sites within the existing map, including five pocket gardens/playgrounds added after the 20 October gap review. It does not move the eastern coverage boundary or reconstruct the Sai Yee Street development site.

## Sources and boundaries

Site and sports outlines © HKSAR Government / Lands Department, from **iB1000** GML downloaded through the CSDI sheet index. Twelve sheets were retrieved on **19 October 2026 UTC / 18 October local**. The source GeoJSON records every tile URL, revision timestamp, SHA-256, source feature ID, status, feature date and coordinate conversion. GML EPSG:2326 northing/easting/height is converted to WGS84, then to the existing local game origin. Tile-edge pieces sharing an ID are united before clipping. Existing-status features only are used.

- [iB1000 feature definitions](https://www.hkmapmeta.gov.hk/mcs/home/web/data/lands/iB1000.html): Site and BuiltStructurePolygon; FOF football field, BAC basketball court, TEC tennis court, RAT race track.
- [CSDI tile service](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0) and [reuse terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC).
- [LCSD hard-surface pitches](https://www.lcsd.gov.hk/clpss/en/webApp/Facility/Details.do?ftid=43) identifies Anchor Street's two five-a-side pitches and MacPherson's seven-a-side pitch.
- [LCSD Cherry Street facilities](https://www.lcsd.gov.hk/clpss/en/webApp/Facility/Details.do?ftid=26) confirms the artificial-turf pitch, four tennis courts and two basketball/volleyball courts.

| Site | Source Site ID | Source area | Authored fixtures |
| --- | --- | ---: | ---: |
| Anchor Street Playground | 1503005174 | 9,320.14 m² | 19 |
| MacPherson Playground | 1503005482 | 6,437.34 m² | 0 |
| Cherry Street Park | 1503005201 | 40,285.06 m² | 114 |
| Diocesan Boys' School grounds | 1503005534 | 77,700.73 m² | 141 |
| Ivy Street Rest Garden | 1503005143 | 3,646.11 m² | 17 |
| Mong Kok Road Playground | 1503005266 | 3,918.03 m² | 13 |
| Cherry Street Sitting-out Area | 1503005193 | 716.70 m² | 5 |
| Sai Yee Street Garden | 1503005468 | 2,267.98 m² | 7 |
| Waterloo Road/Ferry Street Sitting-out Area | 1810041992 | 1,757.65 m² | 9 |

The MacPherson courts receive surfaces, markings, hoops and goals; its remaining narrow margins do not admit extra furniture under the road/building clearance rules. The gap near Olympian City 3 is not wholly within the sourced Cherry Street Park boundary and is not filled as parkland.

## Authored interpretation

Seventeen sports surface polygons retain the sourced shapes and holes, clipped clear of building footprints and authored road widths. Fifteen intact rectangular courts receive Blender-authored markings and fittings; Anchor Street's grouped source outline is divided into two pitches. Goals, hoops, nets and line layouts are approximate. The school field and track are flattened to the current game terrain; the real hillside, entrances and level changes are not reconstructed.

Planting and furniture comprise **126 street trees, 67 banyans, 126 benches and six planters**, using the existing textured Blender assets. Their positions and the perimeter/court paths are authored, not surveyed. The source sites constrain placement; buildings, roads and sports areas are excluded. Paving and sports colours are blended into the existing single terrain surface, preserving road priority and avoiding overlapping ground meshes. The GLB contains court/play markings and fittings, with separate hidden collision meshes for solid fixtures.

The five pocket sites add 5,364.84 m² of authored paving, with nominal four-metre circulation spines kept clear of furniture and clipped around buildings and roads. Their names were cross-checked against the [LCSD Yau Tsim Mong venue directory](https://www.lcsd.gov.hk/clpss/en/webApp/ContactAccessDetails.do?lsb=YTM&type=lsb&value=YTM). The narrow Cherry Street and Waterloo/Ferry Street sites use planters where tree crowns would crowd the paths. Mong Kok Road Playground has no sports polygon in the retained source: its 10 × 14 m play pad, hopscotch and ring markings are explicitly authored and stored separately in `play_areas`. They do not claim to reproduce the real equipment layout.

The single authored play pad uses its saved centre, direction and dimensions directly in the terrain shader, after paving/edging and before asphalt. Its edge is antialiased in screen space rather than sampled from the large map mask. The seventeen sourced sports surfaces continue using the recreation mask. This preserves the small rectangle as the wider map grows, without changing geometry, road priority or the existing paving expansion used to cover narrow gaps.

All four earlier sites retain their source geometry, sports surfaces, paving and 274 fixtures. Pui Ching Road and Wah Yan College remain larger follow-ups. The broad Olympian City and Sai Yee/Argyle gaps require more land-use evidence.

## Regeneration

The game runs offline. Python, Shapely and pyproj are used only when regenerating data.

```sh
.venv-geodata/bin/python Tools/import_open_spaces.py
# Re-extract downloaded source sheets when deliberately refreshing:
.venv-geodata/bin/python Tools/import_open_spaces.py --extract CACHE_DIR TILE_SOURCES_JSON
# Regression checks use temporary outputs and the same downloaded sheets:
.venv-geodata/bin/python Tools/check_open_spaces.py CACHE_DIR TILE_SOURCES_JSON
```

`Data/mong-kok-open-spaces-source.geojson` retains selected raw geometry and provenance. `Data/mong-kok-open-spaces.json` is the derived runtime layout, with source and dependent building/road hashes. The importer requires the complete twelve-sheet selection declared beside its fixed site list and bounds, with both Site and BuiltStructurePolygon layers in every ZIP. Each required layer must contain recognized feature members; both layers are populated on every sheet in this fixed selection. It checks source-ring continuity, SHA-256, site containment, valid triangulation with retained holes, and road/building clearance. Extraction and derivation finish before either output is replaced; both files are staged, and a reported replacement failure restores any already-replaced file. Rejected extraction or derivation preserves both previous files. The normal offline rebuild also validates its cached sheet selection. Run `Tools/model_open_spaces.py` **through Blender MCP** to export `Assets/Models/mong-kok-recreation.glb` and `Art/mong-kok-recreation.blend`; it uses an isolated scene and restores the user's previous scene.

## Verification and evidence

Evidence is stored locally in `evidence/mong-kok-fix-2026-10-18/`; original overview views remain in `evidence/mong-kok-space-review-2026-10-18/`.

- `regression-before.log` / `regression-after.log`: missing-component regression fails before the shared importer fix and passes afterward; existing download/cache-preservation and height-refresh checks also pass.
- `preservation.json`: all existing northern/western building parts remain identical; 24 additional parts are recovered.
- `building-check.log`: initial in-engine building, surface, road and footpath checks pass, including 776 sampled roof probes, 17 sports-surface samples and 15 court collision meshes.
- `capture.gd` / `capture.log`: matched overview cameras and close views of the four sites and restored podium. `court-capture.gd` / `court-capture.log` replaces the obstructed tennis view and adds a ground-level detail. [Before/after gallery](../evidence/mong-kok-fix-2026-10-18/compare.html).
- `source-model-audit.log`: roads, service routes and the two raw building caches remain byte-identical; source/input hashes and all 15 GLB render/collision pairs match.

The first full run (`self-test.log`) passed all twelve exploration drives and seven ramp/flyover drives, then caught a decoration occupying H2's Wong Chuk Street shelter space. `stop-survey.log` isolates the cause to decorative scenery; all eight H2 bays remained clear for a pole. Routes now load before decoration placement so stop furniture and queue space can be reserved. The route's original six shelters / two poles, distances and passenger totals are retained, and the route checks also verify that every generated street/park detail stays outside the reserved space.

### Final verification — 19 October 2026

`self-test-final.log` exits 0 with `ANTILA_SELF_TEST_OK`. The final build reports **0 warnings / 0 errors**; no engine errors are logged in the final suite or final native capture. The run covers:

- 31,404 building parts in 2,456 render/collision chunk pairs, 776 general roof probes and five targeted probes for the reported missing buildings.
- All 17 recreation-surface samples, 274 clear tree/bench fixtures and 15 court collision meshes; road, footpath, audio, HUD and signal regressions.
- 96,822 bus-envelope clearance probes, all twelve exploration drives and seven ramp/flyover drives without contacts.
- Service menus/results and H1, H2 and H3 driven terminus to terminus: 3/8/4 stops, 26/60/33 passengers, no contacts or red-light violations. H2 retains its six shelters and two poles, including the Wong Chuk Street shelter.
- Both side-street turns and the original H1 driving check. The deliberately commanded outer-barrier impact remains part of that test.

`capture-final.log` exits 0 and records twelve native OpenGL views. The site views and the protected H2 shelter were visually reviewed; the gallery includes four matched overview cameras and the clearer Cherry Street overhead/ground-level views. `implementation-sha256.json` records the final local files. The earlier failed full run is retained as evidence of the stop-space regression and its diagnosis.

The game still uses flat terrain and authored paths, planting, fittings and facades. The eastern coverage edge and unverified Sai Yee Street development site are unchanged. No performance benchmark or surveyed 3D reconstruction is claimed.

### Review repairs — 19 October 2026

The refresh guard now rejects an incomplete twelve-sheet manifest, duplicate/wrong sheets, missing required layers and invalid ZIP hashes. It derives and stages the complete source/runtime pair before replacement and rolls back reported replacement failures. `Tools/check_open_spaces.py` passes a real complete refresh, an identical offline rebuild, and 13 rejection/write-failure preservation cases using temporary outputs. The saved government source and runtime layout remain byte-identical. Logs are in `evidence/mong-kok-review-fixes-2026-10-19/refresh-regressions.log`.

The rebuilt Blender asset corrects Anchor Street's split pitches to run across the combined outline, with approximately 37.96 m goal-to-goal length, 34.11 m width and retained 3 m five-a-side goals. The modeling source checks that every generated fitting stays within its source half. A new engine regression probes the four real goal crossbars on the corrected axis and checks their exported bounds. `pitch-regression-before.log` confirms that the previous asset fails this check for the reported orientation error.

The model was exported through Blender MCP, with the user's original scene restored (`blender-recreation.log`). `asset-preservation.json` confirms that only Anchor Street's visual/collision geometry changed: the other 14 courts' 28 objects retain identical geometry and transforms.

`building-check-final.log` exits 0 with **0 warnings / 0 errors**, including `ANTILA_ANCHOR_PITCHES_OK`, all 17 recreation surfaces, 274 clear fixtures, 15 court collision meshes, restored roofs, road markings, paving and footpath checks. `capture.log` exits 0 with three native OpenGL captures and no engine errors. The matched Anchor Street view, overhead pitch view and Wong Chuk Street shelter clearance were visually inspected. [Before/after gallery](../evidence/mong-kok-review-fixes-2026-10-19/compare.html). `final-sha256.json` records the verified files.

Government source and runtime layout bytes remain unchanged. Internal pitch markings remain authored approximations inside the combined sourced outline. The full driving suite was not repeated for these importer and park-fitting repairs; its earlier result is recorded above.

### Empty-layer follow-up — 19 October 2026

The next review reproduced a remaining gap: a syntactically valid but empty `Site` layer in `11-NW-15C` retained all twelve manifest entries and a matching ZIP hash, yet silently removed 15,768.16 m² from the school grounds. Extraction now rejects any required layer with no recognized feature members before either saved file can be replaced. This guard is specific to the fixed twelve-sheet selection, whose required layers are all populated; a deliberate change to that source contract needs review.

`evidence/mong-kok-empty-layer-fix-2026-10-19/regression-before.log` fails on `empty_Site: invalid refresh accepted`. After the fix, `regression-after.log` exits 0 with **17** rejected refresh/write-failure cases preserving both old files and leaving no staging directory. New cases cover empty collections and unrecognized feature namespaces in both `Site` and `BuiltStructurePolygon`. The real complete refresh and identical offline rebuild also pass.

`building-check.log` exits 0 with **0 warnings / 0 errors** and no engine errors, covering road and pavement checks, 31,404 building parts, the four corrected goal frames, 17 recreation surfaces, 274 fixtures and 15 court collision meshes. Source/runtime data and model assets remain byte-identical (`preservation.json`). The importer/test changes and verification files are recorded in `final-sha256.json`. Native captures and the full driving suite were not repeated for this importer-only repair.

### Five pocket gardens — 20 October 2026

Evidence is in `evidence/mong-kok-pocket-gardens-2026-10-20/`. The [comparison gallery](../evidence/mong-kok-pocket-gardens-2026-10-20/compare.html) contains six matched before/after views and two new detail views, all visually inspected. The bounded infill adds 20 trees, 25 benches, six planters and one authored play pad across the five recommended sites. The wider unresolved gaps remain for separate land-use research.

- `build.log`: **0 warnings / 0 errors**.
- `refresh-check-final.log`: `ANTILA_POCKET_GARDEN_DATA_OK` and `ANTILA_OPEN_SPACE_REFRESH_OK`. Checks cover all five complete source areas, paving and furniture containment, road/building/access clearance, a separate authored play pad, a complete refresh, an identical offline rebuild and 17 rejected refresh/write-failure cases.
- `self-test.log`: `ANTILA_SELF_TEST_OK`, including eight new paving probes, all 325 recreation fixtures, 18 sports/play surface probes and 15 court collision meshes. All exploration/ramp drives, H1/H2/H3 service drives, stop reservations, side-street turns and existing gameplay checks pass. Service drives report no contacts or red-light violations; the intentionally commanded barrier contact remains part of the original test.
- `capture.log`: `ANTILA_POCKET_GARDEN_CAPTURE_OK`, with eight native OpenGL captures and no runtime errors. Paving, furniture and playground paint are visible; the small Cherry and Waterloo sites remain confined to their mapped outlines.
- `preservation.json`: the four earlier sites, 17 sourced sports surfaces, 274 fixtures, 7,217 paving triangles and 32 retained source features are unchanged. The original twelve-sheet manifest is unchanged, and 74 other data/model files retain their hashes.
- `asset-preservation.json`: all 30 earlier Blender court/collision objects retain identical geometry and transforms. Only the flat playground paint object was added. Blender MCP export restored the user's original scene; earlier assets are retained under `Art/before-mong-kok-pocket-gardens/`.

The game and capture completion markers are retained, but their process handles expired across an interrupted chat turn, so final process exit codes are not claimed. The editor import returned 0 and logged an Android SDK settings teardown diagnostic; the game test and capture logs contain no errors. `verification.json` records these distinctions, and `final-sha256.json` records the delivered files.

### Play-pad edge correction — 20–21 October 2026

The subsequent review found that conservative paving expansion and the capped harbour mask covered the play-pad edges. Evidence for the correction is in `evidence/mong-kok-play-pad-fix-2026-10-20/`.

- `regression-before.log` exits 1 with `Paving erases the play-pad edge`; the new check reproduces the defect using the actual terrain shader in an isolated native viewport.
- `regression-after.log` exits 0. `ANTILA_PLAY_BOUNDARY_OK` covers 72 inside/outside probes, 25 cm either side of all four edges, plus the centre. `ANTILA_PLAY_RENDER_OK` additionally proves asphalt still wins over the play surface. The existing road, building, recreation, asset-detail and footpath checks pass in the same run.
- `build.log` reports **0 warnings / 0 errors**. `data-preservation.json` records 172 unchanged data, model and regeneration-tool files and passing source/layout checks.
- `before-play-boundary.png` and `play-boundary.png` show the final material blend with flat diagnostic textures. `render-area.json` measures approximately **139.25 m²** of visible play colour against the authored **140 m²**, within the antialiased edge. This thresholded image measurement differs from the review's base-mip colour-weight measurement.
- `capture.log` exits 0 with `ANTILA_PLAY_PAD_FIX_CAPTURE_OK`, eight native screenshots and no runtime errors. The [before/after gallery](../evidence/mong-kok-play-pad-fix-2026-10-20/compare.html) shows the restored outline. Five views away from the play pad are pixel-identical to the earlier captures; the other three change only around the pad (`image-comparison.json`).

Run `./run.command -- --building-check` for the native rendered regression. It also runs in the native full self-test. Headless checks verify the saved play parameters but explicitly print `ANTILA_PLAY_RENDER_SKIPPED`, since the GPU image check requires a renderer. The full driving suite was not repeated for this material-only correction.
