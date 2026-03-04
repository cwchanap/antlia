# Data Model: Bus Driving Simulator MVP

## Overview

The MVP does not require persistent storage but still has clear runtime entities used for gameplay logic. These can later map to saved data if needed.

## Entities

### Bus
- **Description**: The controllable vehicle driven by the player.
- **Key properties**:
  - `id`: internal identifier
  - `position`: current world position
  - `rotation`: current orientation
  - `velocity`: current linear velocity
  - `steeringAngle`: current steering wheel angle
  - `accelerationInput`: current throttle input
  - `brakeInput`: current brake input

### Track
- **Description**: A simple closed test route.
- **Key properties**:
  - `id`: identifier for the track
  - `path`: curve or set of waypoints defining the route
  - `lapStartTrigger`: area or marker used to detect lap start/finish
  - `roadBounds`: geometry/areas used to detect off-road events

### LapSession
- **Description**: A single attempt at driving a lap on the test route.
- **Key properties**:
  - `id`: internal identifier
  - `startTime`: timestamp when the lap starts
  - `endTime`: timestamp when the lap ends
  - `lapTime`: computed duration (`endTime - startTime`)
  - `offRoadCount`: number of detected off-road events during the lap
  - `collisionCount`: number of collisions during the lap
  - `isCompleted`: whether the player crossed the finish trigger after a valid start

### LapSummary
- **Description**: Data object passed to the summary UI at end of lap.
- **Key properties**:
  - `lapTime`: final lap time
  - `offRoadCount`: final off-road event count
  - `collisionCount`: final collision count

## Relationships

- A **LapSession** is associated with exactly one **Bus** and one **Track** while active.
- A **LapSummary** is derived from a completed **LapSession**.

## State & Transitions (LapSession)

- **States**:
  - `Idle` → no active lap.
  - `Running` → timer is active, tracking events.
  - `Completed` → lap finished successfully.
  - `Cancelled` → lap aborted (e.g., player quits or restarts).
- **Transitions**:
  - `Idle` → `Running` when the player crosses the start trigger.
  - `Running` → `Completed` when the player crosses the finish trigger after at least one valid start.
  - `Running` → `Cancelled` when the player restarts or exits before completion.
