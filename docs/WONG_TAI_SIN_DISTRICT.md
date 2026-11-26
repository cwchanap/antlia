# Wong Tai Sin District expansion

The Home Affairs Department boundary covers 9.351 km² and the complete district remains within the game’s ground. This extension maps 731 of the 1,053 Transport Department road sections that have a centreline in the district. Measured against the same Transport Department archive for both editions, the 35 added sections contribute 2.926 km of centreline inside the boundary, bringing the total to 57.920 km. The bundled version of those 731 sections measures 57.993 km and includes alignments retained from earlier surveys. The 7,571 previously modeled road records and 16 drives are preserved. [District boundary](https://data.gov.hk/en-data/dataset/hk-had-json1-hong-kong-administrative-boundaries) · [Transport Department road network](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2) · [Coverage comparison](../evidence/wong-tai-sin-district-2026-11-25/district-road-coverage.png)

## Choi Hung and Hammer Hill

Press **X** from route select or while stopped to start the 1.600 km Choi Hung → Hammer Hill free drive. Its 22 directed sections connect the Choi Hung Road approach to the Hammer Hill and Fung Tak roundabout via Lung Cheung Road. An eastern return branch, two raised Hammer Hill carriageways, and the lower Lung Cheung Road approaches extend the surrounding network. The game authors roadway widths and ramp profiles using surveyed spacing and relative levels. A 7 m deck separates the raised carriageways from the lower crossing. Two surveyed surface links give the flyovers separate westbound and eastbound connections via Choi Hung. A single level deck joins the three raised ramps. [Road and turn verification](../evidence/wong-tai-sin-district-2026-11-25/final-road-source-check.log)

Three inner-loop links still require a hairpin tighter than the double-decker’s steering limit. The two separately recorded Fung Shing Street ends are about 224 m apart. The surveyed upland Jat’s Incline and Shatin Pass chain has a legal exit onto the current roads, with its incoming Clear Water Bay approach extending beyond the modeled ground. Fei Ngo Shan Road also has a 5.5 t restriction subject to permits. The coverage comparison shows the other unmodeled surfaces, raised roads and tunnels. [Transport Department network downloads](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2) · [Ngau Chi Wan traffic connections](https://www.td.gov.hk/en/traffic_notices/index_id_83298.html)

## Hillside and surveyed buildings

East Tsz Wan Shan has 1.058 km² of collidable relief derived from 3,095 Lands Department contours and 624 ground spot heights. The source uses Hong Kong Principal Datum. The game scales the terrain rise to 65% above a 135 m datum, reaches 131.6 m above the playable plane and tapers over 140 m toward the surrounding ground. Adjacent roads, building footprints and surveyed recreation sites retain their previous ground support. [Contour service](https://ginfo.cedd.gov.hk/server/rest/services/Basemap/MapServer/393) · [Ground spot heights](https://ginfo.cedd.gov.hk/server/rest/services/Basemap/MapServer/382) · [Survey and game relief](../evidence/wong-tai-sin-district-2026-11-25/tsz-wan-shan-height-footprint.png)

The full Lands Department query returned 2,568 active building identities intersecting the district, all present in the bundled source inventory. The Ma Chai Hang Ventilation Building uses its updated 897.44 m² surveyed outline and retains its 10 m roof rise. [Building dataset](https://data.gov.hk/en-data/dataset/hk-landsd-openmap-landsd-building) · [Footprint comparison](../evidence/wong-tai-sin-district-2026-11-25/ma-chai-hang-footprint.png)

## Parks and playgrounds

The recreation layout adds 12 surveyed sites, including Lok Fu Recreation Ground, Wong Tai Sin Cultural Garden and Square, three Tsz Wan Shan playgrounds, and Ngau Chi Wan Park. The additions bring the layout to 80 sites and add 22 sports surfaces. Authored paths connect the new sites to public paving. The Ngau Chi Wan western terraces retain the surveyed pond and pavilions while the east platform carries a fitted court. [Recreation sources, site list and access checks](EAST_KOWLOON_OPEN_SPACES.md#wong-tai-sin-district-recreation)

## Rebuild and verify

Use the reviewed WGS84 Transport Department archives listed in the earlier district expansion. Update the geodata environment before compiling the relief. [Archive hashes and original terrain workflow](DIAMOND_HILL_EXPANSION.md)

```sh
.venv-geodata/bin/pip install -r Tools/requirements-geodata.txt
.venv-geodata/bin/python Tools/import_tunnel.py /path/to/CENTERLINE.kmz --whole-wong-tai-sin-district
.venv-geodata/bin/python Tools/import_buildings.py --wong-tai-sin-district
.venv-geodata/bin/python Tools/import_east_open_spaces.py
.venv-geodata/bin/python Tools/import_wong_tai_sin_relief.py
.venv-geodata/bin/python Tools/check_wong_tai_sin_district.py --turn-archive /path/to/TURN.kmz
.venv-geodata/bin/python Tools/check_east_open_spaces.py --bundled
```

Run the following in a fresh Blender MCP session. Set `root` to your checkout. The harbour exporter incorporates the hillside into `HarbourGround` and the recreation export selects East Kowloon explicitly.

```python
from pathlib import Path

root = Path('/path/to/antlia').resolve()
harbour = root / 'Tools/model_tunnel.py'
exec(compile(harbour.read_text(), str(harbour), 'exec'), {
    '__name__': '__main__', 'ANTILA_ROOT': str(root),
})

recreation = root / 'Tools/model_open_spaces.py'
scope = {'__name__': 'district_recreation', 'ANTILA_ROOT': str(root)}
exec(compile(recreation.read_text(), str(recreation), 'exec'), scope)
scope['build']('east-kowloon')

buildings = root / 'Tools/model_government_buildings.py'
exec(compile(buildings.read_text(), str(buildings), 'exec'), {
    '__name__': '__main__', 'ANTILA_ROOT': str(root), 'EAST_KOWLOON': True,
    'BUILDING_ASSETS': ['wong-tai-sin-buildings'],
})
```

The harbour exporter requires compiled hillside relief for the full district. Rerun the relief importer after changes to the ground mesh, road clearance, district boundary, surveyed lots or recreation clearance. [Relief export regression checks](../evidence/wong-tai-sin-review-fixes-2026-11-25/relief-exporter-regression.log)

Rebuild the chunk pack and bake the terrain masks. [Terrain masks](STARTUP_PERFORMANCE.md#baked-terrain-masks)

```sh
python3 Tools/split_building_chunks.py
python3 Tools/split_building_chunks.py --check
./run.command --headless -- --bake-terrain
./run.command --headless --disable-render-loop --fixed-fps 60 -- --wong-tai-sin-district-check
./run.command --headless --disable-render-loop --fixed-fps 60 -- --east-open-spaces-check
./run.command --headless --disable-render-loop --fixed-fps 60 -- --terrain-mask-check
```

The final Godot build passed the Choi Hung drive, both flyover directions, the eastern return and the Lung Cheung underpass without contact. The district check also verified the X shortcut, separate bridge levels, hillside collision and support across the seam, and the expanded Ma Chai Hang roof collider. [District driving and collision checks](../evidence/wong-tai-sin-review-fixes-2026-11-25/engine-district.log) · [In-game district map](../evidence/wong-tai-sin-district-2026-11-25/choi-hung-map.png) · [Hillside in game](../evidence/wong-tai-sin-district-2026-11-25/tsz-wan-shan-overview.png)

H1, H2 and H3 reached all 15 stops without contact or red-light crossings. The recreation check verifies 286 connected access samples, both surveyed ponds, 4,627 fixtures and all 137 sport colliders. All three terrain masks match the regenerated pixels and mip levels. [Scheduled services](../evidence/wong-tai-sin-district-2026-11-25/engine-routes.log) · [In-game recreation checks](../evidence/wong-tai-sin-review-fixes-2026-11-25/engine-east-open-spaces.log) · [Terrain mask check](../evidence/wong-tai-sin-review-fixes-2026-11-25/engine-terrain-mask.log)

Data © HKSAR Government / Home Affairs Department / Transport Department / Lands Department / Civil Engineering and Development Department / Leisure and Cultural Services Department. [DATA.GOV.HK terms](https://data.gov.hk/en/terms-and-conditions) · [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC)
