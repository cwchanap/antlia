# West Kowloon / Sham Shui Po — 7 October 2026

The 8 October 2026 [government-map corrections](GOVERNMENT_MAP_FIXES.md) supersede the earlier island boundary, flattened elevated-road geometry and exact-metre-scale wording below. Earlier verification records apply to their original snapshots.

The map now reaches the western Kowloon coast and continues north into Sham Shui Po. Overall bounds are **4.91 km east–west × 7.03 km north–south**, at one world unit per metre. The added region is bounded by `[-2700,-4800,650,50]` in world X/Z, with its western edge cut to government-derived shoreline.

Press **L while stopped** to begin the **6.159 km West Kowloon → Tai Kok Tsui → Sham Shui Po drive**, starting on Austin Road West. Its 71 explicit source sections pass Museum Drive, Nga Cheung Road, Lin Cheung Road, the Hoi Fai Road junction, Sham Mong Road, Tonkin Street and Yen Chow Street. The existing **K** drive also connects to a **1.770 km Mong Kok → Sham Shui Po continuation**, using 29 sections through Nathan Road, Cheung Sha Wan Road, Yen Chow Street, Yu Chau Street and Pei Ho Street. **M** opens the map; **R** returns to H1. These are exploration routes, without new stops or turn-by-turn navigation.

## Roads and preservation

© HKSAR Government / Transport Department, [Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2). The cached [CENTERLINE.kmz](https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz) was retrieved at `2026-10-05T13:24:30.608844+00:00`, SHA-256 `108319d165d1059522db6e7506d888c9da78a2c8777b2b42f6f09fbf67bdd568`. New geometry converts HK1980 geographic EPSG:4611 to WGS84 EPSG:4326 before the existing local metre projection.

The extension adds **1,367 source sections**, bringing the expansion dataset to **2,938 sections / eight routes**. Stable `ROUTE_ID` values pin earlier snapshots. All 1,571 preceding road objects, six routes, two tube definitions and twelve tunnel mesh position/index streams are unchanged. Original `Data/nathan-road.json` and `Data/roads.geojson` are byte-for-byte unchanged. Earlier buildings near new connecting roads are trimmed by the existing clearance rules; their GLBs are therefore regenerated.

General additions are connected, named, ground-level streets inside the land region with a 12 m margin, excluding restricted roads and major highway/crossing corridors. Explicit connectors are also retained. New selected drives respect the source travel-direction codes: 1 both ways, 2 reverse digitized direction, 3 forward; 4 restricted is excluded. This does not infer junction turn restrictions or vehicle-specific permissions. Route assembly checks joins within 12 cm and rejects sharp reversals.

Five added sections carry source `ELEVATION=1` and are **flattened to the prototype's ground plane**: `TD_106798` on Nga Cheung Road, and `TD_107043`, `TD_107048`, `TD_106254`, `TD_106173` on Hoi Fai Road. ELEVATION is a relative road level, not a surveyed height. The western drive uses the Nga Cheung connector; the Hoi Fai connectors remain explorable. Road widths, junction paint and vertical geometry remain authored.

## Shoreline

© HKSAR Government / Lands Department, [iB1000 CSDI catalogue](https://portal.csdi.gov.hk/geoportal/rest/metadata/item/landsd_rcd_1637223748322_25497/html). `Tools/import_shoreline.py` queries the [tile index](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0/query) for WGS84 bounds `114.145,22.290,114.175,22.339` and downloads **46 official GML tile archives**. Each tile URL, revision date and SHA-256 is retained in the raw metadata. Retrieval time: `2026-10-07T01:04:30.039432+00:00`.

The 333-fragment extract combines existing Shoreline features with CartoHydroLine `SW` seawall and `HW` high-water features. GML positions are northing/easting/height in **EPSG:2326**; the importer swaps the first two axes for the explicit easting/northing transform. Raw file: `Data/west-kowloon-shoreline.geojson`, SHA-256 `1bdc4dfacacd5846cac334c2eb5ac58a8eb560b1837153375d2ce72a8a3ed99b`. Derived boundary: `Data/west-kowloon-coast.json`.

The mainland exterior uses a 1 mm topology grid and coastline simplification within 0.25 m. **24 straight gap closures**, individually recorded in metadata, repair source discontinuities; the longest is **8.559 m**, below the 12 m importer limit. These repairs are authored. The western land polygon joins the established district at X = −900; the inland rectangle, north/east map cuts, earlier eastern Tsim Sha Tsui apron and island shore remain authored. Small separate breakwaters/islets are omitted. The rendered western shoreline is **6.589 km**, including the West Kowloon peninsula and Yau Ma Tei typhoon-shelter shape. Seawall height is authored, with collision along the sourced horizontal edge.

## Buildings and street detail

© HKSAR Government / Lands Department, [CSDI building layer](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637211194312_35158/MapServer/0). `Data/west-kowloon-buildings.geojson` contains **11,816 records** from a count-checked, unique-OBJECTID extract. Download: `2026-10-07T01:00:28.312229+00:00`; WGS84 bounds `114.14610590681984,22.294550844412505,114.17863080021004,22.33811893639957`; SHA-256 `cd0360e42114d9a6af94e2b9cf34bf2d40f8fbe85fd84a7982d2e35451d2c435`.

The derived western layout excludes both earlier Kowloon regions and clips footprints to land and street clearances. It contains **6,084 parts from 5,344 source IDs**, covering **1,881,511 m²**, plus 838 paving patches. 545 source parts use the existing height fallback. The whole scene now contains 17,372 parts and 1,051 render/collision chunk pairs, with 2,041 paving patches. Region totals: 1,759 original Kowloon, 5,102 prior northern, 6,084 new western/northern, and 4,427 island parts.

Blender MCP exports four new GLBs from the isolated `CSDI_KowloonWest` scene, with 413 chunk pairs included exactly once:

| Asset | Size |
| --- | --- |
| `west-kowloon-buildings.glb` | 16.49 MB |
| `tai-kok-tsui-buildings.glb` | 41.12 MB |
| `sham-shui-po-west-buildings.glb` | 88.36 MB |
| `sham-shui-po-east-buildings.glb` | 70.32 MB |

Editable source: `Art/west-kowloon-buildings.blend`. Splits follow existing 128 m chunks; modeling restores the previous Blender scene. Existing generated facade/shop atlases are reused. Street detail adds 96 posed pedestrians and 24 kiosks; all expansion areas now have 429 trees, 1,491 lamps, 256 posed pedestrians and 66 kiosks, with placement clear of buildings, carriageways and shoreline.

Facades, vegetation, street furniture, flat terrain and seawalls are stylized. The map does not reconstruct surveyed hills, elevated interchanges, real shops, parks or every pier. No additional traffic-light phases, passenger services or performance benchmark are claimed. [TD terms](https://data.gov.hk/en/terms-and-conditions) and [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC) apply. No Google Maps imagery or meshes are used; runtime is fully offline.

## Regeneration and evidence

```sh
.venv-geodata/bin/python Tools/import_shoreline.py --download
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-centerline.kmz --hk1980
.venv-geodata/bin/python Tools/import_buildings.py --west --download
.venv-geodata/bin/python Tools/import_buildings.py --north
.venv-geodata/bin/python Tools/import_buildings.py
# Through Blender MCP: Tools/model_tunnel.py
# Through Blender MCP: Tools/model_government_buildings.py with WEST=True
# Repeat the building model with NORTH=True, then without flags for original seam clearances.
./run.command --headless -- --west-check
./run.command --headless -- --self-test
./run.command --headless -- --restart-check
```

Omit `--download` to regenerate from bundled data. Preserve `cross-harbour-source.geojson` when regenerating; it pins earlier geometry. Before-state files are in `Art/before-west-kowloon-expansion-2026-10-07/`. Logs, the data validator and native matching-camera captures are in `evidence/west-kowloon-expansion-2026-10-07/`.

The data validator checks source hashes, earlier roads/routes/tunnel meshes, H1 byte equality, building land containment, cross-region overlap and exact GLB chunk coverage. In-engine checks cover asphalt and paving, bus clearance, land/sea collision, seawalls, shortcuts and both new physical drives.

- `data-check.log` / `data-check.json`: pass; all 1,571 earlier road objects, six routes, both tubes, twelve tunnel mesh streams and both H1 files are preserved. Source hashes, land containment, absence of cross-region building overlap and all 1,051 chunk pairs pass.
- `capture-final.log`: native GL Compatibility rendering and an L-key input event pass. Eight final images and four matching before views are retained in the [visual comparison](../evidence/west-kowloon-expansion-2026-10-07/compare.html). District labels are separated from H1 stop labels.
- `restart-check.log`: exit 0; all three reloads restore H1 with 2,102 building meshes and 1,051 collision shapes, without engine errors. Each rebuilt scene passes 434 roof probes, 2,041 paving samples and 1,922,604 facade-edge scale checks.
- `build.log`: 0 warnings / 0 errors.
- `self-test.log`: **exit 0 / `ANTILA_SELF_TEST_OK`** on the final code and data. All eight complete drives, portal/exit probes, both Kowloon side-street turns and the original 1.08 km H1 service pass, with all three stops and 26 passengers. The full build has 0 warnings / 0 errors; no engine errors occur. Building, footpath, road-marking, audio, HUD, camera and traffic-signal regressions pass. Coverage includes 3,110 original-district clearance queries, 6,608 asphalt/paired-pavement samples, 49,443 expansion bus-envelope queries, 230 tunnel-wall rays, four land/sea probes and nineteen seawall probes.

The new drives physically cover **6,121 m** from West Kowloon to Sham Shui Po and **1,742 m** from Mong Kok to Sham Shui Po, with no contacts or departures. Lane offset and cornering explain the difference from sampled centreline lengths. The route review removed waypoint-induced turnbacks; this changes only the chosen drive paths, preserving every source road. `west-check-before-endpoint-fix.log` retains the superseded focused-run failure; the final complete suite verifies both corrected routes. The logged `ANTILA_TEST_CONTACT` in the full suite is the intentional outer-boundary collision test; all route drives complete without contacts.
