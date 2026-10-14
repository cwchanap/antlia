# Yau Ma Tei / Mong Kok expansion — 6 October 2026

This records the first northern expansion. See [West Kowloon / Sham Shui Po](WEST_KOWLOON_EXPANSION.md) for the current map extent, seam adjustments and totals.

Kowloon now continues north from Jordan through Yau Ma Tei to Mong Kok. The added land region is **1.55 km east–west × 2.159 km north–south**, with overall map bounds of **4.61 × 5.58 km**. One world unit remains one metre. The original Tsim Sha Tsui / Jordan H1 service, its three stops, both tunnel directions and all five earlier free-drive/test routes are retained.

Press **K while stopped** to start the **2.109 km Jordan → Yau Ma Tei → Mong Kok drive** on Nathan Road. **M** opens the map and **R** returns to H1. This is free exploration, with no additional passenger service or turn-by-turn navigation. The street network also includes Shanghai Street, Portland Street, Temple Street, Canton Road, Waterloo Road, Dundas Street, Argyle Street and Mong Kok Road. Roads end within an authored boundary; the rectangular extent does not promise a road at every point.

## Government sources and processing

Roads: © HKSAR Government / Transport Department, [Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2). The cached [CENTERLINE.kmz](https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz) is the same snapshot used for Central, retrieved on 5 October 2026 UTC, SHA-256 `108319d165d1059522db6e7506d888c9da78a2c8777b2b42f6f09fbf67bdd568`. Its coordinates are converted from HK1980 geographic to WGS84 (EPSG:4611 → EPSG:4326), using the existing `pyproj` dependency only during regeneration. The importer preserves retrieval time when reusing the snapshot and records a separate processing time.

`Tools/import_tunnel.py` adds **673 selected ground-level source sections / 42.146 km of sampled centreline geometry**. This includes parallel carriageways and short junction links, not 42 km of distinct bus itinerary. The expansion dataset now contains **1,571 sections and six routes**. Stable `ROUTE_ID` values identify sections. All 898 earlier sections, five routes and both tunnel definitions remain exactly unchanged; the original 437-section Kowloon side-street dataset and 231-point H1 route are also unchanged. Shared source geometry validates the datum within 2.5 cm. The northern route follows 34 explicit source sections; sections traversed backwards must have the source two-way flag.

Only selected named ground-level streets connected to the chosen network are included. Most northern sections must fit inside the new region with a 12 m buffer; short southern continuations meet the existing Jordan streets. Original coordinates are retained in `Data/cross-harbour-source.geojson`. The existing ground model is regenerated as one union of land regions, preserving the tunnel openings and avoiding overlapping terrain.

Buildings: © HKSAR Government / Lands Department, [CSDI building layer](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637211194312_35158/MapServer/0). `Data/kowloon-north-buildings.geojson` retains **4,868 records**, downloaded at `2026-10-06T15:35:50.704266+00:00`. WGS84 query bounds: `114.16358196893995,22.3057,114.17863080021004,22.3250934243622`. SHA-256: `b10023241ef10ebbe6ffde0772cff203dff0e35b40c0211be89799842c1a7ae0`. Count and unique object-ID checks confirm a complete extract.

The existing building importer produces **5,109 derived parts**, retaining 4,727 source IDs, with 153 storey-based height fallbacks. Their footprint covers **1,042,501 m²**; 509 small enclosed gaps receive paving. Existing district layouts and building assets are retained. Across the whole scene there are **11,300 parts and 639 visual/collision chunk pairs**.

Blender MCP generates `yau-ma-tei-buildings.glb` (46.45 MB) and `mong-kok-buildings.glb` (80.40 MB), split at an existing 128 m chunk boundary. Their combined editable source is `Art/kowloon-north-buildings.blend`. Both assets reuse the existing generated facade and shopfront artwork. Each of the 231 northern chunks is included exactly once with a matching collision mesh. Modeling runs in an isolated scene and restores the user's scene.

The northern region adds **532 street details**, including 48 posed pedestrians and 12 kiosks, plus lamps, trees and planters. Placement excludes building footprints and road clearance corridors. The map labels Yau Ma Tei and Mong Kok; free-drive HUD text now covers both sides of the harbour.

Road widths, lane markings, flat terrain, boundary walls, facades, foliage and street furniture are authored approximations. No surveyed hills, lane restrictions, northern traffic signals, or new passenger service are claimed. The fourteen existing signal junctions remain in the original district. [TD terms](https://data.gov.hk/en/terms-and-conditions) and [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC) apply. The game runs offline without Python or a map API key.

## Regeneration and checks

```sh
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-centerline.kmz --hk1980
.venv-geodata/bin/python Tools/import_buildings.py --north --download
# Through Blender MCP: Tools/model_tunnel.py
# Through Blender MCP: Tools/model_government_buildings.py with NORTH=True
./run.command --headless -- --kowloon-check
./run.command --headless -- --self-test
./run.command --headless -- --restart-check
```

Retain the committed `Data/cross-harbour-source.geojson` when regenerating: it pins prior geometry and the stable-ID mapping. Use `--north` without `--download` to rebuild the layout from the bundled building extract.

Evidence is under `evidence/kowloon-expansion-2026-10-06/`; before-state data and the ground/tunnel model are under `Art/before-kowloon-expansion-2026-10-06/`. `check_data.py` compares all 898 prior road sections, five routes, tunnel definitions and twelve tunnel mesh position/index streams. Native captures use matching cameras before and after expansion.
Verification completed on 7 October 2026 (Hong Kong time):

- `self-test.log`: the complete in-engine suite exits successfully with `ANTILA_SELF_TEST_OK`. It covers all six free-drive/test routes, both Kowloon side-street turns, the original three H1 stops and 26 passengers, plus building, footpath, road, signal, audio and HUD regressions. All 11,300 building parts and 639 chunks pass, including 286 roof collision probes. The build has 0 warnings / 0 errors.
- `restart-check.log`: exits successfully with `ANTILA_RESTART_CHECKS_OK` after three reloads from paused map, island drive and completed service. Every reload restores H1 with 1,278 building meshes and 639 collision shapes; no engine errors are reported.
- `kowloon-check.log`: 0 build warnings / errors; 3,110 existing-district clearance probes, 3,255 asphalt/paving samples, 230 tunnel-wall rays and 23,892 full bus-envelope probes pass. The physical northern drive covers 2,084 m with no contacts or departures. Lane offset and cornering account for its difference from the 2,109 m sampled centreline.
- `capture-final.log`: native GL Compatibility render and real K-key input pass; eight final images and four before views are retained. The full map uses thinner street lines and external district labels to keep the longer north–south layout readable. [Before/after and street views](../evidence/kowloon-expansion-2026-10-06/compare.html).
- `data-check.json`: all prior road, route and tunnel-mesh invariants pass; the new building source hash matches its layout metadata. Original Kowloon road data is byte-for-byte unchanged, and all 231 new visual/collision chunk pairs occur exactly once across the two GLBs.
