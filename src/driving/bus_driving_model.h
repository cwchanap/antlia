#pragma once

namespace antlia::driving {

struct BusDrivingInput {
    double throttle = 0.0;
    double brake = 0.0;
    double steer = 0.0;
    bool handbrake = false;
    double delta_seconds = 0.0;
};

struct BusDrivingTuning {
    double max_forward_speed = 18.0;
    double max_reverse_speed = 5.0;
    double acceleration = 2.5;
    double brake_force = 9.0;
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

class BusDrivingModel {
public:
    BusDrivingFrame step(const BusDrivingInput &input, const BusDrivingTuning &tuning);
    void reset();

    double speed_mps() const;
    double steering_radians() const;
    double last_effective_steering() const;

private:
    static double clamp(double value, double minimum, double maximum);
    static double move_toward(double current, double target, double amount);
    static BusDrivingTuning sanitized(BusDrivingTuning tuning);

    double speed_mps_ = 0.0;
    double steering_radians_ = 0.0;
    double last_effective_steering_ = 0.0;
};

} // namespace antlia::driving
