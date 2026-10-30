# Western junction and park fill implementation plan

**Goal:** Address the confirmed western review: restore the Kwai Yue/Kwai Hei roundabout and Wing Shun approach, then furnish the nine government-bounded park gaps with the established recreation pipeline.

**Spec:** `evidence/western-region-review-2026-10-28/review.md`, approved by the user's “Let's fix it”. Reuse current court/path/tree/bench treatment. Source boundaries and sports remain government-derived; internal paths, planting, finishes and flat terrain remain authored.

**Architecture:** Preserve the code-built scene and shared geometry authorities. Extend the existing sourced recreation pipeline if its current interfaces support the western sites; avoid a duplicate importer/runtime/model system. Keep the existing checkout and accumulated dirty work, with a new before-state snapshot. No commit, push or publication.

## Global constraints

- All shell commands start with `rtk`. Mono Godot is `/Applications/Godot_mono.app/Contents/MacOS/Godot`.
- Preserve all 7,223 existing road objects, 14 routes, tunnel profiles, existing coast/ground/bounds and scheduled service data. Only reviewed additions and necessary local building/paving clearance changes are authorized.
- Restore `TD_8457`, `TD_9137`, `TD_9138` in their source one-way direction and the connected `TD_57333` approach. Assess any additional newly reachable named road before retaining it; do not silently broaden the map selection.
- The fresh TD archive in `/private/tmp/antila-western-region-review-2026-10-28/CENTERLINE.kmz` is WGS84 at validated stable anchors, SHA `3df2c43b6f19bf7b34e0022d60d7cf5bd148ae0e0f001191879333d46ba66e52`. Do not apply the archived HK1980 conversion to it.
- Add exactly the nine reviewed park Site IDs: `1503000390`, `1503000414`, `1503000381`, `1503005413`, `1503000199`, `1503005076`, `1810011761`, `1910064509`, `1910069198`. Use complete whole sheets and exact Site/sport fragment multiplicities. The western source sports inventory is the 49 IDs in `confirmed-park-gaps.json` in the review evidence directory.
- Preserve all 16 existing eastern/northern gardens, source Site/sports geometries, path/access/sample arrays, 1,505 fixtures, 71 sport surfaces, 50 fittings and their exported mesh positions. Keep the separate Mong Kok recreation unchanged.
- Every retained paving component must retain its valid interior probe and connection to public pavement. Preserve the 1.1 m safe-interior contract and road/building/sports/stop clearances. Fit rectangular markings only when safe inside source sports outlines.
- Rebuild models only through Blender MCP, in isolated scenes, restoring the user's current scene, objects, selection and active object. No new bitmap asset or asset download is needed.
- Keep runtime offline. Bound the expanded recreation mask to at most 8,192 pixels on either axis (RGB8 buffer at most 192 MiB), by adapting the existing mask request density; preserve native sport/mask probes. Update provenance/attribution, relevant docs and HUD. Build must have zero warnings/errors. Final native views must hide the actual HUD layer and cab and be inspected directly.

## Review focus

1. Restore a source-directed closed roundabout and usable asphalt connection, with a regression that fails on the current missing ring.
2. Preserve all old road/source/route/vertical mesh state while adding the four reviewed sections; clear new road/building intersections through shared geometry.
3. Reject a partial western Site or multi-sheet sport refresh and preserve both output files; retain deterministic valid rebuilds.
4. Preserve existing recreation geometry and ensure every new retained path component is probed and connected; do not hide missing source fragments by clipping the manifest.
5. Verify native terrain priority, safe fixtures, matching model/collision geometry and physically driven roundabout/approach continuity as well as existing services.

### Task 1: Restore the western roundabout and approach

**Files:** `Tools/import_tunnel.py`, relevant existing source/geometry checks or a focused `Tools/check_western_junction.py`, `Data/cross-harbour.json`, `Data/cross-harbour-source.geojson`, affected building layouts, `Scripts/Main.Harbour.cs`, relevant count assertions in `Scripts/Main.cs`, `docs/KWAI_CHUNG_EXPANSION.md`. Regenerate affected harbour/building models using existing generators.

**Interfaces:** Consumes the current verified working tree and fresh validated TD KMZ. Produces the repaired `Data/cross-harbour.json`, pinned source additions, corresponding clear building layouts/models and a focused in-engine physical junction check. These exact road/building files become Task 2's inputs.

- [x] Add and run a red source/geometry check for the three source-directed ring sections and `TD_57333` connectivity, preserving the old road/source/route arrays.
- [x] Retain the required roundabout with the existing explicit-connection pattern; regenerate with WGS84 input, inspect any extra reachable additions, and pin only the authorized scope.
- [x] Regenerate affected building clearances and models; preserve unchanged regions and old tunnel/deck mesh streams. Add meaningful in-engine pavement/physical driving coverage for the restored junction and approach.
- [x] Pass focused source/geometry/model/build/runtime checks, document provenance and provide scoped before/current diff and report for task review.

### Task 2: Fill the nine western parks

**Files:** `Tools/import_east_open_spaces.py`, `Tools/check_east_open_spaces.py`, `Scripts/Main.EasternOpenSpaces.cs`, count/credit callers where needed, `Data/east-kowloon-open-spaces.json`, `Data/east-kowloon-open-spaces-source.geojson`, existing recreation blend/GLB, `README.md`, `docs/EAST_KOWLOON_OPEN_SPACES.md`, a companion western recreation doc if needed. Use `Tools/model_open_spaces.py` unchanged unless a real reuse issue requires a minimal change.

**Interfaces:** Consumes Task 1's final roads/buildings, review Site polygons, 41 current western whole-sheet ZIPs and existing 16-site archives. Produces a single integrated 25-site recreation source/layout/model and runtime reservations/checks using the established schema.

- [x] Add and run red coverage checks for the nine Site IDs and 49 western source sports IDs. Obtain a complete official index response for the enlarged extent and pin exact selected fragments.
- [x] Extend the existing importer, source validation and runtime counts/reservations; reuse placement and connectivity logic. Pin exact Site fragment multiplicity as well as sports (including two Tsuen Wan Site patches on one sheet). Use complete western/mainland land and street-target extents, and cap the recreation mask at 8,192 per axis with in-engine assertions. Preserve all existing Site/sports/path/fixture/fitting records.
- [x] Regenerate source/layout deterministically, reject malformed/partial refreshes without changing outputs, and export the recreation model through Blender MCP.
- [x] Pass source, failure-atomicity, preservation, model, build and in-engine checks. Update attribution/docs and produce a task review package.

### Task 3: Verify the integrated result and record delivery

**Files:** `evidence/western-map-fixes-2026-10-28/`, final documentation verification sections.

**Interfaces:** Consumes Tasks 1–2's reviewed code/data/models; produces fresh headless/native logs, matching before/after views and a hash-bound final report.

- [x] Run the full in-engine suite, including existing exploration routes/services and the new junction drive; repair any regressions before proceeding.
- [x] Run native terrain/building checks and capture the nine parks plus repaired junction/approach, source map and relevant map UI. Directly inspect the images and verify local gallery links.
- [x] Audit all baseline product files, previous source/layout/model geometry and final evidence hashes; dispatch one fresh whole-change reviewer and address confirmed defects.
- [x] Record completed work, actual verification and remaining physical/manual/performance limits; leave the work local and uncommitted.
