using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;

public partial class Main
{
    public Rect2 HarbourBounds,IslandBounds;
    private readonly List<(Vector3 Position,float Radius)> _islandDetails = new();
    public bool HarbourDrive;
    public readonly List<(string Name,bool Tunnel,List<Vector3> Points)> HarbourRoads = new();
    private readonly List<(string Name,List<Vector3> Points)> _harbourRoutes = new();
    private Node3D _harbour = null!;
    private MeshInstance3D[] _vehicleMeshes = Array.Empty<MeshInstance3D>();
    private ShaderMaterial _harbourPaint = null!;
    private readonly List<Vector2[]> _harbourPaving = new();

    private MeshInstance3D BuildHarbour()
    {
        using var doc=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/cross-harbour.json"));
        var root=doc.RootElement;var b=root.GetProperty("bounds");
        var island=root.GetProperty("island_bounds");IslandBounds=new(island[0].GetSingle(),island[1].GetSingle(),island[2].GetSingle()-island[0].GetSingle(),island[3].GetSingle()-island[1].GetSingle());
        HarbourBounds=new(b[0].GetSingle(),b[1].GetSingle(),b[2].GetSingle()-b[0].GetSingle(),b[3].GetSingle()-b[1].GetSingle());
        List<Vector3> Points(JsonElement row)=>row.GetProperty("points").EnumerateArray().Select(p=>new Vector3(p[0].GetSingle(),p[1].GetSingle(),p[2].GetSingle())).ToList();
        foreach(var road in root.GetProperty("roads").EnumerateArray())
            HarbourRoads.Add((road.GetProperty("name").GetString()!,road.GetProperty("tunnel").GetBoolean(),Points(road)));
        foreach(var route in root.GetProperty("routes").EnumerateArray())_harbourRoutes.Add((route.GetProperty("name").GetString()!,Points(route)));
        _harbour=Asset("cross-harbour",Vector3.Zero);_harbour.Name="CrossHarbour";
        _harbourPaint=new ShaderMaterial {Shader=GD.Load<Shader>("res://Assets/Materials/harbour-paint.gdshader")};
        _harbourPaint.SetShaderParameter("map_origin",Map.Bounds.Position);_harbourPaint.SetShaderParameter("map_size",Map.Bounds.Size);
        var tubeIds=root.GetProperty("tubes").EnumerateArray().Select(t=>t.GetProperty("model_source_ids")[0].GetString()!).ToArray();
        var exterior=new StandardMaterial3D {AlbedoTexture=GD.Load<Texture2D>("res://Assets/Textures/pavement-stone.png"),
            AlbedoColor=new("9b9e91"),Roughness=.92f,Uv1Triplanar=true,Uv1Scale=new(.5f,.5f,.5f)};
        MeshInstance3D ground=null!;
        foreach(var mesh in _harbour.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>())
        {
            string name=mesh.Name;
            // Render layer 2 receives tunnel lamps/ambient, never direct sunlight past the shadow range.
            if(!name.StartsWith("Exterior") && tubeIds.Any(id=>name.EndsWith("_"+id)))mesh.Layers=2;
            if(name.StartsWith("Ceiling"))mesh.CastShadow=GeometryInstance3D.ShadowCastingSetting.DoubleSided;
            if(name=="HarbourGround")ground=mesh;
            if(name=="RoadSurface")mesh.Visible=false;
            if(name=="HarbourWater")mesh.MaterialOverride=new ShaderMaterial {Shader=GD.Load<Shader>("res://Assets/Materials/harbour-water.gdshader")};
            if(name.StartsWith("Paint") && mesh.Layers==1)mesh.MaterialOverride=_harbourPaint;
            if(name.StartsWith("Exterior") || name.StartsWith("Portal"))mesh.MaterialOverride=exterior;
            if(name=="RoadSurface" || name=="HarbourWater" || name.StartsWith("Paint") || name.StartsWith("Lamps") || name.StartsWith("Reflectors"))continue;
            var body=new StaticBody3D {Name="Solid",Position=name.StartsWith("Road_")?Vector3.Down*.035f:Vector3.Zero};mesh.AddChild(body);
            body.AddChild(new CollisionShape3D {Shape=mesh.Mesh.CreateTrimeshShape()});
        }
        foreach(var road in HarbourRoads.Where(r=>r.Tunnel))
        {
            for(int i=6;i<road.Points.Count-6;i+=8)
                AddChild(new OmniLight3D {Position=road.Points[i]+Vector3.Up*4.7f,LightColor=new("d5e8e8"),
                    LightEnergy=.8f,LightCullMask=2,OmniRange=24,ShadowEnabled=false,DistanceFadeEnabled=true,DistanceFadeBegin=70,DistanceFadeLength=30});
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
        return ground;
    }

    private void BuildHarbourScenery()
    {
        bool Clear(Vector3 p,float margin)=>IslandBounds.Grow(-margin-1).HasPoint(new(p.X,p.Z)) &&
            !_lots.Any(l=>l.Bounds.Grow(margin).HasPoint(new(p.X,p.Z))) &&
            !_islandDetails.Any(d=>p.DistanceTo(d.Position)<d.Radius+margin+1) &&
            !HarbourRoads.Any(r=>Enumerable.Range(1,r.Points.Count-1).Any(j=>
                p.DistanceTo(Geometry3D.GetClosestPointToSegment(p,r.Points[j-1],r.Points[j]))<6+margin));
        void Detail(string name,Vector3 p,float yaw,float radius,float scale=1)
        {
            var asset=Asset(name,p,yaw,new(scale,scale,scale));_islandDetails.Add((p,radius));
            foreach(var mesh in asset.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>())
                mesh.VisibilityRangeEnd=name.StartsWith("passenger")?100:350;
            if(name=="news-kiosk")
            {
                var body=new StaticBody3D();asset.AddChild(body);
                body.AddChild(new CollisionShape3D {Position=new(0,1.2f,0),Shape=new BoxShape3D {Size=new(3,2.4f,2.1f)}});
            }
        }
        var rng=new Random(1972);int trees=0,lamps=0,people=0,kiosks=0;
        var kioskSites=new List<Vector3>();var districtPeople=new int[2];var districtKiosks=new int[2];
        foreach(var road in HarbourRoads.Where(r=>!r.Tunnel && r.Points[0].Z>1100 && r.Name!="-99"))
            for(int i=8;i<road.Points.Count-8;i+=22)
            {
                var p=road.Points[i];var f=(road.Points[i+1]-p).Normalized();var right=f.Cross(Vector3.Up);
                float yaw=Mathf.Atan2(-f.X,-f.Z);
                foreach(int side in new[]{-1,1})
                {
                    var at=p+right*side*8;
                    if(!Clear(at,.6f))continue;
                    var lamp=new Node3D {Name="IslandStreetLamp",Position=at,Rotation=new(0,yaw,0)};AddChild(lamp);
                    Box(lamp,new(0,4.2f,0),new(.12f,8.4f,.12f),"89918a");
                    Box(lamp,new(-.9f*side,8.3f,0),new(1.9f,.10f,.10f),"89918a");
                    Box(lamp,new(-1.75f*side,8.25f,0),new(.55f,.12f,.35f),"e7d6ad");
                    _islandDetails.Add((at,.3f));lamps++;
                    if(lamps%3==0 && !road.Name.StartsWith("&"))
                    {
                        Box(lamp,new(0,5.4f,0),new(3.4f,.5f,.06f),"e2e3d1");
                        var label=Label(lamp,road.Name,new(0,5.4f,.04f),.006f,30);label.Modulate=new("203631");
                    }
                    var tree=p+right*side*12;
                    if(Clear(tree,2.7f))
                    {Detail(trees%2==0?"street-tree":"banyan",tree,rng.NextSingle()*Mathf.Tau,2.7f,trees%2==0?1:.7f);trees++;}
                    else if(Clear(at+f*4,1))Detail("planter",at+f*4,yaw,1);
                    int district=at.X < -300?1:0;
                    var pedestrian=at-f*5;
                    if(districtPeople[district]<(district==0?64:48) && lamps%2==0 && Clear(pedestrian,.45f))
                    {Detail(new[]{"passenger_mei","passenger_dennis","passenger_headphones"}[people%3],pedestrian,yaw+.4f,.45f);people++;districtPeople[district]++;}
                    var kiosk=at+right*side*3+f*12;
                    if(districtKiosks[district]<(district==0?18:12) && Clear(kiosk,2.2f) && !kioskSites.Any(k=>k.DistanceTo(kiosk)<160))
                    {
                        Detail("news-kiosk",kiosk,yaw-side*Mathf.Pi/2,2.2f);kiosks++;districtKiosks[district]++;kioskSites.Add(kiosk);
                        var c=new Vector2(kiosk.X,kiosk.Z);_harbourPaving.Add(new[]{c+new Vector2(-3,-3),c+new Vector2(3,-3),c+new Vector2(3,3),c+new Vector2(-3,3)});
                    }
                }
            }
        // Authored waterside groves occupy clear spaces between the promenade and street network.
        for(float x=IslandBounds.Position.X+24;x<IslandBounds.End.X-24;x+=48)
            foreach(float z in new[]{1148f,1200f})
            {
                var p=new Vector3(x+rng.NextSingle()*16-8,0,z+rng.NextSingle()*12-6);
                if(!Clear(p,3))continue;
                Detail(trees%2==0?"street-tree":"banyan",p,rng.NextSingle()*Mathf.Tau,3,trees%2==0?1.1f:.8f);trees++;
            }
        var stone=new StandardMaterial3D {AlbedoTexture=GD.Load<Texture2D>("res://Assets/Textures/pavement-stone.png"),
            AlbedoColor=new("89948c"),Roughness=.92f,Uv1Triplanar=true,Uv1Scale=new(1.5f,1.5f,1.5f)};
        foreach(var (a,b) in new[]{(new Vector2(IslandBounds.Position.X,1100),new Vector2(1060,1100)),(new Vector2(1140,1100),new Vector2(IslandBounds.End.X,1100)),
            (new Vector2(IslandBounds.Position.X,1100),new Vector2(IslandBounds.Position.X,IslandBounds.End.Y)),(new Vector2(IslandBounds.End.X,1100),new Vector2(IslandBounds.End.X,IslandBounds.End.Y)),(new Vector2(IslandBounds.Position.X,IslandBounds.End.Y),new Vector2(IslandBounds.End.X,IslandBounds.End.Y))})
        {
            var center=(a+b)/2;var d=b-a;float length=d.Length();float yaw=Mathf.Atan2(-d.X,-d.Y);
            var edge=new Node3D {Name="Seawall",Position=new(center.X,0,center.Y),Rotation=new(0,yaw,0)};AddChild(edge);
            var wall=Box(edge,new(0,-.65f,0),new(.75f,3.3f,length),"777e78",true);wall.MaterialOverride=stone;
            Box(edge,new(0,1.05f,0),new(.95f,.18f,length),"adaf9f");
        }
        // Authored promenade stays on the existing land apron and clear of both portal openings.
        foreach(var (start,end) in new[]{(IslandBounds.Position.X+6,1055f),(1145f,IslandBounds.End.X-6)})
        {
            _harbourPaving.Add(new[]{new Vector2(start,1101),new Vector2(end,1101),new Vector2(end,1108),new Vector2(start,1108)});
            for(float x=start+16;x<end-8;x+=32)
            {
                var p=new Vector3(x,0,1106);if(!Clear(p,2))continue;
                Detail("bench",p,Mathf.Pi,1.6f);if(Clear(p+Vector3.Right*4,1))Detail("planter",p+Vector3.Right*4,0,1);
            }
        }
        GD.Print($"ANTILA_HARBOUR_SCENERY: {trees} trees, {lamps} lamps, {people} pedestrians, {kiosks} kiosks; government island blocks and promenade");
    }

    private bool InsideTunnel(Vector3 position)
    {
        if(position.Y>5.6f)return false;
        foreach(var road in HarbourRoads.Where(r=>r.Tunnel))
            for(int i=1;i<road.Points.Count;i++)
            {
                var a=road.Points[i-1];var b=road.Points[i];
                var p=Geometry3D.GetClosestPointToSegment(position,a,b);var delta=position-p;
                if(new Vector2(delta.X,delta.Z).Length()<4.2f && delta.Y>=0 && delta.Y<5.6f)return true;
            }
        return false;
    }

    private void UpdateVehicleLighting()
    {
        uint layer=InsideTunnel(Bus.Position+Vector3.Up*2)?2u:1u;
        foreach(var mesh in _vehicleMeshes)if(mesh.Layers!=layer)mesh.Layers=layer;
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

    private void StartHarbourDrive(int route=0)
    {
        if(Paused || Complete || MapOpen || Bus.Kmh>.5f)return;
        HarbourDrive=true;Complete=false;
        var p=_harbourRoutes[route].Points;var f=p[1]-p[0];
        Bus.ResetAt(p[0]+f.Normalized().Cross(Vector3.Up)*(route>=3?-1.8f:1.8f),Mathf.Atan2(-f.X,-f.Z));
        Bus.SetPaused(false);SetCab(true);
        ShowNotice(route==4?"Admiralty / Central • M map • R returns to H1":route==0?"Follow the tunnel signs. M opens the map; R returns to H1.":"Wan Chai / Causeway Bay • M map • R returns to H1");
    }

    private async Task CheckHarbour()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(HarbourRoads.Count==898 && _harbourRoutes.Count==5,"harbour data count");
        Check(HarbourBounds.Size.Y>3500 && IslandBounds.Size.X==4450 && HarbourBounds.Position.X<=IslandBounds.Position.X-80,"expanded harbour world extent");
        Check(_harbourRoutes[3].Points.Min(p=>p.X)<-190 && _harbourRoutes[3].Points.Max(p=>p.X)>1750,"Scenic drive must reach both expanded districts");
        Check(_islandDetails.Count(d=>d.Position.X < -300)>200,"Western street details missing");
        Check(_lots.Count(l=>l.Center.X < -300 && l.Center.Z>1100)>2000,"Central / Admiralty building massing missing");
        Check(_harbourRoutes[4].Points.Min(p=>p.X)<-1550 && _harbourRoutes[4].Points[0].DistanceTo(_harbourRoutes[4].Points[^1])<.12f,"Central route must reach the west and close");
        using(var mask=((Texture2D)_terrain.GetShaderParameter("harbour_mask").AsGodotObject()).GetImage())
        {
            Color Surface(Vector3 p)
            {
                var uv=(new Vector2(p.X,p.Z)-HarbourBounds.Position)/HarbourBounds.Size;
                return mask.GetPixel((int)(uv.X*mask.GetWidth()),(int)(uv.Y*mask.GetHeight()));
            }
            int paved=0;
            foreach(var road in HarbourRoads.Where(r=>!r.Tunnel))
                for(int i=1;i<road.Points.Count-1;i+=10)
                {
                    var p=road.Points[i];var side=(road.Points[i+1]-p).Normalized().Cross(Vector3.Up)*8;
                    Check(Surface(p).R>.95f,$"Harbour asphalt missing at {p}");
                    Check(Surface(p+side).G>.9f && Surface(p-side).G>.9f,$"Harbour roadside paving missing at {p}");paved++;
                }
            Check(_lots.Count(l=>l.Center.Z>1100)>1900,"Island government building layout missing");
            GD.Print($"ANTILA_HARBOUR_SURFACES_OK: {paved} asphalt and paired pavement samples; island government massing");
        }
        var start=Bus.Position;
        MapOpen=true;_UnhandledInput(new InputEventAction {Action="tunnel",Pressed=true});
        _UnhandledInput(new InputEventAction {Action="island",Pressed=true});
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.J,Pressed=true});
        Check(!HarbourDrive && Bus.Position==start,"map must block the tunnel shortcut");
        MapOpen=false;Paused=true;_UnhandledInput(new InputEventAction {Action="tunnel",Pressed=true});
        _UnhandledInput(new InputEventAction {Action="island",Pressed=true});
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.J,Pressed=true});
        Check(!HarbourDrive && Bus.Position==start,"pause must block the tunnel shortcut");
        Paused=false;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.J,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[4].Points[0])<3,"Central shortcut must start the western loop");
        HarbourDrive=false;_UnhandledInput(new InputEventAction {Action="island",Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[3].Points[0])<3,"island shortcut must start at the scenic route");
        HarbourDrive=false;_UnhandledInput(new InputEventAction {Action="tunnel",Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[0].Points[0])<3,"tunnel shortcut must start at the approach in cab view");
        HarbourDrive=false;SetCab(false);Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        int walls=0;
        foreach(var road in HarbourRoads.Where(r=>r.Tunnel))
            for(int i=3;i<road.Points.Count-3;i++)
            {
                var p=road.Points[i];if(p.Y<-6.5f)continue;
                var side=(road.Points[i+1]-road.Points[i-1]).Cross(Vector3.Up).Normalized();
                foreach(int sign in new[]{-1,1})
                {
                    var origin=p+Vector3.Up*2.5f;
                    var hit=GetWorld3D().DirectSpaceState.IntersectRay(PhysicsRayQueryParameters3D.Create(origin,origin+side*sign*5.5f,1));
                    Check(hit.Count>0 && !(hit["collider"].AsGodotObject() as Node)!.GetParent().Name.ToString().StartsWith("Exterior"),$"Exterior cladding obscures tunnel wall at {p}");walls++;
                }
            }
        GD.Print($"ANTILA_HARBOUR_WALLS_OK: {walls} interior wall rays clear of exterior cladding");
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
        foreach(var route in new[]{(Name:"South portal ramp",Points:ramp),(Name:"Hung Hom exit bend",Points:_harbourRoutes[2].Points.Skip(780).ToList())}.Concat(_harbourRoutes)
            .Where(r=>(!OS.GetCmdlineUserArgs().Contains("--island-check") || r.Name==_harbourRoutes[3].Name) &&
                (!OS.GetCmdlineUserArgs().Contains("--central-check") || r.Name==_harbourRoutes[4].Name)))
        {
            var path=route.Points;var f=(path[1]-path[0]).Normalized();
            bool scenic=route.Name==_harbourRoutes[3].Name || route.Name==_harbourRoutes[4].Name;float lane=scenic?-1.8f:1.8f;
            Bus.ResetAt(path[0]+f.Cross(Vector3.Up)*lane,Mathf.Atan2(-f.X,-f.Z));
            Bus.TestThrottle=Bus.TestBrake=Bus.TestSteer=0;
            for(int frame=0;frame<10;frame++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            int contacts=Bus.Collisions,closest=0;float driven=Bus.DistanceDriven,minY=0;
            for(int tick=0;tick<Mathf.Max(22000,path.Count*20) && closest<path.Count-3;tick++)
            {
                float best=float.MaxValue;
                for(int i=Mathf.Max(0,closest-4),end=Mathf.Min(path.Count,closest+20);i<end;i++)
                {
                    float d=Bus.Position.DistanceTo(path[i]);
                    if(d<best){best=d;closest=i;}
                }
                bool underground=path[closest].Y<-1;
                int index=Mathf.Min(path.Count-2,closest+(underground?4:scenic?3:2));
                var direction=(path[index+1]-path[index]).Normalized();
                var target=path[index]+direction.Cross(Vector3.Up)*lane;
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
