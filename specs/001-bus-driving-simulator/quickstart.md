# Quickstart: Bus Driving Simulator MVP

## Prerequisites

- Install **Godot 4.x** with C# support (e.g., 4.2 or later).
- Install a recent **.NET SDK** compatible with Godot C#.

## Project layout

```text
antlia/ (repository root)
├── project.godot
├── scenes/
│   ├── test_track.tscn
│   └── bus.tscn
├── scripts/
│   ├── BusController.cs
│   ├── CameraFollow.cs
│   └── LapManager.cs
└── ui/
    └── LapSummary.tscn
```

## Running the game

1. Open **Godot 4.x** (version 4.2 or later with C# support).
2. Choose **Import/Scan** and point to the repository root directory.
3. Select `project.godot` to import the project.
4. The project is pre-configured with `test_track.tscn` as the main scene.
5. Press **F5** (Run) to start the test route scene.
6. The game will open with the bus positioned at the start line.

## Building (Optional)

To build the C# project separately:
```bash
dotnet build BusDrivingSimulator.csproj
```

To run tests:
```bash
cd tests/gameplay
dotnet test
```

## Controls

- **W / Up Arrow**: Accelerate forward
- **S / Down Arrow**: Brake / Reverse
- **A / Left Arrow**: Steer left
- **D / Right Arrow**: Steer right
- **Esc**: Pause (native Godot pause)

## Gameplay Loop

1. **Start**: Drive the bus forward through the start/finish line to begin timing your lap.
2. **Drive**: Navigate the closed test route using keyboard controls.
   - Stay on the road to avoid off-road penalties
   - Avoid obstacles to prevent collision penalties
3. **Complete**: Cross the start/finish line again to complete your lap.
4. **Results**: The Lap Summary UI displays:
   - Total lap time (in seconds)
   - Number of off-road events
   - Number of collisions
5. **Restart**: Click "Restart Lap" to try again or "Quit" to exit.

## Track Layout

The test track is a simple rectangular closed circuit with:
- **Road surface**: Gray road segments forming a complete loop
- **Road boundaries**: Inner and outer walls (red) defining track limits
- **Off-road zones**: Areas outside the walls that trigger penalties
- **Obstacles**: Two obstacles (green boxes) that count as collisions
- **Start/Finish**: Positioned at the south end of the track

## Physics & Handling

The bus features semi-realistic handling:
- **Acceleration**: Gradual acceleration up to ~108 km/h (~30 m/s)
- **Braking**: Longer stopping distance than normal vehicles
- **Steering**: Speed-dependent steering (tighter at low speeds)
- **Weight**: 5000kg mass with realistic momentum
- **Stability**: Limited roll/pitch to prevent flipping

## Tips

- Start with gentle inputs to feel the bus weight and momentum
- Brake early before corners due to longer stopping distance
- Avoid hitting obstacles - each collision is counted
- Stay on the road - leaving track boundaries counts as off-road
- Complete a clean lap (0 penalties) for the best result

## Troubleshooting

**Bus won't move**: Ensure you've pressed W or Up Arrow to accelerate.

**Camera not following**: The camera should automatically follow the bus. Check that Camera3D is set to "current" in the scene.

**No lap summary**: Make sure you crossed the start line first, then completed a full lap by crossing it again.

**Performance issues**: The game targets 60 fps on mid-range hardware. Try reducing MSAA in project settings if needed.
