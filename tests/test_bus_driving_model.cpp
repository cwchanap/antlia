#include "test_harness.h"

#include "driving/bus_driving_model.h"

#include <cmath>
#include <limits>

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

ANTLIA_TEST(handbrake_decelerates_more_aggressively_than_normal_drag) {
    BusDrivingModel drag_model;
    BusDrivingModel handbrake_model;
    BusDrivingTuning params = tuning();

    for (int i = 0; i < 60; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        drag_model.step(input, params);
        handbrake_model.step(input, params);
    }

    drag_model.step(tick(0.25), params);

    BusDrivingInput handbrake = tick(0.25);
    handbrake.handbrake = true;
    handbrake_model.step(handbrake, params);

    CHECK(handbrake_model.speed_mps() < drag_model.speed_mps());
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

ANTLIA_TEST(frame_reports_yaw_and_forward_distance_when_moving_and_steering) {
    BusDrivingModel model;
    BusDrivingTuning params = tuning();

    for (int i = 0; i < 60; ++i) {
        BusDrivingInput input = tick(1.0 / 60.0);
        input.throttle = 1.0;
        input.steer = 1.0;
        model.step(input, params);
    }

    BusDrivingInput input = tick(0.1);
    input.throttle = 1.0;
    input.steer = 1.0;
    const auto frame = model.step(input, params);

    CHECK(frame.yaw_delta_radians > 0.0);
    CHECK(frame.forward_distance_meters > 0.0);
}

ANTLIA_TEST(inputs_are_clamped_to_public_ranges) {
    BusDrivingModel clamped_model;
    BusDrivingModel reference_model;
    BusDrivingTuning params = tuning();

    BusDrivingInput excessive = tick(0.25);
    excessive.throttle = 99.0;
    excessive.brake = -99.0;
    excessive.steer = 99.0;

    BusDrivingInput clamped = tick(0.25);
    clamped.throttle = 1.0;
    clamped.brake = 0.0;
    clamped.steer = 1.0;

    const auto excessive_frame = clamped_model.step(excessive, params);
    const auto clamped_frame = reference_model.step(clamped, params);

    CHECK_NEAR(excessive_frame.speed_mps, clamped_frame.speed_mps, 0.0001);
    CHECK_NEAR(excessive_frame.steering_radians, clamped_frame.steering_radians, 0.0001);
}

ANTLIA_TEST(delta_seconds_is_clamped_for_large_ticks) {
    BusDrivingModel clamped_model;
    BusDrivingModel repeated_model;
    BusDrivingTuning params = tuning();

    BusDrivingInput giant_tick = tick(10.0);
    giant_tick.throttle = 1.0;
    const auto clamped_frame = clamped_model.step(giant_tick, params);

    BusDrivingInput normal_tick = tick(0.25);
    normal_tick.throttle = 1.0;
    for (int i = 0; i < 40; ++i) {
        repeated_model.step(normal_tick, params);
    }

    const double unclamped_single_tick_distance = params.max_forward_speed * 10.0;
    CHECK(clamped_frame.forward_distance_meters < unclamped_single_tick_distance);
    CHECK(clamped_model.speed_mps() < repeated_model.speed_mps());
}

ANTLIA_TEST(non_finite_input_and_tuning_are_sanitized) {
    const double infinity = std::numeric_limits<double>::infinity();
    const double nan = std::numeric_limits<double>::quiet_NaN();

    BusDrivingModel input_model;
    BusDrivingInput invalid_input;
    invalid_input.throttle = nan;
    invalid_input.brake = infinity;
    invalid_input.steer = nan;
    invalid_input.delta_seconds = infinity;
    invalid_input.handbrake = true;

    const auto input_frame = input_model.step(invalid_input, tuning());

    CHECK(std::isfinite(input_model.speed_mps()));
    CHECK(std::isfinite(input_model.steering_radians()));
    CHECK(std::isfinite(input_model.last_effective_steering()));
    CHECK(std::isfinite(input_frame.speed_mps));
    CHECK(std::isfinite(input_frame.steering_radians));
    CHECK(std::isfinite(input_frame.effective_steering));
    CHECK(std::isfinite(input_frame.yaw_delta_radians));
    CHECK(std::isfinite(input_frame.forward_distance_meters));

    BusDrivingModel tuning_model;
    BusDrivingTuning params = tuning();
    params.max_forward_speed = nan;
    params.max_reverse_speed = infinity;
    params.acceleration = nan;
    params.brake_force = infinity;
    params.drag = nan;
    params.handbrake_drag = infinity;
    params.steering_speed = nan;
    params.steering_return_speed = infinity;
    params.max_steering_angle = nan;
    params.high_speed_steering_scale = infinity;
    params.turn_rate = nan;

    BusDrivingInput valid_input = tick(0.25);
    valid_input.throttle = 1.0;
    valid_input.steer = 1.0;

    const auto tuning_frame = tuning_model.step(valid_input, params);

    CHECK(std::isfinite(tuning_model.speed_mps()));
    CHECK(std::isfinite(tuning_model.steering_radians()));
    CHECK(std::isfinite(tuning_model.last_effective_steering()));
    CHECK(std::isfinite(tuning_frame.speed_mps));
    CHECK(std::isfinite(tuning_frame.steering_radians));
    CHECK(std::isfinite(tuning_frame.effective_steering));
    CHECK(std::isfinite(tuning_frame.yaw_delta_radians));
    CHECK(std::isfinite(tuning_frame.forward_distance_meters));
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
