using System;
using BusDrivingSimulator;

namespace GameplayTests;

/// <summary>
/// Unit tests for LapManager lap timing and penalty logic.
/// Tests verify core gameplay mechanics without requiring Godot runtime.
/// </summary>
[TestFixture]
public class LapManagerTests
{
    [Test]
    public void LapSession_NewSession_StartsInIdleState()
    {
        // Arrange & Act
        var session = new LapSession();

        // Assert
        Assert.That(session.State, Is.EqualTo(LapSessionState.Idle));
        Assert.That(session.IsCompleted, Is.False);
        Assert.That(session.OffRoadCount, Is.EqualTo(0));
        Assert.That(session.CollisionCount, Is.EqualTo(0));
    }

    [Test]
    public void LapSession_LapTime_ReturnsNullWhenNotCompleted()
    {
        // Arrange
        var session = new LapSession
        {
            StartTime = 100.0,
            State = LapSessionState.Running
        };

        // Act
        var lapTime = session.LapTime;

        // Assert
        Assert.That(lapTime, Is.Null);
    }

    [Test]
    public void LapSession_LapTime_CalculatesCorrectDuration()
    {
        // Arrange
        var session = new LapSession
        {
            StartTime = 100.0,
            EndTime = 165.5,
            State = LapSessionState.Completed
        };

        // Act
        var lapTime = session.LapTime;

        // Assert
        Assert.That(lapTime, Is.EqualTo(65.5).Within(0.001));
    }

    [Test]
    public void LapSummary_FromSession_CreatesCorrectSummary()
    {
        // Arrange
        var session = new LapSession
        {
            StartTime = 100.0,
            EndTime = 165.5,
            OffRoadCount = 3,
            CollisionCount = 1,
            IsCompleted = true,
            State = LapSessionState.Completed
        };

        // Act
        var summary = LapSummary.FromSession(session);

        // Assert
        Assert.That(summary.LapTime, Is.EqualTo(65.5).Within(0.001));
        Assert.That(summary.OffRoadCount, Is.EqualTo(3));
        Assert.That(summary.CollisionCount, Is.EqualTo(1));
    }

    [Test]
    public void LapSummary_FromSession_ThrowsWhenSessionIncomplete()
    {
        // Arrange
        var session = new LapSession
        {
            StartTime = 100.0,
            State = LapSessionState.Running,
            IsCompleted = false
        };

        // Act & Assert
        Assert.Throws<InvalidOperationException>(() => LapSummary.FromSession(session));
    }

    [Test]
    public void LapSummary_FromSession_ThrowsWhenSessionCancelled()
    {
        // Arrange
        var session = new LapSession
        {
            StartTime = 100.0,
            EndTime = 120.0,
            State = LapSessionState.Cancelled,
            IsCompleted = false
        };

        // Act & Assert
        Assert.Throws<InvalidOperationException>(() => LapSummary.FromSession(session));
    }

    [Test]
    public void LapSession_OffRoadCount_IncrementsCorrectly()
    {
        // Arrange
        var session = new LapSession
        {
            State = LapSessionState.Running
        };

        // Act
        session.OffRoadCount++;
        session.OffRoadCount++;
        session.OffRoadCount++;

        // Assert
        Assert.That(session.OffRoadCount, Is.EqualTo(3));
    }

    [Test]
    public void LapSession_CollisionCount_IncrementsCorrectly()
    {
        // Arrange
        var session = new LapSession
        {
            State = LapSessionState.Running
        };

        // Act
        session.CollisionCount++;
        session.CollisionCount++;

        // Assert
        Assert.That(session.CollisionCount, Is.EqualTo(2));
    }

    [Test]
    public void LapSession_StateTransitions_IdleToRunning()
    {
        // Arrange
        var session = new LapSession { State = LapSessionState.Idle };

        // Act
        session.State = LapSessionState.Running;
        session.StartTime = 100.0;

        // Assert
        Assert.That(session.State, Is.EqualTo(LapSessionState.Running));
    }

    [Test]
    public void LapSession_StateTransitions_RunningToCompleted()
    {
        // Arrange
        var session = new LapSession
        {
            State = LapSessionState.Running,
            StartTime = 100.0
        };

        // Act
        session.EndTime = 165.5;
        session.IsCompleted = true;
        session.State = LapSessionState.Completed;

        // Assert
        Assert.That(session.State, Is.EqualTo(LapSessionState.Completed));
        Assert.That(session.IsCompleted, Is.True);
        Assert.That(session.LapTime, Is.EqualTo(65.5).Within(0.001));
    }

    [Test]
    public void LapSession_StateTransitions_RunningToCancelled()
    {
        // Arrange
        var session = new LapSession
        {
            State = LapSessionState.Running,
            StartTime = 100.0
        };

        // Act
        session.State = LapSessionState.Cancelled;

        // Assert
        Assert.That(session.State, Is.EqualTo(LapSessionState.Cancelled));
        Assert.That(session.IsCompleted, Is.False);
    }

    [Test]
    public void LapSession_VeryShortLap_HandlesCorrectly()
    {
        // Arrange
        var session = new LapSession
        {
            StartTime = 100.0,
            EndTime = 100.5, // 0.5 second lap
            IsCompleted = true,
            State = LapSessionState.Completed
        };

        // Act
        var summary = LapSummary.FromSession(session);

        // Assert
        Assert.That(summary.LapTime, Is.EqualTo(0.5).Within(0.001));
    }

    [Test]
    public void LapSession_VeryLongLap_HandlesCorrectly()
    {
        // Arrange
        var session = new LapSession
        {
            StartTime = 100.0,
            EndTime = 700.0, // 10 minute lap
            IsCompleted = true,
            State = LapSessionState.Completed
        };

        // Act
        var summary = LapSummary.FromSession(session);

        // Assert
        Assert.That(summary.LapTime, Is.EqualTo(600.0).Within(0.001));
    }

    [Test]
    public void LapSession_HighPenaltyCount_HandlesCorrectly()
    {
        // Arrange
        var session = new LapSession
        {
            StartTime = 100.0,
            EndTime = 200.0,
            OffRoadCount = 150,
            CollisionCount = 75,
            IsCompleted = true,
            State = LapSessionState.Completed
        };

        // Act
        var summary = LapSummary.FromSession(session);

        // Assert
        Assert.That(summary.OffRoadCount, Is.EqualTo(150));
        Assert.That(summary.CollisionCount, Is.EqualTo(75));
    }
}
