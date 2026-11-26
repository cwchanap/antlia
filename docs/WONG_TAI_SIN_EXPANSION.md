# Wong Tai Sin extension — 24 October 2026

This extension continues north from Kowloon City toward Wong Tai Sin and Chuk Yuen. It added 552 government road sections (7,223 total at the time) and a 2.122 km exploration drive of 39 directed source sections / 550 sampled points. The October Kwai Chung junction repair added four reviewed sections, for 7,227 at that snapshot. **Y while stopped** selects the `Kowloon City → Wong Tai Sin` exploration drive. **P** selects the preceding eastern drive. H1, H2 and H3 remain the same fictional scheduled services. [Current district coverage through Diamond Hill](DIAMOND_HILL_EXPANSION.md)

The eastern inland selection grows from `(550,-4700,3150,-100)` to `(550,-6400,3150,-100)` local metres. The overall 17.11 × 13.43 km world and terrain-mask bounds stay unchanged. The extended regional land covers 13.084 km²; its 576 shoreline fragments and 7.202 km coast are unchanged. The new northern edge is an authored map cut. Existing government shoreline fragments and the earlier eastern land remain intact.

## Government sources and identity

Road XY and directions come from the [Transport Department Road Network](https://data.gov.hk/en-data/dataset/hk-td-tis_15-road-network-v2), using the retained CENTERLINE snapshot retrieved on 12 October 2026 UTC, SHA-256 `dcd0632d9d0f72bee549e24307b28ed98b17963c30899de0675d5e1163586735`. Stable ROUTE_ID values retain the older road snapshots. The [Lands Department district map](https://www.landsd.gov.hk/doc/en/mapping/ehkg/MapPages/GeoPDF/KN03_KowloonTong_WongTaiSin.pdf) provides a separate geographical reference. No Google tiles, imagery or meshes are bundled.

The connected itinerary needs the government's elevated Fung Mo Street link `TD_103731`. The parallel `TD_103730` also has its own source-connected ground approaches; neither carriageway is snapped to the other. TD `ELEVATION` describes a relative road level, not a measured height in metres. Its metric deck/ramp profile follows the prototype's authored convention; ordinary terrain is flat. Exact surveyed gradients, hillside terrain, full turn restrictions and detailed temple interiors are outside this extension.

The two neighbouring one-way approaches `TD_103438` and `TD_103954` use authored 3.2 m and 3.0 m single-lane ribbons respectively, fitted to the available space beside the decks. The initial 6 m ribbons let their outer bus lanes intersect the adjacent structure. Source XY and continuous height samples remain unchanged, and the actual lower crossing stays low. Lane centers are fitted inside the road using the full 2.48 m bus body and a 0.25 m edge margin; left, center and right full-size collision probes remain. The single-lane ribbons have no two-lane divider. These widths are game authoring, not a surveyed lane-width claim.

Buildings come from the [Lands Department CSDI Building dataset](https://portal.csdi.gov.hk/csdi-webpage/dataset/landsd_rcd_1637211194312_35158). The expanded query was retrieved at 2026-10-25 05:13:05 UTC (24 October in Vancouver): 8,137 features, including six valid MultiPolygons. Its feature-array SHA-256 is `4a57ccc71a97b045a48271ff217ce1eaeb7b76e038d7b52f8e7ad7f19fe3e163`.

The service revised many OBJECTIDs and footprints. Merge identity therefore uses persistent `BuildingCSUID`: all 6,559 saved records remain verbatim, including 18 now absent from the live response. Only 1,594 previously unseen northern identities are appended, producing 8,153 cached records. Thirty-eight new records reuse an older OBJECTID; their internal IDs are deterministically reassigned, with the upstream value retained in `source_OBJECTID` and an explicit provenance map. Raw new geometry and other source attributes are retained. Existing file-level height precedence remains pinned; `query_retrieved_utc`, donor metadata and merge provenance distinguish the mixed snapshots.

© HKSAR Government / Transport Department / Lands Department. [DATA.GOV.HK terms](https://data.gov.hk/en/terms-and-conditions), [CSDI terms](https://portal.csdi.gov.hk/csdi-webpage/doc/TNC). No government endorsement is implied.

## Assets and approximations

Coordinates retain the established approximate metre projection (+X east, −Z north); north–south distances are about 0.53% longer than geodesic distance. The older road arrays remain pinned.

The existing eastern source/layout is extended rather than adding a tenth layout. Blender MCP exports the shared ground/boundaries and affected building regions. Eastern building chunks north of the existing 128 m boundary at northing 4,864 m use `wong-tai-sin-buildings.glb`; the three earlier eastern assets keep their roles. Each visual chunk has a matching collision chunk. The final nine layouts contain 39,946 parts; the east contains 8,528, including 1,666 parts in 202 Wong Tai Sin chunk pairs. All four eastern GLBs are below 100 MB; the northern GLB is 75.37 MB. All 496 protected prior tunnel/deck accessor streams remain exact. Two unchanged west-model files were restored byte-for-byte after equivalent generator output was checked. Modeling restores the user's original Blender scene.

Facade textures, trees, lamps, kiosks and fixed-pose people reuse existing authored assets and clearance rules. The 24 October native build placed 116 roadside trees, 346 lamps, 48 pedestrians and 12 kiosks through existing clearance rules. The 28 October park fill reserves the added gardens from later roadside placement: the current native build places 110 roadside trees and 339 lamps, with the same people/kiosks, alongside the seven parks’ 712 new tree and bench fixtures. Road widths, pavement, metric deck height, planting and facade appearance are authored approximations. No new scheduled service, landmark-faithful temple model, walking animation or performance benchmark is claimed. Gameplay remains offline.

## Park refresh

Clearance-input hashes were refreshed for the existing parks. Government site boundaries, sports/fittings, path/access geometry and paved areas remain unchanged. Deterministic authored furniture regeneration changes Mong Kok from 325 to 324 fixtures and eastern Kowloon from 788 to 793; these are bench-placement changes, not new source corrections. The older recreation group is now 273 fixtures, with 51 pocket-garden fixtures. Most eastern positional differences are below 1 mm; a few benches move farther along the same paths, up to 14.56 m. The saved older positions remain clear. See the evidence `park-delta-review.md`; the baseline Mong metadata was already stale, while eastern metadata was consistent.

## 28 October open-space continuation

The northern park fill extends the eastern recreation dataset to 16 government-bounded sites across 16 complete iB1000 sheets. Its current layout contains 71 unique source sports outlines across 81 sheet fragments, 50 fitting records, 1,505 authored fixtures and 44,518 paving triangles. The expanded CSDI index query, source hashes, revision dates, retrieval times and preservation comparisons are recorded in [the eastern open-space source and verification notes](EAST_KOWLOON_OPEN_SPACES.md). The existing nine site geometries, old 38 source sports outlines/42 sheet fragments, old path/access arrays and 793 fixtures are preserved exactly. This remains a stylized recreation layout; it does not establish present-day construction access or venue opening status.

## Verification — 25 October 2026

The final fixed-60 full engine self-test passed with exit 0 and `ANTILA_SELF_TEST_OK`. It includes 133,581 full bus-envelope queries, all 23 physical exploration/approach drives, the new WTS support/shortcut guards, and H1/H2/H3 terminus-to-terminus: 15 stops and 119 passengers, without route contacts or red-light crossings. Six fitted-lane samples and all 12 H2/H3 stop centers protect the original combined-carriageway service fit. The original 1.08 km steering/boarding loop also passes. The deliberate boundary-contact check remains active.

| Check | Recorded result |
| --- | --- |
| .NET build | Exit 0; 0 warnings / 0 errors |
| WTS source/preservation | Exit 0; directed itinerary, all old records, shoreline, tubes and routes preserved; 72 full bus OBBs clear of 1,888 raised triangles |
| Actual GLB audit | Exit 0; 496 older structural mesh streams exact; 680 eastern visual/collision chunk pairs match the layout |
| Park source guards | Both exit 0; Mong Kok rejects 17 invalid/file-failure cases; East Kowloon rejects 18, retaining all 42 reviewed sports fragments |
| Full engine suite | Exit 0; 23 exploration/approach drives plus all three services and existing checks |
| Native Compatibility captures | Exit 0; six scene views and two keyboard-driven maps inspected, including the road/coast raster and H2 label spacing |

The [evidence gallery](../evidence/wong-tai-sin-expansion-2026-10-24/index.html), [verification record](../evidence/wong-tai-sin-expansion-2026-10-24/verification.json), and [preservation audit](../evidence/wong-tai-sin-expansion-2026-10-24/preservation-audit.md) retain the results and before/after views. Source/code/asset backups and the initial 464 file hashes precede regeneration. A fresh independent whole-feature review found the Fung Mo bus-envelope and map-label defects; both were corrected and their regressions pass. The [final scoped review](../evidence/wong-tai-sin-expansion-2026-10-24/fix-wave-review.md) has no actionable residual defects after checking the full-suite results and all eight native images.

The headless run explicitly skips the older combined terrain-edge numeric render probes; these scenery captures do not imply those probes ran. Reload stress and performance benchmarking were not run. No DEM/hillside reconstruction or survey-grade metric elevation is claimed. Delivery remains local and uncommitted.

## Capture review follow-up — 25 October 2026

A fresh review found the final six scenery images still had the route-selection menu over them. The capture helper now hides the actual HUD CanvasLayer, restores it for both keyboard maps, and fails if the layer is missing. It also reuses the existing forced-render capture method when a window is covered. The replacement native run exits 0; all six unobstructed scenery views and both restored road/coast maps were directly inspected by root and an independent reviewer. The [fix record](../evidence/wong-tai-sin-expansion-2026-10-24/self-review-fix-2026-10-25/review.md) preserves the obscured before images and corrected evidence. Game code, map data and assets are unchanged; the prior full driving test was not repeated.

## Execution decisions

- Proceed under the user's standing planning/execution delegation. A mistaken scope assumption could require reversible rework.
- Reuse the current feature checkout because the complete map baseline is uncommitted; preserve unrelated files with saved hashes and explicit file ownership. Incorrect preservation would affect unrelated work.
- Prepare disjoint source, building and runtime changes in parallel; serialize derived layouts, Blender exports and engine runs. Interface mismatches must be fixed before verification.
- Leave the delivery uncommitted and review against the saved baseline, since HEAD alone does not describe this feature's starting point.
- Merge buildings by persistent identity and annotate transient-ID collisions. A wrong identity match could duplicate or omit a newly mapped building; uniqueness and geometry/provenance checks are required.
- Accept deterministic authored bench reflow when refreshing park inputs, preserving the actual park/path/sports geometry. An unwanted aesthetic change costs reversible furniture-placement rework.
- Include the real elevated connector with an authored metric profile. A bad grade could create a vertical step or clearance failure; directed joins, profile continuity and physical driving must pass.
- Fit the two new one-way bypass lanes to their source spacing, preserving the lower crossing and all existing wider-road offsets. An incorrect width assumption could leave a link undriveable; analytical and actual full-bus checks are required.

## Northern park verification — 28 October 2026

The seven reviewed park gaps are filled through the existing eastern recreation layer: 16 total sites, 71 source sports outlines, 50 model/collider pairs and 1,505 fixtures. All earlier nine garden arrays, 38 sports surfaces, 25 fitting records and 793 fixture records remain exact. The source refresh passes 19 rejected-refresh cases and deterministic byte comparisons. Build, Blender export, full physical-driving suite, native building/render checks and 14 final native captures pass; the independent review has no actionable findings. The native run now also executes the 72 combined terrain-edge probes that the earlier headless-only expansion could not prove.

[Park sources and verification](EAST_KOWLOON_OPEN_SPACES.md), [before/after gallery](../evidence/wong-tai-sin-open-spaces-2026-10-28/index.html), [independent review](../evidence/wong-tai-sin-open-spaces-2026-10-28/final-review.md). Reload stress and performance benchmarking remain unrun; paths, planting, flat terrain and metric elevations remain authored.
