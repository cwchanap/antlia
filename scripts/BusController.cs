using Godot;
using System;

namespace BusDrivingSimulator;

/// <summary>
/// Controls bus physics and input handling.
/// Provides semi-realistic bus handling with weighty, slower acceleration,
/// longer braking distance but forgiving control.
/// </summary>
public partial class BusController : RigidBody3D
{
    // Tunable physics parameters for semi-realistic bus handling
    [Export] public float MaxEngineForce = 8000.0f;
    [Export] public float MaxBrakeForce = 12000.0f;
    [Export] public float MaxSteeringAngle = 30.0f;
    [Export] public float SteeringSpeed = 2.0f;
    [Export] public float AccelerationRate = 2000.0f;
    [Export] public float BrakeRate = 3000.0f;
    [Export] public float ReverseForce = 4000.0f;

    // Current input states
    private float _accelerationInput = 0.0f;
    private float _brakeInput = 0.0f;
    private float _steeringInput = 0.0f;
    private float _currentSteeringAngle = 0.0f;

    // References
    private LapManager? _lapManager;

    public override void _Ready()
    {
        GD.Print("BusController initialized");
        
        // Find LapManager in the scene
        _lapManager = GetTree().Root.FindChild("LapManager", true, false) as LapManager;
        if (_lapManager == null)
        {
            GD.PrintErr("LapManager not found in scene!");
        }

        // Enable collision detection for penalty counting
        ContactMonitor = true;
        MaxContactsReported = 4;
    }

    public override void _Process(double delta)
    {
        // Read keyboard input
        ReadInput();
    }

    public override void _PhysicsProcess(double delta)
    {
        // Apply steering
        ApplySteering((float)delta);

        // Apply acceleration/braking forces
        ApplyDrivingForces((float)delta);
    }

    private void ReadInput()
    {
        // Acceleration (W or Up Arrow)
        if (Input.IsActionPressed("ui_up"))
        {
            _accelerationInput = 1.0f;
        }
        else
        {
            _accelerationInput = 0.0f;
        }

        // Braking/Reverse (S or Down Arrow)
        if (Input.IsActionPressed("ui_down"))
        {
            _brakeInput = 1.0f;
        }
        else
        {
            _brakeInput = 0.0f;
        }

        // Steering Left (A or Left Arrow)
        if (Input.IsActionPressed("ui_left"))
        {
            _steeringInput = -1.0f;
        }
        // Steering Right (D or Right Arrow)
        else if (Input.IsActionPressed("ui_right"))
        {
            _steeringInput = 1.0f;
        }
        else
        {
            _steeringInput = 0.0f;
        }
    }

    private void ApplySteering(float delta)
    {
        // Smoothly interpolate steering angle
        float targetSteeringAngle = _steeringInput * MaxSteeringAngle;
        _currentSteeringAngle = Mathf.Lerp(_currentSteeringAngle, targetSteeringAngle, SteeringSpeed * delta);

        // Apply steering by rotating the bus based on forward velocity
        var velocity = LinearVelocity;
        float forwardSpeed = velocity.Length();

        if (forwardSpeed > 0.5f) // Only steer if moving
        {
            // Calculate steering rotation based on speed (slower at high speed for realism)
            float steeringFactor = Mathf.Clamp(forwardSpeed / 20.0f, 0.3f, 1.0f);
            float rotationAmount = Mathf.DegToRad(_currentSteeringAngle) * delta * steeringFactor;
            
            // Rotate the bus
            Rotate(Vector3.Up, rotationAmount);
        }
    }

    private void ApplyDrivingForces(float delta)
    {
        // Get forward direction
        var forward = -Transform.Basis.Z.Normalized();
        var velocity = LinearVelocity;
        float forwardSpeed = velocity.Dot(forward);

        // Apply acceleration
        if (_accelerationInput > 0.0f && forwardSpeed < 30.0f) // Max speed ~30 m/s (~108 km/h)
        {
            float force = Mathf.Lerp(0, MaxEngineForce, _accelerationInput);
            ApplyCentralForce(forward * force);
        }

        // Apply braking or reverse
        if (_brakeInput > 0.0f)
        {
            if (forwardSpeed > 0.5f) // Moving forward, apply brake
            {
                float brakeForce = Mathf.Lerp(0, MaxBrakeForce, _brakeInput);
                ApplyCentralForce(-forward * brakeForce);
            }
            else if (forwardSpeed > -5.0f) // Allow reverse up to -5 m/s
            {
                // Apply reverse force
                ApplyCentralForce(-forward * ReverseForce * _brakeInput);
            }
        }

        // Apply some natural drag to prevent infinite acceleration
        if (_accelerationInput == 0.0f && _brakeInput == 0.0f)
        {
            ApplyCentralForce(-velocity * 50.0f); // Natural drag
        }
    }

    public override void _IntegrateForces(PhysicsDirectBodyState3D state)
    {
        // Keep bus upright (prevent flipping)
        var rotation = state.Transform.Basis.GetEuler();
        rotation.X = Mathf.Clamp(rotation.X, -0.3f, 0.3f); // Limit pitch
        rotation.Z = Mathf.Clamp(rotation.Z, -0.3f, 0.3f); // Limit roll
        
        var newBasis = Basis.FromEuler(rotation);
        var newTransform = state.Transform;
        newTransform.Basis = newBasis;
        state.Transform = newTransform;
    }

    /// <summary>
    /// Called when the bus collides with another body.
    /// Records collision with obstacles for penalty counting.
    /// </summary>
    public void OnBodyEntered(Node body)
    {
        // Check if collision is with an obstacle (layer 4)
        if (body is StaticBody3D staticBody)
        {
            uint collisionLayer = staticBody.CollisionLayer;
            
            // Layer 4 (bit 3) is Obstacles
            if ((collisionLayer & (1 << 3)) != 0)
            {
                GD.Print($"Bus collided with obstacle: {body.Name}");
                _lapManager?.RecordCollision();
            }
        }
    }

    /// <summary>
    /// Gets the current forward speed of the bus in m/s.
    /// </summary>
    public float GetForwardSpeed()
    {
        var forward = -Transform.Basis.Z.Normalized();
        return LinearVelocity.Dot(forward);
    }

    /// <summary>
    /// Gets the current steering angle in degrees.
    /// </summary>
    public float GetSteeringAngle()
    {
        return _currentSteeringAngle;
    }
}
