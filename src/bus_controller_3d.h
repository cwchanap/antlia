#pragma once

#include "driving/bus_driving_model.h"

#include <godot_cpp/classes/character_body3d.hpp>
#include <godot_cpp/variant/string_name.hpp>
#include <godot_cpp/variant/transform3d.hpp>

namespace godot {

class BusController3D : public CharacterBody3D {
    GDCLASS(BusController3D, CharacterBody3D)

public:
    BusController3D();

    void _ready() override;
    void _physics_process(double delta) override;

    void reset_bus();

    void set_max_forward_speed(double value);
    double get_max_forward_speed() const;

    void set_max_reverse_speed(double value);
    double get_max_reverse_speed() const;

    void set_acceleration(double value);
    double get_acceleration() const;

    void set_brake_force(double value);
    double get_brake_force() const;

    void set_drag(double value);
    double get_drag() const;

    void set_handbrake_drag(double value);
    double get_handbrake_drag() const;

    void set_steering_speed(double value);
    double get_steering_speed() const;

    void set_steering_return_speed(double value);
    double get_steering_return_speed() const;

    void set_max_steering_angle(double value);
    double get_max_steering_angle() const;

    void set_high_speed_steering_scale(double value);
    double get_high_speed_steering_scale() const;

    void set_turn_rate(double value);
    double get_turn_rate() const;

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

    double get_current_speed() const;
    double get_current_steering() const;

protected:
    static void _bind_methods();

private:
    static double clamp_min(double value, double minimum);
    static double clamp_range(double value, double minimum, double maximum);

    bool is_action_pressed_safe(const StringName &action_name) const;
    antlia::driving::BusDrivingInput read_input(double delta) const;

    antlia::driving::BusDrivingModel model_;
    antlia::driving::BusDrivingTuning tuning_;
    Transform3D spawn_transform_;
    bool has_spawn_transform_ = false;

    StringName accelerate_action_ = "drive_accelerate";
    StringName brake_action_ = "drive_brake";
    StringName steer_left_action_ = "drive_steer_left";
    StringName steer_right_action_ = "drive_steer_right";
    StringName handbrake_action_ = "drive_handbrake";
    StringName reset_action_ = "drive_reset";
};

} // namespace godot
