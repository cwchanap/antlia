# Antila — Kowloon bus driving prototype

Build one complete, small driving session in Godot 4.6 .NET / C#.

1. Import a local Nathan Road extract from Transport Department road centrelines; retain provenance and offline data.
2. Model an original double-decker, Hong Kong shop buildings, shelter, taxi and trees in Blender through MCP. Generate an original shelter poster with imagegen.
3. Build a daytime Tsim Sha Tsui → Jordan corridor with three fictional H1 stops, left-side lanes, streetscape, collisions and simple ambient traffic.
4. Implement keyboard driving, braking/reverse, doors with a movement interlock, passenger boarding, chase/cab cameras, route guidance and a restartable completion state.
5. Build C#, run a repeatable in-engine check, inspect rendered gameplay and exercise native keyboard controls. Document launch instructions and known limits.

Scope: a stylized prototype. Government centreline geometry anchors the road alignment; widths, elevations, buildings, stop placements, traffic and service H1 are authored approximations. No full-city import, operator branding, timetable, vehicle damage, saved career or traffic-network simulation.

Completed 12 September 2026. All five steps are implemented. The launcher builds with no warnings/errors; the in-engine test physically drove the route, served all three stops and exited cleanly. Rendered views and native camera/door/gear/pause/restart checks are recorded in README.md and evidence/.

## Horizontal expansion — 12 September 2026

1. Re-clip the cached, attributed Transport Department dataset to 2.06 × 1.24 km; retain the original H1 samples and connected named surface streets.
2. Widen the ground and boundaries, pave the street network, populate its sides with existing Blender buildings and trees, and extend Kowloon Park.
3. Fit the minimap to the district and add a paused M-key overview with neighborhood labels.
4. Verify turns west through Haiphong Road and east through Granville Road using the actual bus controller, rerun the complete H1 service, and inspect street and aerial captures.

Complete: clean launcher build, both side-street drives, the full three-stop service, map pause/resume checks and ten rendered views passed. The native M-key check could not proceed because the computer-use tool reported that macOS was locked; the same map action was verified in-engine. The original three stops remain the service route. All side-street widths, scenery and turning permissions remain game approximations.

## Road and density review

Reviewed junction renders, corrected surface depth fighting and conflicting road paint, opened the former internal road caps, and rebuilt building placement around shared footprints and block infill. Park planting now follows paths. See `POLISH_REVIEW.md` for findings and before/after evidence. Full-network bus-clearance queries and the existing driving checks verify the changes.
