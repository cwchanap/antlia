using Godot;
using System;

namespace BusDrivingSimulator;

/// <summary>
/// Third-person chase camera that follows the bus with smooth interpolation.
/// Maintains a fixed offset behind and above the bus.
/// </summary>
public partial class CameraFollow : Camera3D
{
    [Export] public NodePath? TargetPath { get; set; }
    [Export] public Vector3 Offset = new Vector3(0, 3.5f, 8);
    [Export] public float FollowSpeed = 5.0f;
    [Export] public float LookAheadDistance = 3.0f;
    [Export] public float RotationSpeed = 3.0f;

    private Node3D? _target;

    public override void _Ready()
    {
        // Find the target node (bus)
        if (TargetPath != null)
        {
            _target = GetNode<Node3D>(TargetPath);
        }
        else
        {
            // Try to find the bus in the scene
            _target = GetTree().Root.FindChild("Bus", true, false) as Node3D;
        }

        if (_target == null)
        {
            GD.PrintErr("CameraFollow: Target not found!");
        }
        else
        {
            GD.Print($"CameraFollow: Following {_target.Name}");
        }
    }

    public override void _Process(double delta)
    {
        if (_target == null)
            return;

        // Calculate desired camera position behind the bus
        var targetTransform = _target.GlobalTransform;
        var targetPosition = targetTransform.Origin;
        var targetRotation = targetTransform.Basis;

        // Calculate offset position in world space
        Vector3 desiredPosition = targetPosition + targetRotation * Offset;

        // Smoothly move camera to desired position
        GlobalPosition = GlobalPosition.Lerp(desiredPosition, FollowSpeed * (float)delta);

        // Calculate look-at point (slightly ahead of the bus for better forward visibility)
        Vector3 lookAtPoint = targetPosition + (-targetRotation.Z * LookAheadDistance);

        // Smoothly rotate camera to look at the point
        var currentRotation = GlobalTransform.Basis;
        var lookDirection = (lookAtPoint - GlobalPosition).Normalized();
        
        if (lookDirection.Length() > 0.001f)
        {
            var targetBasis = Basis.LookingAt(lookDirection, Vector3.Up);
            var smoothRotation = currentRotation.Slerp(targetBasis, RotationSpeed * (float)delta);
            
            var newTransform = GlobalTransform;
            newTransform.Basis = smoothRotation;
            GlobalTransform = newTransform;
        }
    }

    /// <summary>
    /// Sets the target node for the camera to follow.
    /// </summary>
    public void SetTarget(Node3D target)
    {
        _target = target;
        GD.Print($"CameraFollow: Target set to {target.Name}");
    }

    /// <summary>
    /// Gets the current target being followed.
    /// </summary>
    public Node3D? GetTarget()
    {
        return _target;
    }
}
