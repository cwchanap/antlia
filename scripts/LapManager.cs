using Godot;
using System;

namespace BusDrivingSimulator;

/// <summary>
/// Represents a single attempt at driving a lap on the test route.
/// Tracks timing and penalties during the lap.
/// </summary>
public class LapSession
{
    /// <summary>
    /// Internal identifier for this lap session.
    /// </summary>
    public string Id { get; set; } = Guid.NewGuid().ToString();

    /// <summary>
    /// Timestamp when the lap starts (in seconds since game start).
    /// </summary>
    public double StartTime { get; set; }

    /// <summary>
    /// Timestamp when the lap ends (in seconds since game start).
    /// </summary>
    public double? EndTime { get; set; }

    /// <summary>
    /// Computed lap duration in seconds (EndTime - StartTime).
    /// Returns null if lap is not yet completed.
    /// </summary>
    public double? LapTime => EndTime.HasValue ? EndTime.Value - StartTime : null;

    /// <summary>
    /// Number of detected off-road events during the lap.
    /// </summary>
    public int OffRoadCount { get; set; }

    /// <summary>
    /// Number of collisions during the lap.
    /// </summary>
    public int CollisionCount { get; set; }

    /// <summary>
    /// Whether the player crossed the finish trigger after a valid start.
    /// </summary>
    public bool IsCompleted { get; set; }

    /// <summary>
    /// Current state of the lap session.
    /// </summary>
    public LapSessionState State { get; set; } = LapSessionState.Idle;
}

/// <summary>
/// States a lap session can be in.
/// </summary>
public enum LapSessionState
{
    /// <summary>
    /// No active lap.
    /// </summary>
    Idle,

    /// <summary>
    /// Timer is active, tracking events.
    /// </summary>
    Running,

    /// <summary>
    /// Lap finished successfully.
    /// </summary>
    Completed,

    /// <summary>
    /// Lap aborted (e.g., player quits or restarts).
    /// </summary>
    Cancelled
}

/// <summary>
/// Data object passed to the summary UI at end of lap.
/// Contains final lap statistics.
/// </summary>
public class LapSummary
{
    /// <summary>
    /// Final lap time in seconds.
    /// </summary>
    public double LapTime { get; set; }

    /// <summary>
    /// Final off-road event count.
    /// </summary>
    public int OffRoadCount { get; set; }

    /// <summary>
    /// Final collision count.
    /// </summary>
    public int CollisionCount { get; set; }

    /// <summary>
    /// Creates a LapSummary from a completed LapSession.
    /// </summary>
    public static LapSummary FromSession(LapSession session)
    {
        if (!session.IsCompleted || !session.LapTime.HasValue)
        {
            throw new InvalidOperationException("Cannot create summary from incomplete lap session");
        }

        return new LapSummary
        {
            LapTime = session.LapTime.Value,
            OffRoadCount = session.OffRoadCount,
            CollisionCount = session.CollisionCount
        };
    }
}

/// <summary>
/// Manages lap timing, penalties, and state transitions for the driving simulator.
/// Tracks a single active lap session and provides events for lap lifecycle.
/// </summary>
public partial class LapManager : Node
{
    [Signal]
    public delegate void LapStartedEventHandler();

    [Signal]
    public delegate void LapCompletedEventHandler(double lapTime, int offRoadCount, int collisionCount);

    [Signal]
    public delegate void OffRoadEventEventHandler(int totalCount);

    [Signal]
    public delegate void CollisionEventEventHandler(int totalCount);

    private LapSession? _currentSession;
    private bool _hasCrossedStart = false;
    private Node3D? _bus;

    public override void _Ready()
    {
        GD.Print("LapManager initialized");
        
        // Find the bus in the scene
        _bus = GetTree().Root.FindChild("Bus", true, false) as Node3D;
        if (_bus == null)
        {
            GD.PrintErr("Bus not found in scene!");
        }
    }

    /// <summary>
    /// Gets the current active lap session, if any.
    /// </summary>
    public LapSession? CurrentSession => _currentSession;

    /// <summary>
    /// Starts a new lap session.
    /// </summary>
    public void StartLap()
    {
        if (_currentSession != null && _currentSession.State == LapSessionState.Running)
        {
            GD.PrintErr("Cannot start new lap while another lap is running");
            return;
        }

        _currentSession = new LapSession
        {
            StartTime = Time.GetTicksMsec() / 1000.0,
            State = LapSessionState.Running
        };

        GD.Print($"Lap started at {_currentSession.StartTime}s");
        EmitSignal(SignalName.LapStarted);
    }

    /// <summary>
    /// Completes the current lap session and returns summary data.
    /// </summary>
    public void CompleteLap()
    {
        if (_currentSession == null || _currentSession.State != LapSessionState.Running)
        {
            GD.PrintErr("No active lap to complete");
            return;
        }

        _currentSession.EndTime = Time.GetTicksMsec() / 1000.0;
        _currentSession.IsCompleted = true;
        _currentSession.State = LapSessionState.Completed;

        var summary = LapSummary.FromSession(_currentSession);
        GD.Print($"Lap completed: {summary.LapTime:F2}s, {summary.OffRoadCount} off-road, {summary.CollisionCount} collisions");

        EmitSignal(SignalName.LapCompleted, summary.LapTime, summary.OffRoadCount, summary.CollisionCount);
    }

    /// <summary>
    /// Cancels the current lap session.
    /// </summary>
    public void CancelLap()
    {
        if (_currentSession != null && _currentSession.State == LapSessionState.Running)
        {
            _currentSession.State = LapSessionState.Cancelled;
            GD.Print("Lap cancelled");
        }
    }

    /// <summary>
    /// Records an off-road event during the current lap.
    /// </summary>
    public void RecordOffRoadEvent()
    {
        if (_currentSession != null && _currentSession.State == LapSessionState.Running)
        {
            _currentSession.OffRoadCount++;
            GD.Print($"Off-road event recorded. Total: {_currentSession.OffRoadCount}");
            EmitSignal(SignalName.OffRoadEvent, _currentSession.OffRoadCount);
        }
    }

    /// <summary>
    /// Records a collision event during the current lap.
    /// </summary>
    public void RecordCollision()
    {
        if (_currentSession != null && _currentSession.State == LapSessionState.Running)
        {
            _currentSession.CollisionCount++;
            GD.Print($"Collision recorded. Total: {_currentSession.CollisionCount}");
            EmitSignal(SignalName.CollisionEvent, _currentSession.CollisionCount);
        }
    }

    /// <summary>
    /// Resets the lap manager to idle state.
    /// </summary>
    public void Reset()
    {
        _currentSession = null;
        _hasCrossedStart = false;
        GD.Print("LapManager reset");
    }

    /// <summary>
    /// Called when a body enters the start/finish trigger.
    /// Starts a new lap if idle, or completes the lap if already running.
    /// </summary>
    public void OnStartFinishTriggerEntered(Node body)
    {
        // Only respond to the bus entering the trigger
        if (body != _bus)
            return;

        if (_currentSession == null || _currentSession.State != LapSessionState.Running)
        {
            // Start a new lap
            StartLap();
            _hasCrossedStart = true;
        }
        else if (_hasCrossedStart)
        {
            // Complete the lap (only if we've crossed start before)
            CompleteLap();
            _hasCrossedStart = false;
        }
    }

    /// <summary>
    /// Called when the bus enters an off-road area.
    /// </summary>
    public void OnOffRoadAreaEntered(Node body)
    {
        if (body == _bus)
        {
            RecordOffRoadEvent();
        }
    }
}
