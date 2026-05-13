# Realistic Bus Physics Design

## Context

Antlia already has a playable bus driving scaffold built around a pure C++ `BusDrivingModel` and a Godot `BusController3D` adapter. The current model provides deterministic arcade-style speed, braking, reverse, drag, handbrake, steering smoothing, and high-speed steering reduction.

The next slice upgrades the feel toward realistic bus physics while preserving the existing testable architecture. The goal is not a full wheel and suspension simulation. The goal is a heavier, force-driven single-body model that produces believable acceleration, braking, coasting, turning, understeer, and handbrake grip loss.

## Approved Direction

Use a force-based single-body bus model.

The driving model remains pure C++ and deterministic. It should integrate longitudinal acceleration from force terms and compute yaw from steering geometry and grip limits. Godot remains responsible for collision movement through `CharacterBody3D`; the C++ model remains responsible for handling feel.

This direction is closer to realistic vehicle physics than the current direct-speed controller, but it avoids the runtime and testing cost of switching to `RigidBody3D`, `VehicleBody3D`, or a wheel/suspension setup before the basic handling model is proven.

## Scope

Included:

- Force-based longitudinal acceleration.
- Bus mass as a tuning value.
- Engine force and brake force tuning.
- Reverse force tuning.
- Rolling resistance.
- Aerodynamic drag that increases with speed.
- Wheelbase-style yaw behavior.
- Lateral grip and understeer behavior.
- Handbrake grip reduction.
- Additional frame telemetry for physics tests and later debug UI.
- Inspector exposure for new tuning fields.
- Unit tests in the existing C++ harness.

Excluded:

- Full wheel simulation.
- Suspension.
- Tire contact patches.
- Weight transfer.
- Gearbox or drivetrain simulation.
- ABS, traction control, or differential behavior.
- Traffic, passengers, routes, cockpit UI, save files, or route gameplay.

## Model Boundary

`BusDrivingModel` stays the source of truth for driving simulation. `BusController3D` continues to read Godot input actions, pass a `BusDrivingInput` into the model, then apply the returned yaw and speed through Godot movement APIs.

The model should move away from directly adding acceleration constants to speed. Instead, each tick should:

1. Sanitize input and tuning.
2. Smooth steering toward the requested steering angle.
3. Compute engine, brake, reverse, rolling resistance, and aerodynamic drag forces.
4. Convert net longitudinal force into acceleration using bus mass.
5. Integrate speed over the physics delta.
6. Clamp forward and reverse speed caps.
7. Compute turning from steering angle, wheelbase, speed, and grip.
8. Reduce effective yaw through understeer when lateral demand exceeds grip.
9. Apply handbrake grip reduction when active.
10. Return speed, yaw, distance, steering, and physics telemetry.

The model remains scalar and local to the bus. It does not need Godot vectors, collision data, or scene state.

## Tuning Shape

Keep existing tuning values when they still make sense:

- `max_forward_speed`
- `max_reverse_speed`
- `brake_force`
- `drag`
- `handbrake_drag`
- `steering_speed`
- `steering_return_speed`
- `max_steering_angle`
- `high_speed_steering_scale`
- `turn_rate`

Add physics-oriented tuning values:

- `mass_kg`
- `engine_force`
- `reverse_force`
- `rolling_resistance`
- `air_drag_coefficient`
- `wheelbase_meters`
- `lateral_grip`
- `handbrake_grip_scale`

`acceleration` can remain as a compatibility value during this slice, but the new model should prefer `engine_force / mass_kg` for forward acceleration. If both are present, tests should describe the force-based behavior rather than relying on the old direct acceleration path.

All tuning values must be sanitized at the pure model boundary. Values that can break the model, such as non-finite mass or zero wheelbase, must be clamped to safe minimums.

## Frame Output

Keep existing frame fields:

- `speed_mps`
- `steering_radians`
- `effective_steering`
- `yaw_delta_radians`
- `forward_distance_meters`

Add physics telemetry:

- `longitudinal_acceleration_mps2`
- `lateral_slip`
- `grip_scale`

These fields are intentionally small. They make the new physics testable and give future HUD or debug UI work a stable source without forcing any UI into this slice.

## Godot Adapter

`BusController3D` stays a `CharacterBody3D`.

Adapter changes are limited to:

- Expose new tuning fields as inspector properties.
- Clamp unsafe inspector values before assigning tuning.
- Keep existing input actions unchanged.
- Continue to call `BusDrivingModel::step(...)` from `_physics_process`.
- Continue to rotate by `frame.yaw_delta_radians`.
- Continue to set velocity along the bus forward axis using `frame.speed_mps`.

The adapter should not create wheel nodes, switch body type, or move vehicle math into Godot scene code.

## Runtime Behavior

The target feel is close to realistic bus physics:

- Acceleration should feel heavy and force-limited.
- Braking should create a meaningful stopping distance.
- Coasting should slow from rolling resistance and air drag.
- Air drag should matter more at high speed than low speed.
- Turning should feel wider at higher speed.
- Steering should understeer when lateral demand exceeds grip.
- The handbrake should reduce grip and increase slip without turning the bus into an arcade drift car by default.
- Reverse should remain simple and controllable.

## Tests

Use the existing local C++ harness in `tests/test_bus_driving_model.cpp`.

Tests should cover:

- Heavier mass accelerates slower under the same engine force.
- Engine force increases speed up to the forward cap.
- Brake force reduces forward speed faster than rolling resistance alone.
- Continued braking or reverse input can move the bus backward.
- Reverse speed respects its cap.
- Rolling resistance slows the bus without driver input.
- Aerodynamic drag has a stronger slowing effect at higher speed.
- Steering eases toward input and recenters when released.
- Yaw follows speed and steering angle.
- High-speed steering reduces effective turning through grip limits.
- Handbrake reduces grip and increases slip.
- Large delta values are clamped.
- Non-finite input and tuning values sanitize to finite outputs.
- Reset clears speed, steering, and physics telemetry.

The tests should assert behavior, not implementation formulas, except where simple force relationships are the public contract for the physics model.

## Acceptance Criteria

The slice is acceptable when:

- The pure C++ tests build with `scons -C tests`.
- `./tests/bin/test_bus_driving_model` passes.
- The GDExtension builds with `scons platform=macos target=template_debug` when local dependencies are available.
- The Godot adapter exposes the new physics tuning fields without removing the existing driving controls.
- Existing user-owned changes outside this slice are not overwritten.

Godot editor or CLI runtime verification is best-effort. This repo has not established a verified `godot` CLI run path, so final reporting must distinguish native build and unit-test evidence from any manual/editor verification.

## Error Handling

The model must sanitize unsafe input at the pure C++ boundary:

- Non-finite inputs fall back to inactive or safe values.
- Negative or non-finite mass clamps to a safe positive mass.
- Zero or non-finite wheelbase clamps to a safe positive wheelbase.
- Grip and handbrake grip scale clamp to stable ranges.
- Drag and resistance clamp to non-negative values.
- Large physics deltas remain clamped.

This keeps the Godot inspector safe and preserves deterministic unit-test behavior.
