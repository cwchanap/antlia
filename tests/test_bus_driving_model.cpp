#include "test_harness.h"

#include "driving/bus_driving_model.h"

using antlia::driving::BusDrivingInput;
using antlia::driving::BusDrivingModel;
using antlia::driving::BusDrivingTuning;

namespace {

BusDrivingInput tick(double seconds) {
    BusDrivingInput input;
    input.delta_seconds = seconds;
    return input;
}

BusDrivingTuning tuning() {
    BusDrivingTuning value;
    value.max_forward_speed = 10.0;
    value.max_reverse_speed = 3.0;
    value.acceleration = 5.0;
    value.brake_force = 8.0;
    value.drag = 1.0;
    value.handbrake_drag = 6.0;
    value.steering_speed = 2.0;
    value.steering_return_speed = 4.0;
    value.max_steering_angle = 0.5;
    value.high_speed_steering_scale = 0.25;
    value.turn_rate = 1.2;
    return value;
}

} // namespace

ANTLIA_TEST(acceleration_increases_speed_up_to_forward_cap) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    for (int i = 0; i < 120; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        model.step(input, params);
    }

    CHECK(model.speed_mps() > 0.0);
    CHECK(model.speed_mps() <= params.max_forward_speed);
}

ANTLIA_TEST(braking_reduces_forward_speed) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    for (int i = 0; i < 60; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        model.step(input, params);
    }

    const double before_brake = model.speed_mps();
    for (int i = 0; i < 20; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.brake = 1.0;
        model.step(input, params);
    }

    CHECK(model.speed_mps() < before_brake);
}

ANTLIA_TEST(continued_braking_transitions_into_reverse) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    for (int i = 0; i < 120; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.brake = 1.0;
        model.step(input, params);
    }

    CHECK(model.speed_mps() < 0.0);
}

ANTLIA_TEST(reverse_speed_respects_reverse_cap) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    for (int i = 0; i < 600; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.brake = 1.0;
        model.step(input, params);
    }

    CHECK(model.speed_mps() >= -params.max_reverse_speed);
    CHECK_NEAR(model.speed_mps(), -params.max_reverse_speed, 0.001);
}

ANTLIA_TEST(drag_slows_bus_without_input) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    for (int i = 0; i < 60; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        model.step(input, params);
    }

    const double before_drag = model.speed_mps();
    for (int i = 0; i < 60; ++i) {
        model.step(tick(1.0 / 60.0), params);
    }

    CHECK(model.speed_mps() < before_drag);
}

ANTLIA_TEST(steering_eases_toward_input) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    BusDrivingInput input = tick(0.1);
    input.steer = 1.0;
    model.step(input, params);

    CHECK(model.steering_radians() > 0.0);
    CHECK(model.steering_radians() < params.max_steering_angle);
}

ANTLIA_TEST(steering_recenters_when_released) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    BusDrivingInput steer = tick(0.5);
    steer.steer = 1.0;
    model.step(steer, params);
    const double before_release = model.steering_radians();

    model.step(tick(0.1), params);

    CHECK(std::fabs(model.steering_radians()) < std::fabs(before_release));
}

ANTLIA_TEST(steering_effect_reduces_at_high_speed) {
    BusDrivingModel slow_model;
    BusDrivingModel fast_model;
    BusDrivingTuning params = tuning();

    BusDrivingInput steer = tick(0.25);
    steer.steer = 1.0;
    slow_model.step(steer, params);

    for (int i = 0; i < 180; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        fast_model.step(input, params);
    }
    fast_model.step(steer, params);

    CHECK(std::fabs(fast_model.last_effective_steering()) < std::fabs(slow_model.last_effective_steering()));
}

ANTLIA_TEST(reset_clears_speed_and_steering) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    BusDrivingInput input = tick(0.5);
    input.throttle = 1.0;
    input.steer = 1.0;
    model.step(input, params);

    model.reset();

    CHECK_NEAR(model.speed_mps(), 0.0, 0.0001);
    CHECK_NEAR(model.steering_radians(), 0.0, 0.0001);
}

int main() {
    return antlia::test::run_all();
}
