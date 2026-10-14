# Mei Foo / Kwai Chung Expansion

Use executing-plans inline and one fresh-context final review. User specification: continue west through Mei Foo toward Kwai Chung.

## Scope and constraints
Preserve all 3,435 current roads, nine routes, tunnels and H1. Extend government-derived land, connected streets and building massing; append a source-direction-valid exploration drive from route 8. Keep runtime offline and existing assets. Widths, elevations, furnishings and itinerary are authored. Reuse isolated Blender exports. No commits or publication requested.

## Review focus
Datum and source identity preservation; land/coast seams and physical barriers; building overlaps and consistent shared heights; route direction, physical bus clearance and shortcut guards; offline loading/restart; HUD readability.

### Task 1: Government geography
Files: Tools/import_tunnel.py, Tools/import_shoreline.py, Data/kwai-chung-{shoreline,coast} and harbour outputs.
- [x] Snapshot baseline and observe failing coverage/preservation audit.
- [x] Select continuous government route, download coast, extend land preserving earlier regions.
- [x] Regenerate roads and pass independent source/geometry audit.
Expected: check-data.py exit 0, earlier roads/routes/source records unchanged.

### Task 2: Buildings and Blender
Files: Tools/import_buildings.py, Tools/model_government_buildings.py, Tools/check_buildings.py, new layout/models and changed seam assets.
- [x] Observe failing building coverage audit.
- [x] Download count-checked footprints, reconcile shared heights across extracts and build new region excluding earlier footprints.
- [x] Export new/changed models through Blender MCP; pass geometry and chunk audits.
Expected: no overlap, missing collision chunks or changed old tunnel/deck mesh streams.

### Task 3: Runtime and verification
Files: Scripts/Main.cs, Main.Harbour.cs, Main.BuildingReview.cs, Main.RestartReview.cs, Hud.cs; README.md and docs/KWAI_CHUNG_EXPANSION.md.
- [x] Add failing route/shortcut/coverage checks; integrate route 9 and B shortcut, buildings and district scenery.
- [x] Pass focused physical route, full self-test, reload check and native capture.
- [x] Independent final review; resolve important findings; record exact sources, limits and evidence.
Expected: 0 build warnings/errors; ANTILA_SELF_TEST_OK; native images inspected and restart succeeds.

## Ledger
Baseline eb81d31c739953be2d494fba6a1531c5820d18ee plus existing uncommitted work, snapshot Art/before-kwai-chung-expansion-2026-10-13.
Ruling: stay in the existing feature checkout, preserving all earlier work; review against the snapshot because HEAD predates multiple expansions. No commit or publishing step.
Pre-flight: shoreline produces the land used for road selection; roads produce building exclusions; layouts produce model chunks/runtime checks. New raw extract must join shared building-height reconciliation and its regression fixture.

RED: data audit fails at missing Kwai Chung roads; building audit fails at missing new layout. Selected 59 ground-level source sections, 5,362.3 m via Lai Wan Road, Lai King Hill Road, Kwai Chung Road, Kwai Yik Road, Hing Fong Road and Kwai Fuk Road. Region (-6500,-8500,-3100,-4400). Reuse the Oct 12 government KMZ hash dcd0632d9d0f72bee549e24307b28ed98b17963c30899de0675d5e1163586735; new coast/buildings fetched Oct 13.

Task 1 complete: road preservation audit exit 0. 1,191 new / 4,626 total roads; ten routes, new sampled centreline 5,358.314 m. All 3,435 prior road objects, nine routes, tunnel profiles, government records and previous coast preserved. Added land 10,653,812.4 m²; bounds 8.71 × 10.73 km. Native before views captured.
Runtime RED: engine exit 1, B shortcut must start the Kwai Chung drive. Implemented B/action/route9, stopped and UI guards, seventh scenery district and new model loads; final runtime verification pending model generation.

Model audit found Kwai Chung GLB was 126 MB, above the existing 100 MB per-asset limit. Split that district again on a 128 m chunk boundary (x=-4864), preserving all geometry; runtime and chunk audit now load three new GLBs. Native/physics results before the split must be followed by final validation against the split assets.

Focused engine run exited 0: B and four guards, 588 lane-support probes, 86,691 full-bus envelope queries; Mei Foo–Kwai Chung physically driven 5,323 m without contacts. This run used pre-split geometry. Final split exports are complete; final model/collision audit and full simulation pending.

Task 2 complete: final model audit exit 0; 267 tunnel/deck streams preserved, all 1,842 chunks have exactly one visual/collision pair, 167 shared identities have equal derived heights. Each GLB <100 MB. New region 3,422 parts /440 pairs /379 patches; total 24,250 parts /1,842 pairs /2,676 patches. Scene/selection/transforms restored through Blender MCP. Building/regional overlap and refresh regressions pass.

Native capture exited 0; B input, all eight views and 16 land/water physics probes pass. Visual inspection found a subtitle panel overflow and lower map labels close to the legend; shorten subtitle and reposition West Kowloon/Admiralty/Wan Chai labels. Coast camera moved to frame the physical coastline. Saved pre-polish images/log; final native run pending.

Final native capture exit 0: revised subtitle/map-label spacing inspected, coastline visible, all eight images, B keyboard event and 16 land/water physics probes pass. Full self-test runs on these final assets/code. One fresh-context read-only final reviewer dispatched; findings pending, no second reviewer planned.

Full self-test exit 0 / ANTILA_SELF_TEST_OK. 17 harbour drives (ten routes + seven focused ramp/flyover drives), two side-street turns, H1 1.08 km / three stops /26 passengers; 602 roof probes,2,676 paving samples,11,077 asphalt/paving samples,86,691 bus-envelope queries. Build 0 warnings/errors. Intentional boundary-contact marker only. Five-reload check running; independent review pending.

Independent final review: no Critical/Important/Minor findings; full self-test and manifest checked by reviewer. Remaining gate is five-reload restart.
Final: Ruling: real terrain gradients remain unmodeled — declared flat-terrain prototype scope; cost: Lai King has no real hillside grades.
Final: Ruling: widths/elevations/lane layouts/turn restrictions/bus access/stops remain authored/unreconstructed — preserve established simulation scope; cost: no real route/lane reconstruction.
Final: Ruling: architectural/facade/furnishing/itinerary fidelity remains approximate — government footprints and relative massing are source authority; cost: no surveyed visual replica.
Final: Ruling: subjective style set aside — captures verify clarity/seams/clipping; cost: no aesthetic-parity claim.
Final: Ruling: performance/memory targets set aside — no benchmark requested; cost: other hardware remains unbenchmarked.
Final: Ruling: reviewer used recorded Blender state — coordinator verifies restored live state; cost: none after matching check.
Final: Ruling: restart result pending — await observed exit0/five reload marker before completion; cost: task stays incomplete until verification.

Task 3 complete: final restart-check exit0, all six constructed scenes/five reloads restore H1 with3,684meshes/1,842collisions;602roof and2,676paving probes each; no engine errors. Full-suite/native/data/building/model/importer gates pass. Final independent review has no findings or deferred minors. All reviewer conditions resolved; live final Blender state matches baseline. Final documentation/checksums retained; work stays local/uncommitted.
