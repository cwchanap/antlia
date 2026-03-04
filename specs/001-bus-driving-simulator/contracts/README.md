# Contracts: Bus Driving Simulator MVP

The MVP bus driving simulator is an **offline single-player desktop game**. There are **no external HTTP APIs or network services** in scope for this feature.

Instead of external contracts, the primary "contracts" are internal scene/script interfaces in the Godot project, for example:

- `BusController` exposes methods/properties to control bus movement.
- `LapManager` exposes events or signals for lap start/end and penalty updates.
- `LapSummary` UI expects a data object containing `lapTime`, `offRoadCount`, and `collisionCount`.

If future features introduce online leaderboards or telemetry, this directory can be extended with HTTP API specs (e.g., OpenAPI documents).
