# Antlia Bus Driving Simulator

Antlia is a Godot 4 bus driving simulator prototype built with C++ GDExtension.

## First Slice

This scaffold provides:

- A pure C++ bus driving model.
- Unit tests for acceleration, braking, reverse, drag, steering, and reset.
- A Godot `BusController3D` GDExtension class.
- A minimal runnable demo scene.

## Dependencies

- Godot 4.x
- SCons
- A C++17 compiler
- godot-cpp checked out at `godot-cpp/`

Fetch the C++ bindings:

```bash
git submodule add https://github.com/godotengine/godot-cpp.git godot-cpp
git submodule update --init --recursive
```

## Unit Tests

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

## Build GDExtension

On macOS:

```bash
scons platform=macos target=template_debug
```

The build writes the native library into `bin/`.

## Run Demo

Open this folder in Godot 4 and run `res://scenes/demo_bus_test.tscn`.

Default controls:

- `W` or up arrow: accelerate
- `S` or down arrow: brake and reverse
- `A` or left arrow: steer left
- `D` or right arrow: steer right
- `Space`: handbrake
- `R`: reset bus
