# Cheung Sha Wan / Lai Chi Kok expansion

The map continues north and west from Sham Shui Po through Cheung Sha Wan to Lai Chi Kok. Press **N while stopped** to start the **2.924 km exploration drive**; **M** opens the map and **R** returns to H1. The route connects to the existing Mong Kok → Sham Shui Po endpoint and follows Lai Chi Kok Road, Butterfly Valley Road, Cheung Sha Wan Road and Mei Lai Road to the Lai Wan Road junction. It is an authored itinerary, without new passenger stops or turn-by-turn guidance.

Overall bounds are **6.81 km east–west × 8.23 km north–south**, `[-4680,-6080,2130,2150]` in world X/Z. The added selection rectangle is `[-4600,-6000,0,-3900]`. This is approximately metre scale: the established local projection stretches north–south distances by about 0.53%. Bounds describe the loaded region, not uninterrupted drivable roads or surveyed terrain.

## Government sources and preservation

**Roads:** © HKSAR Government / Transport Department, [Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2), [official centreline KMZ](https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz). Downloaded 12 October 2026 UTC: 125,565,141 bytes; SHA-256 `dcd0632d9d0f72bee549e24307b28ed98b17963c30899de0675d5e1163586735`. The importer converts HK1980 geographic coordinates (EPSG:4611) to WGS84 before using the existing local projection. Stable `ROUTE_ID` matches retain earlier snapshots.

The extension adds **445 connected road sections**, for **3,435 total expansion sections and nine exploration routes**. The new drive uses 31 explicit source sections and follows their travel-direction attributes. Source direction does not establish real vehicle restrictions or permitted turns. The original 437-section Nathan Road dataset remains separate.

All **2,990 prior road objects, eight routes, two tunnel profiles and retained source records** are unchanged. Both H1 data files remain byte-identical. The 267 existing tunnel and raised-deck position/index streams also match the pre-expansion GLB, retaining the preceding ramp and deck-join fixes. Earlier western and island shoreline extracts are preserved.

**Coast:** © HKSAR Government / Lands Department, [iB1000 tile index](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0/query). A separate 40-tile GML extract contains 114 Shoreline / seawall / high-water fragments. WGS84 query bounds: `[114.127,22.329,114.173,22.350]`; retrieved `2026-10-12T14:43:55.197233+00:00`. Raw `Data/lai-chi-kok-shoreline.geojson` SHA-256: `b1776537e0d7bc774dc434f51762b06a84f5f8511d2c1f292c1fef3aeaec9494`. Each tile URL, revision and hash is recorded in metadata.

EPSG:2326 GML northing/easting order is corrected before transformation. The derived boundary uses the existing 1 mm topology grid and simplification within 0.25 m; this extract needs **no straight gap closures**. Its land is merged only outside the previous western selection rectangle, preserving the old land/coast footprint exactly and adding **7.173 km² of land**. The merged western coastline is 7.492 km, 903 m longer than before. Inland map cuts, flat ground and seawall height are authored. Small separate islands/breakwaters and surveyed hills are not reconstructed.

**Buildings:** © HKSAR Government / Lands Department, [CSDI building catalogue](https://portal.csdi.gov.hk/csdi-webpage/dataset/landsd_rcd_1637211194312_35158), [source query](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637211194312_35158/MapServer/0/query). The count-checked extract has **4,504 records**, with unique OBJECTIDs. WGS84 bounds: `[114.12765895235972,22.33003413582465,114.17232,22.348898670499462]`; retrieved `2026-10-12T14:35:03.543939+00:00`. Raw `Data/lai-chi-kok-buildings.geojson` SHA-256: `49cf3ed1e6f6b8aca63b9b06c3ffd25dd47439324a7e6fa151db30b6ff4d92d2`.

The new layout contains **2,799 derived parts from 2,598 source IDs**, with **817,324 m² of footprints** and 200 paving patches. Prior regions, water and road clearances are excluded. 481 retained source parts use the existing missing-height fallback. Shared base datums and latest roof/storey inputs are reconciled across all four Kowloon extracts; each derived layout records all four hashes.

Original Kowloon and northern building/paving arrays are unchanged. The western layout becomes 6,082 parts: 84 retained source IDs have derived geometry/height changes and two IDs are removed for new road clearance. Eleven heights change because newly connected source groups supply lower base datums; the 1,895 shared western/northwestern source records have unchanged height inputs. All 158 building identities retained in more than one region have identical derived heights. The island layout and models are unchanged.

## Models and scene

Three new GLBs use the existing 128 m render/collision chunks and facade/shop atlases:

- `Assets/Models/lai-chi-kok-west-buildings.glb`
- `Assets/Models/lai-chi-kok-buildings.glb`
- `Assets/Models/cheung-sha-wan-buildings.glb`

Editable source: `Art/lai-chi-kok-buildings.blend`. The four western GLBs and harbour model are regenerated at the changed boundary. Blender MCP runs each generator in its own scene and restores the user's original scene, objects, selection and active object. No additional image or passenger assets were generated.

The whole scene contains **20,832 building parts, 1,403 render/collision chunk pairs and 2,281 paving patches**. Existing trees, lamps, scanned posed pedestrians and kiosks furnish the extension. The new district has 48 pedestrians and 12 kiosks; all expansion regions total 497 trees, 1,904 lamps, 304 pedestrians and 78 kiosks. Placement uses the existing building, road and coast clearance rules.

The expanded surface mask is capped at 16,384 pixels per axis, with pixel density reduced proportionally only when required. World-coordinate mapping stays unchanged. This prevents the new north–south extent requesting a 16,460-pixel texture. The mask cap has an in-engine boundary regression.

## Regeneration

Run from the repository using the existing `.venv-geodata` environment:

```sh
.venv-geodata/bin/python Tools/import_shoreline.py --northwest --download
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/CENTERLINE.kmz --hk1980
.venv-geodata/bin/python Tools/import_buildings.py --northwest --download
.venv-geodata/bin/python Tools/import_buildings.py --west
.venv-geodata/bin/python Tools/import_buildings.py --north
.venv-geodata/bin/python Tools/import_buildings.py
```

Omit `--download` to use the bundled extracts. Preserve `Data/cross-harbour-source.geojson` to pin earlier geometry. Through **Blender MCP**, execute `Tools/model_tunnel.py`, then `Tools/model_government_buildings.py` with `NORTHWEST=True` and separately with `WEST=True`. Re-export any other regional model if its derived building array changes. Never run modeling scripts with ordinary Python.

## Verification — 12–13 October 2026

Evidence directory: `evidence/lai-chi-kok-expansion-2026-10-12/`. The date identifies the start of the work; final validation continues on 13 October Hong Kong time. Baseline snapshots are in `Art/before-lai-chi-kok-expansion-2026-10-12/`. The expansion-only source diff excludes older uncommitted map work.

- `data-check.log`: earlier roads/routes/profiles/source records and coast preserved; new carriageways are on land; source-direction checks pass.
- `building-check.log`: new footprints are valid and on land; no overlap with prior regional building parts.
- `model-check.log`: all source hashes and 1,403 render/collision chunk pairs match; 158 cross-region building identities have equal heights; 267 existing tunnel/deck mesh streams are unchanged.
- `shoreline-regression.log` and `building-refresh-regression.log`: importer safety and shared height refresh checks pass.
- `northwest-check.log`: exit 0; **2,910 m physically driven without contacts or departures**, 321 lane-support probes, shortcut guards for movement/map/pause/completion, 7,837 asphalt/paving samples and 61,335 expansion bus-envelope queries pass. Build: **0 warnings / 0 errors**. Centreline and driven lengths differ due to lane offset and cornering.
- `self-test.log`: **exit 0 / `ANTILA_SELF_TEST_OK`**; all nine complete routes, seven focused ramp/flyover drives, both side-street turns and the original 1.08 km H1 service pass, with three stops and 26 passengers. Building, footpath, paint, audio, HUD, camera and signal regressions pass. Build: **0 warnings / 0 errors**; no engine errors. The single `ANTILA_TEST_CONTACT` is the intentional boundary-collision test.
- `capture-final.log`: **exit 0**; final native GL Compatibility capture and N input event pass on the rebuilt assembly. Eight final views cover two matching aerial cameras, three street/seam views, coastline, cab and full map. The Sham Shui Po label is spaced clear of the expanded road network. See the [before/after comparison](../evidence/lai-chi-kok-expansion-2026-10-12/compare.html).
- `restart-check.log`: **exit 0**; four reloads from paused map, island drive, northwest drive and completed service restore H1 with **2,806 meshes / 1,403 collision shapes**, no engine errors, and 519 roof probes plus 2,281 paving samples passing in each rebuilt scene. `restart-stale-build.log` is a superseded three-reload run: a source edit landed during compilation, and incremental building reused the earlier DLL. A forced nonincremental build (`rebuild.log`, 0 warnings/errors) and compiled-marker check replace that result. The full simulation run precedes only the final map-label spacing adjustment and four-reload test update; gameplay implementation is unchanged. `rebuilt-assembly.json` records the assembly used by the corrected restart and final native capture.

The independent final review reports no concrete correctness/regression findings; both conditional gates (four reloads and the final map capture) are complete. See `final-review.md` for scope and coordinator rulings.

Road widths, elevations, terrain, facades and street details remain authored approximations. The new drive adds no passenger service, traffic-light phases, walking animation or traffic routing. No performance benchmark or surveyed 3D reconstruction is claimed. [TD terms](https://data.gov.hk/en/terms-and-conditions) and [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC) apply. No Google Maps imagery/meshes are used; gameplay remains offline.
