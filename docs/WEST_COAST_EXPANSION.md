# Ting Kau / Sham Tseng coastal expansion

**O while stopped** starts an **8.317 km exploration drive** from the existing Tsuen Wan endpoint through Tsuen King Circuit, On Yin Street and Castle Peak Road to Ting Kau and Sham Tseng. The initial circuit preserves the incoming direction of the preceding drive. **M** opens the map; **R** returns to H1. This adds exploration, with no new passenger service or turn-by-turn navigation.

Loaded bounds are **16.01 km east–west × 13.43 km north–south**, `[-13880,-11280,2130,2150]` in world X/Z. The selection rectangle is `[-13800,-11200,-6400,-6900]`, adding 18,742,880 m² of mainland outside previous regions. Bounds include undeveloped land and water; they do not imply continuous road coverage. The established approximate metre projection retains about 0.53% north–south stretch.

## Sources and accuracy

- [Transport Department Road Network (2nd Generation)](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2): official CENTERLINE.kmz downloaded 12 October 2026 UTC, SHA-256 `dcd0632d9d0f72bee549e24307b28ed98b17963c30899de0675d5e1163586735`. New geometry is converted from HK1980 geographic EPSG:4611 to WGS84, then projected into the established world. Stable ROUTE_ID retains earlier source snapshots.
- **114 new connected sections** give **5,164 expansion sections and twelve routes**. All 5,050 earlier road objects, eleven routes, tunnel profiles and original H1 files are unchanged. The 75-section itinerary follows source travel directions, including two required unnamed connectors. This does not verify bus-access rules or junction turn permissions. Tuen Mun Road and unrelated highways/interchanges are omitted.
- Castle Peak Road source-level-1 sections west of the prior Tsuen Wan boundary retain their relative raised status. Their **7 m decks and 150 m transition profiles are authored**, using the existing bridge treatment; source level is not a measured height. Existing elevated road profiles remain unchanged.
- [LandsD building footprints](https://portal.csdi.gov.hk/csdi-webpage/dataset/landsd_rcd_1637211194312_35158): **3,811 source records**, retrieved `2026-10-15T07:06:08.795770+00:00`; WGS84 query bounds `[114.03833685707917,22.356983471074383,114.11018289023961,22.395610851598995]`. Raw SHA-256 `a3a5ec67b1fc406dd879ba3490dbf6fecfe6cc81d618502271284d08e61b3a52`.
- [LandsD iB1000 tile index](https://portal.csdi.gov.hk/server/rest/services/common/landsd_rcd_1637223748322_25497/FeatureServer/0): **97 GML tiles, 1,164 retained fragments**: 495 Shoreline, 521 seawall/high-water lines, 40 pier outlines and 108 connected rocky-shore outlines from CartoLandCoverLine. Retrieved `2026-10-15T07:08:23.480236+00:00`. Raw SHA-256 `40a318d6db94d03917aa15fb0d9eb1bdbaa6db2248fa5c49404ee0eacb2377c6`. Archive URLs, revisions and hashes are retained. EPSG:2326 northing/easting is converted to WGS84.
- The regional shoreline is approximately **10.07 km**, including overlap with Tsuen Wan. **111 closure records represent 87 distinct authored joins, at most 115.34 m**. Connected government rock outlines close the missing rocky foreshore; inland rock outlines are excluded. A 1 mm topology grid and up-to-0.25 m simplification support polygonization. Earlier coast files and mainland geometry inside earlier regions remain unchanged. Sea off Sham Tseng remains open.

© HKSAR Government, Transport Department / Lands Department. [TD terms](https://data.gov.hk/en/terms-and-conditions), [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC). Runtime remains offline; Google Maps imagery, tiles and meshes are not included.

## Buildings and assets

The new layout contains **2,134 building parts**, **195 render/collision chunk pairs**, and **57 small paving patches**. Shared BuildingCSUID heights use seven Kowloon extracts, with newest height/storey inputs taking precedence. Earlier region rectangles are excluded from the new layout. All earlier building arrays are unchanged; the Tsuen Wan paving serialization changes, but its geometric union is identical. Earlier building GLBs are retained.

The combined scene contains **31,380 building parts, 2,456 render/collision chunk pairs and 2,989 paving patches**. Blender MCP exports `west-coast-buildings.glb` (33.72 MB) and its editable blend, and regenerates harbour ground, shoreline and raised-road assets. Existing generated facade/shopfront atlases, trees, kiosks and scanned posed passengers are reused. The new district receives 48 pedestrians and 12 kiosks; expansion scenery totals 915 trees, 3,187 lamps, 448 posed pedestrians and 114 kiosks. All 267 earlier tunnel/deck mesh streams remain unchanged. Models are generated in isolated Blender scenes and restore the original scene and selection.

## Regeneration

```sh
.venv-geodata/bin/python Tools/import_shoreline.py --west-coast --download
.venv-geodata/bin/python Tools/import_tunnel.py /tmp/antila-lai-chi-kok-centerline.kmz --hk1980
.venv-geodata/bin/python Tools/import_buildings.py --west-coast --download
.venv-geodata/bin/python Tools/import_buildings.py --tsuen-wan
.venv-geodata/bin/python Tools/import_buildings.py --kwai-chung
.venv-geodata/bin/python Tools/import_buildings.py --northwest
.venv-geodata/bin/python Tools/import_buildings.py --west
.venv-geodata/bin/python Tools/import_buildings.py --north
.venv-geodata/bin/python Tools/import_buildings.py
```

Execute `Tools/model_tunnel.py` through Blender MCP, followed by `Tools/model_government_buildings.py` with `WEST_COAST=True` in a fresh execution namespace. Retain the compression-disabled harbour import setting. Rebuild earlier regional building models only when their building arrays change; pavement patches are consumed directly by the runtime.

## Verification

Evidence directory: `evidence/next-expansion-2026-10-14/`. Baseline is the reviewed Tsuen Wan working tree on `8c70017`, saved in `Art/before-next-expansion-2026-10-14/` with a 154-file hash manifest.

- Data and geometry checks pass: unchanged earlier roads/routes/source records, zero route seam gap, matching incoming heading, source travel directions, full carriageway land support, no missing added-land ground triangles and no boundary barriers crossing new roads. Maximum serialized point deviation from the source centreline is below 0.1 mm.
- Land/sea assertions rejected the first incomplete coastline. A separate regression rejected fragmented seawall output; the repaired complete polygon boundary now has no missing coastal span beyond the 0.3 m tolerance.
- Building containment and cross-region overlap checks pass. Seven-mode download safety and newest shared-height/fallback regression pass. Model checks confirm exact chunk pairs, all 267 earlier tunnel/deck streams and 234 shared building identities with equal heights.
- Initial engine checks pass O plus four shortcut guards, 909 route-support probes, 12,332 asphalt/pavement samples and 96,822 full-bus envelope probes. A nearest-texel audit mismatch is corrected to use the shader's linear sampling. The normal-clock drive then exposed an overshoot at a tight staggered junction; the test follower now anticipates sharp turns and slows earlier, preserving road geometry, player handling and the departure limit.
- Full/restart checks exposed a narrow existing island paving patch that missed texel centres at the expanded 16K mask cap. Paving rasterization now conservatively covers touched texels, with a half-texel-diagonal texture margin; no physical footprints or roads change.
- Final native capture passes with exit 0: nine 1280×800 GL Compatibility views, actual O-key input and 25 land/sea collision probes. All nine images were inspected. Ting Kau label spacing and the long tunnel label are corrected. The overview/seam views retain the camera-attached cab overlay used in the baseline captures; the map and street views provide additional inspection angles.
- Full suite passes with exit 0 / `ANTILA_SELF_TEST_OK`: all twelve exploration routes, seven ramp/flyover drives, both side-street turns and the original 1.08 km H1 service (three stops, 26 passengers). The new coastal drive physically covers 8,238 m without contacts or departures. All 2,989 paving patches, 776 roof probes, building facade checks, audio, HUD, signals and controller regressions pass. The logged outer-barrier collision is intentional. Build: **0 warnings / 0 errors**.
- Restart suite passes with exit 0: seven reloads from paused map, island drive, Lai Chi Kok drive, Kwai Chung drive, Tsuen Wan drive, west coast drive and completed service. Each of eight scenes has 4,912 building meshes / 2,456 collision shapes and restores H1; no engine errors occur.
- The independent reviewer identified the tight-turn driver failure and confirmed the map-label issue, both addressed. Its final assessment was interrupted by a service usage limit. The remaining source/runtime review was completed locally; this is not a completed independent sign-off. No further actionable issue was found locally.
- Headless full/restart commands use `--fixed-fps 60`, which [disables wall-clock synchronization while supplying a fixed frame duration](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html). Physics tick rate and the suite's existing time scale are unchanged; this is not a performance measurement.
- `verification.json` records accepted commands and results; `final-engine-inputs-sha256.json` binds the engine checks to 69 unchanged runtime files. `final-files-sha256.json` and `native-images.json` record final source, asset, documentation and image hashes. Failed diagnostic runs are retained separately and are not acceptance results.

## Street-label fix — 16 October 2026

The self-review reproduced literal `&lt;Null&gt;` street labels on source connectors `TD_110626` and `TD_110628` near Ting Kau. `CurrentStreet()` now displays **UNNAMED CONNECTION** for encoded/raw null markers, `-99` and blank names. Raw government attributes remain unchanged; named streets and tunnel names retain their source names. The three earlier `-99` links now receive the same neutral fallback instead of a location-specific Wan Chai label.

The existing `CheckHud()` regression visits all five unnamed links, explicitly requires both Ting Kau connectors and verifies named-street restoration. `./run.command --headless --fixed-fps 60 -- --hud-check` passes with exit 0, `ANTILA_HUD_CHECKS_OK` and `ANTILA_REVIEW_CHECKS_OK`; build **0 warnings / 0 errors**. This also covers the existing cache, lane/service guidance, map/input, camera and taxi regressions. The earlier failing reproduction remains in `evidence/west-coast-self-review-2026-10-16/runtime-labels.log`; the passing run, small diff and hashes are in `evidence/west-coast-label-fix-2026-10-16/`.

Full driving/reload suites and native captures were not repeated for this display-only fix. All frozen runtime files except `Main.cs` and `Main.Harbour.cs` match the previous expansion snapshot; the earlier full-suite evidence belongs to that recorded snapshot.

## Limits

Road XY, footprint massing and coastline derive from government data. Terrain is flat; the hills, real road gradients, road widths, lane layouts, facade imagery, furniture and itinerary are authored. Buildings are clipped for bus clearance and use relative roof/base datums. This is not a surveyed reconstruction of Ting Kau or Sham Tseng. No moving traffic expansion, real timetable, bus-access validation or performance benchmark is claimed.
