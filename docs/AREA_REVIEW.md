# Surrounding-area review — 20 September 2026

Reviewed the current working tree after the asset-detail fixes: Kowloon streets and park, Hung Hom approaches, both island portal surroundings, and the island return loop. This is a visual/source review; no gameplay, map data or assets were changed.

## Findings, in recommended order

### 1. P2 — Reconcile the original roads with the extension surface

At the Chatham approach, a light asphalt strip runs inside a darker, wider street. Its edges cut across the established road treatment; farther along, kerbs, paving and edge markings disappear. The driver sees two different road presentations on a continuous journey.

Evidence: [approach start](../evidence/area-review-2026-09-20/approach-start.png), [approach bend](../evidence/area-review-2026-09-20/approach-bend.png), [Kowloon exit](../evidence/area-review-2026-09-20/kowloon-exit-loop.png).

The source has two surface paths: `RoadMap.Width` assigns Chatham Road South 18 m and paints it through the terrain mask; `Tools/import_tunnel.py` assigns surface approaches 12 m, and `Tools/model_tunnel.py:79` adds a separate road mesh at Y=0.035. Extension markings also bypass the original road-marking placement checks. Footpath detail placement is restricted to `Map.Bounds` in `Scripts/Main.Footpaths.cs:47`.

Recommended fix: reconcile shared carriageway footprints and materials, render shared sections once, and continue appropriate edge lines, kerbs or roadside barriers across the transition. Preserve the government centreline coordinates. Recheck lane paint, bus clearance and the physical approach drive afterward.

### 2. P2 — Build an island streetscape around the driving corridor

The 1.44 km return loop is surrounded by broad, flat, untextured ground. Lamps and planters sit on that ground with no pavement. All 22 towers form a distant, nearly straight row, so they do little to establish street scale or distinct neighbourhoods from the cab.

Evidence: [north road](../evidence/area-review-2026-09-20/island-north-road.png), [west bend](../evidence/area-review-2026-09-20/island-west-bend.png), [island overview](../evidence/area-review-2026-09-20/island-district.png).

`Scripts/Main.Harbour.cs:63` places identical-footprint towers at regular X intervals with a narrow range of Z positions. Outside the original district, `Assets/Materials/terrain.gdshader:22` clears the surface mask, leaving the plain ground colour. This is a documented scenery limitation, not a regression from the recent facade pass.

Recommended fix: extend the existing government-building import to the island corridor, then add pavement and planted verges where appropriate. Prioritize the first row visible from the road; additional distant towers alone will not address the empty foreground. Retain provenance and label any authored infill.

### 3. P2 — Finish the exterior of the tunnel portals

The portals read as exposed rectangular tube ends standing on an empty plane. The Hung Hom view exposes long tiled exterior walls; the island view exposes the shell above the flat apron. There is little surrounding retaining structure, shoulder treatment or landscaping to connect them to the ground.

Evidence: [Hung Hom portal](../evidence/area-review-2026-09-20/hung-hom-portal.png), [island portals](../evidence/area-review-2026-09-20/island-portal-overview.png).

The authored structure in `Tools/model_tunnel.py:127` supplies the continuous tube walls and ceiling; the portal decoration at line 157 adds pillars and lintels. The surrounding land remains flat in `Tools/import_tunnel.py:110`.

Recommended fix: add exterior concrete retaining walls, finished portal surrounds and ground coverage around the exposed shell. Keep the current ramp profile, opening dimensions and verified bus envelope intact. Exterior concrete should receive outdoor lighting independently of the tunnel interior.

### 4. P3 — Give the waterfront depth and a finished edge

Water appears as a uniform bright cyan sheet. The straight rectangular land edge and low boundary barrier remain conspicuous, particularly when looking back toward Kowloon. The view lacks a convincing seawall or promenade transition.

Evidence: [shore view](../evidence/area-review-2026-09-20/harbour-shore.png), [island portal overview](../evidence/area-review-2026-09-20/island-portal-overview.png).

`Tools/import_tunnel.py:112` deliberately uses a rectangular island apron; `Tools/model_tunnel.py:71` supplies a single water material without surface detail.

Recommended fix: add a modest animated water-normal treatment compatible with GL Compatibility and a textured seawall edge. Use sourced coastline geometry if extending geographic accuracy; the current rectangle is authored scenery.

## Lower-priority observation

The original Kowloon streets have much stronger spatial definition: continuous paving, road markings, close building fronts and ground-floor variety. Kowloon Park still repeats one tree silhouette across a mostly uniform lawn, and its roadside wall is an untextured box. A small vegetation variant and wall material would help, after the extension transitions. See [park edge](../evidence/area-review-2026-09-20/park-edge.png), [park interior](../evidence/area-review-2026-09-20/park-interior.png) and [west street](../evidence/area-review-2026-09-20/west-street.png).

## Evidence and limits

The [capture harness](../evidence/area-review-2026-09-20/capture.gd) renders 19 current views using native Godot 4.6.2 .NET / OpenGL Compatibility. Driver-height views use the cab's 0.25 m near plane; aerial views use 10 m to avoid introducing depth artefacts. All use a 3,200 m far plane. HUD and bus model are hidden for scenery inspection; the east courtyard view is not a drivable street.

Command:

```sh
/Applications/Godot_mono.app/Contents/MacOS/Godot --path . \
  --script res://evidence/area-review-2026-09-20/capture.gd \
  --log-file evidence/area-review-2026-09-20/capture-final.log
```

The [fresh capture log](../evidence/area-review-2026-09-20/capture-final.log) ends with `ANTILA_AREA_REVIEW_CAPTURE_OK: 19 surrounding-area views`; the process exited 0 with no engine errors or warnings.

The existing full physical-drive checks passed earlier on this same game-code state; see [verified self-test log](../evidence/asset-fixes-2026-09-20/self-test-verified.log). They were not repeated for this read-only scenery review. Screenshot inspection does not establish collision safety, moving-camera behaviour or performance.

## Implementation follow-up

The four recommended areas have now been updated:

- The flat extension asphalt mesh is hidden. Both district and extension surfaces use the existing terrain shader, with separate masks at 3 and 2 pixels/metre. Shared road sections retain the original wider carriageway treatment. Extension centre lines are clipped out where the district already supplies road markings. Surface approaches and the island loop now have continuous paving and kerb edging.
- The placeholder tower row was replaced with 766 derived building sections from 731 original island features obtained from the same Lands Department CSDI layer. Existing building generation preserves footprint shapes, relative heights, courtyard holes, facade scale and collision chunks. The scene now contains 2,530 parts and 179 chunks across both districts. Lamps and planters avoid the imported lots; 46 trees line available roadside spaces.
- Blender MCP rebuilt the tunnel model with exterior retaining shells and roof caps outside the existing tube clearance, plus frames at all four ends. Cladding is omitted around the shared space where the tubes converge, preserving visible interior tiles and lamps. Triplanar stone mapping prevents stretched wall textures. Exterior surfaces receive daylight; the interior keeps its separate lighting layer.
- Animated water normals fade with screen footprint to avoid distant moire. The existing island boundary has a textured seawall and coping, with a paved north-side promenade, benches and planters.

The government road paths and authored ramp profiles are unchanged. The island land apron and shoreline remain authored rectangles; only building geometry was additionally sourced. This is still a stylized corridor, with generic facades and a selected street network. The lower-priority park vegetation variation remains a future art pass.

Before views remain in `evidence/area-review-2026-09-20/`; new views and logs are in `evidence/area-fixes-2026-09-20/`. Prior tunnel sources are preserved in `Art/before-area-fixes-2026-09-20/`. See [government building sources](GOVERNMENT_BUILDINGS.md#island-corridor--20-september-2026) and [crossing notes](CROSS_HARBOUR.md#surrounding-area-polish--20-september-2026).

### Verification of the follow-up

- [Before/after comparison](../evidence/area-fixes-2026-09-20/compare.html): five paired road, street, district, portal and shoreline views. The [final capture](../evidence/area-fixes-2026-09-20/final-capture.log) exited 0 with 20 scenery images plus eight cab views, including indoor/outdoor vehicle-lighting assertions at all four portals. No engine warnings or errors. Actual Godot OpenGL Compatibility renders; no image edits.
- [Full self-test](../evidence/area-fixes-2026-09-20/self-test.log): exit 0 with road markings, building/material/roof checks, footpaths, audio, map/camera regressions, signals, both tunnel directions, the island loop, both side streets and the complete three-stop H1 service. No unintended contacts; the boundary-impact test is deliberately retained. This full run preceded the final removal of intrusive cladding where the two tubes converge.
- [Final crossing check](../evidence/area-fixes-2026-09-20/harbour-final-check.log): rerun after the last model export, exit 0, no warnings or errors. Build: **0 warnings / 0 errors**. Passed 3,110 original-road probes, 112 surface/pavement samples, 230 interior wall rays, 1,887 bus-envelope queries, camera/control guards, the 218 m portal ramp, 621 m exit bend, 2,933 m southbound crossing, 1,442 m island loop and 3,721 m northbound return. Every driven crossing section completed without contacts; both tunnels reached −32 m.
- The original overlapping road mesh failed the new surface assertion in [baseline-check.log](../evidence/area-fixes-2026-09-20/baseline-check.log). The cladding regression similarly failed the new wall-ray assertion in [cladding-before-check.log](../evidence/area-fixes-2026-09-20/cladding-before-check.log), then passed after excluding the neighbouring tube's footprint.
- [Geometry comparison](../evidence/area-fixes-2026-09-20/tunnel-geometry-parity.json): all 13 original ground, floor, wall, ceiling and service-ledge mesh position/index streams match the pre-pass model. Crossing map data is byte-for-byte unchanged. The island source hash matches the generated layout metadata. Blender restored the user's previous scene after each export.

Native keyboard driving and performance were not benchmarked in this pass; the physical route tests use the real bus controller and collision world.
