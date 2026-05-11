# Bus Driving Simulator Basic Driving Scaffold Design

## Context

Antlia starts as an empty workspace. The first slice will create a Godot 4.6-compatible project using C++ GDExtension and scaffold a runnable bus driving prototype.

The goal is not a complete simulator. The goal is a small, playable foundation with a stable driving feel, clear C++ boundaries, and unit tests for the driving math.

## Approved Direction

Use a prototype-hybrid controller:

- Keep the runtime feel arcade-stable for the first playable slice.
- Structure the code so richer vehicle physics can replace the motion layer later.
- Avoid a full wheel/suspension simulation until the basic loop is proven.

This is preferable to a `RigidBody3D` or full vehicle-wheel setup for the first scaffold because predictable handling and fast tuning matter more than physical completeness at this stage.

## Scope

Included:

- Godot 4 project files.
- C++ GDExtension scaffold.
- A runnable demo scene.
- A placeholder bus with collision and a simple visual mesh.
- A flat road or test ground with collision.
- A chase camera.
- Default input actions for driving.
- A reusable bus controller node.
- A pure C++ driving model with unit tests.
- Build and run documentation.

Excluded:

- Traffic.
- Routes, stops, passengers, fares, or scheduling.
- Cockpit instruments.
- Save files.
- AI vehicles or pedestrians.
- Real wheel, suspension, tire, or drivetrain simulation.
- Art-quality bus or city assets.

## Runtime Architecture

The project will be split into a Godot scene layer and a C++ runtime layer.

The main extension class is `BusController3D`. It inherits from Godot's `CharacterBody3D`, is used as the bus root node in the demo scene, and acts as the Godot adapter. It reads input actions, calls the driving model, and applies movement and rotation to the bus body during physics ticks.

The driving math lives in a pure C++ helper, `BusDrivingModel`. This model has no Godot node dependency. It owns the scalar driving state and returns enough information for `BusController3D` to move the bus.

This boundary keeps Godot integration small and gives the project meaningful unit tests without requiring a full engine runtime for every driving behavior check.

## Project Structure

Expected scaffold:

```text
project.godot
SConstruct
antlia.gdextension
README.md
src/
  register_types.cpp
  register_types.h
  bus_controller_3d.cpp
  bus_controller_3d.h
  driving/
    bus_driving_model.cpp
    bus_driving_model.h
tests/
  SConstruct
  test_harness.h
  test_bus_driving_model.cpp
scenes/
  demo_bus_test.tscn
```

The exact file names can be adjusted during implementation if Godot or SCons conventions require it, but the separation between Godot adapter, pure driving model, tests, and scenes should remain.

## Controller Responsibilities

`BusController3D` is responsible for:

- Exposing tuning values in the Godot inspector.
- Reading input actions.
- Capturing the spawn transform when ready.
- Passing per-tick input into `BusDrivingModel`.
- Applying forward movement and yaw rotation to the bus through Godot's 3D collision movement APIs.
- Resetting the bus safely.
- Publishing read-only state for future HUD or debug UI.

`BusController3D` should not own scene construction or asset creation. The scene stays editable in Godot so the placeholder mesh, camera, and ground can be replaced later.

## Driving Model Responsibilities

`BusDrivingModel` is responsible for:

- Maintaining speed and steering state.
- Applying acceleration, braking, reverse, drag, and handbrake behavior.
- Limiting forward and reverse speed.
- Smoothing steering input.
- Recentering steering when released.
- Reducing steering authority as speed rises.
- Clearing driving state on reset.

The first model represents the bus as a single body, not separate wheels. The desired feel is heavy and stable: gradual acceleration, wide turning radius, capped steering at speed, coasting drag, and simple reverse behavior.

## Inspector Tuning

`BusController3D` should expose at least these properties:

- `max_forward_speed`
- `max_reverse_speed`
- `acceleration`
- `brake_force`
- `drag`
- `handbrake_drag`
- `steering_speed`
- `steering_return_speed`
- `max_steering_angle`
- `high_speed_steering_scale`
- `turn_rate`

Names can be refined during implementation, but the first scaffold needs enough tuning controls to adjust feel without recompiling C++.

## Input Actions

Use intent-based input action names:

- `drive_accelerate`
- `drive_brake`
- `drive_steer_left`
- `drive_steer_right`
- `drive_handbrake`
- `drive_reset`

Default mappings:

- `W` and up arrow: accelerate.
- `S` and down arrow: brake or reverse.
- `A` and left arrow: steer left.
- `D` and right arrow: steer right.
- `Space`: handbrake.
- `R`: reset.

If an action is missing, the controller should treat it as inactive instead of crashing. The scaffold should still define all expected actions in `project.godot`.

## Physics Tick Flow

Each physics tick:

1. Read driving input from Godot actions.
2. If reset is pressed, restore the spawn transform and clear model state.
3. Smooth steering toward the requested direction.
4. Reduce effective steering as speed rises.
5. Update speed using acceleration, braking, reverse limits, drag, and handbrake drag.
6. Calculate yaw change from steering and speed.
7. Move the bus forward in its local forward direction with collision.
8. Expose current speed and steering amount for future UI/debug use.

The implementation should prioritize predictable control over physical realism.

## Demo Scene

The demo scene should include:

- A bus root node with `BusController3D`.
- A placeholder bus mesh sized roughly like a bus.
- A collision shape for the bus.
- A flat test road or ground plane with collision.
- A chase camera positioned behind and above the bus.
- Basic lighting.

The scene only needs to prove the driving loop. It should avoid city layout, route gameplay, or decorative content in this first slice.

## Unit Testing

Use a tiny local C++ test harness for the pure driving model. The first scaffold avoids adding a second external dependency before the Godot C++ binding is stable.

Initial unit tests should cover:

- Acceleration increases speed up to the forward cap.
- Braking reduces forward speed.
- Continued braking can transition into reverse.
- Reverse speed respects its own cap.
- Drag slows the bus when no input is held.
- Steering eases toward input.
- Steering recenters when released.
- Steering effect is reduced at higher speeds.
- Reset clears speed and steering state.

The unit-test target should build separately from the Godot extension. These tests should not require launching the Godot editor.

## Build And Verification

Expected verification after implementation:

1. Build the GDExtension library.
2. Build and run the unit tests.
3. Open or run the Godot project.
4. Confirm the demo scene loads.
5. Confirm the bus accelerates, brakes, reverses, steers, handbrakes, and resets.

If the local Godot or C++ GDExtension toolchain is unavailable, implementation should still leave the project structure and commands ready, and the limitation should be reported explicitly.

## Error Handling

The scaffold should handle missing or early state defensively:

- Missing input actions are inactive.
- Reset before spawn capture should not crash.
- Unit-test model reset should be deterministic.
- Invalid or extreme inspector values should be clamped where they would break basic driving behavior.

The first scaffold should keep failure behavior simple and visible rather than adding a complex logging framework.

## Acceptance Criteria

The first implementation is acceptable when:

- The Godot project opens as a Godot 4 project.
- The GDExtension class is registered and usable from the demo scene.
- The demo scene is runnable.
- The bus can accelerate, brake, reverse, steer, handbrake, and reset.
- Driving parameters are tunable from the inspector.
- Unit tests cover the pure driving model.
- README instructions explain setup, build, tests, and how to run the demo.
