# Research: Bus Driving Simulator MVP

## Godot version for 3D C# MVP

- **Decision**: Use Godot 4.x with C# (e.g., 4.2).
- **Rationale**: Godot 4.x provides improved 3D rendering and physics, a more modern editor, and is the recommended choice for new 3D projects. C# support is sufficiently mature for gameplay scripting, and aligns with the feature requirement to use C#.
- **Alternatives considered**:
  - **Godot 3.x with Mono**: More battle-tested, but older rendering/physics stack and a less future-proof choice for a new project.
  - **Non-C# languages in Godot (GDScript)**: Simpler integration, but conflicts with the explicit requirement to use C#.

## Testing harness for lap and penalty logic

- **Decision**: Use NUnit-based C# unit tests for lap timing and penalty calculation logic, alongside manual playtesting for feel and UX.
- **Rationale**: NUnit is a well-known, lightweight C# testing framework that can validate pure logic (timers, counters, thresholds) outside of the Godot runtime. It reduces regression risk for scoring and feedback while leaving physics and input feel to manual playtesting.
- **Alternatives considered**:
  - **Godot-specific test tooling only**: Ties tests more closely to engine scenes but makes it harder to run fast, isolated logic tests.
  - **No automated tests**: Faster to start but risks regressions in lap timing and scoring as the project evolves.

## Scope confirmation for MVP

- **Decision**: Keep the MVP to a single bus, one closed test route, and a single gameplay mode (timed lap with basic penalties) with no networking or persistence.
- **Rationale**: This aligns with the clarified spec and keeps the scope tight enough to reach a playable prototype quickly while still testing key feel and UX.
- **Alternatives considered**:
  - **Multiple routes or buses**: Adds content overhead without directly improving the core feel prototype.
  - **Persistence of stats/leaderboards**: Useful later, but out of scope for a first driving-feel MVP.
