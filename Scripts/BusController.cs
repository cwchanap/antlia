using Godot;
using System;
using System.Collections.Generic;

public partial class BusController : CharacterBody3D
{
    public float Speed { get; private set; }
    public float Steering { get; private set; }
    public bool DoorsOpen { get; private set; }
    public bool Reverse { get; private set; }
    public int Collisions { get; private set; }
    public float DistanceDriven { get; private set; }
    public float Kmh => Mathf.Abs(Speed) * 3.6f;
    public Node3D Model = null!;
    public Action<string>? Notify;
    public Action<Transform3D, Transform3D>? Moved;
    public bool AutomaticTest;
    public float TestThrottle, TestBrake, TestSteer;
    private float _collisionCooldown;
    private readonly KinematicCollision3D _steeringHit = new();
    private readonly Dictionary<string, AudioStreamPlayer> _audio = new();
    private bool _brakeArmed;
    public bool CabAudio;
    private readonly List<Node3D> _wheels = new();
    private readonly List<(Node3D Node, Vector3 Closed)> _doors = new();
    private float _doorAmount;

    public override void _Ready()
    {
        Name = "Bus";
        CollisionLayer = 2;
        CollisionMask = 1;
        FloorSnapLength = .4f;
        AddChild(new CollisionShape3D { Shape = new BoxShape3D { Size = new(2.48f, 4.2f, 10.55f) }, Position = new(0, 2.12f, 0) });
        Model = GD.Load<PackedScene>("res://Assets/Models/bus.glb").Instantiate<Node3D>();
        AddChild(Model);
        foreach (var node in Model.FindChildren("Wheel_*", "Node3D", true, false))
            _wheels.Add((Node3D)node);
        foreach (var node in Model.FindChildren("Door_*", "Node3D", true, false))
            _doors.Add(((Node3D)node,((Node3D)node).Position));
        foreach(var (name,volume,loop) in new[]{("engine",-14f,true),("rolling",-60f,true),("city",-18f,true),
            ("door-open",-9f,false),("door-close",-9f,false),("air-brake",-10f,false),
            ("horn",-8f,false),("stop-bell",-10f,false),("contact",-8f,false)})
        {
            var sound=GD.Load<AudioStreamWav>($"res://Assets/Audio/{name}.wav");
            sound.LoopMode=loop?AudioStreamWav.LoopModeEnum.Forward:AudioStreamWav.LoopModeEnum.Disabled;
            sound.LoopEnd=(int)Math.Round(sound.GetLength()*sound.MixRate);
            var player=new AudioStreamPlayer {Name="Audio_"+name,Stream=sound,VolumeDb=volume};
            AddChild(player);_audio[name]=player;
            if(loop)player.Play();
        }
        var music=GD.Load<AudioStreamOggVorbis>("res://Assets/Audio/kowloon-drive.ogg");
        music.Loop=true;
        var musicPlayer=new AudioStreamPlayer {Name="Audio_music",Stream=music,VolumeDb=-16};
        AddChild(musicPlayer);_audio["music"]=musicPlayer;musicPlayer.Play();
    }

    public static float IntegrateSpeed(float speed, float throttle, float brake, bool reverse, bool doorsOpen, float dt)
    {
        if (doorsOpen) return Mathf.MoveToward(speed, 0, 8 * dt);
        if (brake > 0) return Mathf.MoveToward(speed, 0, 5.5f * brake * dt);
        if (throttle > 0)
            return Mathf.MoveToward(speed, reverse ? -3.5f : 14.4f, 1.7f * throttle * dt);
        return Mathf.MoveToward(speed, 0, .27f * dt);
    }

    public override void _PhysicsProcess(double delta)
    {
        var beforeMove = GlobalTransform;
        float dt = (float)delta;
        _collisionCooldown -= dt;
        float throttle = AutomaticTest ? TestThrottle : Input.GetActionStrength("accelerate");
        float brake = AutomaticTest ? TestBrake : Input.GetActionStrength("brake");
        float steer = AutomaticTest ? TestSteer : Input.GetAxis("steer_right", "steer_left");
        if (!AutomaticTest && Input.IsActionPressed("handbrake")) brake = 1;
        Speed = IntegrateSpeed(Speed, throttle, brake, Reverse, DoorsOpen, dt);
        if(Mathf.Abs(Speed)>2)_brakeArmed=true;
        if(_brakeArmed && Mathf.Abs(Speed)<.3f && brake>0)
        {
            Sound("air-brake");_brakeArmed=false;
        }
        Steering = Mathf.MoveToward(Steering, steer * Mathf.DegToRad(32), dt * 1.0f);
        // ponytail: kinematic bicycle model; add suspension/weight transfer when handling needs it.
        float yaw = Speed / 6.0f * Mathf.Tan(Steering) * dt;
        // Test the full body rotation so a stopped bus cannot steer through a wall.
        var prior = Rotation;
        var flatForward=new Vector3(-Mathf.Sin(Rotation.Y),0,-Mathf.Cos(Rotation.Y));
        // Follow the floor grade so the long bus nose cannot catch a rising road triangle.
        float pitch=IsOnFloor()?Mathf.Asin(flatForward.Slide(GetFloorNormal()).Normalized().Y):Rotation.X;
        Rotation=new(pitch,Rotation.Y+yaw,0);
        if (TestMove(GlobalTransform, -GlobalBasis.Z * Speed * dt, _steeringHit, .01f) && Mathf.Abs(_steeringHit.GetNormal().Y)<.6f)
            Rotation = prior;
        var forward = -GlobalBasis.Z;
        Velocity = (IsOnFloor()?forward:flatForward) * Speed + Vector3.Up * (IsOnFloor() ? -.4f : Velocity.Y - 20 * dt);
        var before = GlobalPosition;
        MoveAndSlide();
        Moved?.Invoke(beforeMove, GlobalTransform);
        DistanceDriven += new Vector2(GlobalPosition.X - before.X, GlobalPosition.Z - before.Z).Length();
        for (int i = 0; i < GetSlideCollisionCount(); i++)
        {
            var hit = GetSlideCollision(i);
            if (Mathf.Abs(hit.GetNormal().Y) > .6f) continue;
            if (Mathf.Abs(Speed) > 1.5f && _collisionCooldown <= 0)
            {
                Collisions++;
                if(AutomaticTest)GD.Print($"ANTILA_TEST_CONTACT: at={GlobalPosition}, normal={hit.GetNormal()}, collider={(hit.GetCollider() as Node)?.GetPath()}");
                _collisionCooldown = 2;
                Sound("contact");
                Notify?.Invoke("Contact — brake and give yourself more room");
            }
            Speed = 0;
            break;
        }
        foreach (var wheel in _wheels) wheel.Quaternion = new Quaternion(Vector3.Right,Speed / .54f * dt)*wheel.Quaternion;
        _doorAmount = Mathf.MoveToward(_doorAmount, DoorsOpen?1:0, dt*1.6f);
        foreach (var (node,closed) in _doors)
            node.Position=closed+new Vector3(-.08f*_doorAmount,0,(node.Name.ToString().Contains("_L")?1:-1)*.55f*_doorAmount);
        float blend=1-Mathf.Exp(-4*dt);
        var engine=_audio["engine"];
        // ponytail: one pitched engine loop; add RPM layers with a simulated gearbox.
        engine.PitchScale=Mathf.Lerp(engine.PitchScale,.85f+Kmh/95+throttle*.18f,blend);
        engine.VolumeDb=Mathf.Lerp(engine.VolumeDb,-14+throttle*5-(CabAudio?2:0),blend);
        _audio["rolling"].VolumeDb=Mathf.Lerp(_audio["rolling"].VolumeDb,
            Mathf.Lerp(-60,-12,Mathf.Clamp(Kmh/40,0,1)),blend);
        _audio["city"].VolumeDb=CabAudio?(DoorsOpen?-18:-24):-18;
        _audio["music"].VolumeDb=Mathf.Lerp(_audio["music"].VolumeDb,
            DoorsOpen || _audio["stop-bell"].Playing?-22:-16,blend);
    }

    public bool ToggleDoors()
    {
        if (Mathf.Abs(Speed) > .15f)
        {
            Notify?.Invoke("Stop completely before opening the doors");
            return false;
        }
        DoorsOpen = !DoorsOpen;
        Speed = 0;
        _audio["door-open"].Stop();_audio["door-close"].Stop();
        Sound(DoorsOpen?"door-open":"door-close");
        Notify?.Invoke(DoorsOpen ? "Doors open — parking brake engaged" : "Doors closed — ready to depart");
        return true;
    }

    public void ToggleReverse()
    {
        if (Kmh > .5f) { Notify?.Invoke("Stop before changing gear"); return; }
        Reverse = !Reverse;
        Notify?.Invoke(Reverse ? "Reverse selected — check behind you" : "Drive selected");
    }

    public void Sound(string name) => _audio[name].Play();

    public void Horn() => Sound("horn");

    public void SetPaused(bool paused)
    {
        SetPhysicsProcess(!paused);
        foreach(var player in _audio.Values)player.StreamPaused=paused;
    }

    public void StopAudio() { foreach(var player in _audio.Values)player.Stop(); }

    public void RestartAudio() { foreach(var name in new[]{"engine","rolling","city","music"})if(!_audio[name].Playing)_audio[name].Play(); }

    public override void _ExitTree() => StopAudio();

    public void ResetAt(Vector3 position, float heading)
    {
        GlobalPosition = position + Vector3.Up * .1f;
        Rotation = new(0, heading, 0);
        Speed = 0;
        Steering = 0;
        Velocity = Vector3.Zero;
        DoorsOpen = false;
        Reverse = false;
        _brakeArmed=false;
        _doorAmount=0;
        foreach(var (node,closed) in _doors)node.Position=closed;
        foreach(var (name,player) in _audio)
            if(name is not ("engine" or "rolling" or "city" or "music"))player.Stop();
    }
}
