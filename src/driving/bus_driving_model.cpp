#include "driving/bus_driving_model.h"

#include <algorithm>
#include <cmath>

namespace antlia::driving {

namespace {

constexpr double kInputMinimum = -1.0;
constexpr double kInputMaximum = 1.0;
constexpr double kMaximumPhysicsStep = 0.25;
constexpr double kReverseAccelerationScale = 0.6;
constexpr double kStopSpeed = 0.05;

double finite_or(double value, double fallback) {
    return std::isfinite(value) ? value : fallback;
}

double abs_max(double value, double fallback) {
    const double safe_fallback = std::fabs(finite_or(fallback, 0.0));
    return std::max(std::fabs(finite_or(value, safe_fallback)), safe_fallback);
}

double positive_or(double value, double fallback) {
    if (std::isfinite(value) && value > 0.0) {
        return value;
    }
    return std::fabs(finite_or(fallback, 0.0));
}

double sign_of(double value) {
    if (value > 0.0) {
        return 1.0;
    }
    if (value < 0.0) {
        return -1.0;
    }
    return 0.0;
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

    if (brake > 0.0) {
        if (speed_mps_ > kStopSpeed) {
            net_force -= tuning.brake_force * brake;
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

    const bool passive_only = throttle <= 0.0 && brake <= 0.0;
    if (previous_speed > 0.0 && speed_mps_ < 0.0 && (brake > 0.0 || passive_only)) {
        speed_mps_ = 0.0;
    }
    if (previous_speed < 0.0 && speed_mps_ > 0.0 && passive_only) {
        speed_mps_ = 0.0;
    }

    speed_mps_ = clamp(speed_mps_, -tuning.max_reverse_speed, tuning.max_forward_speed);

    const double speed_ratio = clamp(std::fabs(speed_mps_) / tuning.max_forward_speed, 0.0, 1.0);
    const double steering_speed_ratio = speed_ratio * speed_ratio;
    const double steering_scale = 1.0 - ((1.0 - tuning.high_speed_steering_scale) * steering_speed_ratio);
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
    tuning.engine_force = positive_or(tuning.engine_force, tuning.mass_kg * tuning.acceleration);
    tuning.reverse_force = abs_max(tuning.reverse_force, tuning.engine_force * kReverseAccelerationScale);
    tuning.rolling_resistance = std::max(finite_or(tuning.rolling_resistance, 0.0), 0.0);
    tuning.air_drag_coefficient = std::max(finite_or(tuning.air_drag_coefficient, 0.0), 0.0);
    tuning.wheelbase_meters = abs_max(tuning.wheelbase_meters, 0.5);
    tuning.lateral_grip = abs_max(tuning.lateral_grip, 0.1);
    tuning.handbrake_grip_scale = clamp(tuning.handbrake_grip_scale, 0.05, 1.0);
    return tuning;
}

} // namespace antlia::driving
