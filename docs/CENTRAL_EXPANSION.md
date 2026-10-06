# Central / Admiralty expansion — 5 October 2026

The island apron extends 2.10 km west, from 2.35 to **4.45 km east–west**, at one world unit per metre. Overall map bounds are **4.61 × 3.55 km**. The connected street network reaches Central and Admiralty through Queensway, Des Voeux Road Central, Queen’s Road Central, Pedder Street, Chater Road, Connaught Road Central and Harcourt Road. The rectangular bounds include buildings and open space; not every point is a driveable road.

Press **J while stopped** for the new **3.080 km Admiralty / Central loop**, **I** for Wan Chai / Causeway Bay, **T** for the crossing, **M** for the map, and **R** to restart H1. **C** remains the camera switch. Free drive adds no passenger-service stops or turn-by-turn navigation; the named loop is also the physical test itinerary. The western loop joins Hennessy Road, Queensway, Des Voeux Road Central, Pedder Street and Queen’s Road Central. It avoids the compact northern Des Voeux turnaround, which failed the long-bus driving check.

## Government geometry and provenance

Road data: © HKSAR Government / Transport Department, [Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2). The [current KMZ](https://static.data.gov.hk/td/road-network-v2/CENTERLINE.kmz) SHA-256 is `108319d165d1059522db6e7506d888c9da78a2c8777b2b42f6f09fbf67bdd568`. This download’s geographic coordinates require **HK1980 to WGS84 conversion (EPSG:4611 → EPSG:4326)**. `pyproj` is a regeneration-only dependency. A shared Hennessy Road point was independently checked with the ArcGIS Geometry service; 475 of the original 478 sections match within 2.5 cm after conversion. The conversion shifts raw coordinates approximately 253 m east / 170 m south into the existing scene’s WGS84 frame.

`Tools/import_tunnel.py` matches the stable TD `ROUTE_ID`, because KML placemark identifiers changed. All **478 existing road sections, four routes and both tube definitions remain exactly unchanged**, pinned to the prior snapshot SHA-256 `936df4f37875a530d7862862ec5646e6ab2a5b7ef498d081084f9e4750c0ac1b`. Three revised sections (`ID_021556`, `ID_021657`, `ID_025722`) deliberately retain that snapshot. The new **420 sections / 26.781 km** of centreline geometry include parallel carriageways and junction branches, not 26.781 km of distinct bus itinerary. There are **898 crossing/island sections** in total. Connected components and route joins are validated after conversion; reversing a route section requires its source two-way attribute. New feature records carry their source hash; collection metadata retains both snapshot hashes and conversion details.

Building data: © HKSAR Government / Lands Department, [CSDI building layer](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637211194312_35158/MapServer/0). Query bbox WGS84: `114.14901858383986,22.27613546532519,114.19222329297013,22.2851185770751`. Downloaded `2026-10-05T13:15:18.059675+00:00`; raw SHA-256 `62e085014e233a7ea93e4cd4de5d9a82f931beb898d07b97db5f6cef9297e1af`. The count and unique object-ID checks both report **4,226 source records**. The importer retains 4,087 source IDs as **4,427 derived island building parts**, using 278 existing storey-based height fallbacks. Combined with Kowloon: **6,191 parts, 408 render/collision chunks, 1,974,060 m² footprint area, 673 small paving patches**, and relative heights up to **402.4 m**.

Blender MCP regenerated the ground, street paint and building meshes in isolated scenes and restored the user’s original scene. Island buildings export as two GLBs split at an existing 128 m chunk boundary, so each remains below 100 MB. The compressed editable `Art/island-buildings.blend` contains both; Godot loads their matching visual and collision chunks. Existing generated facade textures and decorative models are reused.

The complete island now has **204 trees, 308 lamps, 112 posed pedestrians and 30 kiosks**, plus planters, benches, street-name boards and promenade. Separate eastern/western placement caps ensure the expanded area receives people and kiosks. Buildings and street details are excluded from the authored bus clearance corridor.

Widths, flat surface levels, waterfront apron, foliage, facades and street furniture are authored. The map does not reconstruct surveyed slopes, every road level, tram restrictions or island signal controls. The original fourteen signal-controlled Kowloon junctions are unchanged. Government source geometry and relative building massing remain separate from these gameplay approximations. [TD reuse terms](https://data.gov.hk/en/terms-and-conditions) and [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC) apply; credits are included in the HUD and README.

## Regeneration

```sh
.venv-geodata/bin/pip install -r Tools/requirements-geodata.txt
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-centerline.kmz --hk1980
.venv-geodata/bin/python Tools/import_buildings.py --island --download
# Through Blender MCP: Tools/model_tunnel.py
# Through Blender MCP: Tools/model_government_buildings.py with ISLAND=True
./run.command --headless -- --central-check
./run.command --headless -- --self-test
./run.command --headless -- --restart-check
```

Keep the committed `Data/cross-harbour-source.geojson` when regenerating: it pins the existing geometry and stable-ID mapping. The importer rejects a datum that does not match over 400 shared sections. The game itself remains fully offline and does not require Python, Shapely or pyproj.

## Verification

Evidence is recorded under `evidence/central-expansion-2026-10-05/`; before-state data and models are under `Art/before-central-expansion-2026-10-05/`. The data comparison confirms 478 original sections, four routes, tube definitions and all twelve tunnel floor/wall/ceiling/ledge position/index streams remain identical. In-engine checks cover the expanded bounds, western building/detail coverage, asphalt and paving, full bus clearance, the J keyboard binding and the physically driven loop. Native captures use matching overview cameras before and after expansion.

Checks completed on 6 October 2026 (Hong Kong time):

- `self-test.log`: the complete suite reaches `ANTILA_SELF_TEST_OK`, with 0 build warnings / errors and no engine errors. Both tunnel directions, the Wan Chai return loop, 9,165 m scenic drive, 3,060 m Central drive, both Kowloon side-street turns and the complete 1.08 km H1 service pass without unintended contacts. The original three stops and 26 passengers remain operational; building, footpath, audio, HUD and all fourteen signal-junction checks also pass.
- `central-check.log`: 1,898 asphalt / paired-pavement samples, 230 portal wall rays and 14,427 bus-envelope probes pass. The revised loop physically drives 3,060 m without contacts or route departures; its source centreline is 3,080 m. Cornering and lane offsets explain the distance difference.
- `restart-check.log`: three scene reloads from paused map, island drive and completed service pass, preserving 816 building meshes / 408 collision shapes with no engine errors.
- `capture-final.log`: native GL Compatibility rendering exits successfully; real J-key events start the western drive, and C-key events switch the camera without teleporting the bus. Eight final views cover the two districts, panorama, three street scenes, cab and map; four matching before views are retained. [Before/after comparison](../evidence/central-expansion-2026-10-05/compare.html).
- `data-check.json`: original road/route/tunnel invariants and the island source hash pass. The two island GLBs are approximately 65.5 MB and 74.9 MB; their compressed editable Blender scene is 37.8 MB.

The first focused run’s rejected compact turn and a nonfatal editor-import Android SDK diagnostic remain in `central-check-before-route-fix.log`. The final full-suite, native capture and restart logs contain no engine errors.
