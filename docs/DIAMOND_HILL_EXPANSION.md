# Wong Tai Sin through Diamond Hill

The later district expansion extends the Choi Hung and Hammer Hill roads and adds surveyed hillside relief and public spaces. [Current district coverage and rebuild](WONG_TAI_SIN_DISTRICT.md)

The expansion uses the Home Affairs Department’s Wong Tai Sin District boundary (district H) to identify the missing ground, streets and building footprints. Before the expansion, the map covered 7.76484 of the district’s 9.35053 km² and contained 614 intersecting Transport Department road sections, with 48.286 km of centreline within the boundary. The 1.823 km² audit area east of Diamond Hill station through Hammer Hill had ground. Its roads and building footprints remained unmapped. The station and Plaza Hollywood immediately west of that area already had building massing. [Official district boundary](https://data.gov.hk/en-data/dataset/hk-had-json1-hong-kong-administrative-boundaries) · [Bundled district feature](../Data/wong-tai-sin-district-boundary.geojson)

The ground extension adds 1.58569 km² within the district and 0.37950 km² of adjoining terrain. The Civil Engineering and Development Department’s mainland polygon covers the entire district and the 50 m margin. The new terrain extends the eastern map cut to local bounds `(550, −7110, 5380, −100)`, preserves the previous ground and surveyed coastline, and moves the artificial outer wall to the new edge. Surveyed contours in three upland samples range from 360 to 542 m above Hong Kong Principal Datum. This edition used flat terrain in the uplands. [CEDD mainland geometry](https://portal.csdi.gov.hk/csdi-webpage/file-api?dataset_id=cedd_rcd_1636520962284_7237&format=geojson&layer_name=Coastline) · [CEDD contours](https://ginfo.cedd.gov.hk/server/rest/services/Basemap/MapServer/393)

Press **G** from route select or while stopped to start the Wong Tai Sin → Diamond Hill free drive. The **Y** drive still runs from Kowloon City to Wong Tai Sin. [Earlier Wong Tai Sin expansion](WONG_TAI_SIN_EXPANSION.md)

## Roads and building sources

The 3.140 km drive follows the exact endpoint of the Y itinerary via Wong Tai Sin Road, Shatin Pass Road, Tsz Wan Shan Road and Po Kong Village Road to Lung Poon Street by Plaza Hollywood. It uses 58 signed sections and 817 sampled points. Transport Department centrelines supply alignments, travel directions and relative levels. The reviewed WGS84 centreline and turn archives retain the hashes recorded for Kowloon City. [Transport Department Road Network](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2) · [Archive hashes](KOWLOON_CITY_DISTRICT_REVIEW.md#kai-tak-and-ho-man-tin-expansion)

The expansion adds 82 connected surface sections, including Hammer Hill Road, the six-section clockwise roundabout at Fung Tak Road and the sports-ground approaches. The correction preserves all 7,489 pre-expansion road sections and all 16 drive paths. Within the district, 696 sections contribute 55.067 km of centreline. The review deferred 14 Choi Hung Road links that formed a one-way loop with no legal return through the modeled interchange. The retained approach has a legal five-section return. The lower Hammer Hill and Lung Cheung interchange approaches and the rural Shatin Pass spur also await complete playable connections. [Coverage comparison](../evidence/diamond-hill-review-fixes-2026-11-25/district-coverage.png) · [Transport Department turn replay](../evidence/diamond-hill-review-fixes-2026-11-25/road-scratch-verification.log)

The Lands Department Building query returned 3,809 active records in the full district envelope. The importer kept all 8,528 pinned East Kowloon records and added 889 active building IDs that intersect the district. It preserves full source footprints and records the 51 collisions between new OBJECTIDs and pinned internal IDs. The new records include 18 named Chi Lin Nunnery structures, eight Nan Lian Garden structures and the Grand View Garden towers. After clipping for roads and land, 876 of the new records contribute 902 rendered parts. The East Kowloon layout has 9,843 parts in total, and its metadata records the effective map bounds. [Lands Department Building dataset](https://data.gov.hk/en-data/dataset/hk-landsd-openmap-landsd-building)

## Public spaces

The CEDD survey supplies the boundaries of Hammer Hill Road Sports Ground, Hammer Hill Park, Po Kong Village Road Park and Nan Lian Garden. It also supplies five sports outlines and the Nan Lian pond and pavilion geometry used to keep authored paths and fixtures clear. [Recreation sources and checks](EAST_KOWLOON_OPEN_SPACES.md#wong-tai-sin-and-diamond-hill)

## Rebuild from the bundled sources

These commands reproduce the Diamond Hill snapshot in a checkout of that edition. Run them from the repository root with the geodata dependencies installed. Use the whole-district workflow for the current checkout. [Current rebuild instructions](WONG_TAI_SIN_DISTRICT.md#rebuild-and-verify)

```sh
.venv-geodata/bin/python Tools/import_shoreline.py --east-kowloon --wong-tai-sin-district
.venv-geodata/bin/python Tools/import_tunnel.py /path/to/CENTERLINE.kmz --wong-tai-sin-district
.venv-geodata/bin/python Tools/import_buildings.py --wong-tai-sin-district
.venv-geodata/bin/python Tools/import_east_open_spaces.py
```

Use a fresh Blender MCP session for the model exports. Set `ANTILA_ROOT` to the checkout when running `Tools/model_tunnel.py`, then load `Tools/model_open_spaces.py` and call `build('east-kowloon')` for recreation. For the building GLBs, run the following in Blender MCP with the path to your checkout.

```python
from pathlib import Path

root = Path('/path/to/antlia').resolve()
exporter = root / 'Tools/model_government_buildings.py'
exec(compile(exporter.read_text(), str(exporter), 'exec'), {
    '__name__': '__main__',
    'ANTILA_ROOT': str(root),
    'EAST_KOWLOON': True,
    'BUILDING_ASSETS': [
        'diamond-hill-buildings',
        'hung-hom-buildings',
        'kowloon-city-buildings',
        'wong-tai-sin-buildings',
    ],
})
```

This selection matches the four source GLBs updated for the expansion. Run `python3 Tools/split_building_chunks.py` and bake the terrain masks with `./run.command --headless -- --bake-terrain`. [Terrain mask workflow](STARTUP_PERFORMANCE.md#baked-terrain-masks)

## Verification

```sh
.venv-geodata/bin/python Tools/check_wong_tai_sin_district.py --turn-archive /path/to/TURN.kmz
.venv-geodata/bin/python Tools/check_wong_tai_sin_terrain.py
.venv-geodata/bin/python Tools/check_buildings.py --wong-tai-sin-district
.venv-geodata/bin/python Tools/check_east_open_spaces.py --bundled
python3 Tools/split_building_chunks.py --check
./run.command --headless --disable-render-loop --fixed-fps 60 -- --diamond-hill-check
./run.command --headless --disable-render-loop --fixed-fps 60 -- --route-check
./run.command --headless --disable-render-loop --fixed-fps 60 -- --east-open-spaces-check
./run.command --headless --disable-render-loop --fixed-fps 60 -- --terrain-mask-check
```

The focused Godot check verifies G from route select, Tab back to route select, the moving and paused shortcut guards, 82 lane-support probes and collision at the new outer wall. The bus drove 3,084 m on the Diamond Hill itinerary and 1,809 m on the Fung Tak Road, Hammer Hill and Po Kong Village detour without contact. The route check verifies the physical G key from route select and while stopped using a non-QWERTY key event. [Focused Godot check](../evidence/diamond-hill-review-fixes-2026-11-25/engine-diamond-hill.log) · [Route check](../evidence/diamond-hill-review-fixes-2026-11-25/engine-routes.log)

The recreation check covers access paving, all six surveyed ponds, 115 court colliders and 4,296 fixtures across 68 sites. The terrain check compares all three baked masks with the regenerated pixels and mip levels. [Recreation check](../evidence/diamond-hill-review-fixes-2026-11-25/engine-open-spaces.log) · [Nan Lian pavement comparison](../evidence/diamond-hill-review-fixes-2026-11-25/nan-lian-paving-comparison.png) · [Terrain check](../evidence/diamond-hill-review-fixes-2026-11-25/terrain-check.log)

The original Diamond Hill expansion passed the full Godot self-test with 141,225 bus-clearance probes, 29 contact-free driving paths and all three scheduled passenger services. [Original full Godot test](../evidence/diamond-hill-2026-11-25/engine-self-test.log)

The native game captures show the expanded district, the G shortcut on route select and the new streets on the full map. [District overview](../evidence/diamond-hill-2026-11-25/diamond-hill-overview.png) · [Route select](../evidence/diamond-hill-2026-11-25/diamond-hill-menu.png) · [In-game map](../evidence/diamond-hill-2026-11-25/diamond-hill-map.png)

Data © HKSAR Government / Home Affairs Department / Transport Department / Lands Department / Civil Engineering and Development Department / Leisure and Cultural Services Department. [DATA.GOV.HK terms](https://data.gov.hk/en/terms-and-conditions) · [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC)
