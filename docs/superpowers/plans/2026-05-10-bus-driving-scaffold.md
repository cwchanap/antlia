# Bus Driving Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable Godot 4 + C++ GDExtension scaffold for a heavy bus driving prototype with unit-tested driving math.

**Architecture:** Keep the driving math in a pure C++ `BusDrivingModel` so unit tests run without Godot. Wrap that model with a Godot `CharacterBody3D` GDExtension class named `BusController3D`, then wire it into a minimal demo scene with input actions, camera, collision, and placeholder geometry.

**Tech Stack:** Godot 4, godot-cpp GDExtension bindings, C++17, SCons, a tiny local C++ test harness for model unit tests, Git.

---

## File Structure

- Create: `.gitignore`
  - Ignores Godot generated state, build outputs, and local binaries.
- Create: `README.md`
  - Explains setup, dependency fetch, build, unit tests, and demo run.
- Create: `project.godot`
  - Defines the Godot project, main demo scene, and driving input map.
- Create: `antlia.gdextension`
  - Registers the native library entry symbol and per-platform library paths.
- Create: `SConstruct`
  - Builds the GDExtension library using the `godot-cpp` submodule.
- Create: `src/register_types.h`
  - Declares GDExtension initialization functions.
- Create: `src/register_types.cpp`
  - Registers `BusController3D` with Godot.
- Create: `src/driving/bus_driving_model.h`
  - Defines pure C++ input, tuning, frame-result, and model types.
- Create: `src/driving/bus_driving_model.cpp`
  - Implements acceleration, braking, reverse, drag, steering smoothing, steering scaling, and reset.
- Create: `tests/test_harness.h`
  - Provides minimal `CHECK`, `CHECK_NEAR`, and test registration helpers without external test dependencies.
- Create: `tests/test_bus_driving_model.cpp`
  - Unit tests for the pure driving model.
- Create: `tests/SConstruct`
  - Builds the unit-test executable without Godot.
- Create: `src/bus_controller_3d.h`
  - Declares the Godot `CharacterBody3D` adapter and inspector-facing properties.
- Create: `src/bus_controller_3d.cpp`
  - Reads input, calls `BusDrivingModel`, applies movement, and exposes tuning/state methods.
- Create: `scenes/demo_bus_test.tscn`
  - Minimal runnable scene with a placeholder bus, collision, road plane, camera, and light.

## Task 1: Add Repository And Test Harness Scaffolding

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `tests/test_harness.h`
- Create: `tests/SConstruct`
- Create: `tests/test_bus_driving_model.cpp`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
.godot/
.import/
bin/
tests/bin/
godot-cpp/bin/
godot-cpp/gen/
godot-cpp/.sconsign*.dblite
*.os
*.so
*.dylib
*.dll
*.framework/
*.xcworkspace/
*.xcodeproj/
*.DS_Store
```

- [ ] **Step 2: Create the initial `README.md`**

```markdown
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
```

- [ ] **Step 3: Create `tests/test_harness.h`**

```cpp
#pragma once

#include <cmath>
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace antlia::test {

using TestFn = std::function<void()>;

struct TestCase {
    std::string name;
    TestFn run;
};

inline std::vector<TestCase> &registry() {
    static std::vector<TestCase> tests;
    return tests;
}

struct Registrar {
    Registrar(const std::string &name, TestFn run) {
        registry().push_back({name, run});
    }
};

inline void check(bool condition, const char *expression, const char *file, int line) {
    if (!condition) {
        throw std::runtime_error(std::string(file) + ":" + std::to_string(line) + " CHECK failed: " + expression);
    }
}

inline void check_near(double actual, double expected, double tolerance, const char *expression, const char *file, int line) {
    if (std::fabs(actual - expected) > tolerance) {
        throw std::runtime_error(
            std::string(file) + ":" + std::to_string(line) + " CHECK_NEAR failed: " + expression +
            " actual=" + std::to_string(actual) +
            " expected=" + std::to_string(expected) +
            " tolerance=" + std::to_string(tolerance));
    }
}

inline int run_all() {
    int failures = 0;
    for (const TestCase &test : registry()) {
        try {
            test.run();
            std::cout << "[PASS] " << test.name << "\n";
        } catch (const std::exception &error) {
            ++failures;
            std::cerr << "[FAIL] " << test.name << "\n" << error.what() << "\n";
        }
    }

    std::cout << registry().size() - failures << " passed, " << failures << " failed\n";
    return failures == 0 ? 0 : 1;
}

} // namespace antlia::test

#define ANTLIA_TEST(name) \
    static void name(); \
    static ::antlia::test::Registrar name##_registrar(#name, name); \
    static void name()

#define CHECK(expression) ::antlia::test::check((expression), #expression, __FILE__, __LINE__)
#define CHECK_NEAR(actual, expected, tolerance) \
    ::antlia::test::check_near((actual), (expected), (tolerance), #actual " ~= " #expected, __FILE__, __LINE__)
```

- [ ] **Step 4: Create failing model tests in `tests/test_bus_driving_model.cpp`**

```cpp
#include "test_harness.h"

#include "driving/bus_driving_model.h"

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
```

- [ ] **Step 5: Create `tests/SConstruct`**

```python
import os

env = Environment(
    CXX=os.environ.get("CXX", "c++"),
    CPPPATH=["../src"],
    CXXFLAGS=["-std=c++17", "-Wall", "-Wextra", "-Wpedantic"],
)

target = env.Program(
    target="bin/test_bus_driving_model",
    source=[
        "test_bus_driving_model.cpp",
        "../src/driving/bus_driving_model.cpp",
    ],
)

Default(target)
```

- [ ] **Step 6: Run tests to verify they fail before the model exists**

Run:

```bash
scons -C tests
```

Expected: FAIL with a missing include or missing source error for `driving/bus_driving_model.h` or `../src/driving/bus_driving_model.cpp`.

- [ ] **Step 7: Commit the failing tests and harness**

```bash
git add .gitignore README.md tests/test_harness.h tests/SConstruct tests/test_bus_driving_model.cpp
git commit -m "test: add bus driving model test harness"
```

## Task 2: Implement The Pure C++ Driving Model

**Files:**
- Create: `src/driving/bus_driving_model.h`
- Create: `src/driving/bus_driving_model.cpp`
- Modify: `tests/test_bus_driving_model.cpp`

- [ ] **Step 1: Create `src/driving/bus_driving_model.h`**

```cpp
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
    double acceleration = 4.5;
    double brake_force = 9.0;
    double drag = 1.2;
    double handbrake_drag = 7.0;
    double steering_speed = 1.8;
    double steering_return_speed = 3.0;
    double max_steering_angle = 0.45;
    double high_speed_steering_scale = 0.35;
    double turn_rate = 1.15;
};

struct BusDrivingFrame {
    double speed_mps = 0.0;
    double steering_radians = 0.0;
    double effective_steering = 0.0;
    double yaw_delta_radians = 0.0;
    double forward_distance_meters = 0.0;
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
```

- [ ] **Step 2: Create `src/driving/bus_driving_model.cpp`**

```cpp
#include "driving/bus_driving_model.h"

#include <algorithm>
#include <cmath>

namespace antlia::driving {

namespace {

constexpr double kInputMinimum = -1.0;
constexpr double kInputMaximum = 1.0;
constexpr double kMaximumPhysicsStep = 0.25;
constexpr double kReverseAccelerationScale = 0.6;

double abs_max(double value, double fallback) {
    return std::max(std::fabs(value), fallback);
}

} // namespace

BusDrivingFrame BusDrivingModel::step(const BusDrivingInput &input, const BusDrivingTuning &raw_tuning) {
    const BusDrivingTuning tuning = sanitized(raw_tuning);
    const double dt = clamp(input.delta_seconds, 0.0, kMaximumPhysicsStep);
    const double throttle = clamp(input.throttle, 0.0, 1.0);
    const double brake = clamp(input.brake, 0.0, 1.0);
    const double steer = clamp(input.steer, kInputMinimum, kInputMaximum);

    const double target_steering = steer * tuning.max_steering_angle;
    const double steering_rate = std::fabs(steer) > 0.001 ? tuning.steering_speed : tuning.steering_return_speed;
    steering_radians_ = move_toward(steering_radians_, target_steering, steering_rate * dt);

    if (throttle > 0.0) {
        speed_mps_ += tuning.acceleration * throttle * dt;
    }

    if (brake > 0.0) {
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
    return std::min(std::max(value, minimum), maximum);
}

double BusDrivingModel::move_toward(double current, double target, double amount) {
    const double safe_amount = std::max(amount, 0.0);
    if (current < target) {
        return std::min(current + safe_amount, target);
    }
    if (current > target) {
        return std::max(current - safe_amount, target);
    }
    return target;
}

BusDrivingTuning BusDrivingModel::sanitized(BusDrivingTuning tuning) {
    tuning.max_forward_speed = abs_max(tuning.max_forward_speed, 0.1);
    tuning.max_reverse_speed = abs_max(tuning.max_reverse_speed, 0.1);
    tuning.acceleration = abs_max(tuning.acceleration, 0.1);
    tuning.brake_force = abs_max(tuning.brake_force, 0.1);
    tuning.drag = std::max(tuning.drag, 0.0);
    tuning.handbrake_drag = std::max(tuning.handbrake_drag, 0.0);
    tuning.steering_speed = abs_max(tuning.steering_speed, 0.1);
    tuning.steering_return_speed = abs_max(tuning.steering_return_speed, 0.1);
    tuning.max_steering_angle = clamp(std::fabs(tuning.max_steering_angle), 0.01, 1.2);
    tuning.high_speed_steering_scale = clamp(tuning.high_speed_steering_scale, 0.05, 1.0);
    tuning.turn_rate = abs_max(tuning.turn_rate, 0.01);
    return tuning;
}

} // namespace antlia::driving
```

- [ ] **Step 3: Run model unit tests**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected: PASS with all nine test cases passing.

- [ ] **Step 4: Commit the pure C++ model**

```bash
git add src/driving/bus_driving_model.h src/driving/bus_driving_model.cpp tests/test_bus_driving_model.cpp
git commit -m "feat: add unit-tested bus driving model"
```

## Task 3: Add GDExtension Registration And Build Script

**Files:**
- Create: `SConstruct`
- Create: `antlia.gdextension`
- Create: `src/register_types.h`
- Create: `src/register_types.cpp`
- Create: `src/bus_controller_3d.h`
- Create: `src/bus_controller_3d.cpp`

- [ ] **Step 1: Add godot-cpp dependency**

Run:

```bash
git submodule add https://github.com/godotengine/godot-cpp.git godot-cpp
git submodule update --init --recursive
```

Expected: `godot-cpp/` exists and contains `SConstruct`, `include/`, and `gen/` after its own build step.

- [ ] **Step 2: Create root `SConstruct`**

```python
import os

env = SConscript("godot-cpp/SConstruct")

env.Append(CPPPATH=["src"])
env.Append(CXXFLAGS=["-std=c++17"])

sources = Glob("src/*.cpp") + Glob("src/driving/*.cpp")

platform = env["platform"]
target = env["target"]

suffix = env.get("suffix", "")
shared_suffix = env.get("SHLIBSUFFIX", "")

if platform == "macos":
    library_path = f"bin/libantlia.macos.{target}{shared_suffix}"
elif platform == "linux":
    arch = env.get("arch", "x86_64")
    library_path = f"bin/libantlia.linux.{target}.{arch}{shared_suffix}"
elif platform == "windows":
    arch = env.get("arch", "x86_64")
    library_path = f"bin/libantlia.windows.{target}.{arch}{shared_suffix}"
else:
    library_path = f"bin/libantlia.{platform}.{target}{suffix}{shared_suffix}"

library = env.SharedLibrary(library_path, source=sources)
Default(library)
```

- [ ] **Step 3: Create `antlia.gdextension`**

```ini
[configuration]

entry_symbol = "antlia_library_init"
compatibility_minimum = "4.2"

[libraries]

macos.debug = "res://bin/libantlia.macos.template_debug.dylib"
macos.release = "res://bin/libantlia.macos.template_release.dylib"
linux.debug.x86_64 = "res://bin/libantlia.linux.template_debug.x86_64.so"
linux.release.x86_64 = "res://bin/libantlia.linux.template_release.x86_64.so"
windows.debug.x86_64 = "res://bin/libantlia.windows.template_debug.x86_64.dll"
windows.release.x86_64 = "res://bin/libantlia.windows.template_release.x86_64.dll"
```

- [ ] **Step 4: Create `src/register_types.h`**

```cpp
#pragma once

#include <godot_cpp/core/class_db.hpp>

using namespace godot;

void initialize_antlia_module(ModuleInitializationLevel p_level);
void uninitialize_antlia_module(ModuleInitializationLevel p_level);
```

- [ ] **Step 5: Create temporary `src/bus_controller_3d.h`**

```cpp
#pragma once

#include <godot_cpp/classes/character_body3d.hpp>

namespace antlia::driving {
class BusDrivingModel;
struct BusDrivingTuning;
} // namespace antlia::driving

namespace godot {

class BusController3D : public CharacterBody3D {
    GDCLASS(BusController3D, CharacterBody3D)

protected:
    static void _bind_methods();

public:
    BusController3D();
};

} // namespace godot
```

- [ ] **Step 6: Create temporary `src/bus_controller_3d.cpp`**

```cpp
#include "bus_controller_3d.h"

namespace godot {

void BusController3D::_bind_methods() {
}

BusController3D::BusController3D() = default;

} // namespace godot
```

- [ ] **Step 7: Create `src/register_types.cpp`**

```cpp
#include "register_types.h"

#include "bus_controller_3d.h"

#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/godot.hpp>

using namespace godot;

void initialize_antlia_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }

    GDREGISTER_CLASS(BusController3D);
}

void uninitialize_antlia_module(ModuleInitializationLevel p_level) {
    if (p_level != MODULE_INITIALIZATION_LEVEL_SCENE) {
        return;
    }
}

extern "C" {

GDExtensionBool GDE_EXPORT antlia_library_init(
    GDExtensionInterfaceGetProcAddress p_get_proc_address,
    GDExtensionClassLibraryPtr p_library,
    GDExtensionInitialization *r_initialization) {
    GDExtensionBinding::InitObject init_obj(p_get_proc_address, p_library, r_initialization);

    init_obj.register_initializer(initialize_antlia_module);
    init_obj.register_terminator(uninitialize_antlia_module);
    init_obj.set_minimum_library_initialization_level(MODULE_INITIALIZATION_LEVEL_SCENE);

    return init_obj.init();
}

}
```

- [ ] **Step 8: Build the GDExtension skeleton**

Run on macOS:

```bash
scons platform=macos target=template_debug
```

Expected: PASS and a native library at `bin/libantlia.macos.template_debug.dylib`.

- [ ] **Step 9: Commit GDExtension registration**

```bash
git add SConstruct antlia.gdextension src/register_types.h src/register_types.cpp src/bus_controller_3d.h src/bus_controller_3d.cpp .gitmodules godot-cpp
git commit -m "feat: register bus controller gdextension"
```

## Task 4: Implement The Godot Bus Controller Adapter

**Files:**
- Modify: `src/bus_controller_3d.h`
- Modify: `src/bus_controller_3d.cpp`

- [ ] **Step 1: Replace `src/bus_controller_3d.h` with the full controller declaration**

```cpp
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
```

- [ ] **Step 2: Replace `src/bus_controller_3d.cpp` with the full adapter implementation**

```cpp
#include "bus_controller_3d.h"

#include <godot_cpp/classes/input.hpp>
#include <godot_cpp/core/class_db.hpp>

#include <algorithm>

namespace godot {

namespace {

constexpr double kMinimumPositiveTuning = 0.01;

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
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "max_forward_speed", PROPERTY_HINT_RANGE, "0.1,60.0,0.1,or_greater"), "set_max_forward_speed", "get_max_forward_speed");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "max_reverse_speed", PROPERTY_HINT_RANGE, "0.1,20.0,0.1,or_greater"), "set_max_reverse_speed", "get_max_reverse_speed");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "acceleration", PROPERTY_HINT_RANGE, "0.1,30.0,0.1,or_greater"), "set_acceleration", "get_acceleration");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "brake_force", PROPERTY_HINT_RANGE, "0.1,40.0,0.1,or_greater"), "set_brake_force", "get_brake_force");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "drag", PROPERTY_HINT_RANGE, "0.0,20.0,0.1,or_greater"), "set_drag", "get_drag");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "handbrake_drag", PROPERTY_HINT_RANGE, "0.0,40.0,0.1,or_greater"), "set_handbrake_drag", "get_handbrake_drag");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "steering_speed", PROPERTY_HINT_RANGE, "0.1,10.0,0.1,or_greater"), "set_steering_speed", "get_steering_speed");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "steering_return_speed", PROPERTY_HINT_RANGE, "0.1,10.0,0.1,or_greater"), "set_steering_return_speed", "get_steering_return_speed");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "max_steering_angle", PROPERTY_HINT_RANGE, "0.01,1.2,0.01"), "set_max_steering_angle", "get_max_steering_angle");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "high_speed_steering_scale", PROPERTY_HINT_RANGE, "0.05,1.0,0.01"), "set_high_speed_steering_scale", "get_high_speed_steering_scale");
    ADD_PROPERTY(PropertyInfo(Variant::FLOAT, "turn_rate", PROPERTY_HINT_RANGE, "0.01,5.0,0.01,or_greater"), "set_turn_rate", "get_turn_rate");
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

void BusController3D::set_max_forward_speed(double value) { tuning_.max_forward_speed = clamp_min(value, kMinimumPositiveTuning); }
double BusController3D::get_max_forward_speed() const { return tuning_.max_forward_speed; }

void BusController3D::set_max_reverse_speed(double value) { tuning_.max_reverse_speed = clamp_min(value, kMinimumPositiveTuning); }
double BusController3D::get_max_reverse_speed() const { return tuning_.max_reverse_speed; }

void BusController3D::set_acceleration(double value) { tuning_.acceleration = clamp_min(value, kMinimumPositiveTuning); }
double BusController3D::get_acceleration() const { return tuning_.acceleration; }

void BusController3D::set_brake_force(double value) { tuning_.brake_force = clamp_min(value, kMinimumPositiveTuning); }
double BusController3D::get_brake_force() const { return tuning_.brake_force; }

void BusController3D::set_drag(double value) { tuning_.drag = clamp_min(value, 0.0); }
double BusController3D::get_drag() const { return tuning_.drag; }

void BusController3D::set_handbrake_drag(double value) { tuning_.handbrake_drag = clamp_min(value, 0.0); }
double BusController3D::get_handbrake_drag() const { return tuning_.handbrake_drag; }

void BusController3D::set_steering_speed(double value) { tuning_.steering_speed = clamp_min(value, kMinimumPositiveTuning); }
double BusController3D::get_steering_speed() const { return tuning_.steering_speed; }

void BusController3D::set_steering_return_speed(double value) { tuning_.steering_return_speed = clamp_min(value, kMinimumPositiveTuning); }
double BusController3D::get_steering_return_speed() const { return tuning_.steering_return_speed; }

void BusController3D::set_max_steering_angle(double value) { tuning_.max_steering_angle = clamp_range(value, 0.01, 1.2); }
double BusController3D::get_max_steering_angle() const { return tuning_.max_steering_angle; }

void BusController3D::set_high_speed_steering_scale(double value) { tuning_.high_speed_steering_scale = clamp_range(value, 0.05, 1.0); }
double BusController3D::get_high_speed_steering_scale() const { return tuning_.high_speed_steering_scale; }

void BusController3D::set_turn_rate(double value) { tuning_.turn_rate = clamp_min(value, kMinimumPositiveTuning); }
double BusController3D::get_turn_rate() const { return tuning_.turn_rate; }

double BusController3D::get_current_speed() const {
    return model_.speed_mps();
}

double BusController3D::get_current_steering() const {
    return model_.steering_radians();
}

double BusController3D::clamp_min(double value, double minimum) {
    return std::max(value, minimum);
}

double BusController3D::clamp_range(double value, double minimum, double maximum) {
    return std::min(std::max(value, minimum), maximum);
}

bool BusController3D::is_action_pressed_safe(const StringName &action_name) const {
    const Input *input = Input::get_singleton();
    return input != nullptr && input->is_action_pressed(action_name);
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
```

- [ ] **Step 3: Build the GDExtension with the full controller**

Run:

```bash
scons platform=macos target=template_debug
```

Expected: PASS and `bin/libantlia.macos.template_debug.dylib` is updated.

- [ ] **Step 4: Re-run unit tests after adding Godot adapter**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected: PASS with all model tests still passing.

- [ ] **Step 5: Commit the bus controller adapter**

```bash
git add src/bus_controller_3d.h src/bus_controller_3d.cpp
git commit -m "feat: add godot bus controller adapter"
```

## Task 5: Add Godot Project Input Map And Demo Scene

**Files:**
- Create: `project.godot`
- Create: `scenes/demo_bus_test.tscn`

- [ ] **Step 1: Create `project.godot`**

```ini
; Engine configuration file.
; It's best edited using the editor UI and not directly,
; since the parameters that go here are not all obvious.
;
; Format:
;   [section] ; section goes between []
;   param=value ; assign values to parameters

config_version=5

[application]

config/name="Antlia Bus Driving Simulator"
run/main_scene="res://scenes/demo_bus_test.tscn"
config/features=PackedStringArray("4.2", "Forward Plus")

[input]

drive_accelerate={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":87,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null), Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":4194320,"physical_keycode":0,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null)]
}
drive_brake={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":83,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null), Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":4194322,"physical_keycode":0,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null)]
}
drive_steer_left={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":65,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null), Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":4194319,"physical_keycode":0,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null)]
}
drive_steer_right={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":68,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null), Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":4194321,"physical_keycode":0,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null)]
}
drive_handbrake={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":32,"physical_keycode":0,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null)]
}
drive_reset={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":82,"key_label":0,"unicode":0,"location":0,"echo":false,"script":null)]
}
```

- [ ] **Step 2: Create `scenes/demo_bus_test.tscn`**

```ini
[gd_scene load_steps=8 format=3]

[ext_resource type="GDExtension" path="res://antlia.gdextension" id="1_antlia"]

[sub_resource type="BoxShape3D" id="BoxShape3D_bus_collision"]
size = Vector3(2.6, 2.4, 8)

[sub_resource type="BoxMesh" id="BoxMesh_bus"]
size = Vector3(2.6, 2.4, 8)

[sub_resource type="StandardMaterial3D" id="StandardMaterial3D_bus"]
albedo_color = Color(0.94, 0.74, 0.16, 1)

[sub_resource type="BoxShape3D" id="BoxShape3D_ground_collision"]
size = Vector3(120, 1, 120)

[sub_resource type="PlaneMesh" id="PlaneMesh_ground"]
size = Vector2(120, 120)

[sub_resource type="StandardMaterial3D" id="StandardMaterial3D_ground"]
albedo_color = Color(0.18, 0.18, 0.18, 1)

[node name="DemoBusTest" type="Node3D"]

[node name="Bus" type="BusController3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.3, 0)
max_forward_speed = 16.0
max_reverse_speed = 4.0
acceleration = 4.2
brake_force = 9.5
drag = 1.1
handbrake_drag = 8.0
steering_speed = 1.7
steering_return_speed = 3.4
max_steering_angle = 0.44
high_speed_steering_scale = 0.32
turn_rate = 1.12

[node name="CollisionShape3D" type="CollisionShape3D" parent="Bus"]
shape = SubResource("BoxShape3D_bus_collision")

[node name="BusMesh" type="MeshInstance3D" parent="Bus"]
mesh = SubResource("BoxMesh_bus")
surface_material_override/0 = SubResource("StandardMaterial3D_bus")

[node name="Camera3D" type="Camera3D" parent="Bus"]
transform = Transform3D(1, 0, 0, 0, 0.965926, 0.258819, 0, -0.258819, 0.965926, 0, 5.4, 11)
current = true
fov = 70.0

[node name="Ground" type="StaticBody3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, -0.55, 0)

[node name="GroundCollision" type="CollisionShape3D" parent="Ground"]
shape = SubResource("BoxShape3D_ground_collision")

[node name="GroundMesh" type="MeshInstance3D" parent="Ground"]
mesh = SubResource("PlaneMesh_ground")
surface_material_override/0 = SubResource("StandardMaterial3D_ground")

[node name="DirectionalLight3D" type="DirectionalLight3D" parent="."]
transform = Transform3D(0.707107, -0.353553, 0.612372, 0, 0.866025, 0.5, -0.707107, -0.353553, 0.612372, 0, 8, 0)
light_energy = 2.0
shadow_enabled = true

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
```

- [ ] **Step 3: Build extension before opening the scene**

Run:

```bash
scons platform=macos target=template_debug
```

Expected: PASS and `bin/libantlia.macos.template_debug.dylib` exists.

- [ ] **Step 4: Open the project in Godot 4**

Run:

```bash
godot4 --path .
```

Expected: Godot opens Antlia and loads the project without missing-script errors. If the executable is named `godot` locally, run `godot --path .` instead.

- [ ] **Step 5: Run the demo scene manually**

In Godot, run `res://scenes/demo_bus_test.tscn`.

Expected:

- `W` accelerates the bus forward.
- `S` brakes and then reverses.
- `A` and `D` steer.
- `Space` slows the bus more aggressively.
- `R` resets the bus to the spawn transform.
- The bus collides with the ground instead of falling through.

- [ ] **Step 6: Commit the Godot project and demo scene**

```bash
git add project.godot scenes/demo_bus_test.tscn
git commit -m "feat: add runnable bus driving demo scene"
```

## Task 6: Final Documentation And Verification Pass

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-05-10-bus-driving-simulator-design.md`

- [ ] **Step 1: Replace `README.md` with final setup details**

```markdown
# Antlia Bus Driving Simulator

Antlia is a Godot 4 bus driving simulator prototype built with C++ GDExtension.

## Current Prototype

The first playable slice includes:

- A `BusDrivingModel` pure C++ driving model.
- Unit tests for driving math.
- A `BusController3D` Godot C++ class.
- A runnable demo scene at `res://scenes/demo_bus_test.tscn`.
- A placeholder bus, road plane, collision, chase camera, and lighting.

This slice intentionally does not include traffic, passengers, routes, cockpit UI, save files, or wheel/suspension simulation.

## Dependencies

- Godot 4.2 or newer.
- SCons.
- A C++17 compiler.
- `godot-cpp` checked out at `godot-cpp/`.

Fetch the C++ bindings:

```bash
git submodule update --init --recursive
```

If `godot-cpp` has not been added yet:

```bash
git submodule add https://github.com/godotengine/godot-cpp.git godot-cpp
git submodule update --init --recursive
```

## Unit Tests

```bash
scons -C tests
./tests/bin/test_bus_driving_model
```

Expected result:

```text
9 passed, 0 failed
```

## Build The GDExtension

On macOS:

```bash
scons platform=macos target=template_debug
```

Expected output:

```text
bin/libantlia.macos.template_debug.dylib
```

On Linux:

```bash
scons platform=linux target=template_debug
```

On Windows:

```bash
scons platform=windows target=template_debug
```

## Run The Demo

Open this folder in Godot 4 and run:

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

## Tuning

Select the `Bus` node in the demo scene and adjust the `Driving` inspector properties:

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
```

- [ ] **Step 2: Verify the spec acceptance criteria**

Run:

```bash
scons -C tests
./tests/bin/test_bus_driving_model
scons platform=macos target=template_debug
git status --short
```

Expected:

- Unit tests report `9 passed, 0 failed`.
- GDExtension build succeeds.
- `git status --short` only shows expected uncommitted README/spec updates before the next commit.

- [ ] **Step 3: Update the spec only if reality differs from the approved design**

If implementation used the local test harness instead of the preferred doctest runner, update the Unit Testing section in `docs/superpowers/specs/2026-05-10-bus-driving-simulator-design.md` to say:

```markdown
Use a lightweight C++ test runner for the pure driving model. The first scaffold uses a tiny local test harness to avoid adding a second external dependency before the Godot C++ binding is stable.
```

Do not change the approved scope, architecture, or acceptance criteria.

- [ ] **Step 4: Commit final docs**

```bash
git add README.md docs/superpowers/specs/2026-05-10-bus-driving-simulator-design.md
git commit -m "docs: document bus driving scaffold"
```

## Self-Review

Spec coverage:

- Godot 4 project files: Task 5.
- C++ GDExtension scaffold: Task 3 and Task 4.
- Runnable demo scene: Task 5.
- Placeholder bus, road, camera, collision, lighting: Task 5.
- Input actions and default keys: Task 5.
- Reusable bus controller node: Task 4.
- Pure C++ driving model: Task 2.
- Unit tests: Task 1 and Task 2.
- Build and run documentation: Task 1 and Task 6.
- Error handling for missing input/reset/tuning: Task 2 and Task 4.

Placeholder scan:

- No unresolved placeholder requirements remain in this plan.

Type consistency:

- `BusDrivingInput`, `BusDrivingTuning`, `BusDrivingFrame`, and `BusDrivingModel` are introduced before use.
- `BusController3D` property names match the approved spec and demo scene.
- Test method calls match the `BusDrivingModel` public API.
