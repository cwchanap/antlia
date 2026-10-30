# Wong Tai Sin extension

The user requested continuing the existing eastern map until Wong Tai Sin. Their standing instruction delegates planning and execution. Godot C#, the government-data pipeline, Blender MCP and the existing visual style stay in use.

## Scope and approach

Extend the existing eastern land selection north from `(550,-4700,3150,-100)` to `(550,-6400,3150,-100)` metres. This reaches Wong Tai Sin Road and the Chuk Yuen surroundings without increasing the 17.11 × 13.43 km world/mask bounds. Add a connected exploration drive from the present Kowloon City endpoint to Wong Tai Sin Road, with government-directed source sections. Keep the existing thirteen exploration drives and H1/H2/H3 services unchanged. Y while stopped starts the new fourteenth exploration drive; P retains the existing eastern drive.

Considered a narrow road-only corridor and a separate district dataset. The selected extension reuses the current eastern region: it supports surrounding streets and building density while keeping the nine building-layout contracts and existing mask extent. A separate district layout would unnecessarily change all park-clearance consumers. The northern closure is an authored inland map cut; retain the existing government shoreline and repairs exactly.

## Data and appearance

Reuse the verified TD CENTERLINE snapshot at `/private/tmp/antila-east-kowloon-centerline.kmz` with its recorded datum conversion and stable ROUTE_ID pinning. Preserve all 6,671 existing road/source records, thirteen route arrays and both tube profiles. Add only connected, assessed road sections in the northern extension, including the TD Fung Mo Street elevated connector needed to reach Wong Tai Sin Road; store an explicit directed source-ID itinerary reaching Wong Tai Sin Road. Do not infer traffic restrictions or surveyed metric elevation from TD relative levels.

Fetch and validate the additional LandsD/CSDI building coverage. Preserve every existing eastern source feature; retain old footprints/attributes and merge only genuinely additional northern records, recording query bounds, retrieval time, hashes and merge provenance. Keep eight Kowloon source extracts and nine layout files. Reconcile their shared base/roof data using the existing pipeline, and rebuild only assets whose geometry changes. Split the northern east-building chunks at an existing 128 m boundary into `wong-tai-sin-buildings.glb` so individual GLBs remain below 100 MB.

Rebuild the shared ground/water/boundary GLB and changed government-building GLBs through isolated Blender MCP scripts, restoring the user's scene. Reuse the existing generated facade, street-prop and passenger assets. Add ordinary roadside scenery using current clearance helpers and a WONG TAI SIN map label. Internal park/temple detail and exact hillside grades remain outside this first extension: ordinary terrain is flat, with established authored bridge/tunnel profiles. Source review established that the new itinerary needs TD_103731 at relative level 1; use the existing authored deck/ramp convention on new sections, with explicit continuity and clearance checks.

## Preservation and acceptance

- Preserve all older road/source geometries, route arrays, service routes/stops, tubes and shoreline fragments. Explicitly test parity with the saved baseline.
- The new drive must follow allowed source directions, join the old endpoint, reach Wong Tai Sin Road and have ground support and bus clearance throughout.
- Match rendered building geometry/collision to the refreshed layouts; record any earlier layout geometry that genuinely changes before deciding which assets to rebuild.
- Rebuild derived open-space metadata when clearance input hashes change; retain the nine source park boundaries, 42 reviewed sports fragments, 38 sports surfaces and 25 fitting records. Preserve useful paving/fixtures unless an actual new clearance constraint requires a recorded correction.
- Check Y's stopped/map/pause/completion guards, district-label placement, northern boundary collision and the old eastern shortcut.
- Require a clean .NET build, focused source checks, full engine self-test, native captures and one fresh final independent review. Record all evidence and limits; no performance or survey-grade claim.

## Coordinator choices

Bounds, a separate Y exploration shortcut, reuse of the current eastern source/layout, and the fourth eastern GLB are implementation choices made under the user's delegated execution instruction. They do not add a scheduled service, change the engine or request a new task/worktree.
