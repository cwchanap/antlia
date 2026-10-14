# Mei Foo / Lai King / Kwai Chung expansion

The connected map continues west and north from Mei Foo through Lai King into Kwai Chung. **B while stopped** starts a **5.358 km exploration drive** at the previous Lai Chi Kok route endpoint. **M** shows the map and **R** returns to H1. The authored itinerary follows Lai Wan Road, Lai King Hill Road, Kwai Chung Road, Kwai Yik Road, Hing Fong Road and Kwai Fuk Road. It adds no passenger service or turn-by-turn guidance.

Bounds are **8.71 km east–west × 10.73 km north–south**, `[-6580,-8580,2130,2150]` in world X/Z. The selection rectangle is `[-6500,-8500,-3100,-4400]`; 10,653,812 m² of land is added beyond earlier regions. These are loaded bounds, not continuous road coverage. The established approximate metre projection has about 0.53% north–south stretch.

## Government sources

- [Transport Department Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2): the full official CENTERLINE.kmz downloaded 12 October 2026 UTC is reused, SHA-256 `dcd0632d9d0f72bee549e24307b28ed98b17963c30899de0675d5e1163586735`. HK1980 geographic EPSG:4611 is converted to WGS84 before local projection. Stable ROUTE_ID preserves all preceding source records and road objects.
- 1,191 new connected ground-level road sections give **4,626 expansion sections and ten routes**. All 3,435 earlier roads, nine routes, tunnel profiles and original H1 data are unchanged. The 59-section new route obeys source travel-direction attributes; this does not establish vehicle-access or junction turn restrictions. Highways and unrelated raised interchanges are omitted from this expansion.
- [Lands Department building footprints](https://portal.csdi.gov.hk/csdi-webpage/dataset/landsd_rcd_1637211194312_35158): **4,690 source records**, count-checked and unique by OBJECTID, retrieved `2026-10-13T14:04:28.268122+00:00`. WGS84 query bounds `[114.1092119978996, 22.334525691699607, 114.14222233745981, 22.371356449874238]`. Raw SHA-256 `b612b211c966464bc7e7e1c4b161f93ad81e5cdaf5c633736c64e669bccafc4f`.
- [Lands Department iB1000 tile index](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0): **48 GML tiles, 330 shoreline/seawall/high-water fragments**, retrieved `2026-10-13T14:05:55.432086+00:00`. Each archive URL, revision and hash is retained in `Data/kwai-chung-shoreline.geojson`. GML EPSG:2326 northing/easting is transformed to WGS84. There are **28 recorded source-gap joins**, at most **5.37 m**; these joins are authored. All prior coast extracts and the land inside their rectangles remain unchanged.

Attribution: © HKSAR Government, Transport Department / Lands Department. [TD terms](https://data.gov.hk/en/terms-and-conditions), [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC). Runtime is offline; source queries and tools are regeneration-only.

## Building integration

The new region has **3,422 derived building parts**. Earlier regions are excluded geometrically. Shared roof/base heights are reconciled across five Kowloon extracts using persistent BuildingCSUID; newest dated height inputs win. Lai Chi Kok now has 2,795 parts: 38 retained source identities change near the new roads, five are removed for clearance and five derived heights change. Original, northern, western and island building/paving arrays are unchanged.

**24,250 building parts, 1,842 render/collision chunk pairs and 2,676 paving patches** load across all regions. Blender MCP generates `kwai-chung-buildings.glb`, `kwai-chung-east-buildings.glb` and `lai-king-buildings.glb`, using the established 128 m render/collision chunks and existing generated facade/shopfront atlases. Three Lai Chi Kok seam GLBs and the harbour ground/coast GLB are regenerated. The original Blender scene, selection and transforms are preserved. Existing trees, lamps, scanned posed pedestrians and kiosks furnish the new streets. The new district has 48 pedestrians and 12 kiosks; expansion scenery totals 805 trees, 2,825 lamps, 352 posed pedestrians and 90 kiosks.

## Regeneration

```sh
.venv-geodata/bin/python Tools/import_shoreline.py --kwai-chung --download
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-lai-chi-kok-centerline.kmz --hk1980
.venv-geodata/bin/python Tools/import_buildings.py --kwai-chung --download
.venv-geodata/bin/python Tools/import_buildings.py --northwest
.venv-geodata/bin/python Tools/import_buildings.py --west
.venv-geodata/bin/python Tools/import_buildings.py --north
.venv-geodata/bin/python Tools/import_buildings.py
```

Through Blender MCP execute `Tools/model_tunnel.py`, then `Tools/model_government_buildings.py` with `KWAI_CHUNG=True` and `NORTHWEST=True` separately. Keep each GLB below 100 MB and preserve `cross-harbour.glb.import`'s compression-disabled setting. Retain old exports for any other region whose rebuilt building/paving arrays are unchanged.

## Verification

Evidence is in `evidence/kwai-chung-expansion-2026-10-13/`. The baseline is `Art/before-kwai-chung-expansion-2026-10-13/`, including all earlier uncommitted expansions.

- Data/preservation audit passed: unchanged prior roads/routes/source snapshots; source-direction-valid new route; new carriageways contained on mainland.
- Building overlap and height-refresh regressions passed.
- Geometry audit passed: no missing ground triangles in added land, no outer barriers across new carriageways, and coastline lies on the mainland boundary.
- Initial engine regression failed on the missing B shortcut as expected. Initial model audit caught a 126 MB asset; it is split into existing spatial chunks before final validation.
- Final model audit passed: all 1,842 render/collision pairs match, 167 shared building identities have equal heights, and 267 earlier tunnel/deck position/index streams are preserved. The three new GLBs are 63.3 MB, 70.5 MB, 18.8 MB.
- Focused physical drive passed: 5,323 m without contacts/departures, B and four shortcut guards, 588 route-support probes and 86,691 full-bus envelope queries. This run used equivalent pre-split geometry; final split assets are covered by later native/full runs.
- Final `self-test.log`: exit 0 / **ANTILA_SELF_TEST_OK**. All ten complete routes and seven focused ramp/flyover drives pass, both side-street turns pass, and the original H1 service physically covers 1.08 km with three stops and 26 passengers. Building/footpath/audio/HUD/signal/controller regressions pass; build 0 warnings / 0 errors. The single ANTILA_TEST_CONTACT is the intentional outer-barrier test.
- `capture-final.log`: exit 0, eight native 1280×800 GL Compatibility views, B-key input and 16 new-coast land/water physics probes pass. The final map/subtitle labels are spaced clearly; [before/after comparison](../evidence/kwai-chung-expansion-2026-10-13/compare.html).
- `restart-check.log`: **exit 0**, five reloads from paused map, island drive, Lai Chi Kok drive, Kwai Chung drive and completed service restore H1. All six constructed scenes have 3,684 building meshes / 1,842 collision shapes, 602 roof probes and 2,676 paving checks passing; no engine errors.
- Independent fresh-context final review: **no Critical, Important or Minor findings**. The reviewer checked code, geometry, data, current hashes and native images; the pending restart gate was then completed by the coordinator. Recorded as `final-review.md`.
- `verification.json` records accepted gates/log hashes; `final-files-sha256.json` records the final code/data/models/docs. No commits or publication were requested; the prior scene snapshot and current checkout are retained.

The later self-review found a shared building-downloader issue: an empty or malformed service response could overwrite the valid cache before layout generation rejected it. The [13 October cache-safety fix](../evidence/building-download-fix-2026-10-13/REPORT.md) validates responses and stages an atomic replacement. Its regression covers all five regional modes and preserves previous bytes on rejection or file failure. The shipped map data and assets were not regenerated.

## Limits

Road XY, footprints and coastline are source-derived. Road widths, deck heights, flat ground, furnishings, facade imagery and itinerary are authored. **Lai King Hill Road is horizontally aligned to source data but its real gradients and hillside terrain are not modeled.** Junction turn restrictions, restricted bus access, lane configurations and real bus stops are not reconstructed. Buildings use relative height datums and clipped footprint massing rather than surveyed architectural replicas. No frame-time or memory benchmark is claimed.
