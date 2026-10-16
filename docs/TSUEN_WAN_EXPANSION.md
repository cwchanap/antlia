# Kwai Chung / Tsuen Wan expansion

**U while stopped** starts a **3.530 km exploration drive** from the existing Kwai Chung endpoint through Kwai Fuk Road, Texaco Road, Sha Tsui Road, Tai Ho Road, Castle Peak Road (Tsuen Wan) and Tsuen King Circuit. **M** opens the map; **R** returns to H1. There is no additional passenger service or turn-by-turn navigation.

Loaded bounds are **10.71 km east–west × 13.23 km north–south**, `[-8580,-11080,2130,2150]` in world X/Z. The selection rectangle is `[-8500,-11000,-3900,-6900]`, adding 11,981,990 m² of mainland beyond the preceding regions. These bounds include undeveloped areas; they do not imply continuous road coverage. The established approximate metre projection retains about 0.53% north–south stretch.

## Government sources and preservation

- [Transport Department Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2): reuse the official CENTERLINE.kmz downloaded 12 October 2026 UTC, SHA-256 `dcd0632d9d0f72bee549e24307b28ed98b17963c30899de0675d5e1163586735`. Convert HK1980 geographic EPSG:4611 to WGS84 before projecting. Stable ROUTE_ID preserves prior source records.
- **424 new connected surface-road sections** give **5,050 expansion sections and eleven routes**. All 4,626 earlier road objects, ten routes, tunnel profiles and original H1 data are unchanged. The 53-section itinerary follows source travel directions. This does not establish bus-access rules or junction turn permissions. Tuen Mun Road, Tsuen Wan Road and unrelated highways/raised interchanges are omitted from the new selection.
- [LandsD building footprints](https://portal.csdi.gov.hk/csdi-webpage/dataset/landsd_rcd_1637211194312_35158): **7,313 source records**, retrieved `2026-10-14T19:12:26.195252+00:00`; WGS84 query bounds `[114.0897941510995, 22.356983471074383, 114.13445519873977, 22.393814229249013]`. Raw SHA-256 `584326827fd08b43e631aa6f3fc1d261cd82513d926d28e3157bbf55fe126ff4`. The downloader checks counts, unique identities and valid geometry before atomically replacing the cache.
- [LandsD iB1000 tile index](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0): **56 GML tiles and 458 source fragments**, including shoreline, seawall/high-water lines and 21 pier outlines. Retrieved `2026-10-14T19:14:49.845940+00:00`. Raw SHA-256 `8591ee89fd71ca4cf25c712e382d56631ceb0f692d402193545373fc95ed1df3`. Every archive URL, revision and hash is retained. EPSG:2326 GML northing/easting is converted to WGS84.
- The regional mainland follows approximately **4.29 km of source-derived coast**. **29 gap-closure records representing 23 distinct joins, at most 55.08 m**, are authored repairs at source interruptions. The initial 12 m join threshold left the coast open and incorrectly filled Rambler Channel; explicit mainland/channel assertions now reject that result. Earlier coast files and land within their region rectangles remain unchanged.

© HKSAR Government, Transport Department / Lands Department. [TD terms](https://data.gov.hk/en/terms-and-conditions), [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC). Runtime is offline.

## Buildings and scenery

The new layout has **4,996 building parts** and **419 render/collision chunk pairs**. Shared BuildingCSUID roof/base heights use all six Kowloon extracts, with newest height/storey inputs taking precedence. Earlier region rectangles are excluded from the new layout. Kwai Chung is rebuilt at the seam: 76 source identities change clipping/frontages, no identities or heights are lost, and 11 paving patches are added; all original, northern, western, Lai Chi Kok and island building/paving arrays are unchanged.

The combined scene contains **29,246 building parts, 2,261 render/collision chunk pairs and 2,932 paving patches**. Blender MCP exports three new GLBs: `tsuen-wan-buildings` (37.66 MB), `tsuen-wan-west-buildings` (29.80 MB), and `kwai-chung-north-buildings` (30.58 MB). The harbour terrain/coast and three Kwai Chung seam GLBs are regenerated; all 267 existing tunnel/deck mesh streams are preserved. The user's original Blender scene, active selection and transforms are restored. Existing generated facade/shopfront atlases, trees, kiosks and scanned posed passengers furnish the district. It receives 48 pedestrians and 12 kiosks; expansion scenery totals 873 trees, 3,073 lamps, 400 posed pedestrians and 102 kiosks.

## Regeneration

```sh
.venv-geodata/bin/python Tools/import_shoreline.py --tsuen-wan --download
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-lai-chi-kok-centerline.kmz --hk1980
.venv-geodata/bin/python Tools/import_buildings.py --tsuen-wan --download
.venv-geodata/bin/python Tools/import_buildings.py --kwai-chung
.venv-geodata/bin/python Tools/import_buildings.py --northwest
.venv-geodata/bin/python Tools/import_buildings.py --west
.venv-geodata/bin/python Tools/import_buildings.py --north
.venv-geodata/bin/python Tools/import_buildings.py
```

Execute `Tools/model_tunnel.py` through Blender MCP, then `Tools/model_government_buildings.py` with `KWAI_CHUNG=True` and `TSUEN_WAN=True` separately. Keep the existing compression-disabled import setting for the harbour GLB. Other building exports may be retained when their rebuilt building/paving arrays are identical.

## Verification status

Evidence: `evidence/tsuen-wan-expansion-2026-10-14/`. Baseline commit `8c70017`; pre-change snapshot `Art/before-tsuen-wan-expansion-2026-10-14/`.

- Data audit passes: earlier road/route/source preservation, connected and source-directed itinerary, full new carriageway land containment.
- Geometry audit passes: no missing added-land ground triangles, no boundary barriers blocking new roads, coastline on the mainland boundary, source-point deviation below 0.1 mm after serialization.
- Building overlap and land-containment checks pass. Six-mode download regression, rejected-response/file-failure cache protection and shared-height refresh regression pass.
- Model audit passes: 2,261 exact render/collision chunk pairs, 228 shared building identities with equal heights, 267 preserved tunnel/deck streams. All building GLBs remain below 100 MB.
- Initial in-engine check correctly fails on the absent U shortcut before implementation. Focused drive passes: 3,489 m physically driven without contacts or departures, U plus four shortcut guards, 393 route-support probes and 94,014 full-bus envelope queries. Build: 0 warnings / 0 errors.
- Native captures pass: nine 1280×800 GL Compatibility views, actual U-key input and 25 land/sea collision probes.
- Full suite passes with exit 0 / `ANTILA_SELF_TEST_OK`: all eleven exploration routes, seven ramp/flyover drives, both side-street turns and the original H1 service (1.08 km, three stops, 26 passengers). The logged outer-barrier contact is intentional. Building, footpath, audio, HUD, signal and controller checks pass.
- Review clarified duplicate gap-record counts and identified crowded overview labels; the label spacing is adjusted and the revised native overview is approved. The final native pass also restores the precise SPACE Handbrake legend. This layout-only edit follows the full driving suite; source geometry and driving code are unchanged.
- Restart regression passes with exit 0: six reloads from paused map, island drive, Lai Chi Kok drive, Kwai Chung drive, Tsuen Wan drive and completed service restore H1. All seven scenes contain 4,522 building meshes / 2,261 collision shapes; 724 roof probes and 2,932 paving checks pass each time, with no engine errors.
- Independent final review finds no remaining code, geometry or visual issues after the provenance wording, label spacing and handbrake legend fixes. The last stale pending-status line is corrected here. Full driving/restart runs used the pre-label-polish assembly; `hud-only-delta.json` confirms that only Hud.cs changed, and the rebuilt final native capture covers that presentation change.
- Final runtime/source hashes, accepted log hashes and native images are recorded in `verification.json`, `final-files-sha256.json` and `native-images.json`. [Before/after comparison](../evidence/tsuen-wan-expansion-2026-10-14/compare.html).

## Limits

Road XY, footprint massing and coastlines are source-derived. Flat terrain, road widths, lane configurations, facade imagery, furniture and itinerary are authored. Real slopes around Tsuen King Circuit and northern Kwai Chung are not modeled. Buildings are clipped for bus clearance and use relative height datums; these are not surveyed architectural replicas. No new moving traffic, real bus timetable, bus-access validation or performance benchmark is claimed.
