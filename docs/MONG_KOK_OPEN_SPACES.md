# Mong Kok open spaces — 18 October 2026

The empty-area review found both missing building components and genuine open sites. The importer repair restores 24 previously dropped building sections across northern and western Kowloon. The scenery work details four confirmed sites within the existing map. It does not move the eastern coverage boundary or invent buildings at the Sai Yee Street development site.

## Sources and boundaries

Site and sports outlines © HKSAR Government / Lands Department, from **iB1000** GML downloaded through the CSDI sheet index. Twelve sheets were retrieved on **19 October 2026 UTC / 18 October local**. The source GeoJSON records every tile URL, revision timestamp, SHA-256, source feature ID, status, feature date and coordinate conversion. GML EPSG:2326 northing/easting/height is converted to WGS84, then to the existing local game origin. Tile-edge pieces sharing an ID are united before clipping. Existing-status features only are used.

- [iB1000 feature definitions](https://www.hkmapmeta.gov.hk/mcs/home/web/data/lands/iB1000.html): Site and BuiltStructurePolygon; FOF football field, BAC basketball court, TEC tennis court, RAT race track.
- [CSDI tile service](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0) and [reuse terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC).
- [LCSD hard-surface pitches](https://www.lcsd.gov.hk/clpss/en/webApp/Facility/Details.do?ftid=43) identifies Anchor Street's two five-a-side pitches and MacPherson's seven-a-side pitch.
- [LCSD Cherry Street facilities](https://www.lcsd.gov.hk/clpss/en/webApp/Facility/Details.do?ftid=26) confirms the artificial-turf pitch, four tennis courts and two basketball/volleyball courts.

| Site | Source Site ID | Source area | Authored trees / benches |
| --- | --- | ---: | ---: |
| Anchor Street Playground | 1503005174 | 9,320.14 m² | 19 |
| MacPherson Playground | 1503005482 | 6,437.34 m² | 0 |
| Cherry Street Park | 1503005201 | 40,285.06 m² | 114 |
| Diocesan Boys' School grounds | 1503005534 | 77,700.73 m² | 141 |

The MacPherson courts receive surfaces, markings, hoops and goals; its remaining narrow margins do not admit extra furniture under the road/building clearance rules. The gap near Olympian City 3 is not wholly within the sourced Cherry Street Park boundary and is not filled as parkland.

## Authored interpretation

Seventeen sports surface polygons retain the sourced shapes and holes, clipped clear of building footprints and authored road widths. Fifteen intact rectangular courts receive Blender-authored markings and fittings; Anchor Street's grouped source outline is divided into two pitches. Goals, hoops, nets and line layouts are approximate. The school field and track are flattened to the current game terrain; the real hillside, entrances and level changes are not reconstructed.

Planting and furniture comprise **114 street trees, 59 banyans and 101 benches**, using the existing textured assets. Their positions and the perimeter/court paths are authored, not surveyed. The source sites constrain placement; buildings, roads and sports areas are excluded. Paving and sports colours are blended into the existing single terrain surface, preserving road priority and avoiding overlapping ground meshes. The GLB contains only court markings and fittings, with separate hidden collision meshes for solid fixtures.

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
