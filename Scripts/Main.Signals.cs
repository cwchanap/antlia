using Godot;
using System;
using System.Collections.Generic;
using System.Linq;

public enum SignalAspect { Red, RedAmber, Green, Amber }

public sealed class TrafficSignal
{
    public string Name = "";
    public Vector3 Stop, Forward;
    public float Width, Offset;
    public bool SideRoad;
    public SignalAspect Aspect = (SignalAspect)(-1);
    public MeshInstance3D[] Lamps = Array.Empty<MeshInstance3D>();

    public float DistanceFrom(Transform3D vehicle, float nose)
    {
        var offset = vehicle.Origin - vehicle.Basis.Z * nose - Stop;
        float lateral = offset.Dot(Forward.Cross(Vector3.Up));
        if ((-vehicle.Basis.Z).Dot(Forward) < .75f || lateral < -Width / 2 - .2f || lateral > .2f)
            return float.PositiveInfinity;
        return -offset.Dot(Forward);
    }
}

public partial class Main
{
    private readonly List<TrafficSignal> _signals = new();
    private readonly List<Vector3> _signalPoles = new();
    private readonly List<(Vector3 P,Vector3 F)> _crossingStudChecks = new();
    private readonly StandardMaterial3D[] _litLamps = new StandardMaterial3D[3];
    private StandardMaterial3D _darkLamp = null!;
    private float _signalClock;
    public int RedLightCrossings { get; private set; }

    public static SignalAspect SignalPhase(float seconds, bool sideRoad)
    {
        float t = Mathf.PosMod(seconds, 54);
        if (sideRoad)
            return t < 29 ? SignalAspect.Red : t < 31 ? SignalAspect.RedAmber :
                t < 47 ? SignalAspect.Green : t < 50 ? SignalAspect.Amber : SignalAspect.Red;
        return t < 24 ? SignalAspect.Green : t < 27 ? SignalAspect.Amber :
            t < 52 ? SignalAspect.Red : SignalAspect.RedAmber;
    }

    private void BuildTrafficLights()
    {
        _darkLamp = Material("131c1b");
        var colors = new[] { "ff3025", "ffb522", "39ff8b" };
        for (int i = 0; i < 3; i++)
            _litLamps[i] = new StandardMaterial3D { AlbedoColor = new(colors[i]),
                ShadingMode = BaseMaterial3D.ShadingModeEnum.Unshaded,
                EmissionEnabled = true, Emission = new(colors[i]), EmissionEnergyMultiplier = 2 };

        // ponytail: authored junction coverage; use a surveyed inventory if exact installations are needed.
        foreach (var (distance, name, west, east, offset) in new[] {
            (350f, "Haiphong / Humphreys", "HAIPHONG ROAD", "HUMPHREYS AVENUE", 0f),
            (410f, "Cameron Road", "", "CAMERON ROAD", 8f),
            (503f, "Granville Road", "", "GRANVILLE ROAD", 16f),
            (600f, "Kimberley Road", "", "KIMBERLEY ROAD", 24f),
            (920f, "Austin Road", "AUSTIN ROAD", "AUSTIN ROAD", 32f),
            (165f, "Peking Road", "PEKING ROAD", "", 30f),
            (215f, "Mody Road", "", "MODY ROAD", 38f),
            (298f, "Carnarvon Road", "", "CARNARVON ROAD", 46f),
            (855f, "Hillwood Road", "", "HILLWOOD ROAD", 24f) })
        {
            AddSignal(name, Map.At(distance - 16), Map.Forward(distance - 16), 20, offset, false);
            AddSignal(name, Map.At(distance + 16), -Map.Forward(distance + 16), 20, offset, false);
            foreach (var (road, side) in new[] { (west, -1), (east, 1) })
            {
                if (road == "") continue;
                var target = Map.At(distance) + Map.Forward(distance).Cross(Vector3.Up) * side * 18;
                AddStreetSignal(name, road, target, Map.At(distance), offset, true, 36);
            }
        }
        // Junction centres come from intersections in the bundled government road extract.
        foreach (var (name, center, main, west, east, offset) in new[] {
            ("Jordan / Nathan", new Vector3(-69.8f,0,-1152.3f), "NATHAN ROAD", "JORDAN ROAD", "JORDAN ROAD", 12f),
            ("Canton / Haiphong", new Vector3(-361.4f,0,-338.6f), "CANTON ROAD", "", "HAIPHONG ROAD", 8f),
            ("Canton / Austin", new Vector3(-439f,0,-891.2f), "CANTON ROAD", "AUSTIN ROAD WEST", "AUSTIN ROAD", 24f),
            ("Chatham / Granville", new Vector3(397.4f,0,-611.2f), "CHATHAM ROAD SOUTH", "GRANVILLE ROAD", "GRANVILLE ROAD", 16f),
            ("Chatham / Mody", new Vector3(329.7f,0,-252.4f), "CHATHAM ROAD SOUTH", "MODY ROAD", "MODY ROAD", 40f) })
        {
            var axis = Map.NearestStreet(center, main).Forward;
            if (axis.Z > 0) axis = -axis;
            foreach (int side in new[] { -1, 1 })
                AddStreetSignal(name, main, center + axis * side * 22, center, offset, false, 44);
            foreach (var (road, side) in new[] { (west, -1), (east, 1) })
            {
                if (road == "") continue;
                var cross = Map.NearestStreet(center, road).Forward;
                if (cross.Dot(axis.Cross(Vector3.Up)) < 0) cross = -cross;
                AddStreetSignal(name, road, center + cross * side * 22, center, offset, true, 44);
            }
        }
        UpdateSignals();
        GD.Print($"ANTILA_SIGNALS_READY: {_signals.Select(s=>s.Name).Distinct().Count()} junctions, {_signals.Count} approaches, 54-second cycles");
    }

    private void AddStreetSignal(string name, string road, Vector3 target, Vector3 center, float offset, bool sideRoad, float span)
    {
        var street = Map.NearestStreet(target, road);
        if (street.Distance > 8) throw new InvalidOperationException("Missing signal approach near " + name + ": " + road);
        var forward = street.Forward;
        if (forward.Dot(center - street.Point) < 0) forward = -forward;
        var carriageway=Map.Carriageway(street.Point,forward,road);
        AddSignal(name, carriageway.Center, forward, carriageway.Width, offset, sideRoad, span);
    }

    private void AddSignal(string name, Vector3 stop, Vector3 forward, float width, float offset, bool sideRoad, float span=32)
    {
        var right = forward.Cross(Vector3.Up);
        var lamps = new List<MeshInstance3D>();
        foreach (float ahead in new[] { 0f, span })
        {
            var pole = SignalKerb(stop + forward * ahead - right * (width / 2 + .9f));
            var model = Asset("traffic-signal", pole, Mathf.Atan2(-forward.X, -forward.Z));
            _signalPoles.Add(pole);
            foreach (string color in new[] { "Red", "Amber", "Green" })
                lamps.Add((MeshInstance3D)model.FindChild("Lamp" + color, true, false));
        }
        _signals.Add(new TrafficSignal { Name = name, Stop = stop, Forward = forward, Width = width,
            Offset = offset, SideRoad = sideRoad, Lamps = lamps.ToArray() });
        Stripe(stop - right * width / 4, forward, width / 2 - .3f, .35f, "e3dfc9");
        // Short crossing boundary studs beyond the stop line; leave the junction surface clear.
        for (float x = -width / 2 + .5f; x <= width / 2 - .5f; x += 1)
            foreach (float ahead in new[] { 2.5f, 5.5f })
            {
                var p=stop+forward*ahead+right*x;
                if(!PaintOnRoad(p,forward,.3f,.3f))continue;
                Stripe(p,forward,.3f,.3f,"e3dfc9");
                if(SelfTest)_crossingStudChecks.Add((p,forward));
            }
    }

    private Vector3 SignalKerb(Vector3 target)
    {
        bool Clear(Vector3 p)
        {
            var flat = new Vector2(p.X,p.Z);
            return Map.ClearOfRoads(p,.35f) && _signalPoles.All(other=>other.DistanceSquaredTo(p)>9) &&
                !_lots.Any(l=>l.Bounds.Grow(.4f).HasPoint(flat) &&
                    (Geometry2D.IsPointInPolygon(flat,l.Polygon) || Enumerable.Range(0,l.Polygon.Length).Any(i=>
                        Geometry2D.GetClosestPointToSegment(flat,l.Polygon[i],l.Polygon[(i+1)%l.Polygon.Length]).DistanceSquaredTo(flat)<.16f)));
        }
        if (Clear(target)) return target;
        // Skewed crossings and split centrelines can put a straight-line repeater in a lane.
        for (float radius=.5f; radius<=32; radius+=.5f)
            for (int direction=0; direction<16; direction++)
            {
                float angle=direction*Mathf.Tau/16;
                var p=target+new Vector3(Mathf.Cos(angle),0,Mathf.Sin(angle))*radius;
                if (Clear(p)) return p;
            }
        throw new InvalidOperationException("No clear signal kerb near " + target);
    }

    private void UpdateSignals()
    {
        foreach (var signal in _signals)
        {
            var aspect = SignalPhase(_signalClock + signal.Offset, signal.SideRoad);
            if (signal.Aspect == aspect) continue;
            signal.Aspect = aspect;
            for (int i = 0; i < signal.Lamps.Length; i++)
            {
                int color = i % 3;
                bool on = color == 0 ? signal.Aspect is SignalAspect.Red or SignalAspect.RedAmber :
                    color == 1 ? signal.Aspect is SignalAspect.Amber or SignalAspect.RedAmber : signal.Aspect == SignalAspect.Green;
                signal.Lamps[i].MaterialOverride = on ? _litLamps[color] : _darkLamp;
            }
        }
    }

    public (TrafficSignal? Signal, float Distance) NextSignal(Transform3D vehicle, float nose = 5.275f)
    {
        TrafficSignal? next = null;
        float distance = 95;
        foreach (var signal in _signals)
        {
            float d = signal.DistanceFrom(vehicle, nose);
            if (d < -.05f || d >= distance) continue;
            next = signal; distance = Math.Max(0, d);
        }
        return (next, distance);
    }

    private void CheckSignalCrossing(Transform3D before, Transform3D after)
    {
        foreach (var signal in _signals)
            if (signal.Aspect is SignalAspect.Red or SignalAspect.RedAmber &&
                float.IsFinite(signal.DistanceFrom(before, 5.275f)) && signal.DistanceFrom(before, 5.275f) > 0 &&
                signal.DistanceFrom(after, 5.275f) <= 0)
            {
                RedLightCrossings++;
                ShowNotice("Red light crossed — stop behind the white line next time");
                if(!HarbourDrive && !Menu && !Complete)MioSay("red-light",true);
            }
    }

    private bool TestSignalBrake()
    {
        var (signal, distance) = NextSignal(Bus.GlobalTransform);
        return signal != null && signal.Aspect != SignalAspect.Green && distance < Bus.Speed * Bus.Speed / 8 + 2;
    }

    private async System.Threading.Tasks.Task CheckTrafficSignals()
    {
        void Check(bool ok, string message) { if (!ok) throw new Exception(message); }
        Check(_signals.Count == 48 && _signals.Select(s=>s.Name).Distinct().Count() == 14, "14 junctions must cover 48 road approaches");
        Check(_signals.Min(s=>s.Stop.X)<-430 && _signals.Max(s=>s.Stop.X)>410 && _signals.Min(s=>s.Stop.Z)<-1170,
            "signal coverage must reach Canton Road, Chatham Road and Jordan Road");
        foreach (var signal in _signals)
        {
            var road=Map.NearestStreet(signal.Stop);
            var carriageway=Map.Carriageway(signal.Stop,signal.Forward,road.Name);
            Check(carriageway.Center.DistanceTo(signal.Stop)<.5f, "stop line must follow its carriageway at " + signal.Name);
            int lanes=RoadMap.LanesPerDirection(signal.Width);
            for(int lane=0;lane<lanes;lane++)
            {
                var pose = new Transform3D(new Basis(Vector3.Up, Mathf.Atan2(-signal.Forward.X,-signal.Forward.Z)),
                    signal.Stop - signal.Forward*8.275f - signal.Forward.Cross(Vector3.Up)*(lane+.5f)*signal.Width/(lanes*2));
                Check(NextSignal(pose).Signal == signal, "every lane must see the correct approach at " + signal.Name);
            }
        }
        using var poleQuery=new PhysicsShapeQueryParameters3D {Shape=new BoxShape3D {Size=new(.3f,3.8f,.3f)},CollisionMask=1};
        foreach(var pole in _signals.SelectMany(s=>s.Lamps.Where((_,i)=>i%3==0)).Select(l=>l.GetParent<Node3D>()))
        {
            Check(Map.ClearOfRoads(pole.GlobalPosition,.3f), "signal pole must stay off the road");
            poleQuery.Transform=new(Basis.Identity,pole.GlobalPosition+Vector3.Up*2);
            Check(GetWorld3D().DirectSpaceState.IntersectShape(poleQuery,1).Count==0,"signal pole intersects a building at " + pole.GlobalPosition);
        }
        for (float t = 0; t < 108; t += .25f)
        {
            var main = SignalPhase(t, false); var side = SignalPhase(t, true);
            Check(main != SignalAspect.Green || side == SignalAspect.Red, "conflicting main green");
            Check(side != SignalAspect.Green || main == SignalAspect.Red, "conflicting side green");
        }
        Check(SignalPhase(24, false) == SignalAspect.Amber && SignalPhase(27, false) == SignalAspect.Red &&
            SignalPhase(52, false) == SignalAspect.RedAmber && SignalPhase(54, false) == SignalAspect.Green,
            "Hong Kong signal sequence boundaries");
        SetPhysicsProcess(false); Bus.SetPaused(true);
        var savedTraffic = _traffic.ToArray();
        float clock = _signalClock;
        _signalClock = 30; UpdateSignals();
        var north = _signals[0];
        var right = north.Forward.Cross(Vector3.Up);
        var before = new Transform3D(new Basis(Vector3.Up, Mathf.Atan2(-north.Forward.X, -north.Forward.Z)),
            north.Stop - north.Forward * 5.575f - right * 7.3f);
        var after = before.Translated(north.Forward * .6f);
        int violations = RedLightCrossings;
        CheckSignalCrossing(before, after);
        CheckSignalCrossing(after, after.Translated(north.Forward));
        Check(RedLightCrossings == violations + 1, "red crossing counted once at the front bumper");
        CheckSignalCrossing(before.Translated(right * 14), after.Translated(right * 14));
        Check(RedLightCrossings == violations + 1, "opposite lane must not count");
        Bus.ResetAt(after.Origin, 0);
        Check(RedLightCrossings == violations + 1, "reset must not count as crossing");
        _signalClock = 0; UpdateSignals(); CheckSignalCrossing(before, after);
        Check(RedLightCrossings == violations + 1, "green crossing must not count");
        _signalClock = 53; UpdateSignals(); CheckSignalCrossing(before, after);
        Check(RedLightCrossings == violations + 2, "red and amber still means stop");
        Check(north.Lamps[0].MaterialOverride == _litLamps[0] && north.Lamps[1].MaterialOverride == _litLamps[1] &&
            north.Lamps[2].MaterialOverride == _darkLamp, "red and amber lens materials");
        RedLightCrossings = violations;
        Bus.ResetAt(Map.At(22, -7.3f), Map.Heading(22));
        var taxi = _traffic[0].Body;
        taxi.Transform = new(new Basis(Vector3.Up, Map.Heading(395) + Mathf.Pi), Map.At(395, 7.35f));
        _traffic[0] = (taxi, 395);
        await ToSignal(GetTree(), SceneTree.SignalName.PhysicsFrame);
        _signalClock = 30; UpdateSignals();
        for (int i = 0; i < 600; i++) _PhysicsProcess(1.0 / 60);
        float stopped = _traffic[0].Distance;
        Check(stopped < 375 && stopped > 368, "taxi must approach and stop before red line");
        Check(Mathf.Abs(_signals[1].DistanceFrom(taxi.Transform, 2.25f) - 1.2f) < .03f, "taxi front clearance at stop line");
        for (int i = 0; i < 60; i++) _PhysicsProcess(1.0 / 60);
        Check(Mathf.Abs(_traffic[0].Distance - stopped) < .001f, "red taxi must remain stopped");
        _signalClock = 52; UpdateSignals();
        for (int i = 0; i < 60; i++) _PhysicsProcess(1.0 / 60);
        Check(Mathf.Abs(_traffic[0].Distance - stopped) < .001f, "taxi must wait through red and amber");
        _signalClock = 0; UpdateSignals();
        for (int i = 0; i < 120; i++) _PhysicsProcess(1.0 / 60);
        Check(stopped - _traffic[0].Distance > 12, "taxi must resume on green");
        foreach (string gate in new[] { "pause", "map", "complete" })
        {
            Paused = gate == "pause"; MapOpen = gate == "map"; Complete = gate == "complete";
            float heldClock = _signalClock; var heldTaxi = taxi.Position;
            _PhysicsProcess(10);
            Check(_signalClock == heldClock && taxi.Position == heldTaxi, gate + " must freeze signals and traffic");
        }
        Paused = MapOpen = Complete = false;
        for (int i = 0; i < savedTraffic.Length; i++)
        {
            _traffic[i] = savedTraffic[i];
            _traffic[i].Body.Transform = new(new Basis(Vector3.Up, Map.Heading(_traffic[i].Distance) + Mathf.Pi),
                Map.At(_traffic[i].Distance, 7.35f));
        }
        _signalClock = clock; UpdateSignals();
        SetPhysicsProcess(true); Bus.SetPaused(false);
        NoticeTime = 0;
        GD.Print("ANTILA_SIGNALS_OK: 14 junctions / 48 approaches; road alignment and direction; safe phases; red/red-amber crossings; reset/lane rejection; taxi stop, hold and green restart; pause/map/completion freeze");
    }

    private async void CaptureSignals()
    {
        SelfTest = true;
        SetPhysicsProcess(false); Bus.SetPaused(true);
        Bus.ResetAt(Map.At(322, -7.3f), Map.Heading(322));
        StopIndex = 1; Passengers = 8;
        SetCab(true); NoticeTime = 0;
        await ToSignal(GetTree().CreateTimer(2), SceneTreeTimer.SignalName.Timeout);
        foreach (var (name, time) in new[] { ("red", 35f), ("red-amber", 53f), ("green", 5f), ("amber", 25f) })
        {
            _signalClock = time; UpdateSignals(); Hud.QueueRedraw();
            await ToSignal(RenderingServer.Singleton, RenderingServer.SignalName.FramePostDraw);
            GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath($"res://evidence/signal-{name}.png"));
        }
        SetProcess(false); SetCab(false); Hud.Visible = false;
        _signalClock = 35; UpdateSignals();
        Bus.Model.Visible = false;
        Camera.Position = Map.At(323, -7) + Vector3.Up * 3.2f;
        Camera.LookAt(Map.At(343, -10) + Vector3.Up * 2.7f);
        await ToSignal(RenderingServer.Singleton, RenderingServer.SignalName.FramePostDraw);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/signal-junction.png"));
        foreach (var (file, signal) in new[] {
            ("peking", _signals.First(s=>s.Name=="Peking Road" && !s.SideRoad && s.Forward.Z<0)),
            ("canton", _signals.First(s=>s.Name=="Canton / Haiphong" && s.SideRoad)),
            ("chatham", _signals.First(s=>s.Name=="Chatham / Granville" && s.SideRoad && s.Forward.X>0)),
            ("jordan", _signals.First(s=>s.Name=="Jordan / Nathan" && !s.SideRoad && s.Forward.Z<0)) })
        {
            _signalClock=Mathf.PosMod((signal.SideRoad?5:35)-signal.Offset,54); UpdateSignals();
            Camera.Position=signal.Stop-signal.Forward*15-signal.Forward.Cross(Vector3.Up)*signal.Width/4+Vector3.Up*3.2f;
            Camera.LookAt(signal.Stop+signal.Forward*14+Vector3.Up*2.7f);
            await ToSignal(RenderingServer.Singleton, RenderingServer.SignalName.FramePostDraw);
            GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath($"res://evidence/signal-{file}.png"));
        }
        GD.Print("ANTILA_SIGNAL_CAPTURE_OK: four aspects, Haiphong, Peking, Canton, Chatham and Jordan junctions");
        QuitGame();
    }
}
