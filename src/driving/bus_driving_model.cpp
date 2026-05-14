#include "driving/bus_driving_model.h"

#include <algorithm>
#include <cmath>

namespace antlia::driving {

namespace {

constexpr double kInputMinimum = -1.0;
constexpr double kInputMaximum = 1.0;
constexpr double kMaximumPhysicsStep = 0.25;
constexpr double kReverseAccelerationScale = 0.6;

double finite_or(double value, double fallback) {
    return std::isfinite(value) ? value : fallback;
}

double abs_max(double value, double fallback) {
    const double safe_fallback = std::fabs(finite_or(fallback, 0.0));
    return std::max(std::fabs(finite_or(value, safe_fallback)), safe_fallback);
}

} // namespace

BusDrivingFrame BusDrivingModel::step(const BusDrivingInput &input, const BusDrivingTuning &raw_tuning) {
    const BusDrivingTuning tuning = sanitized(raw_tuning);
    const double dt = clamp(input.delta_seconds, 0.0, kMaximumPhysicsStep);
    const double throttle = clamp(input.throttle, 0.0, 1.0);
    const double brake = clamp(input.brake, 0.0, 1.0);
    const double steer = clamp(finite_or(input.steer, 0.0), kInputMinimum, kInputMaximum);

    const double target_steering = steer * tuning.max_steering_angle;
    const double steering_rate = std::fabs(steer) > 0.001 ? tuning.steering_speed : tuning.steering_return_speed;
    steering_radians_ = move_toward(finite_or(steering_radians_, 0.0), target_steering, steering_rate * dt);

    speed_mps_ = finite_or(speed_mps_, 0.0);

    double net_force = 0.0;
    if (throttle > 0.0) {
        const double speed_fraction = clamp(speed_mps_ / tuning.max_forward_speed, 0.0, 1.0);
        const double engine_scale = 1.0 - speed_fraction;
        net_force += tuning.engine_force * throttle * engine_scale;
    }

    const double longitudinal_acceleration = net_force / tuning.mass_kg;
    speed_mps_ += longitudinal_acceleration * dt;

    if (brake > 0.0) {
        speed_mps_ = finite_or(speed_mps_, 0.0);
        if (speed_mps_ > 0.0) {
            speed_mps_ = move_toward(speed_mps_, 0.0, tuning.brake_force * brake * dt);
        } else {
            speed_mps_ -= tuning.acceleration * kReverseAccelerationScale * brake * dt;
        }
    }

    if (throttle <= 0.0 && brake <= 0.0) {
        speed_mps_ = move_toward(speed_mps_, 0.0, tuning.drag * dt);
    }

    if (input.handbrake) {
        speed_mps_ = move_toward(speed_mps_, 0.0, tuning.handbrake_drag * dt);
    }

    speed_mps_ = clamp(speed_mps_, -tuning.max_reverse_speed, tuning.max_forward_speed);

    const double speed_ratio = clamp(std::fabs(speed_mps_) / tuning.max_forward_speed, 0.0, 1.0);
    const double steering_scale = 1.0 - ((1.0 - tuning.high_speed_steering_scale) * speed_ratio);
    last_effective_steering_ = steering_radians_ * steering_scale;

    BusDrivingFrame frame;
    frame.speed_mps = speed_mps_;
    frame.steering_radians = steering_radians_;
    frame.effective_steering = last_effective_steering_;
    frame.yaw_delta_radians = last_effective_steering_ * tuning.turn_rate * (speed_mps_ / tuning.max_forward_speed) * dt;
    frame.forward_distance_meters = speed_mps_ * dt;
    frame.longitudinal_acceleration_mps2 = longitudinal_acceleration;
    frame.lateral_slip = 0.0;
    frame.grip_scale = 1.0;
    return frame;
}

void BusDrivingModel::reset() {
    speed_mps_ = 0.0;
    steering_radians_ = 0.0;
    last_effective_steering_ = 0.0;
}

double BusDrivingModel::speed_mps() const {
    return speed_mps_;
}

double BusDrivingModel::steering_radians() const {
    return steering_radians_;
}

double BusDrivingModel::last_effective_steering() const {
    return last_effective_steering_;
}

double BusDrivingModel::clamp(double value, double minimum, double maximum) {
    const double safe_minimum = finite_or(minimum, 0.0);
    const double safe_maximum = std::max(finite_or(maximum, safe_minimum), safe_minimum);
    return std::min(std::max(finite_or(value, safe_minimum), safe_minimum), safe_maximum);
}

double BusDrivingModel::move_toward(double current, double target, double amount) {
    const double safe_current = finite_or(current, target);
    const double safe_target = finite_or(target, 0.0);
    const double safe_amount = std::max(finite_or(amount, 0.0), 0.0);
    if (safe_current < safe_target) {
        return std::min(safe_current + safe_amount, safe_target);
    }
    if (safe_current > safe_target) {
        return std::max(safe_current - safe_amount, safe_target);
    }
    return safe_target;
}

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

} // namespace antlia::driving
