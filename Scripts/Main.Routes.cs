using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;

public sealed class ServiceRoute
{
    public string Number="",Name="",Chinese="",Area="",Difficulty="",Summary="";
    public Color Color;
    public float Start;
    public bool Nathan;
    public readonly RoutePath Path=new();
    public readonly List<(string Name,string Chinese,float Distance,float Lane,int Passengers)> Stops=new();
    public readonly List<Node3D> Waiting=new();
    public readonly List<(bool Pole,bool Clear)> Sites=new();
    public int TotalPassengers=>Stops.Sum(s=>s.Passengers);
    public string Heading=>Name.ToUpper().Replace(" → ","  →  ");

    // Bays draw the bus from its running lane to the kerb over the approach, then back after departure.
    public float LaneAt(float distance)
    {
        float lane=Path.BaseLane(distance);
        foreach(var stop in Stops)
        {
            float d=distance-stop.Distance;
            float weight=d< -60 || d>45?0:d< -12?Mathf.SmoothStep(-60,-12,d):d>10?1-Mathf.SmoothStep(10,45,d):1;
            lane=Mathf.Lerp(lane,stop.Lane,weight);
        }
        return lane;
    }
}

public partial class Main
{
    public readonly List<ServiceRoute> Routes=new();
    public ServiceRoute Route=null!;
    public int RouteIndex;
    public bool Menu,Briefing,Abandoned,BriefingCab;
    public readonly List<(string Name,float Time,float Offset,int Boarded,bool Missed)> StopLog=new();
    private int _tripContacts,_tripRedLights;
    private float _tripDistance,_menuOrbit;
    private static int _pendingRoute=-1;
    private readonly Dictionary<string,int> _harbourRoadIndex=new();
    private readonly List<string[]> _harbourRouteSources=new();
    public int TripContacts=>Bus.Collisions-_tripContacts;
    public int TripRedLights=>RedLightCrossings-_tripRedLights;
    public float TripDistance=>Bus.DistanceDriven-_tripDistance;
    public int StopsServed=>StopLog.Count(s=>!s.Missed);
    public int StopsMissed=>StopLog.Count(s=>s.Missed);
    private static readonly (Key Key,int Drive)[] FreeDriveKeys={(Key.T,0),(Key.I,3),(Key.J,4),(Key.K,5),(Key.L,6),(Key.N,8),(Key.B,9),(Key.U,10),(Key.O,11)};

    private static string StreetName(string name)=>string.IsNullOrWhiteSpace(name) || name is "-99" or "<Null>" or "&lt;Null&gt;"?"":name;

    private void LoadRoutes()
    {
        using var doc=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/routes.json"));
        foreach(var row in doc.RootElement.GetProperty("routes").EnumerateArray())
        {
            var route=new ServiceRoute {Number=row.GetProperty("number").GetString()!,Name=row.GetProperty("name").GetString()!,
                Chinese=row.GetProperty("zh").GetString()!,Area=row.GetProperty("area").GetString()!,Difficulty=row.GetProperty("difficulty").GetString()!,
                Summary=row.GetProperty("summary").GetString()!,Color=new Color(row.GetProperty("color").GetString()!),Start=row.GetProperty("start").GetSingle()};
            foreach(var leg in row.GetProperty("legs").EnumerateArray())
            {
                if(leg.TryGetProperty("nathan",out var lane))
                {
                    route.Nathan=true;
                    for(int i=0;i<Map.Points.Count;i++)route.Path.Add(Map.Points[i],lane.GetSingle(),"NATHAN ROAD",i*5);
                    foreach(var s in Map.Stops)route.Stops.Add((s.Name,s.Chinese,s.Distance,lane.GetSingle(),s.Passengers));
                    continue;
                }
                int drive=leg.GetProperty("drive").GetInt32();
                float until=leg.TryGetProperty("to",out var to)?to.GetSingle():float.MaxValue;
                var points=_harbourRoutes[drive].Points;var names=new List<string>();
                foreach(var (id,member) in _harbourRouteSources[drive].Select((id,i)=>(id,i)))
                {
                    var road=HarbourRoads[_harbourRoadIndex[id.TrimStart('-')]];
                    names.AddRange(Enumerable.Repeat(StreetName(road.Name),road.Points.Count-(member==0?0:1)));
                }
                if(names.Count!=points.Count)throw new InvalidOperationException($"Drive {drive} street names do not match its points");
                float along=0;
                for(int i=0;i<points.Count && along<=until;i++)
                {
                    if(i>0)along+=points[i].DistanceTo(points[i-1]);
                    route.Path.Add(points[i],0,names[i]);
                }
            }
            if(!route.Nathan){route.Path.Smooth();FitKerbLanes(route.Path);}
            // Bays sit 0.4 m nearer the kerb than the running lane unless the data names a lane.
            if(row.TryGetProperty("stops",out var stops))
                foreach(var s in stops.EnumerateArray())
                {
                    float d=s.GetProperty("distance").GetSingle();
                    route.Stops.Add((s.GetProperty("name").GetString()!,s.GetProperty("zh").GetString()!,d,
                        s.TryGetProperty("lane",out var bay)?bay.GetSingle():route.Path.BaseLane(d)-.4f,s.GetProperty("passengers").GetInt32()));
                }
            route.Path.FindTurns();
            Routes.Add(route);
        }
        Route=Routes[0];
    }

    private Dictionary<(int,int),List<(Vector2 A,Vector2 B,float Ya,float Yb,float Half,bool Tube,bool Raised)>>? _kerbGrid;

    // Same-level carriageway covering a point: its kind, or null where the ground is paving or a drop.
    private (bool Tube,bool Raised)? Carriageway(Vector3 p)
    {
        if(_kerbGrid==null)
        {
            _kerbGrid=new();
            foreach(var r in HarbourRoads)
                for(int j=1;j<r.Points.Count;j++)
                {
                    var a=r.Points[j-1];var b=r.Points[j];
                    // Tube ledges stand 3.95 m out; the carriageway between them is the drivable width.
                    var segment=(new Vector2(a.X,a.Z),new Vector2(b.X,b.Z),a.Y,b.Y,r.Tunnel?3.95f:r.Width/2,r.Tunnel,r.Elevated);
                    for(int x=Mathf.FloorToInt(Mathf.Min(a.X,b.X)/32)-1;x<=Mathf.FloorToInt(Mathf.Max(a.X,b.X)/32)+1;x++)
                        for(int z=Mathf.FloorToInt(Mathf.Min(a.Z,b.Z)/32)-1;z<=Mathf.FloorToInt(Mathf.Max(a.Z,b.Z)/32)+1;z++)
                        {
                            if(!_kerbGrid.TryGetValue((x,z),out var cell))_kerbGrid[(x,z)]=cell=new();
                            cell.Add(segment);
                        }
                }
        }
        var flat=new Vector2(p.X,p.Z);(bool,bool)? hit=null;float nearest=float.MaxValue;
        if(_kerbGrid.TryGetValue((Mathf.FloorToInt(p.X/32),Mathf.FloorToInt(p.Z/32)),out var near))
            foreach(var s in near)
            {
                var closest=Geometry2D.GetClosestPointToSegment(flat,s.A,s.B);float gap=flat.DistanceTo(closest);
                float t=s.A.DistanceTo(s.B)<.01f?0:s.A.DistanceTo(closest)/s.A.DistanceTo(s.B);
                if(gap<s.Half && gap<nearest && Mathf.Abs(Mathf.Lerp(s.Ya,s.Yb,t)-p.Y)<1.5f){nearest=gap;hit=(s.Tube,s.Raised);}
            }
        if(hit==null && Mathf.Abs(p.Y)<1.5f && Map.Bounds.Grow(30).HasPoint(flat) && !Map.ClearOfRoads(p,0))hit=(false,false);
        return hit;
    }

    // Harbour drives run in the kerbside lane of every same-level carriageway to their left.
    // Painted gaps under 2.5 m between twin carriageways are crossed (street lamps need 2.6 m); tube ledges and deck edges are not.
    private void FitKerbLanes(RoutePath path)
    {
        var samples=new List<(float Lane,float Floor)>();
        for(float d=0;d<=path.Length+2.5f;d+=2.5f)
        {
            var centre=Carriageway(path.At(d));bool hard=centre is {Tube:true} or {Raised:true};
            float first=float.NaN,kerb=float.NaN;int clear=0;
            for(float lateral=-.5f;lateral>-30;lateral-=.5f)
            {
                if(Carriageway(path.At(d,lateral))!=null){clear=0;continue;}
                if(float.IsNaN(first))first=lateral;
                if(++clear==6){kerb=lateral+2.5f;break;}
            }
            float edge=hard?first:kerb;
            samples.Add((float.IsNaN(edge)?float.NaN:edge+(centre is {Tube:true}?2.15f:2.4f),hard && !float.IsNaN(first)?first+1.55f:float.NegativeInfinity));
        }
        // A median rejects junction mouths; hard edges bind a bus length either side so the body is inside a tube before its portal.
        int n=samples.Count;float[] target=new float[n],lanes=new float[n];
        for(int i=0;i<n;i++)
        {
            var window=samples.Skip(Math.Max(0,i-10)).Take(21).Select(s=>s.Lane).Where(l=>!float.IsNaN(l)).OrderBy(l=>l).ToList();
            target[i]=Mathf.Max(window.Count==0?-3.6f:window[window.Count/2],samples.Skip(Math.Max(0,i-5)).Take(11).Max(s=>s.Floor));
            // Inside a left turn the lane radius is the line's radius less the offset; keep 11 m for the bus to steer round.
            float d=i*2.5f,left=Mathf.AngleDifference(path.Heading(d-12),path.Heading(d+12));
            if(left>.05f)target[i]=Mathf.Max(target[i],Mathf.Min(-1.5f,11-24/left));
        }
        // Lane changes are capped at 0.12 m per metre, always resolved toward the line: the bus never runs further out than the kerb allows.
        for(int i=0;i<n;i++)
        {
            lanes[i]=float.NegativeInfinity;
            for(int j=Math.Max(0,i-60);j<Math.Min(n,i+61);j++)lanes[i]=Mathf.Max(lanes[i],target[j]-.12f*2.5f*Math.Abs(i-j));
        }
        for(int i=0;i<path.Points.Count;i++)
        {
            float at=path.Along[i]/2.5f;int k=Math.Min((int)at,lanes.Length-2);
            path.Lanes[i]=Mathf.Lerp(lanes[k],lanes[k+1],Mathf.Clamp(at-k,0,1));
        }
    }

    private void BuildStops()
    {
        LoadRoutes();
        foreach(var route in Routes)
            for(int i=0;i<route.Stops.Count;i++)
            {
                var stop=route.Stops[i];var path=route.Path;float d=stop.Distance,lane=stop.Lane;
                bool shelterFits=route.Nathan || ShelterFits(path,d,lane),pole=!shelterFits;
                route.Sites.Add((pole,shelterFits || PoleFits(path,d,lane)));
                if(pole)
                {
                    // Narrow Kowloon pavements take a flag pole beside the bay door instead of a shelter.
                    var flag=new Node3D {Name="StopPole",Position=path.At(d+4,lane-2.6f),Rotation=new(0,path.Heading(d)+Mathf.Pi/2,0)};AddChild(flag);
                    Box(flag,new(0,1.45f,0),new(.09f,2.9f,.09f),"7b817a",true);
                    Box(flag,new(0,2.62f,.07f),new(.72f,.62f,.05f),"efe6c8");
                    Label(flag,"BUS STOP\n巴士站",new(0,2.74f,.1f),.006f,40).Modulate=new("203631");
                    Label(flag,stop.Name.ToUpper()+"\n"+stop.Chinese,new(0,2.47f,.1f),.0035f,30).Modulate=new("203631");
                }
                else
                {
                    var shelter=Asset("shelter",path.At(d,lane-4.9f),path.Heading(d)+Mathf.Pi/2);
                    var poster=new MeshInstance3D {Mesh=new QuadMesh {Size=new(1.19f,1.83f)},Position=new(2,1.4f,-.622f),
                        MaterialOverride=new StandardMaterial3D {AlbedoTexture=GD.Load<Texture2D>("res://Assets/Textures/kowloon-poster.png"),Roughness=.9f}};
                    shelter.AddChild(poster);
                    Label(shelter,stop.Name.ToUpper()+"  /  "+stop.Chinese,new(0,2.48f,1.32f),.009f,30);
                }
                foreach(var (name,along,offset,heading) in new[]{("bench",12f,-5.2f,path.Heading(d)+Mathf.Pi/2),("bin",-7f,-5.4f,0f),("planter",15f,-5.2f,path.Heading(d))})
                    if(route.Nathan || StopSiteClear(path.At(d+along,lane+offset),1))Asset(name,path.At(d+along,lane+offset),heading);
                for(float s=d-7;s<d+8;s+=3)
                    Stripe(path.At(s,lane+2.2f),path.Forward(s),.15f,1.5f,"e1b954");
                Stripe(path.At(d-8,lane),path.Forward(d-8),4.4f,.15f,"e1b954");
                Stripe(path.At(d+8,lane),path.Forward(d+8),4.4f,.15f,"e1b954");
                if(!route.Nathan)
                {
                    // Nathan Road bays are lettered with the other district road details.
                    var text=Label(this,"BUS\nSTOP",path.At(d,lane)+Vector3.Up*.078f,.022f,64);
                    text.Rotation=new(-Mathf.Pi/2,path.Heading(d),0);
                    text.Scale=new(1,1.55f,1);text.Modulate=new("e5bd58");
                }
                var people=new Node3D {Visible=route==Route};AddChild(people);route.Waiting.Add(people);
                for(int p=0;p<Mathf.Min(4,stop.Passengers);p++)
                {
                    var at=path.At(d-3+p*1.45f,lane-(pole?3.3f:3.8f));
                    string model=new[]{"mei","dennis","family","headphones"}[(p+i)%4];
                    var passenger=GD.Load<PackedScene>($"res://Assets/Models/passenger_{model}.glb").Instantiate<Node3D>();
                    people.AddChild(passenger);
                    passenger.Position=at+Vector3.Up*.05f;
                    passenger.Rotation=new(0,path.Heading(d)+Mathf.Pi/2+(p%2==0?-.12f:.10f),0);
                    foreach(MeshInstance3D mesh in passenger.FindChildren("*","MeshInstance3D",true,false))
                        mesh.VisibilityRangeEnd=160;
                }
            }
        _stopMarker=new Node3D();AddChild(_stopMarker);
        var targetMat=new StandardMaterial3D {AlbedoColor=new Color(.39f,.85f,.7f,.32f),Transparency=BaseMaterial3D.TransparencyEnum.Alpha,
            ShadingMode=BaseMaterial3D.ShadingModeEnum.Unshaded,CullMode=BaseMaterial3D.CullModeEnum.Disabled};
        _stopMarker.AddChild(new MeshInstance3D {Mesh=new CylinderMesh {TopRadius=2,BottomRadius=2,Height=.03f,RadialSegments=48},MaterialOverride=targetMat});
        GD.Print($"ANTILA_ROUTES: {Routes.Count} services; {Routes.Sum(r=>r.Stops.Count)} stops; "+string.Join(", ",Routes.Select(r=>$"{r.Number} {r.Path.Length/1000:0.00} km")));
    }

    private bool ShelterFits(RoutePath path,float d,float lane)=>StopSiteClear(path.At(d,lane-4.9f),1.2f) && Enumerable.Range(-1,3).All(k=>StopSiteClear(path.At(d+k*3-1,lane-3.8f),.4f));
    private bool PoleFits(RoutePath path,float d,float lane)=>StopSiteClear(path.At(d+4,lane-2.6f),.3f) && Enumerable.Range(-1,3).All(k=>StopSiteClear(path.At(d+k*3-1,lane-3.3f),.4f));

    // Footprints, not their bounding boxes: Mong Kok blocks sit at an angle to the axes.
    private bool LotClear(Vector2 p,float margin)=>!_lots.Any(l=>l.Bounds.Grow(margin).HasPoint(p) &&
        (Geometry2D.IsPointInPolygon(p,l.Polygon) || l.Polygon.Select((a,i)=>Geometry2D.GetClosestPointToSegment(p,a,l.Polygon[(i+1)%l.Polygon.Length]).DistanceTo(p)).Min()<margin));

    // Street furniture and queues need pavement: no building, scenery, carriageway or tunnel mouth underfoot.
    private bool StopSiteClear(Vector3 p,float margin)
    {
        var flat=new Vector2(p.X,p.Z);
        return LotClear(flat,margin) && !_islandDetails.Any(d=>p.DistanceTo(d.Position)<d.Radius+margin) &&
            !_footpathObstacles.Any(o=>o.Center.DistanceTo(p)<o.Radius+margin) && Map.ClearOfRoads(p,margin) &&
            !HarbourRoads.Any(r=>Enumerable.Range(1,r.Points.Count-1).Any(j=>r.Points[j].Y>-6 &&
                flat.DistanceTo(Geometry2D.GetClosestPointToSegment(flat,new(r.Points[j-1].X,r.Points[j-1].Z),new(r.Points[j].X,r.Points[j].Z)))<6+margin));
    }

    public bool NearRoute(float distance,float clearance)=>Bus.GlobalPosition.DistanceTo(Route.Path.At(distance,Route.LaneAt(distance)))<clearance;

    public void ShowRouteSelect()
    {
        Menu=true;Briefing=false;Paused=false;MapOpen=false;HarbourDrive=false;Complete=false;Abandoned=false;
        NoticeTime=0;SetCab(false);PreviewRoute(RouteIndex);
    }

    private void PreviewRoute(int index)
    {
        RouteIndex=index;Route=Routes[index];StopIndex=0;Passengers=0;Boarding=0;
        foreach(var route in Routes)foreach(var group in route.Waiting)group.Visible=route==Route;
        Bus.ResetAt(Route.Path.At(Route.Start,Route.LaneAt(Route.Start)),Route.Path.Heading(Route.Start));
        Bus.SetPaused(true);
        Hud.ShowRouteMap(Route);
    }

    public void BeginRoute(int index)
    {
        PreviewRoute(index);_pendingRoute=index;
        Menu=Briefing=false;Paused=MapOpen=HarbourDrive=Complete=Abandoned=false;
        Elapsed=0;StopLog.Clear();
        Bus.SetPhysicsProcess(true);Bus.SetPaused(false);Bus.RestartAudio();
        _tripContacts=Bus.Collisions;_tripRedLights=RedLightCrossings;_tripDistance=Bus.DistanceDriven;
        SetCab(BriefingCab);
        Notice=$"Welcome aboard {Route.Number}. Pull into {Route.Stops[0].Name}, stop and press E.";NoticeTime=9;
    }

    private void FinishRoute(bool abandoned)
    {
        Complete=true;Abandoned=abandoned;Paused=false;MapOpen=false;
        Bus.SetPhysicsProcess(false);
        Bus.StopAudio();
        ShowNotice(abandoned?$"{Route.Number} ended before the terminus.":$"Service complete. Thank you for driving {Route.Number}.");
    }

    private void StartFreeDrive(int drive)
    {
        if(Menu){Menu=Briefing=false;Bus.SetPaused(false);Bus.RestartAudio();}
        StartHarbourDrive(drive);
    }

    // Route select and briefing take keys and clicks only; the city keeps moving behind them.
    private void MenuInput(InputEvent e)
    {
        if(e.IsActionPressed("mute")){AudioServer.SetBusMute(0,!AudioServer.IsBusMute(0));return;}
        if(e is InputEventKey {Pressed:true,Keycode:Key.F12}){Capture();return;}
        if(Briefing)
        {
            if(e.IsActionPressed("confirm"))BeginRoute(RouteIndex);
            else if(e.IsActionPressed("pause") || e.IsActionPressed("routes"))Briefing=false;
            else if(e.IsActionPressed("camera"))BriefingCab=!BriefingCab;
            else if(e is InputEventMouseButton {Pressed:true,ButtonIndex:MouseButton.Left} click && Hud.StartButton.HasPoint(Hud.Virtual(click.Position)))BeginRoute(RouteIndex);
            return;
        }
        if(e.IsActionPressed("menu_up"))PreviewRoute((RouteIndex+Routes.Count-1)%Routes.Count);
        else if(e.IsActionPressed("menu_down"))PreviewRoute((RouteIndex+1)%Routes.Count);
        else if(e.IsActionPressed("confirm"))Briefing=true;
        else if(e is InputEventKey {Pressed:true,Echo:false} key && key.Keycode>=Key.Key1 && key.Keycode<Key.Key1+Routes.Count)
            PreviewRoute((int)(key.Keycode-Key.Key1));
        else if(e is InputEventKey {Pressed:true,Echo:false} drive && FreeDriveKeys.Any(k=>k.Key==drive.Keycode))
            StartFreeDrive(FreeDriveKeys.First(k=>k.Key==drive.Keycode).Drive);
        else if(e is InputEventMouseButton {Pressed:true,ButtonIndex:MouseButton.Left} click)
        {
            var at=Hud.Virtual(click.Position);
            for(int i=0;i<Routes.Count;i++)
                if(Hud.RouteCard(i).HasPoint(at)){if(i==RouteIndex)Briefing=true;else PreviewRoute(i);}
        }
    }

    private void UpdateMenuCamera(float dt)
    {
        _menuOrbit+=dt*.09f;
        var focus=Bus.GlobalPosition+Vector3.Up*2.5f;
        var target=focus+new Vector3(Mathf.Sin(_menuOrbit)*30,13,Mathf.Cos(_menuOrbit)*30);
        _cameraSweep.Transform=new(Basis.Identity,focus+Vector3.Up*3);
        _cameraSweep.Motion=target-_cameraSweep.Transform.Origin;
        float fraction=GetWorld3D().DirectSpaceState.CastMotion(_cameraSweep)[0];
        Camera.GlobalPosition=_cameraSweep.Transform.Origin+_cameraSweep.Motion*fraction;
        Camera.LookAt(focus);
    }

    private async Task CheckRoutes()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        async Task Frames(int count){for(int i=0;i<count;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);}
        void Press(string action)=>_UnhandledInput(new InputEventAction {Action=action,Pressed=true});
        await Frames(1);
        Check(Routes.Select(r=>r.Number).SequenceEqual(new[]{"H1","H2","H3"}),"three services H1, H2 and H3");
        var h1=Routes[0];
        Check(h1.Nathan && h1.Path.Points.Count==231 && Mathf.Abs(h1.Path.Length-Map.Length)<.5f && h1.Stops.Count==3 && h1.TotalPassengers==26,$"H1 keeps the Nathan Road corridor and its three stops: {h1.Path.Points.Count} points, {h1.Path.Length} m");
        for(float d=0;d<=Map.Length;d+=37)Check(h1.Path.At(d,-7.3f).DistanceTo(Map.At(d,-7.3f))<.05f && Mathf.Abs(h1.LaneAt(d)+7.3f)<.01f,$"H1 path leaves Nathan Road at {d} m");
        Check(Mathf.Abs(Routes[1].Path.Length-3879)<1 && Mathf.Abs(Routes[2].Path.Length-3431)<1,"H2 and H3 route lengths");
        Check(Routes[1].Stops.Count==8 && Routes[1].TotalPassengers==60 && Routes[1].Sites.Count(s=>s.Pole)==2 && Routes[2].Stops.Count==4 && Routes[2].TotalPassengers==33 && Routes[2].Sites.All(s=>!s.Pole),"H2 and H3 stop tables");
        Check(Routes[1].Path.Turns.Count==3 && Routes[2].Path.Turns.Count==3,"junction turn prompts");
        foreach(var route in Routes.Skip(1))
        {
            for(float d=0;d<route.Path.Length;d+=5)Check(route.LaneAt(d)<-.3f && route.LaneAt(d)>-21,$"{route.Number} lane must stay left of the line at {d} m: {route.LaneAt(d)}");
            foreach(var (stop,i) in route.Stops.Select((s,i)=>(s,i)))
            {
                Check(i==0 || stop.Distance>route.Stops[i-1].Distance+150,$"{route.Number} stops must be in order and spaced: {stop.Name}");
                Check(route.Sites[i].Clear && Mathf.Abs(route.Path.At(stop.Distance).Y)<.05f,$"{route.Number} {stop.Name} needs clear pavement for its {(route.Sites[i].Pole?"pole":"shelter")}");
                Check(route.Waiting[i].GetChildCount()>0 && route.Waiting[i].GetChildCount()<=4,$"{route.Number} {stop.Name} waiting passengers");
            }
            Check(route.Stops[^1].Distance>route.Path.Length-120,$"{route.Number} terminus must close the route");
        }
        // Route select, briefing, abandonment and the results screen run through the same input actions as play.
        ShowRouteSelect();
        Check(Menu && !Briefing && !Bus.IsPhysicsProcessing() && Routes[RouteIndex].Waiting.All(w=>w.Visible),"route select must pause the bus on the chosen route");
        Press("menu_down");Check(Route==Routes[1] && Routes[0].Waiting.All(w=>!w.Visible) && Routes[1].Waiting.All(w=>w.Visible),"menu down must preview H2");
        Press("menu_up");Press("menu_up");Check(Route==Routes[2],"menu up must wrap to H3");
        Press("menu_down");Press("confirm");Check(Briefing && Route==Routes[0],"enter must open the briefing");
        Press("pause");Check(Menu && !Briefing,"escape must return from the briefing");
        Press("menu_down");Press("confirm");Press("confirm");
        Check(!Menu && !Briefing && Route==Routes[1] && Bus.IsPhysicsProcessing() && StopIndex==0 && StopLog.Count==0,"enter on the briefing must start H2");
        Check(Bus.Position.DistanceTo(Routes[1].Path.At(Routes[1].Start,Routes[1].LaneAt(Routes[1].Start)))<.5f,"H2 must start at its first lane position");
        var first=Route.Stops[0];
        Bus.ResetAt(Route.Path.At(first.Distance+35,Route.LaneAt(first.Distance+35)),Route.Path.Heading(first.Distance+35));
        AdvanceService(.1f);
        Check(StopIndex==1 && StopsMissed==1 && StopLog[0].Name==first.Name,"a stop left 30 m behind must count as missed");
        StopIndex=Route.Stops.Count-1;var terminus=Route.Stops[^1];
        Bus.ResetAt(Route.Path.At(terminus.Distance+20,Route.LaneAt(terminus.Distance+20)),Route.Path.Heading(terminus.Distance+20));
        AdvanceService(.1f);Check(StopIndex==Route.Stops.Count-1 && !Complete,"the terminus is never skipped");
        Press("routes");
        Check(Complete && Abandoned && !Bus.IsPhysicsProcessing() && !AudioClip("music").Playing,"tab must end the route and show its results");
        Press("confirm");Check(Menu && !Complete && Route==Routes[1],"enter on the results must return to route select");
        BeginRoute(2);Check(!Menu && Route==Routes[2] && !Complete && StopLog.Count==0,"each route starts fresh");
        // Drive every route through its stops with the player's steering, brakes and door interlock.
        Engine.TimeScale=4;
        var only=OS.GetCmdlineUserArgs().FirstOrDefault(a=>a.StartsWith("--route="))?[8..];
        foreach(var route in Routes.Where(r=>only==null || r.Number==only))
        {
            float minY=await DriveRoute(route);var path=route.Path;
            Check(Complete && !Abandoned && StopsServed==route.Stops.Count && StopsMissed==0 && Passengers==route.TotalPassengers,
                $"{route.Number} service incomplete: stop {StopIndex+1}/{route.Stops.Count}, served {StopsServed}, at {Bus.Position}");
            Check(TripContacts==0 && TripRedLights==0,$"{route.Number} contacts {TripContacts}, red lights {TripRedLights}");
            Check(TripDistance>(route.Stops[^1].Distance-route.Start)*.95f,$"{route.Number} must be physically driven: {TripDistance:0} m");
            Check(StopLog.All(s=>s.Offset<3),$"{route.Number} bay accuracy: "+string.Join(", ",StopLog.Select(s=>$"{s.Offset:0.0}")));
            if(route==Routes[2])Check(minY<-30,"H3 must descend through the harbour tunnel");
            GD.Print($"ANTILA_ROUTE_DRIVE_OK: {route.Number} {TripDistance:0} m in {Elapsed:0} s; {StopsServed} stops, {Passengers} passengers, bay offsets {string.Join("/",StopLog.Select(s=>$"{s.Offset:0.0}"))}; no contacts or red lights");
        }
        Bus.TestThrottle=Bus.TestBrake=Bus.TestSteer=0;Bus.AutomaticTest=false;Engine.TimeScale=1;
        BeginRoute(0);
        GD.Print("ANTILA_ROUTE_CHECKS_OK: route select, briefing, missed stop, abandoned trip, results; drove H1, H2 and H3 terminus to terminus");
    }

    // Test driver: pure-pursuit steering on the route lane, bend and stop braking, signals obeyed, doors at every bay.
    private async Task<float> DriveRoute(ServiceRoute route)
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        BeginRoute(Routes.IndexOf(route));Bus.AutomaticTest=true;
        var path=route.Path;float minY=0;
        for(int tick=0;tick<24000 && !Complete;tick++)
        {
            var (along,lateral,_)=path.Project(Bus.Position);
            Check(Mathf.Abs(lateral-route.LaneAt(along))<3.5f,$"{route.Number} left its lane at {along:0} m ({path.StreetAt(along)}): lateral {lateral:0.0}, lane {route.LaneAt(along):0.0}, {Bus.Position}");
            Check(TripContacts==0,$"{route.Number} contact at {along:0} m ({path.StreetAt(along)}): {Bus.Position}");
            float bend=Mathf.Max(Mathf.Abs(Mathf.AngleDifference(path.Heading(along+4),path.Heading(along+22))),Mathf.Abs(Mathf.AngleDifference(path.Heading(along),path.Heading(along+12))));
            float look=bend>.5f?9:12;
            var target=path.At(along+look,route.LaneAt(along+look));var delta=target-Bus.Position;
            float error=Mathf.AngleDifference(Bus.Rotation.Y,Mathf.Atan2(-delta.X,-delta.Z));
            Bus.TestSteer=Mathf.Clamp(Mathf.Atan(12*Mathf.Sin(error)/look)/Mathf.DegToRad(32),-1,1);
            float limit=bend>.7f?3:bend>.35f?4.5f:bend>.15f||Mathf.Abs(error)>.2f?6:9;
            float remaining=route.Stops[StopIndex].Distance-along;
            Bus.TestBrake=Bus.Speed>limit+.3f || remaining<Bus.Speed*Bus.Speed/8+2 || TestSignalBrake()?1:0;
            Bus.TestThrottle=Bus.TestBrake==0 && Bus.Speed<limit?1:0;
            if(IsAtStop() && Bus.Kmh<.5f){if(!Bus.DoorsOpen)Bus.ToggleDoors();}
            else if(Bus.DoorsOpen)Bus.ToggleDoors();
            AdvanceService((float)GetPhysicsProcessDeltaTime());
            minY=Mathf.Min(minY,Bus.Position.Y);
            if(tick%2000==0)GD.Print($"ANTILA_ROUTE_PROGRESS: {route.Number} {along:0}/{path.Length:0} m, stop {StopIndex+1}/{route.Stops.Count}, {Bus.Kmh:0} km/h");
            await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        }
        Bus.TestThrottle=Bus.TestBrake=Bus.TestSteer=0;Bus.AutomaticTest=false;
        return minY;
    }

    // Rendered evidence of the playable loop: menu, briefing, staged bays and the tunnel, then results after a driven H1.
    private async void CaptureRoutes()
    {
        try
        {
            string folder=ProjectSettings.GlobalizePath("res://evidence/routes");DirAccess.MakeDirRecursiveAbsolute(folder);
            async Task Save(string name)
            {
                for(int i=0;i<4;i++)await ToSignal(RenderingServer.Singleton,RenderingServer.SignalName.FramePostDraw);
                using var image=GetViewport().GetTexture().GetImage();
                if(image.SavePng($"{folder}/{name}.png")!=Error.Ok)throw new Exception($"capture {name} failed");
                GD.Print($"ANTILA_ROUTE_CAPTURE: {name}.png");
            }
            void Staged(int route,float distance,bool cab)
            {
                BeginRoute(route);var r=Routes[route];
                Bus.ResetAt(r.Path.At(distance,r.LaneAt(distance)),r.Path.Heading(distance));
                SetCab(cab);NoticeTime=0;Bus.SetPaused(true);UpdateCamera(1,true);
            }
            ShowRouteSelect();PreviewRoute(1);
            await ToSignal(GetTree().CreateTimer(3),SceneTreeTimer.SignalName.Timeout);
            await Save("route-select");
            Briefing=true;await Save("briefing");Briefing=false;
            Staged(1,Routes[1].Stops[1].Distance-28,false);StopIndex=1;await Save("h2-waterloo-pole-stop");
            Staged(1,Routes[1].Stops[2].Distance-70,true);StopIndex=2;await Save("h2-mong-kok-cab");
            Staged(1,Routes[1].Stops[6].Distance-32,false);StopIndex=6;await Save("h2-yu-chau-street");
            Staged(2,Routes[2].Stops[1].Distance-30,false);StopIndex=1;await Save("h3-tunnel-interchange");
            Staged(2,1600,true);StopIndex=2;await Save("h3-tube-cab");
            Engine.TimeScale=4;await DriveRoute(Routes[0]);Engine.TimeScale=1;
            await Save("results-h1");
            QuitGame();
        }
        catch(Exception error){GD.PushError("ANTILA_ROUTE_CAPTURE_FAILED: "+error);QuitGame(1);}
    }

    private string SiteFailure(Vector3 p,float margin)
    {
        var flat=new Vector2(p.X,p.Z);
        if(!LotClear(flat,margin))return "lot";
        if(_islandDetails.Any(d=>p.DistanceTo(d.Position)<d.Radius+margin))return "detail";
        if(_footpathObstacles.Any(o=>o.Center.DistanceTo(p)<o.Radius+margin))return "footpath";
        if(!Map.ClearOfRoads(p,margin))return "map";
        if(!StopSiteClear(p,margin))return "road";
        return "";
    }

    private async Task SurveyStops()
    {
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        var envelope=new PhysicsShapeQueryParameters3D {Shape=new BoxShape3D {Size=new(2.6f,3,11)},CollisionMask=1};
        foreach(var route in Routes.Where(r=>!r.Nathan))
        {
            var path=route.Path;var runs=new List<string>();float runStart=-1,last=-1;string kinds="";
            GD.Print($"ANTILA_SURVEY_LANES {route.Number}: "+string.Join(" ",Enumerable.Range(0,(int)(path.Length/25)).Select(k=>$"{k*25}:{path.BaseLane(k*25):0.0}")));
            for(float d=40;d<path.Length-15;d+=5)
            {
                float lane=path.BaseLane(d)-.4f;
                bool ground=Enumerable.Range(-4,9).All(k=>Mathf.Abs(path.At(d+k*5).Y)<.05f);
                bool straight=Mathf.Abs(Mathf.AngleDifference(path.Heading(d-12),path.Heading(d+12)))<Mathf.DegToRad(6);
                bool steady=Enumerable.Range(-4,9).All(k=>Mathf.Abs(path.BaseLane(d+k*5)-lane-.4f)<.35f);
                bool shelter=ShelterFits(path,d,lane),pole=PoleFits(path,d,lane);
                string why=shelter || pole?"":SiteFailure(path.At(d+4,lane-2.6f),.3f);
                foreach(int k in new[]{-1,0,1})if(why=="" && !shelter && !pole)why=SiteFailure(path.At(d+k*3-1,lane-3.3f),.4f);
                envelope.Transform=new(new Basis(Vector3.Up,path.Heading(d)),path.At(d,lane)+Vector3.Up*2.3f);
                bool body=GetWorld3D().DirectSpaceState.IntersectShape(envelope,1).Count==0;
                bool ok=ground && straight && steady && (shelter || pole) && body;
                if(ok && runStart<0){runStart=d;kinds="";}
                if(ok)kinds+=shelter?"S":"P";
                if(!ok && runStart>=0){runs.Add($"{runStart:0}-{last:0} {kinds}");runStart=-1;}
                if(ok)last=d;
                if(d%25==0)GD.Print($"ANTILA_SURVEY_ROW {route.Number} {d:0}: lane={lane:0.0} g={ground} s={straight} steady={steady} shelter={shelter} pole={pole} site={why} b={body} {path.StreetAt(d)}");
            }
            if(runStart>=0)runs.Add($"{runStart:0}-{last:0} {kinds}");
            GD.Print($"ANTILA_SURVEY {route.Number} length {path.Length:0}: "+string.Join(", ",runs));
            GD.Print($"ANTILA_SURVEY_TURNS {route.Number}: "+string.Join(", ",path.Turns.Select(t=>$"{t.Distance:0}{(t.Direction>0?"L":"R")} {t.Street}")));
        }
        QuitGame();
    }
}
