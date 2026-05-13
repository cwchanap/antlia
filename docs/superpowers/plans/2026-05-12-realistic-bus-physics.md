# Realistic Bus Physics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade Antlia's bus handling from direct speed changes to a deterministic force-based single-body physics model.

**Architecture:** Keep the pure C++ `BusDrivingModel` as the physics source of truth and keep `BusController3D` as the Godot adapter. Add force, mass, rolling resistance, aerodynamic drag, wheelbase, grip, and handbrake grip tuning to the model, then expose those fields through the existing `CharacterBody3D` inspector properties.

**Tech Stack:** Godot 4.6 C++ GDExtension, C++17-style pure model code, local SCons unit-test harness, Godot text scenes.

---

## File Structure

- Modify: `src/driving/bus_driving_model.h`
  - Owns public physics input, tuning, frame telemetry, and model state getters.
- Modify: `src/driving/bus_driving_model.cpp`
  - Owns deterministic scalar bus physics: force integration, resistance, steering geometry, grip limits, handbrake grip, and sanitization.
- Modify: `tests/test_bus_driving_model.cpp`
  - Owns pure C++ behavior coverage for force-based driving physics.
- Modify: `src/bus_controller_3d.h`
  - Owns Godot-facing getters and setters for new inspector tuning fields.
- Modify: `src/bus_controller_3d.cpp`
  - Owns Godot method binding, inspector property exposure, and adapter-side value clamps.
- No changes: `src/register_types.cpp`
  - `BusController3D` remains the only GDExtension class needed for this slice.
- No changes: `project.godot`
  - Existing input actions remain unchanged.
- No changes: `scenes/*.tscn`
  - The physics upgrade does not require scene graph changes.

## Task 1: Add Force-Based Public Contract And Acceleration Behavior

**Files:**
- Modify: `tests/test_bus_driving_model.cpp`
- Modify: `src/driving/bus_driving_model.h`
- Modify: `src/driving/bus_driving_model.cpp`

- [ ] **Step 1: Write failing tests for mass, engine force, and frame acceleration**

In `tests/test_bus_driving_model.cpp`, replace the existing `tuning()` helper with this version:

```cpp
BusDrivingTuning tuning() {
    BusDrivingTuning value;
    value.max_forward_speed = 10.0;
    value.max_reverse_speed = 3.0;
    value.acceleration = 2.5;
    value.brake_force = 60000.0;
    value.drag = 0.15;
    value.handbrake_drag = 5.0;
    value.steering_speed = 2.0;
    value.steering_return_speed = 4.0;
    value.max_steering_angle = 0.5;
    value.high_speed_steering_scale = 0.25;
    value.turn_rate = 1.0;
    value.mass_kg = 12000.0;
    value.engine_force = 36000.0;
    value.reverse_force = 22000.0;
    value.rolling_resistance = 650.0;
    value.air_drag_coefficient = 18.0;
    value.wheelbase_meters = 6.0;
    value.lateral_grip = 4.5;
    value.handbrake_grip_scale = 0.35;
    return value;
}
```

Add these tests after `acceleration_increases_speed_up_to_forward_cap`:

```cpp
ANTLIA_TEST(heavier_mass_accelerates_slower_under_same_engine_force) {
    BusDrivingTuning light = tuning();
    BusDrivingTuning heavy = tuning();
    light.mass_kg = 9000.0;
    heavy.mass_kg = 18000.0;
    light.engine_force = 36000.0;
    heavy.engine_force = 36000.0;

    BusDrivingModel light_model;
    BusDrivingModel heavy_model;

    for (int i = 0; i < 60; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        light_model.step(input, light);
        heavy_model.step(input, heavy);
    }

    CHECK(light_model.speed_mps() > heavy_model.speed_mps());
}

ANTLIA_TEST(frame_reports_force_based_longitudinal_acceleration) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();
    params.mass_kg = 12000.0;
    params.engine_force = 36000.0;
    params.rolling_resistance = 0.0;
    params.air_drag_coefficient = 0.0;
    params.drag = 0.0;

    BusDrivingInput input = tick(0.1);
    input.throttle = 1.0;
    const auto frame = model.step(input, params);

    CHECK_NEAR(frame.longitudinal_acceleration_mps2, 3.0, 0.0001);
    CHECK(frame.speed_mps > 0.0);
}
```

- [ ] **Step 2: Run the tests and verify the contract failure**

Run:

```bash
scons -C tests
```

Expected result:

```text
error: no member named 'mass_kg' in 'antlia::driving::BusDrivingTuning'
```

The exact compiler wording may differ, but the failure must be caused by missing physics fields.

- [ ] **Step 3: Extend the model header**

In `src/driving/bus_driving_model.h`, replace the `BusDrivingTuning` and `BusDrivingFrame` definitions with:

```cpp
struct BusDrivingTuning {
    double max_forward_speed = 18.0;
    double max_reverse_speed = 5.0;
    double acceleration = 2.5;
    double brake_force = 90000.0;
    double drag = 0.15;
    double handbrake_drag = 5.0;
    double steering_speed = 1.8;
    double steering_return_speed = 3.0;
    double max_steering_angle = 0.45;
    double high_speed_steering_scale = 0.35;
    double turn_rate = 1.0;
    double mass_kg = 12000.0;
    double engine_force = 36000.0;
    double reverse_force = 22000.0;
    double rolling_resistance = 650.0;
    double air_drag_coefficient = 18.0;
    double wheelbase_meters = 6.0;
    double lateral_grip = 4.5;
    double handbrake_grip_scale = 0.35;
};

struct BusDrivingFrame {
    double speed_mps = 0.0;
    double steering_radians = 0.0;
    double effective_steering = 0.0;
    double yaw_delta_radians = 0.0;
    double forward_distance_meters = 0.0;
    double longitudinal_acceleration_mps2 = 0.0;
    double lateral_slip = 0.0;
    double grip_scale = 1.0;
};
```

- [ ] **Step 4: Implement force-based forward acceleration**

In `src/driving/bus_driving_model.cpp`, update `BusDrivingModel::sanitized` by replacing its body with:

```cpp
BusDrivingTuning BusDrivingModel::sanitized(BusDrivingTuning tuning) {
    tuning.max_forward_speed = abs_max(tuning.max_forward_speed, 0.1);
    tuning.max_reverse_speed = abs_max(tuning.max_reverse_speed, 0.1);
    tuning.acceleration = abs_max(tuning.acceleration, 0.1);
    tuning.brake_force = abs_max(tuning.brake_force, 100.0);
    tuning.drag = std::max(finite_or(tuning.drag, 0.0), 0.0);
    tuning.handbrake_drag = std::max(finite_or(tuning.handbrake_drag, 0.0), 0.0);
    tuning.steering_speed = abs_max(tuning.steering_speed, 0.1);
    tuning.steering_return_speed = abs_max(tuning.steering_return_speed, 0.1);
    tuning.max_steering_angle = clamp(std::fabs(finite_or(tuning.max_steering_angle, 0.01)), 0.01, 1.2);
    tuning.high_speed_steering_scale = clamp(tuning.high_speed_steering_scale, 0.05, 1.0);
    tuning.turn_rate = abs_max(tuning.turn_rate, 0.01);
    tuning.mass_kg = abs_max(tuning.mass_kg, 100.0);
    tuning.engine_force = abs_max(tuning.engine_force, tuning.mass_kg * tuning.acceleration);
    tuning.reverse_force = abs_max(tuning.reverse_force, tuning.engine_force * kReverseAccelerationScale);
    tuning.rolling_resistance = std::max(finite_or(tuning.rolling_resistance, 0.0), 0.0);
    tuning.air_drag_coefficient = std::max(finite_or(tuning.air_drag_coefficient, 0.0), 0.0);
    tuning.wheelbase_meters = abs_max(tuning.wheelbase_meters, 0.5);
    tuning.lateral_grip = abs_max(tuning.lateral_grip, 0.1);
    tuning.handbrake_grip_scale = clamp(tuning.handbrake_grip_scale, 0.05, 1.0);
    return tuning;
}
```

In `BusDrivingModel::step`, replace the direct throttle block:

```cpp
    if (throttle > 0.0) {
        speed_mps_ = finite_or(speed_mps_, 0.0) + tuning.acceleration * throttle * dt;
    }
```

with:

```cpp
    speed_mps_ = finite_or(speed_mps_, 0.0);

    double net_force = 0.0;
    if (throttle > 0.0) {
        const double speed_fraction = clamp(speed_mps_ / tuning.max_forward_speed, 0.0, 1.0);
        const double engine_scale = 1.0 - speed_fraction;
        net_force += tuning.engine_force * throttle * engine_scale;
    }

    const double longitudinal_acceleration = net_force / tuning.mass_kg;
    speed_mps_ += longitudinal_acceleration * dt;
```

Set the new frame fields before returning:

```cpp
    frame.longitudinal_acceleration_mps2 = longitudinal_acceleration;
    frame.lateral_slip = 0.0;
    frame.grip_scale = 1.0;
```

- [ ] **Step 5: Run the tests and verify they pass**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected result:

```text
All tests passed
```

- [ ] **Step 6: Commit Task 1**

Run:

```bash
git add src/driving/bus_driving_model.h src/driving/bus_driving_model.cpp tests/test_bus_driving_model.cpp
git commit -m "feat: add force-based bus acceleration"
```

## Task 2: Add Braking, Reverse Force, And Passive Resistance

**Files:**
- Modify: `tests/test_bus_driving_model.cpp`
- Modify: `src/driving/bus_driving_model.cpp`

- [ ] **Step 1: Write failing tests for braking, rolling resistance, and air drag**

Replace `braking_reduces_forward_speed` with:

```cpp
ANTLIA_TEST(brake_force_slows_bus_faster_than_passive_resistance) {
    BusDrivingModel passive_model;
    BusDrivingModel brake_model;
    BusDrivingTuning params = tuning();

    for (int i = 0; i < 90; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        passive_model.step(input, params);
        brake_model.step(input, params);
    }

    BusDrivingInput brake = tick(0.5);
    brake.brake = 1.0;
    const double passive_speed_before = passive_model.speed_mps();
    passive_model.step(tick(0.5), params);
    brake_model.step(brake, params);

    CHECK(passive_model.speed_mps() < passive_speed_before);
    CHECK(brake_model.speed_mps() < passive_model.speed_mps());
}
```

Add these tests after `drag_slows_bus_without_input`:

```cpp
ANTLIA_TEST(rolling_resistance_slows_bus_without_input) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();
    params.air_drag_coefficient = 0.0;
    params.drag = 0.0;
    params.rolling_resistance = 1200.0;

    for (int i = 0; i < 90; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        model.step(input, params);
    }

    const double before = model.speed_mps();
    model.step(tick(1.0), params);

    CHECK(model.speed_mps() < before);
}

ANTLIA_TEST(aerodynamic_drag_has_stronger_effect_at_high_speed) {
    BusDrivingTuning params = tuning();
    params.rolling_resistance = 0.0;
    params.drag = 0.0;
    params.air_drag_coefficient = 80.0;

    BusDrivingModel slow_model;
    BusDrivingModel fast_model;

    for (int i = 0; i < 30; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        slow_model.step(input, params);
    }

    for (int i = 0; i < 180; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        fast_model.step(input, params);
    }

    const double slow_before = slow_model.speed_mps();
    const double fast_before = fast_model.speed_mps();
    slow_model.step(tick(1.0), params);
    fast_model.step(tick(1.0), params);

    const double slow_loss = slow_before - slow_model.speed_mps();
    const double fast_loss = fast_before - fast_model.speed_mps();
    CHECK(fast_loss > slow_loss);
}
```

- [ ] **Step 2: Run the tests and verify the behavior failure**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected result:

```text
FAIL: brake_force_slows_bus_faster_than_passive_resistance
```

At least one new resistance or braking assertion should fail because the model does not yet apply those forces.

- [ ] **Step 3: Add force helpers**

In the anonymous namespace in `src/driving/bus_driving_model.cpp`, add:

```cpp
constexpr double kStopSpeed = 0.05;

double sign_of(double value) {
    if (value > 0.0) {
        return 1.0;
    }
    if (value < 0.0) {
        return -1.0;
    }
    return 0.0;
}
```

- [ ] **Step 4: Apply brake, reverse, rolling resistance, drag, and handbrake drag**

In `BusDrivingModel::step`, replace the braking, idle drag, and handbrake blocks with this force-based block immediately after the throttle force block:

```cpp
    if (brake > 0.0) {
        if (speed_mps_ > kStopSpeed) {
            net_force -= tuning.brake_force * brake;
        } else if (speed_mps_ < -kStopSpeed) {
            net_force += tuning.brake_force * brake;
        } else {
            net_force -= tuning.reverse_force * brake;
        }
    }

    const double speed_sign = sign_of(speed_mps_);
    if (speed_sign != 0.0) {
        const double drag_force = tuning.air_drag_coefficient * speed_mps_ * speed_mps_;
        const double linear_drag_force = tuning.drag * tuning.mass_kg;
        net_force -= speed_sign * (tuning.rolling_resistance + drag_force + linear_drag_force);
    }

    if (input.handbrake && speed_sign != 0.0) {
        net_force -= speed_sign * tuning.handbrake_drag * tuning.mass_kg;
    }

    const double previous_speed = speed_mps_;
    const double longitudinal_acceleration = net_force / tuning.mass_kg;
    speed_mps_ += longitudinal_acceleration * dt;

    if (previous_speed > 0.0 && speed_mps_ < 0.0 && brake > 0.0) {
        speed_mps_ = 0.0;
    }
    if (previous_speed < 0.0 && speed_mps_ > 0.0 && brake <= 0.0 && throttle <= 0.0) {
        speed_mps_ = 0.0;
    }
```

Remove the older duplicate lines that compute `longitudinal_acceleration` and update `speed_mps_` so the function integrates speed once per tick.

- [ ] **Step 5: Run the tests and verify they pass**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected result:

```text
All tests passed
```

- [ ] **Step 6: Commit Task 2**

Run:

```bash
git add src/driving/bus_driving_model.cpp tests/test_bus_driving_model.cpp
git commit -m "feat: model bus braking and resistance forces"
```

## Task 3: Add Wheelbase Steering Geometry, Grip Limits, And Slip Telemetry

**Files:**
- Modify: `tests/test_bus_driving_model.cpp`
- Modify: `src/driving/bus_driving_model.cpp`

- [ ] **Step 1: Write failing tests for wheelbase and high-speed grip limits**

Replace `steering_effect_reduces_at_high_speed` with:

```cpp
ANTLIA_TEST(high_speed_steering_reduces_effective_turning_through_grip_limits) {
    BusDrivingModel slow_model;
    BusDrivingModel fast_model;
    BusDrivingTuning params = tuning();
    params.lateral_grip = 2.0;

    BusDrivingInput steer = tick(0.25);
    steer.steer = 1.0;
    const auto slow_frame = slow_model.step(steer, params);

    for (int i = 0; i < 180; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        fast_model.step(input, params);
    }
    const auto fast_frame = fast_model.step(steer, params);

    CHECK(std::fabs(fast_frame.effective_steering) < std::fabs(slow_frame.effective_steering));
    CHECK(fast_frame.grip_scale < slow_frame.grip_scale);
    CHECK(fast_frame.lateral_slip > slow_frame.lateral_slip);
}
```

Add this test after `frame_reports_yaw_and_forward_distance_when_moving_and_steering`:

```cpp
ANTLIA_TEST(longer_wheelbase_turns_more_widely) {
    BusDrivingTuning short_bus = tuning();
    BusDrivingTuning long_bus = tuning();
    short_bus.wheelbase_meters = 4.0;
    long_bus.wheelbase_meters = 9.0;

    BusDrivingModel short_model;
    BusDrivingModel long_model;

    for (int i = 0; i < 120; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        input.steer = 1.0;
        short_model.step(input, short_bus);
        long_model.step(input, long_bus);
    }

    BusDrivingInput turn = tick(0.2);
    turn.throttle = 1.0;
    turn.steer = 1.0;
    const auto short_frame = short_model.step(turn, short_bus);
    const auto long_frame = long_model.step(turn, long_bus);

    CHECK(std::fabs(short_frame.yaw_delta_radians) > std::fabs(long_frame.yaw_delta_radians));
}
```

- [ ] **Step 2: Run the tests and verify the steering failure**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected result:

```text
FAIL: high_speed_steering_reduces_effective_turning_through_grip_limits
```

The current yaw path still uses an old speed-ratio steering scale and should not produce grip telemetry.

- [ ] **Step 3: Replace yaw calculation with wheelbase and grip math**

In `BusDrivingModel::step`, replace the block from `const double speed_ratio = ...` through `frame.forward_distance_meters = ...` with:

```cpp
    const double speed_ratio = clamp(std::fabs(speed_mps_) / tuning.max_forward_speed, 0.0, 1.0);
    const double steering_scale = 1.0 - ((1.0 - tuning.high_speed_steering_scale) * speed_ratio);
    const double requested_steering = steering_radians_ * steering_scale;
    const double requested_steering_abs = std::fabs(requested_steering);

    double grip_scale = 1.0;
    double lateral_slip = 0.0;
    double effective_steering = requested_steering;

    if (requested_steering_abs > 0.0001 && std::fabs(speed_mps_) > 0.001) {
        const double turn_radius = tuning.wheelbase_meters / std::tan(requested_steering_abs);
        const double lateral_acceleration = (speed_mps_ * speed_mps_) / turn_radius;
        const double available_grip = tuning.lateral_grip;
        grip_scale = clamp(available_grip / std::max(lateral_acceleration, 0.0001), 0.05, 1.0);
        lateral_slip = clamp((lateral_acceleration - available_grip) / std::max(available_grip, 0.0001), 0.0, 1.0);
        effective_steering = requested_steering * grip_scale;
    }

    last_effective_steering_ = effective_steering;

    BusDrivingFrame frame;
    frame.speed_mps = speed_mps_;
    frame.steering_radians = steering_radians_;
    frame.effective_steering = last_effective_steering_;
    frame.yaw_delta_radians = 0.0;
    if (std::fabs(last_effective_steering_) > 0.0001) {
        const double yaw_rate = (speed_mps_ / tuning.wheelbase_meters) * std::tan(last_effective_steering_);
        frame.yaw_delta_radians = yaw_rate * tuning.turn_rate * dt;
    }
    frame.forward_distance_meters = speed_mps_ * dt;
    frame.longitudinal_acceleration_mps2 = longitudinal_acceleration;
    frame.lateral_slip = lateral_slip;
    frame.grip_scale = grip_scale;
    return frame;
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected result:

```text
All tests passed
```

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add src/driving/bus_driving_model.cpp tests/test_bus_driving_model.cpp
git commit -m "feat: add wheelbase steering and grip limits"
```

## Task 4: Finish Handbrake, Sanitization, And Reset Coverage

**Files:**
- Modify: `tests/test_bus_driving_model.cpp`
- Modify: `src/driving/bus_driving_model.cpp`

- [ ] **Step 1: Write failing tests for handbrake grip and physics sanitization**

Replace `handbrake_decelerates_more_aggressively_than_normal_drag` with:

```cpp
ANTLIA_TEST(handbrake_reduces_grip_and_increases_slip) {
    BusDrivingModel normal_model;
    BusDrivingModel handbrake_model;
    BusDrivingTuning params = tuning();
    params.lateral_grip = 3.0;
    params.handbrake_grip_scale = 0.25;

    for (int i = 0; i < 180; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        normal_model.step(input, params);
        handbrake_model.step(input, params);
    }

    BusDrivingInput turn = tick(0.25);
    turn.steer = 1.0;
    const auto normal_frame = normal_model.step(turn, params);

    BusDrivingInput handbrake_turn = turn;
    handbrake_turn.handbrake = true;
    const auto handbrake_frame = handbrake_model.step(handbrake_turn, params);

    CHECK(handbrake_frame.speed_mps < normal_frame.speed_mps);
    CHECK(handbrake_frame.grip_scale < normal_frame.grip_scale);
    CHECK(handbrake_frame.lateral_slip > normal_frame.lateral_slip);
}
```

In `non_finite_input_and_tuning_are_sanitized`, add these assignments to the invalid `params` block:

```cpp
    params.mass_kg = nan;
    params.engine_force = infinity;
    params.reverse_force = nan;
    params.rolling_resistance = infinity;
    params.air_drag_coefficient = nan;
    params.wheelbase_meters = infinity;
    params.lateral_grip = nan;
    params.handbrake_grip_scale = infinity;
```

Add these frame checks to both finite-output assertion groups:

```cpp
    CHECK(std::isfinite(input_frame.longitudinal_acceleration_mps2));
    CHECK(std::isfinite(input_frame.lateral_slip));
    CHECK(std::isfinite(input_frame.grip_scale));
```

and:

```cpp
    CHECK(std::isfinite(tuning_frame.longitudinal_acceleration_mps2));
    CHECK(std::isfinite(tuning_frame.lateral_slip));
    CHECK(std::isfinite(tuning_frame.grip_scale));
```

Replace `reset_clears_speed_and_steering` with:

```cpp
ANTLIA_TEST(reset_clears_speed_steering_and_next_frame_telemetry) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    BusDrivingInput input = tick(0.5);
    input.throttle = 1.0;
    input.steer = 1.0;
    input.handbrake = true;
    model.step(input, params);

    model.reset();
    const auto frame = model.step(tick(0.0), params);

    CHECK_NEAR(model.speed_mps(), 0.0, 0.0001);
    CHECK_NEAR(model.steering_radians(), 0.0, 0.0001);
    CHECK_NEAR(frame.longitudinal_acceleration_mps2, 0.0, 0.0001);
    CHECK_NEAR(frame.lateral_slip, 0.0, 0.0001);
    CHECK_NEAR(frame.grip_scale, 1.0, 0.0001);
}
```

- [ ] **Step 2: Run tests and verify any remaining telemetry or sanitization failure**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected result:

```text
FAIL: handbrake_reduces_grip_and_increases_slip
```

If handbrake already passes, the expected failing assertion can be from the expanded sanitization or reset telemetry checks.

- [ ] **Step 3: Apply handbrake grip reduction and tighten finite guards**

In `BusDrivingModel::step`, replace this line in the steering/grip block:

```cpp
        const double available_grip = tuning.lateral_grip;
```

with:

```cpp
        const double available_grip = tuning.lateral_grip * (input.handbrake ? tuning.handbrake_grip_scale : 1.0);
```

Then wrap the final frame assignments for new telemetry with finite fallbacks:

```cpp
    frame.longitudinal_acceleration_mps2 = finite_or(longitudinal_acceleration, 0.0);
    frame.lateral_slip = clamp(lateral_slip, 0.0, 1.0);
    frame.grip_scale = clamp(grip_scale, 0.05, 1.0);
```

Make sure `reset()` remains:

```cpp
void BusDrivingModel::reset() {
    speed_mps_ = 0.0;
    steering_radians_ = 0.0;
    last_effective_steering_ = 0.0;
}
```

The model does not need stored telemetry members because each returned frame is recomputed from the current state.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected result:

```text
All tests passed
```

- [ ] **Step 5: Commit Task 4**

Run:

```bash
git add src/driving/bus_driving_model.cpp tests/test_bus_driving_model.cpp
git commit -m "test: cover bus grip and telemetry safeguards"
```

## Task 5: Expose New Physics Tuning In The Godot Adapter

**Files:**
- Modify: `src/bus_controller_3d.h`
- Modify: `src/bus_controller_3d.cpp`

- [ ] **Step 1: Add adapter declarations**

In `src/bus_controller_3d.h`, add these public methods after `get_turn_rate()`:

```cpp
    void set_mass_kg(double value);
    double get_mass_kg() const;

    void set_engine_force(double value);
    double get_engine_force() const;

    void set_reverse_force(double value);
    double get_reverse_force() const;

    void set_rolling_resistance(double value);
    double get_rolling_resistance() const;

    void set_air_drag_coefficient(double value);
    double get_air_drag_coefficient() const;

    void set_wheelbase_meters(double value);
    double get_wheelbase_meters() const;

    void set_lateral_grip(double value);
    double get_lateral_grip() const;

    void set_handbrake_grip_scale(double value);
    double get_handbrake_grip_scale() const;
```

- [ ] **Step 2: Bind methods and add inspector properties**

In `BusController3D::_bind_methods()` in `src/bus_controller_3d.cpp`, add method bindings after the `turn_rate` binding:

```cpp
    ClassDB::bind_method(D_METHOD("set_mass_kg", "value"), &BusController3D::set_mass_kg);
    ClassDB::bind_method(D_METHOD("get_mass_kg"), &BusController3D::get_mass_kg);
    ClassDB::bind_method(D_METHOD("set_engine_force", "value"), &BusController3D::set_engine_force);
    ClassDB::bind_method(D_METHOD("get_engine_force"), &BusController3D::get_engine_force);
    ClassDB::bind_method(D_METHOD("set_reverse_force", "value"), &BusController3D::set_reverse_force);
    ClassDB::bind_method(D_METHOD("get_reverse_force"), &BusController3D::get_reverse_force);
    ClassDB::bind_method(D_METHOD("set_rolling_resistance", "value"), &BusController3D::set_rolling_resistance);
    ClassDB::bind_method(D_METHOD("get_rolling_resistance"), &BusController3D::get_rolling_resistance);
    ClassDB::bind_method(D_METHOD("set_air_drag_coefficient", "value"), &BusController3D::set_air_drag_coefficient);
    ClassDB::bind_method(D_METHOD("get_air_drag_coefficient"), &BusController3D::get_air_drag_coefficient);
    ClassDB::bind_method(D_METHOD("set_wheelbase_meters", "value"), &BusController3D::set_wheelbase_meters);
    ClassDB::bind_method(D_METHOD("get_wheelbase_meters"), &BusController3D::get_wheelbase_meters);
    ClassDB::bind_method(D_METHOD("set_lateral_grip", "value"), &BusController3D::set_lateral_grip);
    ClassDB::bind_method(D_METHOD("get_lateral_grip"), &BusController3D::get_lateral_grip);
    ClassDB::bind_method(D_METHOD("set_handbrake_grip_scale", "value"), &BusController3D::set_handbrake_grip_scale);
    ClassDB::bind_method(D_METHOD("get_handbrake_grip_scale"), &BusController3D::get_handbrake_grip_scale);
```

Add inspector properties after `turn_rate`:

```cpp
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "mass_kg", PROPERTY_HINT_RANGE, "100.0,30000.0,10.0,or_greater"),
            "set_mass_kg", "get_mass_kg");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "engine_force", PROPERTY_HINT_RANGE, "100.0,200000.0,100.0,or_greater"),
            "set_engine_force", "get_engine_force");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "reverse_force", PROPERTY_HINT_RANGE, "100.0,120000.0,100.0,or_greater"),
            "set_reverse_force", "get_reverse_force");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "rolling_resistance", PROPERTY_HINT_RANGE, "0.0,10000.0,10.0,or_greater"),
            "set_rolling_resistance", "get_rolling_resistance");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "air_drag_coefficient", PROPERTY_HINT_RANGE, "0.0,500.0,1.0,or_greater"),
            "set_air_drag_coefficient", "get_air_drag_coefficient");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "wheelbase_meters", PROPERTY_HINT_RANGE, "0.5,15.0,0.1,or_greater"),
            "set_wheelbase_meters", "get_wheelbase_meters");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "lateral_grip", PROPERTY_HINT_RANGE, "0.1,12.0,0.1,or_greater"),
            "set_lateral_grip", "get_lateral_grip");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "handbrake_grip_scale", PROPERTY_HINT_RANGE, "0.05,1.0,0.01"),
            "set_handbrake_grip_scale", "get_handbrake_grip_scale");
```

- [ ] **Step 3: Implement setters and getters**

In `src/bus_controller_3d.cpp`, add these methods after `get_turn_rate()`:

```cpp
void BusController3D::set_mass_kg(double value) {
    tuning_.mass_kg = clamp_min(value, 100.0);
}

double BusController3D::get_mass_kg() const {
    return tuning_.mass_kg;
}

void BusController3D::set_engine_force(double value) {
    tuning_.engine_force = clamp_min(value, 100.0);
}

double BusController3D::get_engine_force() const {
    return tuning_.engine_force;
}

void BusController3D::set_reverse_force(double value) {
    tuning_.reverse_force = clamp_min(value, 100.0);
}

double BusController3D::get_reverse_force() const {
    return tuning_.reverse_force;
}

void BusController3D::set_rolling_resistance(double value) {
    tuning_.rolling_resistance = clamp_min(value, 0.0);
}

double BusController3D::get_rolling_resistance() const {
    return tuning_.rolling_resistance;
}

void BusController3D::set_air_drag_coefficient(double value) {
    tuning_.air_drag_coefficient = clamp_min(value, 0.0);
}

double BusController3D::get_air_drag_coefficient() const {
    return tuning_.air_drag_coefficient;
}

void BusController3D::set_wheelbase_meters(double value) {
    tuning_.wheelbase_meters = clamp_min(value, 0.5);
}

double BusController3D::get_wheelbase_meters() const {
    return tuning_.wheelbase_meters;
}

void BusController3D::set_lateral_grip(double value) {
    tuning_.lateral_grip = clamp_min(value, 0.1);
}

double BusController3D::get_lateral_grip() const {
    return tuning_.lateral_grip;
}

void BusController3D::set_handbrake_grip_scale(double value) {
    tuning_.handbrake_grip_scale = clamp_range(value, 0.05, 1.0);
}

double BusController3D::get_handbrake_grip_scale() const {
    return tuning_.handbrake_grip_scale;
}
```

- [ ] **Step 4: Build the extension**

Run:

```bash
scons platform=macos target=template_debug
```

Expected result:

```text
scons: done building targets.
```

- [ ] **Step 5: Commit Task 5**

Run:

```bash
git add src/bus_controller_3d.h src/bus_controller_3d.cpp
git commit -m "feat: expose bus physics tuning"
```

## Task 6: Final Verification And Working Tree Review

**Files:**
- Verify: `src/driving/bus_driving_model.h`
- Verify: `src/driving/bus_driving_model.cpp`
- Verify: `src/bus_controller_3d.h`
- Verify: `src/bus_controller_3d.cpp`
- Verify: `tests/test_bus_driving_model.cpp`

- [ ] **Step 1: Run model tests**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected result:

```text
All tests passed
```

- [ ] **Step 2: Run the GDExtension build**

Run:

```bash
scons platform=macos target=template_debug
```

Expected result:

```text
scons: done building targets.
```

- [ ] **Step 3: Check for unintended file changes**

Run:

```bash
git status --short
```

Expected result includes only intended physics files plus any pre-existing user-owned files that were already dirty before this plan was executed:

```text
 M project.godot
?? antlia.gdextension.uid
```

Do not stage or revert `project.godot` or `antlia.gdextension.uid` unless the user explicitly asks.

- [ ] **Step 4: Final implementation summary**

Report:

```text
Implemented force-based bus physics in the pure C++ model, exposed the new tuning fields through BusController3D, and verified with scons -C tests, ./tests/bin/test_bus_driving_model, and scons platform=macos target=template_debug.
```
