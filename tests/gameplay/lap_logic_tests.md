# Lap Logic Tests

## Purpose
Document expected lap timing and penalty behaviors for the Bus Driving Simulator MVP.

## Test Scenarios

### 1. Lap Timing Tests

#### TC-LAP-001: Start Lap
- **Given**: Player's bus is at the start position
- **When**: Bus crosses the start/finish trigger area
- **Then**: 
  - Lap timer starts
  - LapSession state changes to Running
  - StartTime is recorded
  - LapStarted signal is emitted

#### TC-LAP-002: Complete Valid Lap
- **Given**: Lap is in Running state
- **When**: Bus crosses the finish trigger after completing at least one circuit
- **Then**:
  - Lap timer stops
  - EndTime is recorded
  - LapTime is calculated (EndTime - StartTime)
  - LapSession state changes to Completed
  - IsCompleted flag is set to true
  - LapCompleted signal is emitted with LapSummary

#### TC-LAP-003: Invalid Lap Start (Already Running)
- **Given**: A lap is already in Running state
- **When**: Attempt to start another lap
- **Then**:
  - New lap start is rejected
  - Error message is logged
  - Current lap continues unchanged

#### TC-LAP-004: Complete Lap Without Start
- **Given**: No lap is in Running state
- **When**: Attempt to complete a lap
- **Then**:
  - Complete request is rejected
  - Error message is logged

#### TC-LAP-005: Cancel Running Lap
- **Given**: Lap is in Running state
- **When**: Player quits or restarts before completing
- **Then**:
  - LapSession state changes to Cancelled
  - Lap is not marked as completed
  - No LapCompleted signal is emitted

### 2. Penalty Counting Tests

#### TC-PEN-001: Record Off-Road Event
- **Given**: Lap is in Running state
- **When**: Bus leaves road boundary colliders
- **Then**:
  - OffRoadCount increments by 1
  - OffRoadEvent signal is emitted with current count

#### TC-PEN-002: Multiple Off-Road Events
- **Given**: Lap is in Running state with OffRoadCount = 2
- **When**: Bus leaves road boundary again
- **Then**:
  - OffRoadCount increments to 3
  - Separate events are counted individually

#### TC-PEN-003: Off-Road Before Lap Start
- **Given**: No lap is in Running state
- **When**: Attempt to record off-road event
- **Then**:
  - Off-road event is ignored (not counted)
  - No signal is emitted

#### TC-PEN-004: Record Collision
- **Given**: Lap is in Running state
- **When**: Bus collides with obstacle or track-side object
- **Then**:
  - CollisionCount increments by 1
  - CollisionEvent signal is emitted with current count

#### TC-PEN-005: Multiple Collisions
- **Given**: Lap is in Running state with CollisionCount = 1
- **When**: Bus collides with another obstacle
- **Then**:
  - CollisionCount increments to 2
  - Each collision is counted separately

#### TC-PEN-006: Collision Before Lap Start
- **Given**: No lap is in Running state
- **When**: Attempt to record collision
- **Then**:
  - Collision is ignored (not counted)
  - No signal is emitted

### 3. Lap Summary Tests

#### TC-SUM-001: Generate Lap Summary
- **Given**: Completed lap with:
  - LapTime = 65.5 seconds
  - OffRoadCount = 3
  - CollisionCount = 1
- **When**: LapSummary.FromSession() is called
- **Then**:
  - Summary contains correct LapTime (65.5)
  - Summary contains correct OffRoadCount (3)
  - Summary contains correct CollisionCount (1)

#### TC-SUM-002: Summary from Incomplete Lap
- **Given**: Lap in Running state (not completed)
- **When**: Attempt to create LapSummary
- **Then**:
  - InvalidOperationException is thrown
  - Error message indicates lap is incomplete

#### TC-SUM-003: Summary from Cancelled Lap
- **Given**: Lap in Cancelled state
- **When**: Attempt to create LapSummary
- **Then**:
  - InvalidOperationException is thrown
  - Error message indicates lap is incomplete

### 4. State Transition Tests

#### TC-STATE-001: Idle to Running
- **Given**: LapSession in Idle state
- **When**: StartLap() is called
- **Then**: State transitions to Running

#### TC-STATE-002: Running to Completed
- **Given**: LapSession in Running state
- **When**: CompleteLap() is called
- **Then**: State transitions to Completed

#### TC-STATE-003: Running to Cancelled
- **Given**: LapSession in Running state
- **When**: CancelLap() is called
- **Then**: State transitions to Cancelled

#### TC-STATE-004: Reset to Idle
- **Given**: LapSession in any state
- **When**: Reset() is called
- **Then**:
  - Current session is cleared
  - Manager returns to initial state

## Automated Test Coverage

Tests to be implemented in `tests/gameplay/LapManagerTests.cs`:
- All lap timing scenarios (TC-LAP-001 through TC-LAP-005)
- All penalty counting scenarios (TC-PEN-001 through TC-PEN-006)
- All lap summary scenarios (TC-SUM-001 through TC-SUM-003)
- All state transition scenarios (TC-STATE-001 through TC-STATE-004)

## Manual Testing Requirements

The following require manual playtesting in the running game:
- Visual verification of lap timer display
- Off-road detection accuracy (timing and boundary precision)
- Collision detection accuracy (which objects trigger collision count)
- UI display of lap summary data
- Overall feel and responsiveness of timing system

## Performance Targets

- Lap timer precision: ±0.01 seconds
- Penalty detection latency: <50ms from event to count update
- Summary generation: <10ms

## Edge Cases to Test

1. **Very Short Lap**: Complete lap in <1 second (should still count)
2. **Very Long Lap**: Run lap for >10 minutes (no timer overflow)
3. **High Penalty Count**: Accumulate 100+ off-road events or collisions
4. **Rapid State Changes**: Start/cancel/start lap in quick succession
5. **Concurrent Events**: Off-road and collision happen simultaneously
