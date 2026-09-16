using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;

public partial class Main
{
    public Rect2 HarbourBounds;
    public bool HarbourDrive;
    public readonly List<(string Name,bool Tunnel,List<Vector3> Points)> HarbourRoads = new();
    private readonly List<(string Name,List<Vector3> Points)> _harbourRoutes = new();
    private Node3D _harbour = null!;

    private MeshInstance3D BuildHarbour()
    {
        using var doc=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/cross-harbour.json"));
        var root=doc.RootElement;var b=root.GetProperty("bounds");
        HarbourBounds=new(b[0].GetSingle(),b[1].GetSingle(),b[2].GetSingle()-b[0].GetSingle(),b[3].GetSingle()-b[1].GetSingle());
        List<Vector3> Points(JsonElement row)=>row.GetProperty("points").EnumerateArray().Select(p=>new Vector3(p[0].GetSingle(),p[1].GetSingle(),p[2].GetSingle())).ToList();
        foreach(var road in root.GetProperty("roads").EnumerateArray())
            HarbourRoads.Add((road.GetProperty("name").GetString()!,road.GetProperty("tunnel").GetBoolean(),Points(road)));
        foreach(var route in root.GetProperty("routes").EnumerateArray())_harbourRoutes.Add((route.GetProperty("name").GetString()!,Points(route)));
        _harbour=Asset("cross-harbour",Vector3.Zero);_harbour.Name="CrossHarbour";
        MeshInstance3D ground=null!;
        foreach(var mesh in _harbour.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>())
        {
            string name=mesh.Name;
            if(name=="HarbourGround")ground=mesh;
            if(name=="RoadSurface" || name=="HarbourWater" || name.StartsWith("Paint") || name.StartsWith("Lamps") || name.StartsWith("Reflectors"))continue;
            var body=new StaticBody3D {Name="Solid",Position=name.StartsWith("Road_")?Vector3.Down*.035f:Vector3.Zero};mesh.AddChild(body);
            body.AddChild(new CollisionShape3D {Shape=mesh.Mesh.CreateTrimeshShape()});
        }
        foreach(var road in HarbourRoads.Where(r=>r.Tunnel))
        {
            for(int i=6;i<road.Points.Count-6;i+=8)
                AddChild(new OmniLight3D {Position=road.Points[i]+Vector3.Up*4.7f,LightColor=new("d5e8e8"),
                    LightEnergy=.8f,OmniRange=24,ShadowEnabled=false,DistanceFadeEnabled=true,DistanceFadeBegin=70,DistanceFadeLength=30});
        }
        foreach(var (at,forward,text) in new[]{
            (new Vector3(815,0,-730),new Vector3(.15f,0,1),"海底隧道\nCROSS-HARBOUR TUNNEL"),
            (new Vector3(1100,0,1275),new Vector3(.28f,0,-1),"九龍  KOWLOON\nCROSS-HARBOUR TUNNEL"),
            (new Vector3(658,0,-1165),new Vector3(.9f,0,-.4f),"香港島  HONG KONG ISLAND\n↓  海底隧道  ↓")})
        {
            var sign=new Node3D {Position=at,Rotation=new(0,Mathf.Atan2(-forward.X,-forward.Z),0)};AddChild(sign);
            Box(sign,new(0,7.3f,0),new(13,2,.25f),"195b48");
            foreach(float x in new[]{-7f,7f})Box(sign,new(x,3.8f,0),new(.2f,7.6f,.2f),"a3aaa5");
            Label(sign,text,new(0,7.3f,.15f),.023f,40);
        }
        // A finite road apron around the island loop; detail beyond it remains a later district expansion.
        var rng=new Random(1972);
        for(int i=0;i<22;i++)
        {
            float x=360+i*43,h=rng.Next(35,150),z=1760+rng.Next(0,75);
            Box(this,new(x,h/2,z),new(26,h,28),i%3==0?"71878a":"a3a796",true);
        }
        foreach(float x in new[]{330f,1350f})Box(this,new(x,.65f,1495),new(.5f,1.3f,790),"777e78",true);
        Box(this,new(840,.65f,1890),new(1020,1.3f,.5f),"777e78",true);
        foreach(var (start,end) in new[]{(330f,1060f),(1140f,1350f)})Box(this,new((start+end)/2,.65f,1100),new(end-start,1.3f,.5f),"777e78",true);
        return ground;
    }

    public string CurrentStreet()
    {
        var nearest=Map.NearestStreet(Bus.Position);float best=nearest.Distance;
        string name=nearest.Name;
        if(Bus.Position.Y<-1)best=float.MaxValue;
        foreach(var road in HarbourRoads)
            for(int i=1;i<road.Points.Count;i++)
            {
                float d=Bus.Position.DistanceTo(Geometry3D.GetClosestPointToSegment(Bus.Position,road.Points[i-1],road.Points[i]));
                if(d<best){best=d;name=road.Name=="-99"?"WAN CHAI CONNECTION":road.Name;}
            }
        return name;
    }

    private void StartHarbourDrive()
    {
        if(Paused || Complete || MapOpen || Bus.Kmh>.5f)return;
        HarbourDrive=true;Complete=false;
        var p=_harbourRoutes[0].Points;var f=p[1]-p[0];
        Bus.ResetAt(p[0]+f.Normalized().Cross(Vector3.Up)*1.8f,Mathf.Atan2(-f.X,-f.Z));
        Bus.SetPaused(false);SetCab(true);
        ShowNotice("Follow the tunnel signs. M opens the crossing map; R returns to H1.");
    }

    private async Task CheckHarbour()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(HarbourRoads.Count==49 && _harbourRoutes.Count==3,"harbour data count");
        Check(HarbourBounds.Size.Y>3300,"harbour world extent");
        var start=Bus.Position;
        MapOpen=true;_UnhandledInput(new InputEventAction {Action="tunnel",Pressed=true});
        Check(!HarbourDrive && Bus.Position==start,"map must block the tunnel shortcut");
        MapOpen=false;Paused=true;_UnhandledInput(new InputEventAction {Action="tunnel",Pressed=true});
        Check(!HarbourDrive && Bus.Position==start,"pause must block the tunnel shortcut");
        Paused=false;_UnhandledInput(new InputEventAction {Action="tunnel",Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[0].Points[0])<3,"tunnel shortcut must start at the approach in cab view");
        HarbourDrive=false;SetCab(false);Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        var query=new PhysicsShapeQueryParameters3D {Shape=new BoxShape3D {Size=new(2.48f,4.2f,10.55f)},CollisionMask=1};
        int samples=0;
        foreach(var road in HarbourRoads)
            for(int i=2;i<road.Points.Count-2;i+=3)
            foreach(float lane in new[]{-1.8f,0,1.8f})
            {
                var p=road.Points[i];var f=(road.Points[i+1]-p).Normalized();
                query.Transform=new(new Basis(Vector3.Up,Mathf.Atan2(-f.X,-f.Z)),p+f.Cross(Vector3.Up)*lane+Vector3.Up*2.55f);
                var hit=GetWorld3D().DirectSpaceState.IntersectShape(query,1);
                Check(hit.Count==0,$"Harbour obstruction: {road.Name} at {p}; {(hit.Count>0?(hit[0]["collider"].AsGodotObject() as Node)?.GetPath():null)}");samples++;
            }
        var cameraProbe=new PhysicsShapeQueryParameters3D {Shape=new SphereShape3D {Radius=.4f},CollisionMask=1};
        foreach(var tube in HarbourRoads.Where(r=>r.Tunnel && r.Points.Count>100))
        {
            var p=tube.Points[tube.Points.Count/2];var f=(tube.Points[tube.Points.Count/2+1]-p).Normalized();
            Bus.ResetAt(p+f.Cross(Vector3.Up)*1.8f,Mathf.Atan2(-f.X,-f.Z));
            SetCab(false);UpdateCamera(1,true);
            cameraProbe.Transform=new(Basis.Identity,Camera.Position);
            Check(GetWorld3D().DirectSpaceState.IntersectShape(cameraProbe,1).Count==0,"Chase camera intersects tunnel shell");
            Check(Camera.Position.Y<p.Y+5,"Chase camera must stay below the tunnel roof");
        }
        GD.Print($"ANTILA_HARBOUR_CLEARANCE_OK: {samples} full bus envelope queries");
        SetPhysicsProcess(false);HarbourDrive=true;Bus.AutomaticTest=true;Engine.TimeScale=4;
        var ramp=_harbourRoutes[0].Points.Where(p=>p.Z>1080 && p.Z<1300).ToList();
        foreach(var route in new[]{(Name:"South portal ramp",Points:ramp),(Name:"Hung Hom exit bend",Points:_harbourRoutes[2].Points.Skip(780).ToList())}.Concat(_harbourRoutes))
        {
            var path=route.Points;var f=(path[1]-path[0]).Normalized();
            Bus.ResetAt(path[0]+f.Cross(Vector3.Up)*1.8f,Mathf.Atan2(-f.X,-f.Z));
            Bus.TestThrottle=Bus.TestBrake=Bus.TestSteer=0;
            for(int frame=0;frame<10;frame++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            int contacts=Bus.Collisions,closest=0;float driven=Bus.DistanceDriven,minY=0;
            for(int tick=0;tick<22000 && closest<path.Count-3;tick++)
            {
                float best=float.MaxValue;
                for(int i=Mathf.Max(0,closest-4),end=Mathf.Min(path.Count,closest+20);i<end;i++)
                {
                    float d=Bus.Position.DistanceTo(path[i]);
                    if(d<best){best=d;closest=i;}
                }
                bool underground=path[closest].Y<-1;
                int index=Mathf.Min(path.Count-2,closest+(underground?4:2));
                var direction=(path[index+1]-path[index]).Normalized();
                var target=path[index]+direction.Cross(Vector3.Up)*1.8f;
                var delta=target-Bus.Position;float error=Mathf.AngleDifference(Bus.Rotation.Y,Mathf.Atan2(-delta.X,-delta.Z));
                Bus.TestSteer=Mathf.Clamp(Mathf.Atan(12*Mathf.Sin(error)/Mathf.Max(6,delta.Length()))/Mathf.DegToRad(32),-1,1);
                float speed=Mathf.Abs(error)>.22f?4.5f:underground?11:6;
                Bus.TestBrake=Bus.Speed>speed?1:0;Bus.TestThrottle=Bus.TestBrake==0?1:0;
                minY=Mathf.Min(minY,Bus.Position.Y);
                if(tick%1500==0)GD.Print($"ANTILA_HARBOUR_PROGRESS: {route.Name} {closest}/{path.Count}, speed {Bus.Kmh:0} km/h");
                Check(Bus.Collisions==contacts,$"Harbour contact on {route.Name}: {Bus.Position}, node {closest}, road {path[closest]}, off-centre {best}, pitch {Bus.Rotation.X}");
                Check(best<8 && Bus.Position.Y>-40,$"Harbour road departure {route.Name}: {Bus.Position}, node {closest}");
                await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            }
            Check(Bus.Position.DistanceTo(path[^1])<18 && Bus.Collisions==contacts,$"Harbour drive failed {route.Name}: {Bus.Position}, {closest}/{path.Count}, contacts {Bus.Collisions-contacts}");
            if(route.Name.Contains('→'))Check(minY<-30,"bus must descend through the harbour tunnel");
            GD.Print($"ANTILA_HARBOUR_DRIVE_OK: {route.Name}; {Bus.DistanceDriven-driven:0} m; minimum y={minY:0.0}; no contacts");
        }
        Bus.TestThrottle=Bus.TestBrake=Bus.TestSteer=0;Bus.AutomaticTest=false;HarbourDrive=false;Engine.TimeScale=1;
        Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));SetPhysicsProcess(true);
    }

    private async void CaptureHarbour()
    {
        SelfTest=true;SetProcess(false);SetPhysicsProcess(false);Bus.SetPaused(true);Hud.Visible=false;Bus.Model.Visible=false;
        Camera.Far=5000;
        var mid=_harbourRoutes[0].Points.MinBy(p=>Mathf.Abs(p.Z-200));
        foreach(var (name,p,target) in new[]{
            ("hung-hom-portal",new Vector3(850,12,-785),new Vector3(823,1,-685)),
            ("tunnel-interior",mid+new Vector3(-1.8f,2.6f,0),mid+new Vector3(11,2.6f,80)),
            ("island-exit",new Vector3(1150,22,1320),new Vector3(1070,0,1220)),
            ("harbour-overview",new Vector3(1800,1350,1100),new Vector3(500,0,260))})
        {
            Camera.Position=p;Camera.LookAt(target);
            await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);RenderingServer.ForceDraw(false);
            GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath($"res://evidence/harbour/{name}.png"));
        }
        var entry=_harbourRoutes[0].Points;int at=entry.FindIndex(p=>p.Z>-620);
        var direction=(entry[at+1]-entry[at]).Normalized();
        Bus.ResetAt(entry[at]+direction.Cross(Vector3.Up)*1.8f,Mathf.Atan2(-direction.X,-direction.Z));
        SetCab(true);Hud.Visible=true;HarbourDrive=true;NoticeTime=0;Hud.QueueRedraw();
        await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);RenderingServer.ForceDraw(false);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/harbour/driving-cab.png"));
        MapOpen=true;Hud.QueueRedraw();
        await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);RenderingServer.ForceDraw(false);
        GetViewport().GetTexture().GetImage().SavePng(ProjectSettings.GlobalizePath("res://evidence/harbour/map.png"));
        GD.Print("ANTILA_HARBOUR_CAPTURE_OK");QuitGame();
    }
}
