# Antlia Bus Driving Simulator

Antlia is a Godot 4.6+ bus driving simulator prototype built with C++ GDExtension.

## Current Prototype

The first scaffold includes:

- `BusDrivingModel`, a pure C++ driving model for speed, steering, braking, reverse, drag, handbrake, and reset behavior.
- Unit tests for the driving math using a tiny local C++ test harness.
- `BusController3D`, a Godot C++ `CharacterBody3D` class that adapts input and physics ticks to the driving model.
- A runnable demo scene at `res://scenes/demo_bus_test.tscn`.
- A placeholder bus, road plane, collision shapes, chase camera, and lighting.

This prototype intentionally excludes traffic, passengers, routes, cockpit UI, save files, and real wheel/suspension simulation.

## Dependencies

- Godot 4.6 or newer. `antlia.gdextension` sets `compatibility_minimum = "4.6"`.
- SCons.
- A C++17 compiler.
- The `godot-cpp` submodule initialized at `godot-cpp/`.

Fetch the C++ bindings:

```bash
git submodule update --init --recursive
```

## Unit Tests

Build and run the local C++ driving-model tests:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

The expected current result is:

```text
14 passed, 0 failed
```

This environment used `/private/tmp/antlia-scons-venv/bin/scons` because SCons was installed in a temporary virtual environment. A normal local setup can use `scons` directly.

## Build GDExtension

On macOS:

```bash
scons platform=macos target=template_debug
```

The expected macOS debug output is:

```text
bin/libantlia.macos.template_debug.universal.dylib
```

Basic platform mappings also exist for Linux and Windows:

```bash
scons platform=linux target=template_debug
scons platform=windows target=template_debug
```

## Verification Status

Locally verified:

- C++ driving-model tests pass with `14 passed, 0 failed`.
- macOS debug GDExtension build passes and produces `bin/libantlia.macos.template_debug.universal.dylib`.

Not locally verified:

- Godot editor/headless scene import.
- Runtime demo controls in the Godot player.

No `godot` or `godot4` executable was available on `PATH` in this environment.

## Run Demo

Open this folder in Godot 4.6 or newer and run:

```text
res://scenes/demo_bus_test.tscn
```

Default controls:

- `W` or up arrow: accelerate.
- `S` or down arrow: brake and reverse.
- `A` or left arrow: steer left.
- `D` or right arrow: steer right.
- `Space`: handbrake.
- `R`: reset bus.

## Tuning Properties

`BusController3D` exposes these inspector properties:

- `max_forward_speed`
- `max_reverse_speed`
- `acceleration`
- `brake_force`
- `drag`
- `handbrake_drag`
- `steering_speed`
- `steering_return_speed`
- `max_steering_angle`
- `high_speed_steering_scale`
- `turn_rate`
