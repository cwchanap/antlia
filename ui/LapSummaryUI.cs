using Godot;
using System;

namespace BusDrivingSimulator;

/// <summary>
/// UI controller for displaying lap summary at the end of a lap.
/// Shows lap time, off-road count, and collision count with options to restart or quit.
/// </summary>
public partial class LapSummaryUI : CanvasLayer
{
    private Label? _lapTimeLabel;
    private Label? _offRoadLabel;
    private Label? _collisionLabel;
    private LapManager? _lapManager;

    public override void _Ready()
    {
        // Get references to UI elements
        _lapTimeLabel = GetNode<Label>("Panel/VBoxContainer/LapTimeLabel");
        _offRoadLabel = GetNode<Label>("Panel/VBoxContainer/OffRoadLabel");
        _collisionLabel = GetNode<Label>("Panel/VBoxContainer/CollisionLabel");

        // Find LapManager in the scene
        _lapManager = GetTree().Root.FindChild("LapManager", true, false) as LapManager;
        if (_lapManager != null)
        {
            _lapManager.LapCompleted += OnLapCompleted;
        }
        else
        {
            GD.PrintErr("LapSummaryUI: LapManager not found!");
        }

        // Hide initially
        Hide();
    }

    public override void _ExitTree()
    {
        // Unsubscribe from events
        if (_lapManager != null)
        {
            _lapManager.LapCompleted -= OnLapCompleted;
        }
    }

    /// <summary>
    /// Called when a lap is completed. Updates and shows the summary UI.
    /// </summary>
    private void OnLapCompleted(double lapTime, int offRoadCount, int collisionCount)
    {
        UpdateSummary(lapTime, offRoadCount, collisionCount);
        Show();

        // Pause the game (optional - allows player to review summary)
        GetTree().Paused = true;
    }

    /// <summary>
    /// Updates the summary UI with lap data.
    /// </summary>
    public void UpdateSummary(double lapTime, int offRoadCount, int collisionCount)
    {
        if (_lapTimeLabel != null)
        {
            _lapTimeLabel.Text = $"Lap Time: {lapTime:F2}s";
        }

        if (_offRoadLabel != null)
        {
            _offRoadLabel.Text = $"Off-Road Events: {offRoadCount}";
        }

        if (_collisionLabel != null)
        {
            _collisionLabel.Text = $"Collisions: {collisionCount}";
        }

        GD.Print($"LapSummaryUI: Displaying summary - {lapTime:F2}s, {offRoadCount} off-road, {collisionCount} collisions");
    }

    /// <summary>
    /// Called when the Restart button is pressed.
    /// </summary>
    private void OnRestartPressed()
    {
        GD.Print("LapSummaryUI: Restart pressed");
        Hide();
        GetTree().Paused = false;

        // Reset the lap manager
        _lapManager?.Reset();

        // Reset bus position (reload scene)
        GetTree().ReloadCurrentScene();
    }

    /// <summary>
    /// Called when the Quit button is pressed.
    /// </summary>
    private void OnQuitPressed()
    {
        GD.Print("LapSummaryUI: Quit pressed");
        GetTree().Quit();
    }
}
