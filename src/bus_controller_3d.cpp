#include "bus_controller_3d.h"

#include <godot_cpp/classes/input.hpp>
#include <godot_cpp/classes/input_map.hpp>
#include <godot_cpp/core/class_db.hpp>

#include <algorithm>
#include <cmath>

namespace godot {

namespace {

constexpr double kMinimumPositiveTuning = 0.01;

double finite_or(double value, double fallback) {
    return std::isfinite(value) ? value : fallback;
}

} // namespace

BusController3D::BusController3D() {
    set_physics_process(true);
}

void BusController3D::_bind_methods() {
    ClassDB::bind_method(D_METHOD("reset_bus"), &BusController3D::reset_bus);

    ClassDB::bind_method(D_METHOD("set_max_forward_speed", "value"), &BusController3D::set_max_forward_speed);
    ClassDB::bind_method(D_METHOD("get_max_forward_speed"), &BusController3D::get_max_forward_speed);
    ClassDB::bind_method(D_METHOD("set_max_reverse_speed", "value"), &BusController3D::set_max_reverse_speed);
    ClassDB::bind_method(D_METHOD("get_max_reverse_speed"), &BusController3D::get_max_reverse_speed);
    ClassDB::bind_method(D_METHOD("set_acceleration", "value"), &BusController3D::set_acceleration);
    ClassDB::bind_method(D_METHOD("get_acceleration"), &BusController3D::get_acceleration);
    ClassDB::bind_method(D_METHOD("set_brake_force", "value"), &BusController3D::set_brake_force);
    ClassDB::bind_method(D_METHOD("get_brake_force"), &BusController3D::get_brake_force);
    ClassDB::bind_method(D_METHOD("set_drag", "value"), &BusController3D::set_drag);
    ClassDB::bind_method(D_METHOD("get_drag"), &BusController3D::get_drag);
    ClassDB::bind_method(D_METHOD("set_handbrake_drag", "value"), &BusController3D::set_handbrake_drag);
    ClassDB::bind_method(D_METHOD("get_handbrake_drag"), &BusController3D::get_handbrake_drag);
    ClassDB::bind_method(D_METHOD("set_steering_speed", "value"), &BusController3D::set_steering_speed);
    ClassDB::bind_method(D_METHOD("get_steering_speed"), &BusController3D::get_steering_speed);
    ClassDB::bind_method(D_METHOD("set_steering_return_speed", "value"), &BusController3D::set_steering_return_speed);
    ClassDB::bind_method(D_METHOD("get_steering_return_speed"), &BusController3D::get_steering_return_speed);
    ClassDB::bind_method(D_METHOD("set_max_steering_angle", "value"), &BusController3D::set_max_steering_angle);
    ClassDB::bind_method(D_METHOD("get_max_steering_angle"), &BusController3D::get_max_steering_angle);
    ClassDB::bind_method(D_METHOD("set_high_speed_steering_scale", "value"), &BusController3D::set_high_speed_steering_scale);
    ClassDB::bind_method(D_METHOD("get_high_speed_steering_scale"), &BusController3D::get_high_speed_steering_scale);
    ClassDB::bind_method(D_METHOD("set_turn_rate", "value"), &BusController3D::set_turn_rate);
    ClassDB::bind_method(D_METHOD("get_turn_rate"), &BusController3D::get_turn_rate);
    ClassDB::bind_method(D_METHOD("get_current_speed"), &BusController3D::get_current_speed);
    ClassDB::bind_method(D_METHOD("get_current_steering"), &BusController3D::get_current_steering);

    ADD_GROUP("Driving", "");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "max_forward_speed", PROPERTY_HINT_RANGE, "0.1,60.0,0.1,or_greater"),
            "set_max_forward_speed", "get_max_forward_speed");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "max_reverse_speed", PROPERTY_HINT_RANGE, "0.1,20.0,0.1,or_greater"),
            "set_max_reverse_speed", "get_max_reverse_speed");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "acceleration", PROPERTY_HINT_RANGE, "0.1,30.0,0.1,or_greater"),
            "set_acceleration", "get_acceleration");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "brake_force", PROPERTY_HINT_RANGE, "0.1,40.0,0.1,or_greater"),
            "set_brake_force", "get_brake_force");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "drag", PROPERTY_HINT_RANGE, "0.0,20.0,0.1,or_greater"), "set_drag",
            "get_drag");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "handbrake_drag", PROPERTY_HINT_RANGE, "0.0,40.0,0.1,or_greater"),
            "set_handbrake_drag", "get_handbrake_drag");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "steering_speed", PROPERTY_HINT_RANGE, "0.1,10.0,0.1,or_greater"),
            "set_steering_speed", "get_steering_speed");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "steering_return_speed", PROPERTY_HINT_RANGE, "0.1,10.0,0.1,or_greater"),
            "set_steering_return_speed", "get_steering_return_speed");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "max_steering_angle", PROPERTY_HINT_RANGE, "0.01,1.2,0.01"),
            "set_max_steering_angle", "get_max_steering_angle");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "high_speed_steering_scale", PROPERTY_HINT_RANGE, "0.05,1.0,0.01"),
            "set_high_speed_steering_scale", "get_high_speed_steering_scale");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "turn_rate", PROPERTY_HINT_RANGE, "0.01,5.0,0.01,or_greater"),
            "set_turn_rate", "get_turn_rate");
}

void BusController3D::_ready() {
    spawn_transform_ = get_global_transform();
    has_spawn_transform_ = true;
}

void BusController3D::_physics_process(double delta) {
    if (is_action_pressed_safe(reset_action_)) {
        reset_bus();
        return;
    }

    const antlia::driving::BusDrivingFrame frame = model_.step(read_input(delta), tuning_);
    rotate_y(frame.yaw_delta_radians);

    const Vector3 forward = -get_global_transform().basis.get_column(2).normalized();
    set_velocity(forward * frame.speed_mps);
    move_and_slide();
}

void BusController3D::reset_bus() {
    model_.reset();
    set_velocity(Vector3());
    if (has_spawn_transform_) {
        set_global_transform(spawn_transform_);
    }
}

void BusController3D::set_max_forward_speed(double value) {
    tuning_.max_forward_speed = clamp_min(value, kMinimumPositiveTuning);
}

double BusController3D::get_max_forward_speed() const {
    return tuning_.max_forward_speed;
}

void BusController3D::set_max_reverse_speed(double value) {
    tuning_.max_reverse_speed = clamp_min(value, kMinimumPositiveTuning);
}

double BusController3D::get_max_reverse_speed() const {
    return tuning_.max_reverse_speed;
}

void BusController3D::set_acceleration(double value) {
    tuning_.acceleration = clamp_min(value, kMinimumPositiveTuning);
}

double BusController3D::get_acceleration() const {
    return tuning_.acceleration;
}

void BusController3D::set_brake_force(double value) {
    tuning_.brake_force = clamp_min(value, kMinimumPositiveTuning);
}

double BusController3D::get_brake_force() const {
    return tuning_.brake_force;
}

void BusController3D::set_drag(double value) {
    tuning_.drag = clamp_min(value, 0.0);
}

double BusController3D::get_drag() const {
    return tuning_.drag;
}

void BusController3D::set_handbrake_drag(double value) {
    tuning_.handbrake_drag = clamp_min(value, 0.0);
}

double BusController3D::get_handbrake_drag() const {
    return tuning_.handbrake_drag;
}

void BusController3D::set_steering_speed(double value) {
    tuning_.steering_speed = clamp_min(value, kMinimumPositiveTuning);
}

double BusController3D::get_steering_speed() const {
    return tuning_.steering_speed;
}

void BusController3D::set_steering_return_speed(double value) {
    tuning_.steering_return_speed = clamp_min(value, kMinimumPositiveTuning);
}

double BusController3D::get_steering_return_speed() const {
    return tuning_.steering_return_speed;
}

void BusController3D::set_max_steering_angle(double value) {
    tuning_.max_steering_angle = clamp_range(value, 0.01, 1.2);
}

double BusController3D::get_max_steering_angle() const {
    return tuning_.max_steering_angle;
}

void BusController3D::set_high_speed_steering_scale(double value) {
    tuning_.high_speed_steering_scale = clamp_range(value, 0.05, 1.0);
}

double BusController3D::get_high_speed_steering_scale() const {
    return tuning_.high_speed_steering_scale;
}

void BusController3D::set_turn_rate(double value) {
    tuning_.turn_rate = clamp_min(value, kMinimumPositiveTuning);
}

double BusController3D::get_turn_rate() const {
    return tuning_.turn_rate;
}

double BusController3D::get_current_speed() const {
    return model_.speed_mps();
}

double BusController3D::get_current_steering() const {
    return model_.steering_radians();
}

double BusController3D::clamp_min(double value, double minimum) {
    return std::max(finite_or(value, minimum), minimum);
}

double BusController3D::clamp_range(double value, double minimum, double maximum) {
    return std::min(std::max(finite_or(value, minimum), minimum), maximum);
}

bool BusController3D::is_action_pressed_safe(const StringName &action_name) const {
    const Input *input = Input::get_singleton();
    const InputMap *input_map = InputMap::get_singleton();
    return input != nullptr && input_map != nullptr && input_map->has_action(action_name) &&
            input->is_action_pressed(action_name);
}

antlia::driving::BusDrivingInput BusController3D::read_input(double delta) const {
    antlia::driving::BusDrivingInput input;
    input.delta_seconds = delta;
    input.throttle = is_action_pressed_safe(accelerate_action_) ? 1.0 : 0.0;
    input.brake = is_action_pressed_safe(brake_action_) ? 1.0 : 0.0;
    input.handbrake = is_action_pressed_safe(handbrake_action_);

    const double steer_left = is_action_pressed_safe(steer_left_action_) ? 1.0 : 0.0;
    const double steer_right = is_action_pressed_safe(steer_right_action_) ? 1.0 : 0.0;
    input.steer = steer_right - steer_left;
    return input;
}

} // namespace godot
