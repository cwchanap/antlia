# Bus Driving Simulator MVP

A minimal 3D bus driving simulator built with Godot 4 and C#, featuring semi-realistic bus handling and lap timing on a test track.

## Features

- **Realistic Bus Physics**: 5000kg bus with semi-realistic acceleration, braking, and steering
- **Lap Timing System**: Track lap times with precision timing
- **Penalty System**: Counts off-road events and collisions
- **Third-Person Camera**: Smooth chase camera with look-ahead
- **Lap Summary UI**: End-of-lap results showing time and penalties

## Requirements

- **Godot 4.2+** with C# support
- **.NET 7.0 SDK** or later
- Desktop PC (Windows/macOS/Linux)
- Keyboard for controls

## Getting Started

### Opening the Project

1. Install Godot 4.2 or later with .NET support
2. Open Godot and select "Import"
3. Navigate to the repository root and select `project.godot`
4. Press F5 to run the game

### Controls

- **W / ↑**: Accelerate
- **S / ↓**: Brake / Reverse
- **A / ←**: Steer Left
- **D / →**: Steer Right
- **ESC**: Pause

### Gameplay

1. Drive forward through the start/finish line to begin timing
2. Complete a lap around the closed test track
3. Avoid going off-road and hitting obstacles
4. Cross the finish line to see your lap summary

## Project Structure

```
antlia/
├── project.godot           # Godot project configuration
├── BusDrivingSimulator.csproj
├── BusDrivingSimulator.sln
├── scenes/                 # Scene files (.tscn)
│   ├── test_track.tscn    # Main test track scene
│   └── bus.tscn           # Bus prefab
├── scripts/                # C# gameplay scripts
│   ├── BusController.cs
│   ├── CameraFollow.cs
│   └── LapManager.cs
├── ui/                     # User interface
│   └── LapSummary.tscn
├── assets/                 # Game assets
├── tests/                  # Unit tests
│   └── gameplay/
│       ├── LapManagerTests.cs
│       └── lap_logic_tests.md
└── specs/                  # Feature specifications
    └── 001-bus-driving-simulator/
        ├── spec.md
        ├── plan.md
        ├── tasks.md
        └── quickstart.md
```

## Development

### Building

```bash
dotnet build BusDrivingSimulator.csproj
```

### Running Tests

```bash
cd tests/gameplay
dotnet test
```

### Physics Parameters

The bus handling can be tuned in `BusController.cs`:
- `MaxEngineForce`: Maximum acceleration force (default: 8000)
- `MaxBrakeForce`: Maximum braking force (default: 12000)
- `MaxSteeringAngle`: Maximum steering angle in degrees (default: 30)
- `SteeringSpeed`: Steering responsiveness (default: 2.0)

## Implementation Notes

### Technical Stack

- **Engine**: Godot 4.2 (Forward+ renderer)
- **Language**: C# (.NET 7.0)
- **Physics**: Godot 3D physics with RigidBody3D
- **Testing**: NUnit 3.14

### Architecture

- **BusController**: Handles player input and physics forces
- **LapManager**: Manages lap state, timing, and penalties
- **CameraFollow**: Third-person camera with smooth tracking
- **LapSummaryUI**: Displays lap results

### Physics Layers

1. **Layer 1**: Bus
2. **Layer 2**: Track/Road
3. **Layer 3**: Road Boundaries
4. **Layer 4**: Obstacles
5. **Layer 5**: Triggers (Start/Finish, Off-Road)

## Known Limitations (MVP Scope)

- Single bus and single track only
- No persistence or save system
- No audio (structure in place for future)
- Placeholder box meshes (no detailed 3D models)
- No networking or multiplayer
- No schedules, passengers, or routes

## Future Enhancements

See `specs/001-bus-driving-simulator/spec.md` for planned features beyond MVP.

## License

[Add license information here]

## Documentation

Full documentation available in `specs/001-bus-driving-simulator/`:
- `spec.md`: Feature specification
- `plan.md`: Technical implementation plan
- `tasks.md`: Task breakdown and execution order
- `quickstart.md`: Detailed setup and usage guide
