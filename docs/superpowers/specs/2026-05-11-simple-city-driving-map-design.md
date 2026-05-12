# Simple City Driving Map Design

## Context

Antlia already has a Godot 4.6 C++ GDExtension scaffold for a bus driving prototype. The current demo scene contains a `BusController3D` placeholder bus, chase camera, flat ground plane, collision, lighting, and input mappings for acceleration, braking, steering, handbrake, and reset.

The next slice should make the driving prototype feel like a bus-driving environment without changing the driving model or adding route gameplay. The map is a scene-level addition: a compact city blockout with roads, intersections, curbs or barriers, and visible bus stop markers.

## Approved Direction

Use a small city grid with roads and bus stops, implemented as a reusable Godot scene.

This direction gives the prototype a bus-specific setting while keeping the scope narrow. It also avoids baking map geometry into the bus demo scene, so the map can grow later without touching the controller or driving model.

## Scope

Included:

- A reusable `scenes/simple_city_map.tscn` scene.
- A compact rectangular road grid, roughly two to three blocks wide.
- Straight roads and open intersections.
- Curbs or low barriers with collision to make road edges obvious.
- Sidewalk or ground surfaces around the roads.
- Three to four visible bus stop markers.
- A bus spawn placement in the demo scene aligned with the first street.
- Scene organization and node names that are easy to extend later.

Excluded:

- Route logic.
- Passenger pickup or drop-off behavior.
- Stop detection.
- Traffic lights, traffic signs, lane rules, or signal timing.
- AI vehicles, pedestrians, or parked cars.
- Minimap UI.
- Procedural or data-driven map generation.
- Changes to `BusDrivingModel` or `BusController3D`.

## Scene Architecture

The existing demo scene remains the runnable entry point. It should keep the bus, camera, controller tuning, and input-driven driving loop.

The new `simple_city_map.tscn` scene owns the environment:

- Road slabs.
- Intersection openings.
- Curbs or low barriers.
- Sidewalk or ground pieces.
- Bus stop marker nodes.
- Collision shapes for map boundaries.

`scenes/demo_bus_test.tscn` should instance `simple_city_map.tscn` and remove the current single flat ground plane if the map scene replaces it. The bus should start on a road surface, facing down a straight street with enough space for the current wide turning radius.

This keeps map work separate from vehicle work. Future route systems can reference bus stop nodes by name or group without rewriting the bus controller.

## Map Layout

The first map should be compact and readable:

- A rectangular grid with a few connected streets.
- Road widths large enough for the placeholder bus dimensions and current arcade-stable tuning.
- Open intersections that allow wide turns without immediate clipping.
- Curbs or barriers along road edges so collision feedback is visible.
- Three to four bus stops placed on straight road segments after intersections.
- A clear spawn lane aligned with the initial bus heading.

The visual language should stay simple and practical. Roads should use a dark material, sidewalks or surrounding ground should use a lighter contrasting material, and bus stop markers should be clearly visible from the chase camera.

## Bus Stop Markers

Bus stops are visual anchors only in this slice. They do not need interaction, triggers, route IDs, passenger queues, or timing behavior.

Each stop should be a clearly named node, such as `BusStopA`, `BusStopB`, `BusStopC`, and `BusStopD`. If Godot groups are convenient during implementation, stop nodes may also join a `bus_stops` group, but no gameplay should depend on that group yet.

Marker geometry can be simple: a post, sign, or colored standing marker near the curb. It should not block the main driving lane unless intentionally used as roadside collision.

## Collision And Driving Feel

The map should support the existing `CharacterBody3D` bus controller without requiring controller changes.

Roads and sidewalks can be static visual geometry. Curbs or barriers should use collision so the driver can feel road boundaries. Intersections should be forgiving enough that the current placeholder bus can turn through them at reasonable speed.

Collision does not need to represent every visual detail. The goal is readable road-edge feedback, not a physically detailed city.

## Error Handling

This slice should avoid runtime systems that can fail. The main defensive requirement is scene hygiene:

- The map scene should load as a normal Godot scene.
- The demo scene should not depend on missing scripts.
- Bus stop markers should be named consistently.
- The bus should not spawn intersecting barriers or curbs.

If a future system needs stop lookup or route validation, it should be added in a later slice.

## Verification

Verification should remain practical for the current repository:

1. Build and run the existing C++ driving-model tests to confirm the scene work did not disturb the driving core.
2. Build the GDExtension if the local SCons path remains available.
3. If a Godot binary is available, run a headless import or scene-load check for `scenes/demo_bus_test.tscn`.
4. Where runtime Godot verification is unavailable, inspect the scene files directly and report the limitation.

## Acceptance Criteria

The map slice is complete when:

- `scenes/simple_city_map.tscn` exists and is reusable.
- `scenes/demo_bus_test.tscn` instances the city map.
- The bus starts on a road and faces a sensible driving direction.
- Roads and intersections are wide enough for the current bus tuning.
- Curbs or barriers provide collision at road edges.
- Three to four visible bus stop markers exist and are named consistently.
- No route, passenger, traffic, stop-detection, or minimap systems are introduced.
