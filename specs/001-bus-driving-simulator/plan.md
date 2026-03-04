# Implementation Plan: Bus Driving Simulator MVP

**Branch**: `001-bus-driving-simulator` | **Date**: 2025-11-15 | **Spec**: `specs/001-bus-driving-simulator/spec.md`
**Input**: Feature specification from `specs/001-bus-driving-simulator/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a minimal 3D bus driving experience in Godot with C#, focused on a single bus driving a simple closed test route from a third-person chase camera on desktop PC using keyboard controls. The MVP prioritizes semi-realistic bus handling (weighty, slower acceleration, longer braking distance but forgiving) and clear lap feedback (lap time plus counts of off-road events and collisions) over content breadth.

## Technical Context

**Language/Version**: C# with Godot 4.x (e.g., 4.2)  
**Primary Dependencies**: Godot engine (3D), built-in physics and input systems; no external backend services for MVP  
**Storage**: N/A for MVP (no persistent save data required beyond in-memory lap stats)  
**Testing**: Manual playtesting plus lightweight C# unit tests using NUnit for lap/time/penalty logic  
**Target Platform**: Desktop PC (Windows/macOS) with keyboard input only (WASD/arrow keys)  
**Project Type**: single desktop game project (Godot)  
**Performance Goals**: Stable 60 fps on a mid-range desktop PC for the test track scene  
**Constraints**: Offline-capable; no networking; keep asset and code complexity low to enable rapid iteration  
**Scale/Scope**: Single bus, one simple closed test route, one primary gameplay mode (timed lap with basic penalties)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Current constitution file contains only placeholders; no concrete project-wide technology or process constraints are defined yet.  
- This plan follows general simplicity and testability principles by:  
  - Keeping scope to a single Godot game project with one primary gameplay loop.  
  - Planning for at least basic automated tests around lap timing/penalties plus manual playtesting.  
- No known constitution principles are violated by this MVP plan; treat this gate as **provisionally passed** until the constitution is fully authored.

## Project Structure

### Documentation (this feature)

```text
specs/001-bus-driving-simulator/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command; no external API expected for MVP)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
antlia/ (repository root)
├── project.godot          # Godot project file
├── BusDrivingSimulator.csproj
├── BusDrivingSimulator.sln
├── assets/                # Models, textures, audio
├── scenes/
│   ├── main_menu.tscn     # Optional simple menu
│   ├── test_track.tscn    # Closed test route scene
│   └── bus.tscn           # Bus scene (mesh + scripts)
├── scripts/
│   ├── BusController.cs   # Bus movement & physics
│   ├── CameraFollow.cs    # Third-person chase camera
│   └── LapManager.cs      # Lap timing and penalties
├── ui/
│   └── LapSummary.tscn    # End-of-lap summary UI
└── tests/
    └── gameplay/
        └── lap_logic_tests.md # Describes manual/automated tests for lap timing & penalties
```

**Structure Decision**: Single Godot desktop game project at repository root with feature-specific documentation and planning artifacts kept in `specs/001-bus-driving-simulator/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
