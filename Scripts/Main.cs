using Godot;
using System;
using System.Collections.Generic;
using System.Linq;

public partial class Main : Node3D
{
    public RoadMap Map = null!;
    public BusController Bus = null!;
    public Hud Hud = null!;
    public Camera3D Camera = null!;
    public bool CabView, Paused, Complete, MapOpen;
    public int StopIndex, Passengers;
    public float Boarding, Elapsed;
    public string Notice = "Welcome aboard. Pull into Middle Road, stop and press E.";
    public float NoticeTime = 9;
    public bool SelfTest;
    private Node3D _cab = null!, _stopMarker = null!;
    private readonly List<(StaticBody3D Body, float Distance)> _traffic = new();
    private readonly List<Node3D> _waiting = new();
    private readonly PhysicsShapeQueryParameters3D _cameraSweep = new() {
        Shape=new SphereShape3D {Radius=1.2f},CollisionMask=1,Margin=.02f};
    private readonly Dictionary<string,SurfaceTool> _paint = new();
    private readonly List<(Vector3 Center,float Height,Vector2[] Polygon,Rect2 Bounds)> _lots = new();
    private readonly List<(Vector2 Center,Vector2[] Polygon)> _pavementPatches = new();
    private Node3D _city = null!;
    private readonly Vector2[] _park = {new(-26,-368),new(-193,-361),new(-378,-570),new(-415,-903),new(-63,-920)};
    private ShaderMaterial _terrain = null!;
    private readonly List<Vector3> _parkPath = new(){new(-80,0,-430),new(-145,0,-520),new(-180,0,-660),new(-315,0,-720),new(-310,0,-835),new(-100,0,-880)};
    private readonly Dictionary<string, StandardMaterial3D> _materials = new();
    private readonly Dictionary<string, PackedScene> _assetScenes = new();
    private static bool _harbourLaunchConsumed;
    private readonly SystemFont _font = new() { FontNames = new[] { "PingFang HK", "Noto Sans CJK TC", "sans-serif" } };
    private Node3D _steeringWheel = null!;
    private Label3D _cabSpeed = null!, _cabState = null!;

    public override void _Ready()
    {
        SelfTest = OS.GetCmdlineUserArgs().Contains("--self-test") || OS.GetCmdlineUserArgs().Contains("--signal-check") || OS.GetCmdlineUserArgs().Contains("--building-check") || OS.GetCmdlineUserArgs().Contains("--footpath-check") || OS.GetCmdlineUserArgs().Contains("--road-check") || OS.GetCmdlineUserArgs().Contains("--harbour-check") || OS.GetCmdlineUserArgs().Contains("--island-check") || OS.GetCmdlineUserArgs().Contains("--hud-check") || OS.GetCmdlineUserArgs().Contains("--restart-check");
        RegisterInput();
        Map = new RoadMap();
        PrepareParkEntrances();
        BuildEnvironment();
        BuildGovernmentBuildings();
        BuildHarbourScenery();
        BuildStreet();
        BuildNeighborhoods();
        BuildStops();
        BuildTrafficLights();
        BuildRoads();
        BuildRoadDetails();
        BuildFootpaths();
        FinishStreetMeshes();
        Bus = new BusController { Notify = ShowNotice, Moved = CheckSignalCrossing };
        AddChild(Bus);
        Bus.ResetAt(Map.At(22, -7.3f), Map.Heading(22));
        Camera = new Camera3D { Fov = 62, Far = 3200, Near = .7f, Current = true };
        AddChild(Camera);
        BuildCab();
        _vehicleMeshes=Bus.Model.FindChildren("*","MeshInstance3D",true,false).Concat(_cab.FindChildren("*","MeshInstance3D",true,false)).Cast<MeshInstance3D>().ToArray();
        var layer = new CanvasLayer();
        AddChild(layer);
        Hud = new Hud { Game = this };
        layer.AddChild(Hud);
        UpdateCamera(1, true);
        if(!_harbourLaunchConsumed && OS.GetCmdlineUserArgs().Contains("--harbour"))
        { _harbourLaunchConsumed=true;StartHarbourDrive(); }
        if(OS.GetCmdlineUserArgs().Contains("--harbour-review"))CallDeferred(MethodName.CaptureHarbour);
        if (SelfTest) CallDeferred(MethodName.RunChecks);
        if (OS.GetCmdlineUserArgs().Contains("--capture")) CallDeferred(MethodName.CaptureViews);
        if (OS.GetCmdlineUserArgs().Contains("--audio-review")) CallDeferred(MethodName.ReviewAudio);
        if (OS.GetCmdlineUserArgs().Contains("--signal-capture")) CallDeferred(MethodName.CaptureSignals);
        if (OS.GetCmdlineUserArgs().Contains("--building-review") || OS.GetCmdlineUserArgs().Contains("--footpath-review") || OS.GetCmdlineUserArgs().Contains("--road-review")) CallDeferred(MethodName.ReviewScenery);
        GD.Print("ANTILA_READY: government map loaded; 3 stops; Blender GLBs; C# driving");
    }

    private static void RegisterInput()
    {
        foreach (var (name, key) in new (string, Key)[] {
            ("accelerate", Key.W), ("brake", Key.S), ("steer_left", Key.A), ("steer_right", Key.D),
            ("handbrake", Key.Space), ("doors", Key.E), ("camera", Key.C), ("reverse", Key.Q),
            ("tunnel", Key.T), ("island", Key.I), ("restart", Key.R), ("horn", Key.H), ("pause", Key.Escape), ("map", Key.M), ("mute", Key.V) })
        {
            if (InputMap.HasAction(name)) continue;
            InputMap.AddAction(name);
            InputMap.ActionAddEvent(name, new InputEventKey { PhysicalKeycode = key });
        }
        InputMap.ActionAddEvent("accelerate", new InputEventKey { PhysicalKeycode = Key.Up });
        InputMap.ActionAddEvent("brake", new InputEventKey { PhysicalKeycode = Key.Down });
        InputMap.ActionAddEvent("steer_left", new InputEventKey { PhysicalKeycode = Key.Left });
        InputMap.ActionAddEvent("steer_right", new InputEventKey { PhysicalKeycode = Key.Right });
    }

    private StandardMaterial3D Material(string hex, float roughness = .85f)
    {
        if (_materials.TryGetValue(hex, out var material)) return material;
        material = new StandardMaterial3D { AlbedoColor = new Color(hex), Roughness = roughness };
        _materials[hex] = material;
        return material;
    }

    private MeshInstance3D Box(Node3D parent, Vector3 at, Vector3 size, string color, bool solid = false)
    {
        var box = new MeshInstance3D { Position = at, Mesh = new BoxMesh { Size = size }, MaterialOverride = Material(color) };
        parent.AddChild(box);
        if (solid)
        {
            var body = new StaticBody3D { Position = at };
            parent.AddChild(body);
            body.AddChild(new CollisionShape3D { Shape = new BoxShape3D { Size = size } });
        }
        return box;
    }

    private Node3D Asset(string name, Vector3 at, float heading = 0, Vector3? scale = null)
    {
        // Retain scene wrappers while instancing repeatedly; avoid a stale Godot/.NET GC handle.
        if(!_assetScenes.TryGetValue(name,out var scene))_assetScenes[name]=scene=GD.Load<PackedScene>($"res://Assets/Models/{name}.glb");
        var n = scene.Instantiate<Node3D>();
        if(name=="shelter")
            foreach(var mesh in n.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>())
                foreach(var material in Enumerable.Range(0,mesh.Mesh.GetSurfaceCount()).Select(mesh.Mesh.SurfaceGetMaterial).OfType<StandardMaterial3D>().Where(m=>m.ResourceName.Contains("shelter tinted glass")))
                    material.Transparency=BaseMaterial3D.TransparencyEnum.Alpha; // glTF's depth-prepass default casts an opaque pane shadow.
        n.Position = at;
        n.Rotation = new(0, heading, 0);
        if (scale.HasValue) n.Scale = scale.Value;
        float clearance=name switch {"banyan"=>.8f*n.Scale.X,"planter"=>1.1f,"bin"=>.45f,"bench"=>1.6f,"shelter"=>3.4f,_=>0};
        if(clearance>0)_footpathObstacles.Add((at,clearance));
        AddChild(n);
        return n;
    }

    private Label3D Label(Node3D parent, string value, Vector3 at, float pixelSize = .01f, int fontSize = 48)
    {
        var label = new Label3D { Text = value, Position = at, Font = _font, FontSize = fontSize,
            PixelSize = pixelSize, OutlineSize = 0, Modulate = new Color("f3e9cd"), NoDepthTest = false };
        parent.AddChild(label);
        return label;
    }

    private void BuildEnvironment()
    {
        var sky = new ProceduralSkyMaterial {
            SkyTopColor = new("56828d"), SkyHorizonColor = new("cbd5cb"),
            GroundBottomColor = new("4b5757"), GroundHorizonColor = new("cbd5cb"), SkyCurve = .18f };
        AddChild(new WorldEnvironment { Environment = new Godot.Environment {
            BackgroundMode = Godot.Environment.BGMode.Sky, Sky = new Sky { SkyMaterial = sky },
            AmbientLightSource = Godot.Environment.AmbientSource.Color,
            AmbientLightColor = new("c4d6da"), AmbientLightEnergy = .35f,
            ReflectedLightSource = Godot.Environment.ReflectionSource.Sky,
            TonemapMode = Godot.Environment.ToneMapper.Filmic,
            FogEnabled = true, FogLightColor = new("a3b8bf"), FogDensity = .00045f,
            FogLightEnergy = .65f, FogSkyAffect = .15f } });
        AddChild(new DirectionalLight3D { RotationDegrees = new(-48,-38,0), LightColor = new("ffe0af"),
            LightEnergy = .65f, LightCullMask = 1, ShadowEnabled = true, DirectionalShadowMaxDistance = 170 });
        var bounds=Map.Bounds;
        var ground=BuildHarbour();
        _terrain=new ShaderMaterial {Shader=GD.Load<Shader>("res://Assets/Materials/terrain.gdshader")};
        ground.MaterialOverride=_terrain;
        _terrain.SetShaderParameter("map_origin",bounds.Position);_terrain.SetShaderParameter("map_size",bounds.Size);
        _terrain.SetShaderParameter("asphalt",GD.Load<Texture2D>("res://Assets/Textures/asphalt.png"));
        _terrain.SetShaderParameter("paving",GD.Load<Texture2D>("res://Assets/Textures/paving.png"));
        _terrain.SetShaderParameter("grass",GD.Load<Texture2D>("res://Assets/Textures/park-ground.png"));
        _terrain.SetShaderParameter("stone",GD.Load<Texture2D>("res://Assets/Textures/pavement-stone.png"));

    }

    private static void Triangle(SurfaceTool surface,Vector3 a,Vector3 b,Vector3 c)
    {
        foreach(var v in new[]{a,b,c})
        {
            surface.SetNormal(Vector3.Up);surface.SetUV(new Vector2(v.X,v.Z)/2);surface.AddVertex(v);
        }
    }

    private void Stripe(Vector3 p,Vector3 forward,float width,float length,string color)
    {
        if(!_paint.TryGetValue(color,out var surface))
        {
            surface=new SurfaceTool();surface.Begin(Mesh.PrimitiveType.Triangles);_paint[color]=surface;
        }
        var r=forward.Cross(Vector3.Up)*width/2;var f=forward*length/2;p.Y=.072f;
        // Godot front faces wind clockwise; reversed paint faces get lit from below.
        Triangle(surface,p-r-f,p-r+f,p+r-f);Triangle(surface,p+r-f,p-r+f,p+r+f);
    }

    private void Mark(float distance,float lane,float width,float length,string color)
        =>Stripe(Map.At(distance,lane),Map.Forward(distance),width,length,color);

    private void BuildRoads()
    {
        (Vector3 Point,int Road,float Width)? previous=null;
        foreach(var (name,p,f,id,width) in Map.LaneSamples(6))
        {
            if(width>=16 && previous is { } last && last.Road==id && last.Width>=16 && last.Point.DistanceTo(p)<9)
            {
                var direction=(p-last.Point).Normalized();float length=last.Point.DistanceTo(p);
                foreach(int side in new[]{-1,1})
                    LaneStripe((p+last.Point)/2+direction.Cross(Vector3.Up)*side*.16f,direction,.12f,length+.02f,id,"d8d4b9");
            }
            previous=(p,id,width);
        }
        foreach(var (name,p,f,id,width) in Map.LaneSamples(12))
        {
            int lanes=RoadMap.LanesPerDirection(width);
            if(lanes==1)LaneStripe(p,f,.14f,3,id);
            else foreach(int side in new[]{-1,1})
            {
                for(int lane=1;lane<lanes;lane++)
                    LaneStripe(p+f.Cross(Vector3.Up)*side*width*lane/(lanes*2),f,.14f,3,id);
            }
        }
        foreach(var (name,p,f,id) in Map.StreetSamples(2))
            foreach(int side in new[]{-1,1})
            {
                var outwards=f.Cross(Vector3.Up)*side;
                var edge=p+outwards*(RoadMap.Width(name)/2-.3f);
                if(Map.NearOtherRoad(edge+outwards*.7f,id,.4f) ||
                    Map.NearOtherRoad(edge+f,id,.5f) || Map.NearOtherRoad(edge-f,id,.5f))continue;
                Stripe(edge,f,.13f,2.04f,"e5bd58");
            }
        for (float s = 4; s < Map.Length-4; s+=7)
        {
            bool junction = Map.NearSideRoad(Map.At(s), 9);
            if (!junction)
            {
                LaneStripe(Map.At(s,-.16f),Map.Forward(s),.12f,7.03f,-1,"d8d4b9");
                LaneStripe(Map.At(s,.16f),Map.Forward(s),.12f,7.03f,-1,"d8d4b9");
                foreach (var side in new[] {-1,1})
                {
                    LaneStripe(Map.At(s,side*5),Map.Forward(s),.13f,2.3f,-1);
                    Mark(s, side*9.60f, .12f, 7.03f, "e5bd58");
                    Mark(s, side*9.83f, .12f, 7.03f, "e5bd58");
                }
            }
        }
        // Ground markings aligned to actual side-road junctions.
        foreach (float s in new[] {110f,740f})
        {
            for (int x=-8;x<=8;x+=2) Mark(s,x,1,3.6f,"dedec7");
            Mark(s-7,-5,9,.24f,"e3dfc9");
        }
        var bounds=Map.Bounds.Grow(22);
        foreach(float x in new[]{bounds.Position.X,bounds.End.X})
            Box(this,new(x,.65f,bounds.GetCenter().Y),new(.6f,1.3f,bounds.Size.Y),"bb653f",true);
        foreach(float z in new[]{bounds.Position.Y,bounds.End.Y})
        {
            float cursor=bounds.Position.X;
            void Barrier(float start,float end)
            {
                if(end>start)Box(this,new((start+end)/2,.65f,z),new(end-start,1.3f,.6f),"bb653f",true);
            }
            foreach(var p in HarbourRoads.Where(r=>!r.Tunnel).SelectMany(r=>r.Points).Where(p=>Mathf.Abs(p.Z-z)<8).OrderBy(p=>p.X))
            {
                Barrier(cursor,Mathf.Min(p.X-12,bounds.End.X));
                cursor=Mathf.Max(cursor,p.X+12);
            }
            Barrier(cursor,bounds.End.X);
        }

    }

    private void BuildStreet()
    {
        var rng = new Random(7);
        for (float s=20; s<Map.Length; s+=23)
        {
            for(int side=-1;side<=1;side+=2)
            {
                var center=Map.At(s,side*23);
                bool park = side==-1 && InPark(center);
                if(Map.NearSideRoad(center,24)) continue;
                if(park)
                {
                    float start=s-11.4f;
                    foreach(var entrance in _parkEntrances.Where(e=>Mathf.Abs(e.Distance-s)<14).OrderBy(e=>e.Distance))
                    {
                        ParkWall(start,Mathf.Min(s+11.4f,entrance.Distance-2.6f));
                        start=Mathf.Max(start,entrance.Distance+2.6f);
                    }
                    ParkWall(start,s+11.4f);
                    for(int row=0;row<3;row++)
                    {
                        var tree=Map.At(s+rng.Next(-6,6),-20-row*10);float rotation=rng.NextSingle()*3;
                        if(!NearParkEntrance(tree,5))Asset("banyan",tree,rotation,new Vector3(1.5f,1.8f,1.5f));
                    }
                    if(Map.Stops.All(stop=>Mathf.Abs(s-stop.Distance)>18) && !NearParkEntrance(Map.At(s,-12.7f),4))
                        Asset("planter",Map.At(s,-12.7f),Map.Heading(s));
                    continue;
                }
                rng.Next(3);rng.NextSingle(); // Keep the established roadside tree variation.
            }
        }
        for(float s=35;s<Map.Length;s+=42)
        {
            for(int side=-1;side<=1;side+=2)
            {
                if(Map.NearSideRoad(Map.At(s,side*11.5f),8))continue;
                var lamp=new Node3D {Position=Map.At(s,side*11.6f),Rotation=new(0,Map.Heading(s),0)};
                AddChild(lamp);
                Box(lamp,new(0,4.2f,0),new(.12f,8.4f,.12f),"89918a");
                Box(lamp,new(-side*.9f,8.3f,0),new(1.9f,.10f,.10f),"89918a");
                Box(lamp,new(-side*1.75f,8.25f,0),new(.55f,.12f,.35f),"e7d6ad");
                if(side==1 && (int)s%2==1 && !Map.NearSideRoad(Map.At(s+13,12.7f),9))
                {
                    var at=Map.At(s+13,12.7f);
                    var pit=Box(this,at+Vector3.Up*.07f,new(2.3f,.05f,2.3f),"444339");
                    pit.Rotation=new(0,Map.Heading(s),0);
                    Asset("banyan",at,rng.NextSingle()*Mathf.Tau,new(.65f,.95f,.65f));
                }
            }
        }
        // Readable place signs give the corridor its real-world context.
        foreach(var (s,name,zh) in new[]{(95f,"NATHAN ROAD","彌敦道"),(370f,"HAIPHONG ROAD","海防道"),(990f,"JORDAN","佐敦")})
        {
            var sign=new Node3D {Position=Map.At(s,10.9f),Rotation=new(0,Map.Heading(s),0)};
            AddChild(sign);
            Box(sign,new(0,2.8f,0),new(.12f,5.6f,.12f),"969d94");
            Box(sign,new(-1.5f,4.9f,0),new(4.6f,1.25f,.12f),"226255");
            Label(sign,zh+"\n"+name,new(-1.5f,4.9f,.075f),.013f,34);
        }
        for(int i=0;i<7;i++)
        {
            float distance=172+i*145;
            var body=new StaticBody3D {CollisionMask=3,Position=Map.At(distance,7.35f),Rotation=new(0,Map.Heading(distance)+Mathf.Pi,0)};
            AddChild(body);
            var taxi=GD.Load<PackedScene>("res://Assets/Models/taxi.glb").Instantiate<Node3D>();
            body.AddChild(taxi);
            body.AddChild(new CollisionShape3D {Shape=new BoxShape3D {Size=new(1.8f,1.6f,4.5f)},Position=new(0,.85f,0)});
            _traffic.Add((body,distance));
        }
    }

    private bool InPark(Vector3 p)=>Geometry2D.IsPointInPolygon(new(p.X,p.Z),_park);

    private void FinishStreetMeshes()
    {
        foreach(var (color,surface) in _paint)
        {
            var mesh=surface.Commit();
            if(SelfTest)
            {
                var vertices=mesh.SurfaceGetArrays(0)[(int)Mesh.ArrayType.Vertex].AsVector3Array();
                for(int i=0;i<vertices.Length;i+=3)
                    if((vertices[i+1]-vertices[i]).Cross(vertices[i+2]-vertices[i]).Y>=0)
                        throw new Exception("Road paint must face upward with clockwise winding");
            }
            AddChild(new MeshInstance3D {Mesh=mesh,MaterialOverride=new StandardMaterial3D {AlbedoColor=new(color),Roughness=.95f},CastShadow=GeometryInstance3D.ShadowCastingSetting.Off});
            surface.Dispose();
        }
        _paint.Clear();
        var pads=_lots.SelectMany(l=>Geometry2D.OffsetPolygon(l.Polygon,3)).Concat(_pavementPatches.Select(p=>p.Polygon));
        using(var mask=Map.CreateSurfaceMask(_park,ParkPaths(),pads))
        {
            var texture=ImageTexture.CreateFromImage(mask);_terrain.SetShaderParameter("surface_mask",texture);
            _harbourPaint.SetShaderParameter("district_mask",texture);
        }
        var harbourRoads=HarbourRoads.Where(r=>!r.Tunnel).SelectMany(r=>Enumerable.Range(1,r.Points.Count-1)
            .Select(i=>(new Vector2(r.Points[i-1].X,r.Points[i-1].Z),new Vector2(r.Points[i].X,r.Points[i].Z),6f)));
        using(var mask=Map.CreateSurfaceMask(Array.Empty<Vector2>(),Array.Empty<(Vector3,Vector3)>(),pads.Concat(_harbourPaving),HarbourBounds,harbourRoads,2))
            _terrain.SetShaderParameter("harbour_mask",ImageTexture.CreateFromImage(mask));
        _terrain.SetShaderParameter("harbour_origin",HarbourBounds.Position);_terrain.SetShaderParameter("harbour_size",HarbourBounds.Size);
    }

    private void BuildNeighborhoods()
    {
        var rng=new Random(41);
        var path=_parkPath;
        var trees=new List<Vector3>();
        for(int i=0;i<400;i++)
        {
            var p=new Vector3(rng.Next(-410,-65),0,rng.Next(-900,-375));
            bool nearPath=Enumerable.Range(0,path.Count-1).Any(j=>p.DistanceTo(Geometry3D.GetClosestPointToSegment(p,path[j],path[j+1]))<8);
            if(InPark(p) && !nearPath && Map.ClearOfRoads(p,7) && trees.All(t=>t.DistanceTo(p)>14))
            {
                trees.Add(p);float size=.85f+rng.NextSingle()*.65f;
                float rotation=rng.NextSingle()*Mathf.Tau;
                if(!NearParkEntrance(p,7))Asset("banyan",p,rotation,new(size,size*1.15f,size));
            }
        }
        foreach(var (name,p,f,id) in Map.StreetSamples(20))
        {
            float heading=Mathf.Atan2(-f.X,-f.Z);var right=f.Cross(Vector3.Up);
            foreach(int side in new[]{-1,1})
            {
                rng.Next(3);rng.NextSingle(); // Preserve the decoration sequence from the former building grid.
                if(id%2!=0 || Map.NearOtherRoad(p,id,10))continue;
                var tree=p+right*(side*(RoadMap.Width(name)/2+1.8f));
                if(Map.ClearOfRoads(tree,1.2f) && trees.All(t=>t.DistanceTo(tree)>22))
                {
                    trees.Add(tree);Asset("banyan",tree,heading,new(.5f,.8f,.5f));
                    Box(this,tree+Vector3.Up*.025f,new(1.6f,.03f,1.6f),"4a4e40");
                }
            }
        }
        foreach(var (at,name,zh) in new[]{
            (new Vector3(-307,0,-339),"CANTON ROAD","廣東道"),
            (new Vector3(263,0,-479),"CHATHAM ROAD SOUTH","漆咸道南"),
            (new Vector3(595,0,-509),"SCIENCE MUSEUM ROAD","科學館道")})
        {
            Box(this,at+Vector3.Up*2.8f,new(.12f,5.6f,.12f),"969d94");
            Box(this,at+new Vector3(0,5,0),new(5.5f,1.2f,.12f),"226255");
            Label(this,zh+"\n"+name,at+new Vector3(0,5,.075f),.012f,32);
        }
        GD.Print($"ANTILA_MAP: {Map.Bounds.Size.X:0} × {Map.Bounds.Size.Y:0} m; {Map.SideRoads.Select(r=>r.Name).Distinct().Count()} side streets; {Map.SourceSections} sections joined to {Map.SideRoads.Count} polylines");
    }

    private void BuildStops()
    {
        for(int i=0;i<Map.Stops.Count;i++)
        {
            var stop=Map.Stops[i];
            var shelter=Asset("shelter",Map.At(stop.Distance,-12.2f),Map.Heading(stop.Distance)+Mathf.Pi/2);
            Asset("bench",Map.At(stop.Distance+12,-12.5f),Map.Heading(stop.Distance)+Mathf.Pi/2);
            Asset("bin",Map.At(stop.Distance-7,-12.7f));
            Asset("planter",Map.At(stop.Distance+15,-12.5f),Map.Heading(stop.Distance));
            var poster=new MeshInstance3D {Mesh=new QuadMesh {Size=new(1.19f,1.83f)},Position=new(2,1.4f,-.622f),
                MaterialOverride=new StandardMaterial3D {AlbedoTexture=GD.Load<Texture2D>("res://Assets/Textures/kowloon-poster.png"),Roughness=.9f}};
            shelter.AddChild(poster);
            var label=Label(shelter,stop.Name.ToUpper()+"  /  "+stop.Chinese,new(0,2.48f,1.32f),.009f,30);
            for(float d=stop.Distance-7;d<stop.Distance+8;d+=3)
                Mark(d,-5.1f,.15f,1.5f,"e1b954");
            Mark(stop.Distance-8,-7.3f,4.4f,.15f,"e1b954");
            Mark(stop.Distance+8,-7.3f,4.4f,.15f,"e1b954");
            var people=new Node3D();AddChild(people);_waiting.Add(people);
            for(int p=0;p<4;p++)
            {
                var at=Map.At(stop.Distance-3+p*1.45f,-11.1f);
                string model=new[]{"mei","dennis","family","headphones"}[(p+i)%4];
                var passenger=GD.Load<PackedScene>($"res://Assets/Models/passenger_{model}.glb").Instantiate<Node3D>();
                people.AddChild(passenger);
                passenger.Position=at+Vector3.Up*.05f;
                passenger.Rotation=new(0,Map.Heading(stop.Distance)+Mathf.Pi/2+(p%2==0?-.12f:.10f),0);
                foreach(MeshInstance3D mesh in passenger.FindChildren("*","MeshInstance3D",true,false))
                    mesh.VisibilityRangeEnd=160;
            }
        }
        _stopMarker=new Node3D();AddChild(_stopMarker);
        var targetMat=new StandardMaterial3D {AlbedoColor=new Color(.39f,.85f,.7f,.32f),Transparency=BaseMaterial3D.TransparencyEnum.Alpha,
            ShadingMode=BaseMaterial3D.ShadingModeEnum.Unshaded,CullMode=BaseMaterial3D.CullModeEnum.Disabled};
        _stopMarker.AddChild(new MeshInstance3D {Mesh=new CylinderMesh {TopRadius=2,BottomRadius=2,Height=.03f,RadialSegments=48},MaterialOverride=targetMat});
    }

    private void BuildCab()
    {
        _cab=new Node3D();Camera.AddChild(_cab);_cab.Visible=false;
        Box(_cab,new(0,-.64f,-1.05f),new(2.6f,.4f,.75f),"293638");
        Box(_cab,new(.05f,-.35f,-.99f),new(.76f,.26f,.18f),"101c1e");
        Box(_cab,new(.05f,-.35f,-.893f),new(.69f,.21f,.012f),"080f10");
        _cabSpeed=Label(_cab,"0 km/h",new(-.15f,-.30f,-.88f),.0013f,36);
        _cabState=Label(_cab,"D  •  READY",new(.15f,-.345f,-.88f),.001f,30);
        Label(_cab,"ANTILA",new(.15f,-.27f,-.88f),.0008f,24);
        foreach(float x in new[]{.49f,.58f,.67f})
        {
            Box(_cab,new(x,-.465f,-.87f),new(.065f,.055f,.018f),"151d1d");
            Box(_cab,new(x,-.462f,-.859f),new(.04f,.008f,.005f),"7e9391");
        }
        for(int i=0;i<7;i++)Box(_cab,new(-.46f+i*.035f,-.46f,-.88f),new(.012f,.06f,.01f),"111919");
        Box(_cab,new(-.73f,-.34f,-1),new(.18f,.48f,.18f),"263638");
        Box(_cab,new(-.73f,-.22f,-.89f),new(.14f,.16f,.02f),"719d94");
        foreach(float x in new[]{-.87f,1.3f})Box(_cab,new(x,.3f,-1.5f),new(.10f,2.4f,.15f),"cac4ad");
        _steeringWheel=new Node3D {Position=new(0,-.55f,-.72f),RotationDegrees=new(62,0,0)};
        _cab.AddChild(_steeringWheel);
        _steeringWheel.AddChild(new MeshInstance3D {Mesh=new TorusMesh {InnerRadius=.205f,OuterRadius=.24f,Rings=24,RingSegments=8},MaterialOverride=Material("101c1e")});
        Box(_steeringWheel,Vector3.Zero,new(.43f,.035f,.045f),"313e3e");
        Box(_steeringWheel,new(0,0,.12f),new(.045f,.035f,.20f),"313e3e");
    }

    private void UpdateCabInstruments()
    {
        _cabSpeed.Text=$"{Bus.Kmh:0} km/h";
        _cabState.Text=$"{(Bus.Reverse?"R":"D")}  •  {(Bus.DoorsOpen?"DOORS OPEN":"READY")}";
        _cabState.Modulate=new Color(Bus.DoorsOpen?"f3bb55":"9fdbbb");
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if(e.IsActionPressed("pause"))
        {
            if(MapOpen)MapOpen=false; else Paused=!Paused;
            Bus.SetPaused(Paused || Complete);
            return;
        }
        if(e.IsActionPressed("map")) { MapOpen=!MapOpen; Bus.SetPaused(Paused || Complete || MapOpen); return; }
        if(e.IsActionPressed("tunnel")){StartHarbourDrive();return;}
        if(e.IsActionPressed("island")){StartHarbourDrive(3);return;}
        if(e.IsActionPressed("restart"))
        {
            // As on quit, finish temporary C# wrappers before replacing their native scene/resources.
            GC.Collect();GC.WaitForPendingFinalizers();
            GetTree().ReloadCurrentScene();return;
        }
        if(e.IsActionPressed("camera")) { SetCab(!CabView); return; }
        if(e.IsActionPressed("mute")) { AudioServer.SetBusMute(0,!AudioServer.IsBusMute(0)); return; }
        if(e is InputEventKey { Pressed:true, Keycode:Key.F12 }) { Capture(); return; }
        if(Paused || Complete || MapOpen)return;
        if(e.IsActionPressed("doors"))Bus.ToggleDoors();
        if(e.IsActionPressed("reverse"))Bus.ToggleReverse();
        if(e.IsActionPressed("horn"))Bus.Horn();
    }

    public void SetCab(bool cab)
    {
        CabView=cab;
        Bus.CabAudio=cab;
        Bus.Model.Visible=!cab;
        _cab.Visible=cab;
        Camera.Fov=cab?73:62;
        Camera.Near=cab?.25f:.7f;
        UpdateCamera(1,true);
        UpdateCabInstruments();
    }

    public void ShowNotice(string text) { Notice=text; NoticeTime=4; }

    private void QuitGame(int code=0)
    {
        // Release temporary C# resource wrappers before Godot 4.6 tears down its instance bindings.
        GC.Collect();
        GC.WaitForPendingFinalizers();
        GetTree().Quit(code);
    }

    private async void Capture()
    {
        await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
        string path=ProjectSettings.GlobalizePath($"res://evidence/{(CabView?"cab":"chase")}.png");
        GetViewport().GetTexture().GetImage().SavePng(path);
        GD.Print("CAPTURE_SAVED: "+path);
    }

    private async void CaptureViews()
    {
        SelfTest=true; // Keep automatic boarding from advancing while shaders compile for captures.
        await ToSignal(GetTree().CreateTimer(2),SceneTreeTimer.SignalName.Timeout);
        foreach(bool cab in new[]{false,true})
        {
            SetCab(cab);
            await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
            GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath($"res://evidence/{(cab?"cab":"chase")}.png"));
        }
        SetCab(false);
        float parkStop=Map.Stops[1].Distance;
        Bus.ResetAt(Map.At(parkStop,-7.3f),Map.Heading(parkStop));
        StopIndex=1;
        Bus.ToggleDoors();
        await ToSignal(GetTree().CreateTimer(1),SceneTreeTimer.SignalName.Timeout);
        await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/park-stop.png"));
        SetProcess(false);
        Camera.Position=Map.At(parkStop+18,-9.8f)+Vector3.Up*3.5f;
        Camera.LookAt(Map.At(parkStop,-9.5f)+Vector3.Up*1.8f);
        await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/bus-and-shelter.png"));
        Hud.Visible=false;
        Camera.Position=Map.At(parkStop+28,-9)+Vector3.Up*3.5f;
        Camera.LookAt(Map.At(parkStop+11,-18)+Vector3.Up*4.8f);
        await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/decoration.png"));
        Bus.Model.Visible=false;
        Camera.Position=Map.At(parkStop+1,-6.8f)+Vector3.Up*1.7f;
        Camera.LookAt(Map.At(parkStop-1,-11.1f)+Vector3.Up*1.10f);
        await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/passengers.png"));
        Bus.Model.Visible=true;
        Hud.Visible=true;
        NoticeTime=0;
        Bus.ResetAt(Map.At(220,-7.3f),-Mathf.Pi/2);
        UpdateCamera(1,true);Hud.QueueRedraw();
        await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/camera-wall.png"));
        foreach(var (name,position,heading) in new[]{
            ("west-street",new Vector3(-225,0,-337),Mathf.Pi/2),
            ("east-street",new Vector3(485,0,-598),-1.2f)})
        {
            Bus.ResetAt(position,heading);
            UpdateCamera(1,true);Hud.QueueRedraw();
            await ToSignal(GetTree().CreateTimer(.5f),SceneTreeTimer.SignalName.Timeout);
            await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
            GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath($"res://evidence/{name}.png"));
        }
        MapOpen=true;Hud.QueueRedraw();
        await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/map.png"));
        Hud.Visible=false;
        // A clear survey view makes the full extent readable above the street-level haze.
        GetChildren().OfType<WorldEnvironment>().First().Environment.FogEnabled=false;
        Camera.Near=10;Camera.Far=3200;Camera.Position=new(20,1200,200);Camera.LookAt(new(0,0,-600));
        await ToSignal(GetTree().CreateTimer(.5f),SceneTreeTimer.SignalName.Timeout);
        await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/wide-map.png"));
        foreach(var (name,position,target) in new[]{
            ("junction-salisbury",new Vector3(140,95,100),new Vector3(15,0,5)),
            ("junction-chatham",new Vector3(485,95,-390),new Vector3(355,0,-510)),
            ("density-block",new Vector3(80,175,-780),new Vector3(-210,0,-1030))})
        {
            Camera.Position=position;Camera.LookAt(target);
            await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
            GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath($"res://evidence/{name}.png"));
        }
        GD.Print($"ANTILA_CAPTURE_OK: chase, cab, park stop, bus/shelter, decoration, passengers, west/east streets, map and aerial; FPS {Engine.GetFramesPerSecond()}");
        QuitGame();
    }

    public override void _Process(double delta)
    {
        if(Bus==null)return;
        float dt=(float)delta;
        if(!Paused && !Complete && !MapOpen)
        {
            Elapsed+=dt;
            NoticeTime=Mathf.Max(0,NoticeTime-dt);
            if(!SelfTest && !HarbourDrive)AdvanceService(dt);
        }
        _stopMarker.Visible=!Complete && !HarbourDrive;
        if(!Complete)_stopMarker.Position=Map.At(Map.Stops[StopIndex].Distance,-7.3f)+Vector3.Up*.08f;
        UpdateCamera(dt,false);
        UpdateVehicleLighting();
        UpdateCabInstruments();
        Hud.QueueRedraw();
    }

    public override void _PhysicsProcess(double delta)
    {
        if(Bus==null || Paused || Complete || MapOpen)return;
        _signalClock=Mathf.PosMod(_signalClock+(float)delta,54);
        UpdateSignals();
        // ponytail: fixed-speed lane followers; add junction decisions with network traffic routing.
        for(int i=0;i<_traffic.Count;i++)
        {
            var (body,distance)=_traffic[i];
            float travel=(float)delta*6.5f;
            var (signal,metres)=NextSignal(body.Transform,2.25f);
            if(signal!=null && signal.Aspect!=SignalAspect.Green)travel=Mathf.Min(travel,Mathf.Max(0,metres-1.2f));
            float next=Mathf.PosMod(distance-12-travel,Map.Length-25)+12;
            var destination=new Transform3D(new Basis(Vector3.Up,Map.Heading(next)+Mathf.Pi),Map.At(next,7.35f));
            bool wraps=next>distance;
            var from=wraps?destination:new Transform3D(destination.Basis,body.Position);
            var motion=wraps?Vector3.Zero:destination.Origin-body.Position;
            if(body.TestMove(from,motion,null,.02f,true))continue;
            body.Transform=destination;
            _traffic[i]=(body,next);
        }
    }

    public bool IsAtStop()
    {
        if(Complete)return false;
        var target=Map.Stops[StopIndex];
        var (distance,lateral)=Map.Project(Bus.GlobalPosition);
        return Mathf.Abs(distance-target.Distance)<7 && Mathf.Abs(lateral+7.3f)<1.6f &&
            (-Bus.GlobalBasis.Z).Dot(Map.Forward(target.Distance))>.94f;
    }

    public void AdvanceService(float dt)
    {
        if(Complete)return;
        if(IsAtStop() && Bus.DoorsOpen && Bus.Kmh<.5f)
        {
            Boarding+=dt;
            if(Boarding>=4)
            {
                Passengers+=Map.Stops[StopIndex].Passengers;
                _waiting[StopIndex].Visible=false;
                StopIndex++;
                Boarding=0;
                if(StopIndex==Map.Stops.Count)
                {
                    Complete=true;
                    Bus.SetPhysicsProcess(false);
                    Bus.StopAudio();
                    ShowNotice("Service complete. Thank you for driving H1.");
                }
                else ShowNotice("Passengers aboard. Close doors with E, then continue north.");
                Bus.Sound("stop-bell");
            }
        }
        else Boarding=0;
    }

    private void UpdateCamera(float dt,bool snap)
    {
        Vector3 target;
        if(CabView)
        {
            Camera.GlobalTransform=Bus.GlobalTransform*new Transform3D(Basis.Identity,new(.73f,2.02f,-4.65f));
            _steeringWheel.Rotation=new(Mathf.DegToRad(62),Bus.Steering*2,0);
            return;
        }
        target=Bus.ToGlobal(new(0,7.6f,15.8f));
        target=snap?target:Camera.GlobalPosition.Lerp(target,1-Mathf.Exp(-5*dt));
        var origin=Bus.GlobalPosition+Vector3.Up*(Bus.Position.Y<-1?3.5f:4.6f);
        _cameraSweep.Transform=new(Basis.Identity,origin);
        _cameraSweep.Motion=target-origin;
        float fraction=GetWorld3D().DirectSpaceState.CastMotion(_cameraSweep)[0];
        Camera.GlobalPosition=origin+_cameraSweep.Motion*fraction;
        Camera.LookAt(Bus.GlobalPosition-Bus.GlobalBasis.Z*5+Vector3.Up*2.6f);
    }

    private async System.Threading.Tasks.Task CheckSideStreet(string name,float junction,bool west)
    {
        var parts=Map.SideRoads.Where(r=>r.Name==name).Select(r=>new List<Vector3>(r.Points)).ToList();
        var source=new List<Vector3>();
        var cursor=Map.At(junction);
        while(parts.Count>0)
        {
            var line=parts.OrderBy(p=>Mathf.Min(p[0].DistanceTo(cursor),p[^1].DistanceTo(cursor))).First();
            if(line[^1].DistanceTo(cursor)<line[0].DistanceTo(cursor))line.Reverse();
            if(source.Count>0 && line[0].DistanceTo(cursor)>1)throw new Exception(name+" source junction gap");
            source.AddRange(line);cursor=line[^1];parts.Remove(line);
        }
        var path=new List<Vector3>();
        for(float d=junction-45;d<junction+(west?-6:9);d+=5)path.Add(Map.At(d,-7.3f));
        float travelled=0;
        for(int i=0;i<source.Count-1;i++)
        {
            var delta=source[i+1]-source[i];float length=delta.Length();
            if(length<.01f)continue;
            var f=delta/length;
            for(float d=0;d<length;d+=4)
                if(travelled+d>25)path.Add(source[i]+f*d-f.Cross(Vector3.Up)*2.5f);
            travelled+=length;
        }
        Bus.ResetAt(path[0],Map.Heading(junction-45));
        int contacts=Bus.Collisions;
        int redLights=RedLightCrossings;
        float before=Bus.DistanceDriven;
        for(int tick=0;tick<5000;tick++)
        {
            int closest=0;float best=float.MaxValue;
            for(int i=0;i<path.Count;i++)
            {
                float distance=Bus.Position.DistanceTo(path[i]);
                if(distance<best){best=distance;closest=i;}
            }
            if(closest>=path.Count-2)break;
            var target=path[closest];
            float ahead=8;
            for(int i=closest+1;i<path.Count;i++)
            {
                float step=target.DistanceTo(path[i]);
                if(step>=ahead){target=target.Lerp(path[i],ahead/step);break;}
                ahead-=step;target=path[i];
            }
            var direction=target-Bus.Position;
            float error=Mathf.AngleDifference(Bus.Rotation.Y,Mathf.Atan2(-direction.X,-direction.Z));
            Bus.TestSteer=Mathf.Clamp(Mathf.Atan(12*Mathf.Sin(error)/Mathf.Max(6,direction.Length()))/Mathf.DegToRad(32),-1,1);
            Bus.TestBrake=Bus.Speed>6 || TestSignalBrake()?1:0;
            // The test driver yields before a right turn across the southbound taxi lane.
            float toJunctionLine=junction-16-5.275f-Map.Project(Bus.Position).Distance;
            if(!west && toJunctionLine>=0 && toJunctionLine<Bus.Speed*Bus.Speed/8+2 &&
                _traffic.Any(t=>t.Distance>junction-12 && t.Distance<junction+65))Bus.TestBrake=1;
            Bus.TestThrottle=Bus.TestBrake==0 && Bus.Speed<5.5f?1:0;
            if(Map.NearestStreet(Bus.Position).Distance>11)throw new Exception(name+" left the road at "+Bus.Position);
            await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        }
        if(Bus.Position.DistanceTo(path[^1])>12 || Bus.Collisions!=contacts || RedLightCrossings!=redLights || Bus.DistanceDriven-before<travelled-25)
            throw new Exception($"{name} driving failed: {Bus.Position}, contacts {Bus.Collisions-contacts}, distance {Bus.DistanceDriven-before:0}");
        if(west?Bus.Position.X>=-340:Bus.Position.X<=600)throw new Exception(name+" did not reach the expansion");
        GD.Print($"ANTILA_SIDE_STREET_OK: turned from Nathan Road onto {name}; {Bus.DistanceDriven-before:0} m; x={Bus.Position.X:0}; no contacts");
        Bus.TestThrottle=0;Bus.TestBrake=0;Bus.TestSteer=0;
    }

    private void CheckStreetClearance()
    {
        var roadQuery=new PhysicsShapeQueryParameters3D {
            Shape=new BoxShape3D {Size=new(2.48f,4.2f,10.55f)},CollisionMask=1,
            Exclude=new Godot.Collections.Array<Rid>(_traffic.Select(t=>t.Body.GetRid()))};
        int roadSamples=0;
        var driveSamples=Map.StreetSamples(10).Select(s=>(s.Point,s.Forward))
            .Concat(Map.RoadPoints.Take(Map.RoadPoints.Count-1).Select((p,i)=>(p,(Map.RoadPoints[i+1]-p).Normalized())));
        foreach(var (p,f) in driveSamples)
        {
            roadQuery.Transform=new(new Basis(Vector3.Up,Mathf.Atan2(-f.X,-f.Z)),p+Vector3.Up*2.3f);
            var hits=GetWorld3D().DirectSpaceState.IntersectShape(roadQuery,1);
            if(hits.Count>0)throw new Exception($"road obstructed near {Map.NearestStreet(p).Name}: {p}; {(hits[0]["collider"].AsGodotObject() as Node)?.GetPath()}");roadSamples++;
        }
        GD.Print($"ANTILA_ROAD_AUDIT_OK: {roadSamples} bus-sized road clearance queries, including both former Nathan Road barriers");
    }

    private async void RunChecks()
    {
        try
        {
            void Check(bool ok,string message) { if(!ok)throw new Exception(message); }
            await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            if(OS.GetCmdlineUserArgs().Contains("--restart-check")){await CheckRestart();return;}
            if(OS.GetCmdlineUserArgs().Contains("--hud-check")){CheckHud();await CheckReviewRegressions();QuitGame();return;}
            CheckStreetClearance();
            if(OS.GetCmdlineUserArgs().Contains("--harbour-check") || OS.GetCmdlineUserArgs().Contains("--island-check")){await CheckHarbour();QuitGame();return;}
            CheckRoadMarkings();
            if(OS.GetCmdlineUserArgs().Contains("--road-check")) { QuitGame(); return; }
            await CheckBuildings();
            CheckAssetDetails();
            await CheckFootpaths();
            if(OS.GetCmdlineUserArgs().Contains("--footpath-check")) { QuitGame(); return; }
            if(OS.GetCmdlineUserArgs().Contains("--building-check")) { QuitGame(); return; }
            await CheckAudio();
            CheckHud();
            await CheckReviewRegressions();
            await CheckTrafficSignals();
            if(OS.GetCmdlineUserArgs().Contains("--signal-check")) { QuitGame(); return; }
            await CheckHarbour();
            Check(Map.Points.Count==231 && Map.Length==1150,"map geometry");
            Check(Map.Bounds.Size.X>2000 && Map.SourceSections==437,"expanded road extract");
            Check(Map.SideRoads.Any(r=>r.Name=="SCIENCE MUSEUM ROAD") && Map.SideRoads.Any(r=>r.Name=="CANTON ROAD"),"east/west streets");
            _UnhandledInput(new InputEventAction {Action="map",Pressed=true});
            Check(MapOpen && !Bus.IsPhysicsProcessing(),"overview must pause driving");
            _UnhandledInput(new InputEventAction {Action="map",Pressed=true});
            Check(!MapOpen && Bus.IsPhysicsProcessing(),"closing overview must resume driving");
            int haiphong=Map.SideRoads.FindIndex(r=>r.Name=="HAIPHONG ROAD");
            Check(!Map.CanPaintLane(Map.At(350),Vector3.Left,haiphong),"lane paint must stop at Nathan/Haiphong junction");
            Check(Map.CanPaintLane(new(-200,0,-342),Vector3.Left,haiphong),"open street lane paint must remain");
            using(var mask=((Texture2D)_terrain.GetShaderParameter("surface_mask").AsGodotObject()).GetImage())
            {
                Color SurfaceAt(Vector3 p)
                {
                    var uv=(new Vector2(p.X,p.Z)-Map.Bounds.Position)/Map.Bounds.Size;
                    return mask.GetPixel((int)(uv.X*mask.GetWidth()),(int)(uv.Y*mask.GetHeight()));
                }
                Check(SurfaceAt(Map.At(220)).R>.99f,"terrain asphalt must follow Nathan Road");
                Check(SurfaceAt(new(-250,0,-550)).B>.99f,"terrain park mask");
                Check(SurfaceAt(_lots[0].Center).G>.99f,"terrain pavement under building lots");
            }
            Check(_lots.Count>1500 && _lots.Count(l=>l.Height>75)>70,"government building density and tower variation");
            Check(Map.RoadPoints[0].Z>0 && Map.RoadPoints[^1].Z<-Map.Length,"Nathan Road must reach the surrounding junctions");
            await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            Check(_waiting.Count==3 && _waiting.All(group=>group.GetChildCount()==4),"passenger models at every stop");
            float v=0;
            for(int i=0;i<600;i++)v=BusController.IntegrateSpeed(v,1,0,false,false,1f/60);
            Check(v>14 && v<14.5f,"acceleration/speed cap");
            for(int i=0;i<180;i++)v=BusController.IntegrateSpeed(v,0,1,false,false,1f/60);
            Check(v==0,"brakes must stop without reversing");
            Check(BusController.IntegrateSpeed(0,1,0,false,true,1)==0,"door interlock");
            Check(BusController.IntegrateSpeed(0,1,0,true,false,1)<0,"reverse");
            var initial=Bus.Position;
            Bus.AutomaticTest=true;Bus.TestThrottle=1;
            for(int i=0;i<90;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            Check(Bus.Position.DistanceTo(initial)>1,"bus must move through physics");
            Check(!Bus.ToggleDoors(),"moving door lock");
            Bus.TestThrottle=0;Bus.TestBrake=1;
            for(int i=0;i<60;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            Check(Bus.Kmh<.5f,"physics brake");
            Bus.TestBrake=0;
            Bus.ResetAt(Map.At(55,7.3f),Map.Heading(55));
            Bus.ToggleDoors();AdvanceService(5);
            Check(StopIndex==0,"wrong side must not board");
            Engine.TimeScale=4;
            Bus.ResetAt(Map.At(80,-7.3f),Map.Heading(80));
            Bus.ToggleReverse();Bus.TestThrottle=1;
            initial=Bus.Position;
            for(int i=0;i<30;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            Check(Bus.Position.Z>initial.Z+1,"physical reverse travel");
            Bus.ResetAt(new Vector3(Map.Bounds.End.X+7,0,-550),-Mathf.Pi/2);
            for(int i=0;i<85;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            Check(Bus.Collisions>0 && Bus.Position.X<Map.Bounds.End.X+17,$"outer barrier must block the bus: contacts={Bus.Collisions}, position={Bus.Position}");
            Bus.TestThrottle=0;Bus.TestBrake=0;
            await CheckSideStreet("HAIPHONG ROAD",350,true);
            await CheckSideStreet("GRANVILLE ROAD",503,false);
            int contacts=Bus.Collisions;
            int redLights=RedLightCrossings;
            float serviceStartDistance=Bus.DistanceDriven;
            Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
            // Drive the complete corridor using the same steering, brakes and body collision path.
            for(int tick=0;tick<7500 && !Complete;tick++)
            {
                var projected=Map.Project(Bus.Position);
                float remaining=Map.Stops[StopIndex].Distance-projected.Distance;
                float lookahead=12;
                var direction=Map.At(projected.Distance+lookahead,-7.3f)-Bus.Position;
                float desired=Mathf.Atan2(-direction.X,-direction.Z);
                float error=Mathf.AngleDifference(Bus.Rotation.Y,desired);
                Bus.TestSteer=Mathf.Clamp(Mathf.Atan(12*Mathf.Sin(error)/lookahead)/Mathf.DegToRad(32),-1,1);
                Bus.TestBrake=remaining<Bus.Speed*Bus.Speed/8+2 || TestSignalBrake()?1:0;
                Bus.TestThrottle=Bus.TestBrake==0 && Bus.Speed<9?1:0;
                if(IsAtStop() && Bus.Kmh<.5f)
                {
                    if(!Bus.DoorsOpen)Bus.ToggleDoors();
                    AdvanceService((float)GetPhysicsProcessDeltaTime());
                }
                else if(Bus.DoorsOpen)Bus.ToggleDoors();
                await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            }
            Check(Complete && Passengers==26,"full service completion");
            Check(!AudioClip("music").Playing,"service completion must stop background music");
            Check(_waiting.All(group=>!group.Visible),"boarded passenger queues must disappear");
            Check(Bus.Collisions==contacts,"corridor must be drivable without collision");
            Check(RedLightCrossings==redLights,"route driver must obey red traffic lights");
            Check(Bus.DistanceDriven-serviceStartDistance>1070,"full route must be physically driven");
            GD.Print("ANTILA_SELF_TEST_OK: map, acceleration, brakes, physical reverse, moving-door lock, barrier collision, wrong-side rejection; drove 1.08 km with steering, 3 stops, 26 passengers, no route contacts");
            QuitGame();
        }
        catch(Exception error) { GD.PushError("ANTILA_SELF_TEST_FAILED: "+error); QuitGame(1); }
    }

    private void CheckHud()
    {
        var failures=new List<string>();
        void Check(bool ok,string message){if(!ok)failures.Add(message);}
        var saved=Bus.GlobalTransform;float notice=NoticeTime;bool harbour=HarbourDrive;
        int stopIndex=StopIndex;StopIndex=0;
        NoticeTime=0;
        foreach(bool freeDrive in new[]{false,true})
        {
            HarbourDrive=freeDrive;
            foreach(int node in new[]{709,899})
            {
                var points=_harbourRoutes[3].Points;var p=points[node];var f=(points[node+1]-p).Normalized();
                Bus.GlobalPosition=p-f.Cross(Vector3.Up)*1.8f;
                Check(!Hud.OncomingLaneWarning,$"False island lane warning at node {node}, free drive {freeDrive}");
                if(!freeDrive)Check(Hud.ServiceInstruction.StartsWith("Exploring"),$"Island node {node} displays H1 stop distance");
            }
            foreach(bool southbound in new[]{false,true})
                foreach(float lane in new[]{-7.3f,7.3f})
                {
                    Bus.GlobalPosition=Map.At(700,lane);Bus.Rotation=new(0,Map.Heading(700)+(southbound?Mathf.Pi:0),0);
                    bool wrongSide=southbound?lane<0:lane>0;
                    Check(Hud.OncomingLaneWarning==wrongSide,$"Lane warning: southbound={southbound}, lane={lane}, free drive={freeDrive}");
                }
            Bus.GlobalPosition=Map.At(700,7.3f);Bus.Rotation=new(0,Map.Heading(700)+Mathf.Pi/2,0);
            Check(!Hud.OncomingLaneWarning,"Perpendicular turning pose must not receive a directional lane warning");
            Bus.Rotation=new(0,Map.Heading(350),0);
            Bus.GlobalPosition=Map.At(350,7.3f);
            Check(!Hud.OncomingLaneWarning,"Haiphong junction must allow turning across Nathan Road");
            Bus.GlobalPosition=Map.At(120,7.3f)+Vector3.Down*32;
            Check(!Hud.OncomingLaneWarning,"Below-road tunnel pose must not warn about Nathan Road");
            if(!freeDrive)Check(Hud.ServiceInstruction.StartsWith("Exploring"),"Below-road pose displays H1 service guidance");
            var south=Map.At(0,7.3f)-Map.Forward(0)*2000;
            var north=Map.At(Map.Length,7.3f)+Map.Forward(Map.Length)*2000;
            foreach(var p in new[]{south,north})
            {
                Bus.GlobalPosition=p;Check(!Hud.OncomingLaneWarning,"Lane warning extends beyond corridor endpoint");
                if(!freeDrive)Check(Hud.ServiceInstruction.StartsWith("Exploring"),"Service guidance extends beyond corridor endpoint");
            }
        }
        HarbourDrive=false;
        Bus.GlobalPosition=Map.At(22,-7.3f);Bus.Rotation=new(0,Map.Heading(22),0);
        Check(Hud.ServiceInstruction.StartsWith("33 m"),"H1 approach distance changed");
        Bus.GlobalPosition=Map.At(55,-7.3f);Bus.Rotation=new(0,Map.Heading(55),0);
        Check(Hud.ServiceInstruction=="Stop & press E to open doors","H1 boarding instruction missing");
        Bus.ToggleDoors();Check(Hud.ServiceInstruction=="Boarding passengers…","Open-door boarding instruction missing");Bus.ToggleDoors();
        Bus.GlobalPosition=Map.At(80,-7.3f);
        Check(Hud.ServiceInstruction.StartsWith("Stop missed"),"H1 missed-stop instruction changed");
        Bus.GlobalTransform=saved;NoticeTime=notice;HarbourDrive=harbour;StopIndex=stopIndex;
        if(failures.Count>0)throw new Exception(string.Join("; ",failures));
        GD.Print("ANTILA_HUD_CHECKS_OK: north/south correct and oncoming lanes in both modes; turning/junction guards; island, depth and endpoint exploration; H1 distance/boarding/missed-stop guidance");
    }

    private async System.Threading.Tasks.Task CheckReviewRegressions()
    {
        var failures=new List<string>();
        void Check(bool ok,string message) { if(!ok)failures.Add(message); }
        _UnhandledInput(new InputEventAction {Action="map",Pressed=true});
        _UnhandledInput(new InputEventAction {Action="doors",Pressed=true});
        _UnhandledInput(new InputEventAction {Action="reverse",Pressed=true});
        Check(!Bus.DoorsOpen && !Bus.Reverse,"map permits door and gear changes");
        _UnhandledInput(new InputEventAction {Action="pause",Pressed=true});
        Check(!MapOpen && !Paused && Bus.IsPhysicsProcessing(),"Escape must close the map and resume");
        _UnhandledInput(new InputEventAction {Action="pause",Pressed=true});
        _UnhandledInput(new InputEventAction {Action="map",Pressed=true});
        _UnhandledInput(new InputEventAction {Action="map",Pressed=true});
        Check(Paused && !Bus.IsPhysicsProcessing(),"closing a map opened during pause must stay paused");
        _UnhandledInput(new InputEventAction {Action="pause",Pressed=true});
        SetProcess(false);SetPhysicsProcess(false);Bus.SetPaused(true);
        var savedTraffic=_traffic.ToArray();
        float savedElapsed=Elapsed;
        Bus.ResetAt(Map.At(220,-7.3f),-Mathf.Pi/2);
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        UpdateCamera(1,true);
        var cameraQuery=new PhysicsShapeQueryParameters3D {Shape=new SphereShape3D {Radius=.4f},
            CollisionMask=1,Transform=new(Basis.Identity,Camera.GlobalPosition)};
        Check(GetWorld3D().DirectSpaceState.IntersectShape(cameraQuery,1).Count==0,"chase camera enters a building beside Nathan Road");
        Check(Camera.Position.DistanceTo(Bus.ToGlobal(new(0,7.6f,15.8f)))>3,"obstructed camera must pull forward");
        for(int i=0;i<30;i++)
        {
            UpdateCamera(1f/60,false);
            cameraQuery.Transform=new(Basis.Identity,Camera.GlobalPosition);
            Check(GetWorld3D().DirectSpaceState.IntersectShape(cameraQuery,1).Count==0,"camera smoothing re-enters the wall");
        }
        Bus.ResetAt(Map.At(220,-7.3f),Map.Heading(220));UpdateCamera(1,true);
        Check(Camera.Position.DistanceTo(Bus.ToGlobal(new(0,7.6f,15.8f)))<.01f,"clear chase camera must retain its full distance");
        SetCab(true);
        Check(Camera.Position.DistanceTo(Bus.ToGlobal(new(.73f,2.02f,-4.65f)))<.01f,"cab camera must stay in the driver seat");
        SetCab(false);
        Bus.ResetAt(Map.At(120,7.35f),Map.Heading(120)+Mathf.Pi);
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        var taxiQuery=new PhysicsShapeQueryParameters3D {Shape=new BoxShape3D {Size=new(1.8f,1.6f,4.5f)},CollisionMask=2};
        float taxiStart=_traffic[0].Distance;
        bool overlap=false;
        for(int i=0;i<600;i++)
        {
            _Process(1.0/60);_PhysicsProcess(1.0/60);
            taxiQuery.Transform=_traffic[0].Body.GlobalTransform.TranslatedLocal(new(0,.85f,0));
            overlap|=GetWorld3D().DirectSpaceState.IntersectShape(taxiQuery,1).Count>0;
        }
        Check(!overlap,"ambient taxi passes through a stopped bus");
        Check(taxiStart-_traffic[0].Distance>30 && _traffic[0].Distance>127,"taxi must approach and wait before the stopped bus");
        float stoppedDistance=_traffic[0].Distance;
        for(int i=0;i<120;i++)_PhysicsProcess(1.0/60);
        Check(_traffic[0].Distance==stoppedDistance,"blocked taxi must remain stopped");
        Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        for(int i=0;i<60;i++)_PhysicsProcess(1.0/60);
        Check(stoppedDistance-_traffic[0].Distance>6,"taxi must resume after the lane clears");
        MapOpen=true;
        var held=_traffic[0].Body.Position;
        _PhysicsProcess(1);
        Check(_traffic[0].Body.Position==held,"map must pause traffic");
        MapOpen=false;
        var taxi=_traffic[0].Body;
        _traffic[0]=(taxi,12.01f);taxi.Position=Map.At(12.01f,7.35f);
        float wrap=12+Map.Length-25-.1f;
        Bus.ResetAt(Map.At(wrap,7.35f),Map.Heading(wrap)+Mathf.Pi);
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        _PhysicsProcess(1.0/60);
        Check(_traffic[0].Distance==12.01f,"taxi must not wrap into an occupied destination");
        Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        _PhysicsProcess(1.0/60);
        Check(_traffic[0].Distance>1100,"taxi must wrap after its destination clears");
        for(int i=0;i<savedTraffic.Length;i++)
        {
            var (body,distance)=savedTraffic[i];_traffic[i]=savedTraffic[i];
            body.Position=Map.At(distance,7.35f);body.Rotation=new(0,Map.Heading(distance)+Mathf.Pi,0);
        }
        Elapsed=savedElapsed;UpdateCamera(1,true);
        Bus.SetPaused(false);SetProcess(true);SetPhysicsProcess(true);
        if(failures.Count>0)throw new Exception(string.Join("; ",failures));
        GD.Print("ANTILA_REVIEW_CHECKS_OK: map input lock, nested pause, camera obstruction/smoothing/cab, taxi approach/wait/resume/pause and occupied wrap");
    }
}
