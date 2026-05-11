#pragma once

#include <godot_cpp/classes/character_body3d.hpp>

namespace godot {

class BusController3D : public CharacterBody3D {
    GDCLASS(BusController3D, CharacterBody3D)

protected:
    static void _bind_methods();

public:
    BusController3D();
};

} // namespace godot
