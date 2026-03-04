# Tasks: Bus Driving Simulator MVP

**Input**: Design documents from `specs/001-bus-driving-simulator/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/`

**Tests**: This feature includes targeted test tasks for lap timing and penalty logic using NUnit.

**Organization**: Tasks are grouped by phase and user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., [US1])
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the Godot 4 C# project and basic structure.

- [X] T001 Create Godot 4 project in `game/project.godot` per implementation plan
- [X] T002 [P] Create `assets/`, `scenes/`, `scripts/`, `ui/`, and `tests/gameplay/` directories under `game/`
- [X] T003 [P] Add Godot 4 and .NET build artifacts to `.gitignore` at `.gitignore`
- [X] T004 Enable C# support in `game/project.godot` and verify the project builds with the installed .NET SDK
- [X] T005 Initialize NUnit test assembly for gameplay logic in `tests/gameplay/` (project file and initial test project structure)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before User Story 1 implementation.

- [X] T006 Create `LapSession` and `LapSummary` data types in `game/scripts/LapManager.cs` according to `data-model.md`
- [X] T007 [P] Configure physics layers and masks for bus, track, road boundaries, and obstacles in `game/project.godot`
- [X] T008 [P] Create base `game/scenes/test_track.tscn` scene with ground plane and world environment
- [X] T009 [P] Create base `game/scenes/bus.tscn` scene with a root node and placeholder bus mesh
- [X] T010 Create `tests/gameplay/lap_logic_tests.md` documenting expected lap timing and penalty behaviors for the MVP

**Checkpoint**: Foundation ready – User Story 1 implementation can now begin.

---

## Phase 3: User Story 1 – Drive bus on test route (Priority: P1) 🎯 MVP

**Goal**: Allow the player to drive a single bus around a simple closed test route with semi-realistic handling from a third-person chase camera using keyboard controls.

**Independent Test**: Player can complete one full lap of the test route without leaving the road, with lap time, off-road count, and collision count shown in an end-of-lap summary.

### Tests for User Story 1

- [X] T011 [P] [US1] Add NUnit test fixture `LapManagerTests` in `tests/gameplay/LapManagerTests.cs` to verify lap time and penalty counts for simulated events

### Implementation for User Story 1

- [X] T012 [P] [US1] Implement `BusController.cs` in `game/scripts/BusController.cs` to read keyboard input (WASD/arrow keys) and apply semi-realistic acceleration, braking, and steering forces
- [X] T013 [P] [US1] Add rigid body, collision shapes, and `BusController` script to `game/scenes/bus.tscn` so the bus moves and collides correctly
- [X] T014 [P] [US1] Layout `game/scenes/test_track.tscn` as a closed route with road mesh/segments and colliders defining road boundaries
- [X] T015 [P] [US1] Implement `CameraFollow.cs` in `game/scripts/CameraFollow.cs` to follow the bus from a third-person chase position with basic smoothing
- [X] T016 [US1] Attach a Camera3D node with `CameraFollow` script in `game/scenes/test_track.tscn` and link it to the bus instance
- [X] T017 [US1] Implement `LapManager.cs` in `game/scripts/LapManager.cs` to manage `LapSession` state, start/end times, and counters for off-road events and collisions
- [X] T018 [US1] Add start/finish trigger Areas in `game/scenes/test_track.tscn` and connect signals to `LapManager` to start and complete a lap
- [X] T019 [US1] Implement off-road detection in `game/scripts/LapManager.cs` by monitoring when the bus leaves road boundary colliders and increment `offRoadCount`
- [X] T020 [US1] Implement collision counting in `game/scripts/BusController.cs` (or `LapManager.cs`) to increment `collisionCount` when colliding with obstacles or track-side objects
- [X] T021 [US1] Create `game/ui/LapSummary.tscn` UI to display lap time, off-road count, and collision count, and wire it to `LapManager` so it appears when a lap completes

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Improve feel and clarity across User Story 1.

- [X] T022 [P] Tune physics parameters in `game/scripts/BusController.cs` (acceleration, braking force, steering sensitivity) to achieve the agreed semi-realistic but forgiving handling
- [X] T023 [P] Refine camera offsets and smoothing in `game/scripts/CameraFollow.cs` to keep the bus and upcoming road clearly visible at all times
- [X] T024 Add minimal audio/visual feedback assets in `game/assets/` (e.g., basic engine sound and off-road feedback) without expanding MVP scope
- [X] T025 Update `specs/001-bus-driving-simulator/quickstart.md` with any final control tweaks and instructions for running and testing the MVP

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 – Setup**: No dependencies – start immediately.
- **Phase 2 – Foundational**: Depends on Phase 1; blocks all User Story work.
- **Phase 3 – User Story 1 (P1)**: Depends on Phase 2 completion.
- **Phase 4 – Polish**: Depends on Phase 3 being functionally complete.

### User Story Dependencies

- **User Story 1 (P1)**:
  - Can start after Phase 2 foundational tasks (T006–T010) are complete.
  - Does not depend on any other user stories.

### Within User Story 1

- T011 (tests) should be created before or alongside implementation tasks that touch `LapManager`.
- T012–T015 (bus movement and camera) can largely proceed in parallel after foundational scenes exist.
- T016–T021 depend on the bus and track scenes and scripts being present.

### Parallel Opportunities

- Setup tasks T002–T005 can run in parallel once T001 is done.
- Foundational tasks T007–T009 can run in parallel after T006 is defined.
- In User Story 1, T012–T015 can run in parallel (different files), followed by wiring tasks T016–T021.
- Polish tasks T022–T024 can run in parallel, with T025 last to update documentation.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete **Phase 1: Setup** (T001–T005).
2. Complete **Phase 2: Foundational** (T006–T010).
3. Implement **Phase 3: User Story 1** (T011–T021) until the lap is fully playable and summarized.
4. Run through the independent test for User Story 1:
   - Player can complete a full lap without leaving the road.
   - Lap summary shows lap time, off-road count, and collision count.
5. Apply **Phase 4: Polish** (T022–T025) as time permits.

### Incremental Delivery

- After Phase 2, you can deliver an internal prototype with basic movement and track (partial US1).
- After Phase 3, you have a complete MVP slice ready for user feedback.
- Phase 4 improves feel and presentation without changing core behavior.
