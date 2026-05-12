# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Antlia is a Godot 4.6+ bus driving simulator built as a C++ GDExtension. Godot loads the compiled shared library via `antlia.gdextension`; gameplay logic lives in C++.

## Setup

The `godot-cpp` bindings live in a submodule and must be initialized before any build:

```bash
git submodule update --init --recursive
```

## Build

GDExtension shared library (output lands in `bin/`, referenced by `antlia.gdextension`):

```bash
scons platform=macos target=template_debug    # macOS (verified)
scons platform=linux target=template_debug    # mapped, not verified
scons platform=windows target=template_debug  # mapped, not verified
```

The macOS debug build produces `bin/libantlia.macos.template_debug.universal.dylib`. Library filenames are derived from `env["suffix"]` in the root `SConstruct`; the `[libraries]` section of `antlia.gdextension` must match for Godot to pick up a new platform.

## Tests

The driving-model tests use a tiny in-repo harness (`tests/test_harness.h`) and a separate SCons project that does **not** depend on `godot-cpp` — they compile pure C++ and run as a standalone binary:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Add new test cases with the `ANTLIA_TEST(name) { ... }` macro in `tests/test_bus_driving_model.cpp`; they self-register. There is no per-test filter; the harness runs the whole registry. To run a subset, comment out or temporarily rename other `ANTLIA_TEST` blocks.

Run the demo scene by opening the project folder in Godot 4.6+ — `project.godot` already sets `res://scenes/demo_bus_test.tscn` as the main scene. No `godot` CLI invocation has been verified in this repo.

## Architecture

The code is deliberately split so driving math can be unit-tested without Godot:

- **`src/driving/` — pure C++ driving model.** `BusDrivingModel::step(input, tuning)` is a stateless-per-call function (state is the model's speed/steering) that takes a `BusDrivingInput` (throttle, brake, steer, handbrake, `delta_seconds`) and `BusDrivingTuning` constants, and returns a `BusDrivingFrame` (speed, yaw delta, etc.). No Godot headers are included here, which is why `tests/SConstruct` can link it directly.
- **`src/bus_controller_3d.{h,cpp}` — Godot adapter.** `BusController3D` is a `CharacterBody3D` that, in `_physics_process`, reads the named input actions (`drive_accelerate`, `drive_brake`, `drive_steer_left`, `drive_steer_right`, `drive_handbrake`, `drive_reset`) into a `BusDrivingInput`, calls `model_.step(...)`, applies `frame.yaw_delta_radians` via `rotate_y`, and pushes velocity through `move_and_slide()`. Every tuning field is exposed as an inspector property via `_bind_methods()` with clamped setters (see `kMinimumPositiveTuning` and `clamp_range`).
- **`src/register_types.cpp` — GDExtension entrypoint.** `antlia_library_init` registers `BusController3D` at `MODULE_INITIALIZATION_LEVEL_SCENE`. Any new GDExtension class must be added here with `GDREGISTER_CLASS(...)` to appear in Godot.
- **`project.godot` — input action map.** The `[input]` section defines the `drive_*` actions the controller reads. New input actions must be added here, not just in C++.

When adding gameplay logic, prefer extending the pure-C++ side first (covered by tests), then expose it through the Godot adapter. The root `SConstruct` globs `src/*.cpp` and `src/driving/*.cpp`; new subdirectories of `src/` are not picked up automatically and need a glob added.

## Scope

The prototype intentionally excludes: traffic, passengers, routes, cockpit UI, save files, and real wheel/suspension simulation. Treat additions in those areas as feature work, not bug fixes.

## Design Docs

`docs/superpowers/specs/` holds design specs and `docs/superpowers/plans/` holds implementation plans for larger features — read the relevant doc before making non-trivial changes to driving behavior or scaffold structure.
