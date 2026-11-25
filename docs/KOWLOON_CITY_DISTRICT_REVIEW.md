# Kowloon City District government-data review

The review uses the Home Affairs Department’s official Kowloon City District polygon (district G) to measure Antila’s coverage. The bundled extract preserves all 326 coordinate positions and the source attributes. Its metadata records the download location, coordinate reference system and a hash of the extracted feature. [District Boundary dataset](https://data.gov.hk/en-data/dataset/hk-had-json1-hong-kong-administrative-boundaries) · [Bundled extract](../Data/kowloon-city-district-boundary.geojson)

## Coverage before the expansion

| Measure | Result |
| --- | ---: |
| Official administrative extent, including water | 14.515 km² |
| Game ground inside that extent | 9.074 km² |
| Bundled TD sections intersecting the district | 1,594 |
| TD centreline length clipped to the district | 118.777 km |
| Bundled iB1000 sites with most of their footprint in the district | 15 |

Areas and lengths use the game’s local projection. The 5.441 km² outside mapped ground includes harbour water, so it cannot be used as a missing-land total. The audit counts distinct `ROUTE_ID` and `SITEID` values. The P exploration drive reaches Kowloon City via Hung Hom, Whampoa and To Kwa Wan. The Y drive connects Kowloon City to Wong Tai Sin. Earlier work added Kowloon Tong streets, buildings and surveyed recreation sites. [Eastern Kowloon drive](EAST_KOWLOON_EXPANSION.md) · [Government building coverage](GOVERNMENT_BUILDINGS.md) · [Public spaces](EAST_KOWLOON_OPEN_SPACES.md)

## Gaps identified in the review

- **Kai Tak runway and Cruise Terminal.** The game’s east edge is at local X 3,150 m. The bundled iB1000 extract contains 4.343 km of distinct shoreline lines inside the district beyond that edge, but the runway shore ends at the edge of the saved sheets. Query the iB1000 index for the missing runway sheets, starting with 11-NE-17D, 11-NE-22B and 11-NE-22D. Use surveyed shoreline and seawall features to place the waterfront. [Lands Department iB1000](https://www.hkmapmeta.gov.hk/mcs/home/web/data/lands/iB1000.html)
- **Eastern road network.** The bundled TD inventory includes Shing Kai Road and part of Shing Fung Road. Its easternmost section stops at X 3,131 m. Check the latest TD centrelines for continuity to the Cruise Terminal and for links at Kai Tak Bridge Road, Shing Cheong Road and Cheung Yip Street. Government traffic notices identify which connections opened. The TD centrelines supply the alignments and travel directions. [TD Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2) · [Shing Fung Road opening](https://www.td.gov.hk/en/traffic_notices/index_id_71254.html) · [Kai Tak Hospital access](https://www.info.gov.hk/gia/general/202609/28/P2026092700336p.htm)
- **Inland east edge.** A 0.192 km² component of the district northeast of the runway lies beyond the game cut. A trial using the saved coast tiles extended the cut to X 3,382 m without moving the retained ground. The bundled Building layer already intersects the new area, including portions of Ching Long Shopping Centre and the Tak Yu and Tak Ying houses. Fresh footprint and road extracts are needed for continuous coverage across the new edge. [Lands Department Building layer](https://data.gov.hk/en-data/dataset/hk-landsd-openmap-landsd-building)
- **Northern map edge.** The district extends about 48 m beyond the game cut north of Kowloon Tong, leaving a separate strip of about 0.005 km². Check the road and building extracts there when reviewing the district perimeter.
- **Ho Man Tin and Kai Tak public spaces.** Ho Man Tin Park, Perth Street Sports Ground, Ho Man Tin East Sitting-out Area and Carmel Village Street Garden are absent from the curated iB1000 layouts. Kai Tak Station Square and Avenue Park are also absent. Use the LCSD inventory to identify venues and iB1000 Site and sports geometry for footprints and courts. [LCSD venues](https://www.lcsd.gov.hk/en/healthy/wheretorun.html) · [LCSD parks and gardens data](https://data.gov.hk/en-data/dataset/hk-lcsd-csdi-parks-zoos-gardens)

For a playable expansion, join reviewed TD sections to the existing street network, clip building footprints using the established clearance rules and rebuild the terrain, road and collision assets together. Check road direction and junction continuity, the two existing eastern exploration drives, land and seawall collision, and the resulting terrain masks in Godot.

## Kai Tak and Ho Man Tin expansion

Press **F** from route select or while stopped to start the 3.017 km Kai Tak exploration drive. It starts at the existing P itinerary’s Shing Kai Road junction and reaches the Cruise Terminal approach via Shing Fung Road and Shing King Street. The district refresh adds 214 sections, including Pui Ching Road, bringing the map total to 7,489. The TD record supplies link directions and relative road levels. The game fits the Shing Fung Road deck and its approach grades. Lane widths, terrain elevations, and building appearance are authored. [TD Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2)

The November 19 TD archive already contains WGS84 coordinates. More than 7,250 sections agree with the bundled geometry within 2.5 cm. The importer preserves the earlier source records, checks the district boundary and land support, and adds connected roads. The signed 34-section Kai Tak itinerary was also checked against the official November turn restriction archive. `CENTERLINE.kmz` SHA-256 `ebdc7052bbd07fbc3f6f068012ba8354e62c9f3c21c080d6cd43f334b1169adf`. `TURN.kmz` SHA-256 `b6911192e9cfc9c719ec317d3a5c2a7e6db01fc27d751af952546203ac7a9bc4`.

The Kai Tak Bridge Road approach is deferred until `TD_266683` has a supported bridge deck and connected approaches across the channel. The omitted approach links are `TD_267096`, `TD_266963` and `TD_274787`. The 34-section outbound drive and the verified return via `TD_284206` retain their alignments. [TD Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2)

The east cut extends from X 3,150 m to X 4,900 m. It retains all 576 Lands Department iB1000 shoreline features and uses CEDD sea-fill polygons from the 1:5,000 survey for the eastern extension. Where those earlier polygons predate the runway approach, a bounded patch uses the lower-resolution CEDD geological coastline. The patch adds ground under the newer road approaches and keeps the harbour channel. The source file records both CEDD extracts and their hashes. [iB1000 metadata](https://www.hkmapmeta.gov.hk/mcs/home/web/data/lands/iB1000.html) · [CEDD sea-fill layer](https://ginfo.cedd.gov.hk/server/rest/services/Basemap/MapServer/411)

The Kai Tak expansion brought mapped ground within the district to 10.215 km² before the northern terrain extension. The current road network contributes 1,808 sections and 139.528 km of centreline inside the boundary. Twenty surveyed public-space footprints lie mostly inside the district. [Coverage audit](../evidence/kowloon-city-review-fixes-2026-11-24/district-coverage.log)

The Lands Department Building extract preserves the previous 8,153 source records and adds 375 active records. Each new footprint overlaps the official district by more than 0.01 m². Full footprints are kept for buildings that cross the boundary. All 20 Cruise Terminal source records remain. Chi Man Street now uses a 5 m authored carriageway and a 0.1 m local building setback. The SPCA building beside it retains 509.74 m² of its 509.83 m² surveyed footprint. [Footprint comparison](../evidence/kowloon-city-review-fixes-2026-11-24/chi-man-street-footprint.png) · [Lands Department Building layer](https://data.gov.hk/en-data/dataset/hk-landsd-openmap-landsd-building)

Five Ho Man Tin recreation sites use CEDD survey boundaries. They include Ho Man Tin Park, Perth Street Sports Ground, Carmel Village Street Garden, Ho Man Tin East Service Reservoir Playground, and Ho Man Tin East Sitting-out Area No. 1. The combined recreation layout covers 64 sites and 161 surveyed sports outlines. Dorset Crescent Rest Garden has a new compact plaza and entrance fitted around the added roads. Pui Ching Road Playground remains pending because the tested walking approaches crossed building clearance. The available survey predates Kai Tak Station Square and Avenue Park. Their surveyed boundaries remain open items. [CEDD Site layer](https://ginfo.cedd.gov.hk/server/rest/services/Basemap/MapServer/409) · [CEDD sports outline layer](https://ginfo.cedd.gov.hk/server/rest/services/Basemap/MapServer/397)

## Northern terrain extension

The former cut at Z −6,000 m left two inland pieces of the district without ground. The CEDD mainland polygon supports a 22,500 m² extension from X 250 to 550 m and Z −6,075 to −6,000 m. This covers the full 5,280 m² gap inside the official district, including the small eastern corner, and brings mapped ground within the district to 10.220 km². The collision boundary follows the new perimeter and the former seam is open. [Before and after](../evidence/kowloon-city-north-fill-2026-11-24/northern-coverage.png) · [CEDD mainland geometry](https://portal.csdi.gov.hk/csdi-webpage/file-api?dataset_id=cedd_rcd_1636520962284_7237&format=geojson&layer_name=Coastline)

Planning Department land-use samples identify woodland and shrubland in the gap. CEDD contours cross the extension at 220–306 m elevation. Antila uses its existing flat terrain model. The official Transport Department archive and Lands Department Building layer showed no road centrelines or building footprints in the extension. [Planning Department land use](https://portal.csdi.gov.hk/csdi-webpage/dataset/pland_rcd_1754559265139_25057) · [CEDD contours](https://ginfo.cedd.gov.hk/server/rest/services/Basemap/MapServer/393)

## Repeat the audit

Run these commands from the project root with the geodata dependencies installed.

```sh
.venv-geodata/bin/python Tools/check_kowloon_city_district.py
.venv-geodata/bin/python Tools/check_kai_tak.py
.venv-geodata/bin/python Tools/check_east_kowloon.py
.venv-geodata/bin/python Tools/check_buildings.py --kai-tak
.venv-geodata/bin/python Tools/check_buildings.py --chi-man-street
.venv-geodata/bin/python Tools/check_shoreline.py
.venv-geodata/bin/python Tools/check_east_open_spaces.py --bundled
.venv-geodata/bin/python Tools/check_kowloon_tong_roads.py
.venv-geodata/bin/python Tools/export_runtime_harbour.py --check
python3 Tools/split_building_chunks.py --check
```

The audit reads the checked-in data and reports current coverage without hard-coding the baseline totals. Run `./run.command --headless -- --kai-tak-check` to check the shortcut, driving surface and physical route. Run `./run.command --headless -- --kowloon-city-north-check` to verify the ground and collision walls at the former northern gap. Clean checkouts render procedural passengers when the licensed scans are absent. [Passenger assets and installation](PASSENGER_ASSETS.md)

To replay the expansion, regenerate the coastal geometry from the pinned sources and use the documented November TD archive. Reclip the four building regions touched by the new roads. Rebuild the recreation layout after those outputs are ready so its input hashes match the map.

```sh
.venv-geodata/bin/python Tools/import_shoreline.py --east-kowloon
.venv-geodata/bin/python Tools/import_tunnel.py /path/to/CENTERLINE.kmz --kowloon-city-district
for region in --east-kowloon --north --northwest --west; do
  .venv-geodata/bin/python Tools/import_buildings.py "$region"
done
.venv-geodata/bin/python Tools/import_east_open_spaces.py
```

Regenerate the harbour with `Tools/model_tunnel.py` through Blender MCP. For the eastern recreation scene, load `Tools/model_open_spaces.py` and call `build('east-kowloon')`. Use `Tools/model_government_buildings.py` with `EAST_KOWLOON=True`, `NORTH=True`, `NORTHWEST=True` or `WEST=True` for each region whose building geometry changed. Set `ANTILA_ROOT` to the project root when executing exporter source directly in MCP. Then run `python3 Tools/split_building_chunks.py` and bake the terrain masks with `./run.command --headless -- --bake-terrain`. [Terrain mask workflow](STARTUP_PERFORMANCE.md#baked-terrain-masks)

To refresh the source extracts, pass `--download` to the shoreline or eastern building importer. The shoreline importer validates both candidate CEDD extracts against the supported runway areas, harbour water and northern fill before updating the saved source and coast. The building importer keeps the pinned records and filters new rows to active district footprints. The recreation importer checks the source manifests before reusing earlier fixtures.

The Godot Kai Tak check exercised 78 lane-support probes, F from route select, Tab back to the menu and the four in-game shortcut guards. The automated bus drove 2,983 m with zero contacts. Godot also verified the narrowed Chi Man Street asphalt and the restored northern ground and collision walls. [Drive check](../evidence/kowloon-city-review-fixes-2026-11-24/engine-kai-tak.log) · [Northern terrain check](../evidence/kowloon-city-review-fixes-2026-11-24/engine-north.log)

The recreation check validated 232 paving probes, 233 ground-support probes and 111 court colliders. All three terrain masks matched the regenerated pixels and mip levels. The native harbour RGB8 and RG8 comparison found zero differences at the 1/255 threshold. [Recreation check](../evidence/kowloon-city-review-fixes-2026-11-24/engine-open-spaces.log) · [Terrain check](../evidence/kowloon-city-review-fixes-2026-11-24/terrain-check.log) · [Native harbour mask check](../evidence/kowloon-city-review-fixes-2026-11-24/engine-harbour-rg8.log)

The full Godot self-test passed 139,584 bus-clearance queries, 27 contact-free driving paths and all three scheduled passenger services. [Full Godot test](../evidence/kowloon-city-review-fixes-2026-11-24/engine-self-test.log)

The sparse recreation mask reconstructed all 88,210,391 source mip pixels exactly. Its native sampling check reported differences on Linux Mesa llvmpipe with both the rebuilt map and the unchanged `08dcae8` baseline. The sparse shader and checker are identical across both runs. [Native recreation check](../evidence/kowloon-city-review-fixes-2026-11-24/engine-sparse-recreation.log) · [Baseline](../evidence/kowloon-city-review-fixes-2026-11-24/engine-sparse-recreation-baseline.log)

Data © HKSAR Government / Home Affairs Department / Transport Department / Lands Department / Civil Engineering and Development Department / Leisure and Cultural Services Department, via DATA.GOV.HK and the CSDI Portal. [DATA.GOV.HK terms](https://data.gov.hk/en/terms-and-conditions) · [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC)
