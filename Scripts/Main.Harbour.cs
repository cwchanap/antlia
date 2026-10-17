using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;

public partial class Main
{
    public Rect2 HarbourBounds,IslandBounds,KowloonNorthBounds;
    public Vector2[] KowloonWestLand = Array.Empty<Vector2>();
    public Vector2[] IslandLand = Array.Empty<Vector2>();
    public readonly List<Vector2[]> KowloonCoastline = new();
    public readonly List<Vector2[]> IslandCoastline = new();
    private readonly List<(Vector3 Position,float Radius)> _islandDetails = new();
    public bool HarbourDrive;
    public readonly List<(string Name,bool Tunnel,bool Elevated,float Width,List<Vector3> Points)> HarbourRoads = new();
    private readonly List<(string Name,List<Vector3> Points)> _harbourRoutes = new();
    private Node3D _harbour = null!;
    private MeshInstance3D[] _vehicleMeshes = Array.Empty<MeshInstance3D>();
    private ShaderMaterial _harbourPaint = null!;
    private readonly List<Vector2[]> _harbourPaving = new();
    private Vector3 _streetLookupPosition;
    private string? _streetName;

    private MeshInstance3D BuildHarbour()
    {
        using var doc=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/cross-harbour.json"));
        var root=doc.RootElement;var b=root.GetProperty("bounds");
        var island=root.GetProperty("island_bounds");IslandBounds=new(island[0].GetSingle(),island[1].GetSingle(),island[2].GetSingle()-island[0].GetSingle(),island[3].GetSingle()-island[1].GetSingle());
        var north=root.GetProperty("kowloon_north_bounds");KowloonNorthBounds=new(north[0].GetSingle(),north[1].GetSingle(),north[2].GetSingle()-north[0].GetSingle(),north[3].GetSingle()-north[1].GetSingle());
        Vector2[] FlatPoints(JsonElement row)=>row.EnumerateArray().Select(p=>new Vector2(p[0].GetSingle(),p[1].GetSingle())).ToArray();
        KowloonWestLand=FlatPoints(root.GetProperty("kowloon_west_land").GetProperty("coordinates")[0]);
        IslandLand=FlatPoints(root.GetProperty("island_land").GetProperty("coordinates")[0]);
        foreach(var line in root.GetProperty("kowloon_coastline").EnumerateArray())KowloonCoastline.Add(FlatPoints(line));
        foreach(var line in root.GetProperty("island_coastline").EnumerateArray())IslandCoastline.Add(FlatPoints(line));
        HarbourBounds=new(b[0].GetSingle(),b[1].GetSingle(),b[2].GetSingle()-b[0].GetSingle(),b[3].GetSingle()-b[1].GetSingle());
        List<Vector3> Points(JsonElement row)=>row.GetProperty("points").EnumerateArray().Select(p=>new Vector3(p[0].GetSingle(),p[1].GetSingle(),p[2].GetSingle())).ToList();
        foreach(var road in root.GetProperty("roads").EnumerateArray())
        {
            _harbourRoadIndex[road.GetProperty("id").GetString()!]=HarbourRoads.Count;
            HarbourRoads.Add((road.GetProperty("name").GetString()!,road.GetProperty("tunnel").GetBoolean(),road.GetProperty("elevated").GetBoolean(),road.GetProperty("width").GetSingle(),Points(road)));
        }
        foreach(var route in root.GetProperty("routes").EnumerateArray())
        {
            _harbourRoutes.Add((route.GetProperty("name").GetString()!,Points(route)));
            _harbourRouteSources.Add(route.GetProperty("source_ids").EnumerateArray().Select(id=>id.GetString()!).ToArray());
        }
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
            if(name.StartsWith("Exterior") || name.StartsWith("Portal") || name.StartsWith("Deck") || name.EndsWith("Seawall") || name.EndsWith("Boundary"))mesh.MaterialOverride=exterior;
            if(name=="RoadSurface" || name=="HarbourWater" || name.StartsWith("Paint") || name.StartsWith("Lamps") || name.StartsWith("Reflectors"))continue;
            var body=new StaticBody3D {Name="Solid",Position=name.StartsWith("Road_") || name.StartsWith("Deck")?Vector3.Down*.035f:Vector3.Zero};mesh.AddChild(body);
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
        bool West(Vector3 p,float margin)=>!Map.Bounds.Grow(margin+2).HasPoint(new(p.X,p.Z)) && Geometry2D.IsPointInPolygon(new(p.X,p.Z),KowloonWestLand) &&
            !KowloonCoastline.Any(line=>Enumerable.Range(1,line.Length-1).Any(i=>Geometry2D.GetClosestPointToSegment(new(p.X,p.Z),line[i-1],line[i]).DistanceTo(new(p.X,p.Z))<margin+2));
        bool Island(Vector3 p,float margin)=>Geometry2D.IsPointInPolygon(new(p.X,p.Z),IslandLand) &&
            !IslandCoastline.Any(line=>Enumerable.Range(1,line.Length-1).Any(i=>Geometry2D.GetClosestPointToSegment(new(p.X,p.Z),line[i-1],line[i]).DistanceTo(new(p.X,p.Z))<margin+2));
        bool Clear(Vector3 p,float margin)=>((p.Z<0?KowloonNorthBounds.Grow(-margin-1).HasPoint(new(p.X,p.Z)):Island(p,margin)) || West(p,margin)) &&
            !_lots.Any(l=>l.Bounds.Grow(margin).HasPoint(new(p.X,p.Z))) &&
            !_islandDetails.Any(d=>p.DistanceTo(d.Position)<d.Radius+margin+1) &&
            !HarbourRoads.Any(r=>Enumerable.Range(1,r.Points.Count-1).Any(j=>
                new Vector2(p.X,p.Z).DistanceTo(Geometry2D.GetClosestPointToSegment(new(p.X,p.Z),new(r.Points[j-1].X,r.Points[j-1].Z),new(r.Points[j].X,r.Points[j].Z)))<6+margin));
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
        var kioskSites=new List<Vector3>();var districtPeople=new int[9];var districtKiosks=new int[9];
        foreach(var road in HarbourRoads.Where(r=>!r.Tunnel && !r.Elevated && (r.Points[0].Z>0 || r.Points[0].Z < KowloonNorthBounds.End.Y || West(r.Points[0],0)) && r.Name!="-99"))
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
                    int district=at.X < -8500 || at.Z < -11000?8:at.X < -6500 || at.Z < -8500?7:at.X < -4600 || at.Z < -6000?6:at.X < -2700 || at.Z < -4800?5:at.Z<0?(KowloonNorthBounds.HasPoint(new(at.X,at.Z))?2:at.Z < -3350?4:3):at.X < -300?1:0;
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
        // Promenade follows the sourced shore; the land mesh clips paving at tight pier corners.
        float nextBench=0;
        foreach(var line in IslandCoastline)
            for(int i=1;i<line.Length;i++)
            {
                var a=line[i-1];var b=line[i];var delta=b-a;float length=delta.Length();
                if(length<.1f)continue;
                var normal=delta.Orthogonal().Normalized();var midpoint=(a+b)/2;
                if(!Geometry2D.IsPointInPolygon(midpoint+normal*4,IslandLand))normal=-normal;
                if(!Geometry2D.IsPointInPolygon(midpoint+normal*4,IslandLand))continue;
                _harbourPaving.Add(new[]{a+normal,b+normal,b+normal*8,a+normal*8});
                for(float along=nextBench;along<length;along+=48)
                {
                    var q=a+delta*(along/length)+normal*5;var p=new Vector3(q.X,0,q.Y);
                    if(Clear(p,2))Detail("bench",p,Mathf.Atan2(-normal.X,-normal.Y),1.6f);
                }
                nextBench=(nextBench-length)%48;if(nextBench<0)nextBench+=48;
            }
        // Outer north/east barriers and the sourced coastline are batched in the harbour GLB.
        GD.Print($"ANTILA_WEST_KOWLOON_SCENERY: {districtPeople[3]+districtPeople[4]} pedestrians; {districtKiosks[3]+districtKiosks[4]} kiosks; government western shore");
        GD.Print($"ANTILA_WEST_COAST_SCENERY: {districtPeople[8]} pedestrians; {districtKiosks[8]} kiosks; Ting Kau / Sham Tseng");
        GD.Print($"ANTILA_TSUEN_WAN_SCENERY: {districtPeople[7]} pedestrians; {districtKiosks[7]} kiosks; Tsuen Wan / northern Kwai Chung");
        GD.Print($"ANTILA_KWAI_CHUNG_SCENERY: {districtPeople[6]} pedestrians; {districtKiosks[6]} kiosks; Mei Foo / Lai King / Kwai Chung");
        GD.Print($"ANTILA_NORTHWEST_SCENERY: {districtPeople[5]} pedestrians; {districtKiosks[5]} kiosks; Cheung Sha Wan / Lai Chi Kok");
        GD.Print($"ANTILA_KOWLOON_SCENERY: {_islandDetails.Count(d=>d.Position.Z<KowloonNorthBounds.End.Y)} details; {districtPeople[2]} pedestrians; {districtKiosks[2]} kiosks");
        GD.Print($"ANTILA_HARBOUR_SCENERY: {trees} trees, {lamps} lamps, {people} pedestrians, {kiosks} kiosks; government expansion blocks and island promenade");
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
        var position=Bus.Position;
        // shortcut: street changes may lag by 3 m, use a spatial index if precise junction labels become necessary.
        if(_streetName!=null && position.DistanceSquaredTo(_streetLookupPosition)<9 &&
            (position.Y<-1)==(_streetLookupPosition.Y<-1))return _streetName;
        var nearest=Map.NearestStreet(position);float best=nearest.Distance;
        string name=nearest.Name;
        if(position.Y<-1)best=float.MaxValue;
        foreach(var road in HarbourRoads)
            for(int i=1;i<road.Points.Count;i++)
            {
                float d=position.DistanceTo(Geometry3D.GetClosestPointToSegment(position,road.Points[i-1],road.Points[i]));
                if(d<best){best=d;name=road.Name;}
            }
        _streetLookupPosition=position;_streetName=string.IsNullOrWhiteSpace(name) || name is "-99" or "<Null>" or "&lt;Null&gt;"?"UNNAMED CONNECTION":name;
        return _streetName;
    }

    private void StartHarbourDrive(int route=0)
    {
        if(Paused || Complete || MapOpen || Bus.Kmh>.5f)return;
        HarbourDrive=true;Complete=false;
        var p=_harbourRoutes[route].Points;var f=p[1]-p[0];
        Bus.ResetAt(p[0]+f.Normalized().Cross(Vector3.Up)*(route>=3?-1.8f:1.8f),Mathf.Atan2(-f.X,-f.Z));
        Bus.SetPaused(false);SetCab(true);
        ShowNotice((route==11?"Ting Kau / Sham Tseng • M map • R returns to H1":route==10?"Kwai Chung / Tsuen Wan • M map • R returns to H1":route==9?"Mei Foo / Lai King / Kwai Chung • M map • R returns to H1":route==8?"Sham Shui Po / Cheung Sha Wan / Lai Chi Kok • M map • R returns to H1":route==6?"West Kowloon / Tai Kok Tsui / Sham Shui Po • M map • R returns to H1":route==5?"Jordan / Yau Ma Tei / Mong Kok • M map • R returns to H1":route==4?"Admiralty / Central • M map • R returns to H1":route==0?"Follow the tunnel signs. M opens the map; R returns to H1.":"Wan Chai / Causeway Bay • M map • R returns to H1").Replace("H1",Route.Number));
    }

    private void CheckGovernmentMap()
    {
        var failures=new List<string>();
        foreach(var p in new[]{new Vector3(549.97f,0,1662.43f),new Vector3(555.78f,0,1663.72f),
            new Vector3(-1483.04f,0,-2909.95f),new Vector3(-1436.30f,0,-2939.52f),
            new Vector3(-1523.75f,0,-2972.54f),new Vector3(-1478.03f,0,-3002.60f)})
        {
            using var upperRay=PhysicsRayQueryParameters3D.Create(p+Vector3.Up*14,p+Vector3.Up*5.5f,1);
            using var lowerRay=PhysicsRayQueryParameters3D.Create(p+Vector3.Up*4.8f,p+Vector3.Down,1);
            var upper=GetWorld3D().DirectSpaceState.IntersectRay(upperRay);
            var lower=GetWorld3D().DirectSpaceState.IntersectRay(lowerRay);
            if(upper.Count==0 || Mathf.Abs(upper["position"].AsVector3().Y-7)>.1f || lower.Count==0 || Mathf.Abs(lower["position"].AsVector3().Y)>.1f)
                failures.Add($"Missing separate elevated deck and ground road at {p}");
        }
        using(var ray=PhysicsRayQueryParameters3D.Create(new(-1343.35f,410,1079.88f),new(-1343.35f,390,1079.88f),1))
        {
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
            if(hit.Count==0 || Mathf.Abs(hit["position"].AsVector3().Y-402.5f)>.1f)
                failures.Add("Two IFC tower roof is clipped by the island land boundary");
        }
        foreach(var z in new[]{-1310.2907f,-1313.7907f,-1316.2907f})
        {
            var p=new Vector3(887.6666f,0,z);
            using var ray=PhysicsRayQueryParameters3D.Create(p+Vector3.Up*2,p+Vector3.Down*3,1);
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
            if(hit.Count==0 || Mathf.Abs(hit["position"].AsVector3().Y)>.1f)
                failures.Add($"Hong Chong Road carriageway lacks ground at {p}");
        }
        foreach(var (name,a,b) in new[]{("Ping An Tower",new Vector3(-761.5552f,160,-1164.2289f),new Vector3(-756.2598f,160,-1201.3289f)),
            ("One IGC",new Vector3(-811.1124f,130,-1181.1583f),new Vector3(-805.3707f,130,-1217.0359f))})
        {
            using var rayA=PhysicsRayQueryParameters3D.Create(a,a-Vector3.Up*30,1);
            using var rayB=PhysicsRayQueryParameters3D.Create(b,b-Vector3.Up*30,1);
            var roofA=GetWorld3D().DirectSpaceState.IntersectRay(rayA);
            var roofB=GetWorld3D().DirectSpaceState.IntersectRay(rayB);
            if(roofA.Count==0 || roofB.Count==0 || Mathf.Abs(roofA["position"].AsVector3().Y-roofB["position"].AsVector3().Y)>.05f)
                failures.Add($"{name} roof height differs across the regional boundary");
        }
        foreach(var p in new[]{new Vector3(1082.488f,0,1260.517f),new Vector3(1096.1724f,0,1260.3794f),
            new Vector3(840.4762f,0,-778.3663f),new Vector3(816.3204f,0,-699.4204f)})
        {
            using var ray=PhysicsRayQueryParameters3D.Create(p+Vector3.Up*1.5f,p+Vector3.Down*2,1);
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
            if(hit.Count==0 || Mathf.Abs(hit["position"].AsVector3().Y)>.05f)
                failures.Add($"Tunnel entrance has a ground / floor gap at {p}");
        }
        foreach(var p in new[]{new Vector3(508.0855f,7,1592.6369f),new Vector3(-1335.3376f,2.6915f,-3122.6752f),
            new Vector3(-1531.085f,7,-2965.6006f),new Vector3(-1493.0382f,7,-2905.7468f),
            new Vector3(-1472.9465f,7,-3006.0779f),new Vector3(-1540.3047f,6.8878f,-2951.683f)})
        {
            using var ray=PhysicsRayQueryParameters3D.Create(p+Vector3.Up*.2f,p+Vector3.Down*.2f,1);
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
            if(hit.Count==0 || Mathf.Abs(hit["position"].AsVector3().Y-p.Y)>.1f)
                failures.Add($"Raised road join lacks deck support at {p}");
        }
        foreach(var (p,land) in new[]{(new Vector3(-1600,0,850),true),(new Vector3(-1600,0,1000),true),
            (new Vector3(0,0,600),false),(new Vector3(1000,0,900),false)})
        {
            using var ray=PhysicsRayQueryParameters3D.Create(p+Vector3.Up,p+Vector3.Down*2,1);
            if((GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0)!=land)failures.Add($"Island land / sea collision mismatch at {p}");
        }
        int walls=0;
        foreach(var line in IslandCoastline)
            for(int i=1;i<line.Length;i+=50)
            {
                var a=line[i-1];var b=line[i];if(a.DistanceTo(b)<1)continue;
                var middle=(a+b)/2;var normal=(b-a).Orthogonal().Normalized();
                var p=new Vector3(middle.X,.6f,middle.Y);var side=new Vector3(normal.X,0,normal.Y);
                using var ray=PhysicsRayQueryParameters3D.Create(p+side*1.5f,p-side*1.5f,1);
                var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
                if(hit.Count==0 || (hit["collider"].AsGodotObject() as Node)!.GetParent().Name!="IslandSeawall")failures.Add($"Island seawall collision missing at {p}");
                walls++;
            }
        if(walls==0)failures.Add("No island seawall probes ran");
        if(failures.Count>0)throw new Exception(string.Join("; ",failures));
        GD.Print($"ANTILA_GOVERNMENT_MAP_OK: six grade-separated crossings retain lower roads; Two IFC roof restored; Hong Chong carriageway supported; 2 regional roof seams level; 4 tunnel entrances supported; 6 raised joins supported; 4 island land / sea and {walls} seawall probes");
    }

    private async Task CheckNorthwest()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        var initial=Bus.Position;
        foreach(int state in new[]{0,1,2})
        {
            MapOpen=state==0;Paused=state==1;Complete=state==2;
            _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.N,Pressed=true});
            Check(!HarbourDrive && Bus.Position==initial,"Northwest shortcut must respect map, pause and completed service");
        }
        MapOpen=Paused=Complete=false;
        Bus.AutomaticTest=true;Bus.TestThrottle=1;
        for(int i=0;i<45;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(Bus.Kmh>.5f,"Northwest moving-shortcut check must move the bus");
        var moving=Bus.Position;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.N,Pressed=true});
        Check(!HarbourDrive && Bus.Position==moving,"Northwest shortcut must not teleport a moving bus");
        Bus.TestThrottle=0;Bus.AutomaticTest=false;Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.N,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[8].Points[0])<3,"N shortcut must start the Lai Chi Kok drive");
        HarbourDrive=false;SetCab(false);Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        Check(HarbourBounds.Position.X<=-4680 && HarbourBounds.Position.Y<=-6080,"Northwestern map extent missing");
        Check(_lots.Count(l=>l.Center.X < -2700 || l.Center.Z < -4800)>300,"Lai Chi Kok building coverage missing");
        Check(_islandDetails.Count(d=>d.Position.X < -2700 || d.Position.Z < -4800)>80,"Lai Chi Kok street detail missing");
        var route=_harbourRoutes[8].Points;
        Check(route[0].DistanceTo(_harbourRoutes[7].Points[^1])<.12f && route.Min(p=>p.X)<-3300 && route.Min(p=>p.Z)<-4800,"Northwest drive must connect Sham Shui Po to Lai Chi Kok");
        int support=0;
        for(int i=0;i<route.Count-1;i+=7)
            foreach(float lane in new[]{-1.8f,0,1.8f})
            {
                var at=route[i]+(route[i+1]-route[i]).Normalized().Cross(Vector3.Up)*lane;
                using var ray=PhysicsRayQueryParameters3D.Create(at+Vector3.Up*.2f,at+Vector3.Down*.2f,1);
                Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,$"Northwest route lacks ground support at {at}");support++;
            }
        GD.Print($"ANTILA_NORTHWEST_READY_OK: N shortcut and four guards; regional massing/detail; {support} lane-support probes");
    }

    private async Task CheckKwaiChung()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        var initial=Bus.Position;
        foreach(int state in new[]{0,1,2})
        {
            MapOpen=state==0;Paused=state==1;Complete=state==2;
            _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.B,Pressed=true});
            Check(!HarbourDrive && Bus.Position==initial,"Kwai Chung shortcut must respect map, pause and completed service");
        }
        MapOpen=Paused=Complete=false;
        Bus.AutomaticTest=true;Bus.TestThrottle=1;
        for(int i=0;i<45;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(Bus.Kmh>.5f,"Kwai Chung moving-shortcut check must move the bus");
        var moving=Bus.Position;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.B,Pressed=true});
        Check(!HarbourDrive && Bus.Position==moving,"Kwai Chung shortcut must not teleport a moving bus");
        Bus.TestThrottle=0;Bus.AutomaticTest=false;Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.B,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[9].Points[0])<3,"B shortcut must start the Kwai Chung drive");
        HarbourDrive=false;SetCab(false);Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        Check(HarbourBounds.Position.X<=-6580 && HarbourBounds.Position.Y<=-8580,"Kwai Chung map extent missing");
        Check(_lots.Count(l=>l.Center.X < -4600 || l.Center.Z < -6000)>300,"Kwai Chung building coverage missing");
        Check(_islandDetails.Count(d=>d.Position.X < -4600 || d.Position.Z < -6000)>80,"Kwai Chung street detail missing");
        var route=_harbourRoutes[9].Points;
        Check(route[0].DistanceTo(_harbourRoutes[8].Points[^1])<.12f && route.Min(p=>p.X)<-4500 && route.Min(p=>p.Z)<-6800,"Kwai Chung drive must connect Mei Foo to Kwai Chung");
        int support=0;
        for(int i=0;i<route.Count-1;i+=7)
            foreach(float lane in new[]{-1.8f,0,1.8f})
            {
                var at=route[i]+(route[i+1]-route[i]).Normalized().Cross(Vector3.Up)*lane;
                using var ray=PhysicsRayQueryParameters3D.Create(at+Vector3.Up*.2f,at+Vector3.Down*.2f,1);
                Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,$"Kwai Chung route lacks ground support at {at}");support++;
            }
        GD.Print($"ANTILA_KWAI_CHUNG_READY_OK: B shortcut and four guards; regional massing/detail; {support} lane-support probes");
    }

    private async Task CheckTsuenWan()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(InputMap.HasAction("tsuen_wan"),"Tsuen Wan shortcut action missing");
        var initial=Bus.Position;
        foreach(int state in new[]{0,1,2})
        {
            MapOpen=state==0;Paused=state==1;Complete=state==2;
            _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.U,Pressed=true});
            Check(!HarbourDrive && Bus.Position==initial,"Tsuen Wan shortcut must respect map, pause and completed service");
        }
        MapOpen=Paused=Complete=false;
        Bus.AutomaticTest=true;Bus.TestThrottle=1;
        for(int i=0;i<45;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(Bus.Kmh>.5f,"Tsuen Wan moving-shortcut check must move the bus");
        var moving=Bus.Position;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.U,Pressed=true});
        Check(!HarbourDrive && Bus.Position==moving,"Tsuen Wan shortcut must not teleport a moving bus");
        Bus.TestThrottle=0;Bus.AutomaticTest=false;Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.U,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[10].Points[0])<3,"U shortcut must start the Tsuen Wan drive");
        HarbourDrive=false;SetCab(false);Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        Check(HarbourBounds.Position.X<=-8580 && HarbourBounds.Position.Y<=-11080,"Tsuen Wan map extent missing");
        Check(_lots.Count(l=>l.Center.X < -6500 || l.Center.Z < -8500)>300,"Tsuen Wan building coverage missing");
        Check(_islandDetails.Count(d=>d.Position.X < -6500 || d.Position.Z < -8500)>80,"Tsuen Wan street detail missing");
        var route=_harbourRoutes[10].Points;
        Check(route[0].DistanceTo(_harbourRoutes[9].Points[^1])<.12f && route.Min(p=>p.X)<-6600 && route.Min(p=>p.Z)<-9000,"Tsuen Wan drive must connect Kwai Chung to Tsuen Wan");
        int support=0;
        for(int i=0;i<route.Count-1;i+=7)
            foreach(float lane in new[]{-1.8f,0,1.8f})
            {
                var at=route[i]+(route[i+1]-route[i]).Normalized().Cross(Vector3.Up)*lane;
                using var ray=PhysicsRayQueryParameters3D.Create(at+Vector3.Up*.2f,at+Vector3.Down*.2f,1);
                Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,$"Tsuen Wan route lacks ground support at {at}");support++;
            }
        GD.Print($"ANTILA_TSUEN_WAN_READY_OK: U shortcut and four guards; regional massing/detail; {support} lane-support probes");
    }

    private async Task CheckWestCoast()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(InputMap.HasAction("west_coast"),"West coast shortcut action missing");
        var initial=Bus.Position;
        foreach(int state in new[]{0,1,2})
        {
            MapOpen=state==0;Paused=state==1;Complete=state==2;
            _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.O,Pressed=true});
            Check(!HarbourDrive && Bus.Position==initial,"West coast shortcut must respect map, pause and completed service");
        }
        MapOpen=Paused=Complete=false;
        Bus.AutomaticTest=true;Bus.TestThrottle=1;
        for(int i=0;i<45;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(Bus.Kmh>.5f,"West coast moving-shortcut check must move the bus");
        var moving=Bus.Position;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.O,Pressed=true});
        Check(!HarbourDrive && Bus.Position==moving,"West coast shortcut must not teleport a moving bus");
        Bus.TestThrottle=0;Bus.AutomaticTest=false;Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.O,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[11].Points[0])<3,"O shortcut must start the West coast drive");
        HarbourDrive=false;SetCab(false);Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        Check(HarbourBounds.Position.X<=-13880 && HarbourBounds.Position.Y<=-11280,"West coast map extent missing");
        Check(_lots.Count(l=>l.Center.X < -8500 || l.Center.Z < -11000)>100,"West coast building coverage missing");
        Check(_islandDetails.Count(d=>d.Position.X < -8500 || d.Position.Z < -11000)>80,"West coast street detail missing");
        var route=_harbourRoutes[11].Points;
        Check(route[0].DistanceTo(_harbourRoutes[10].Points[^1])<.12f && route.Min(p=>p.X)<-11700,"West coast drive must connect Tsuen Wan to Sham Tseng");
        int support=0;
        for(int i=0;i<route.Count-1;i+=7)
            foreach(float lane in new[]{-1.8f,0,1.8f})
            {
                var at=route[i]+(route[i+1]-route[i]).Normalized().Cross(Vector3.Up)*lane;
                using var ray=PhysicsRayQueryParameters3D.Create(at+Vector3.Up*.2f,at+Vector3.Down*.2f,1);
                Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,$"West coast route lacks ground support at {at}");support++;
            }
        GD.Print($"ANTILA_WEST_COAST_READY_OK: O shortcut and four guards; regional massing/detail; {support} lane-support probes");
    }

    private async Task CheckHarbour()
    {
        await CheckWestCoast();
        await CheckTsuenWan();
        await CheckKwaiChung();
        CheckGovernmentMap();
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(HarbourRoads.Count==5164 && _harbourRoutes.Count==12,"harbour data count");
        await CheckNorthwest();
        Check(HarbourBounds.Size.Y>3500 && IslandBounds.Size.X==4450 && HarbourBounds.Position.X<=IslandBounds.Position.X-80,"expanded harbour world extent");
        Check(_harbourRoutes[3].Points.Min(p=>p.X)<-190 && _harbourRoutes[3].Points.Max(p=>p.X)>1750,"Scenic drive must reach both expanded districts");
        Check(_islandDetails.Count(d=>d.Position.X < -300 && d.Position.Z>1100)>200,"Western street details missing");
        Check(_lots.Count(l=>l.Center.X < -300 && l.Center.Z>1100)>2000,"Central / Admiralty building massing missing");
        Check(_harbourRoutes[4].Points.Min(p=>p.X)<-1550 && _harbourRoutes[4].Points[0].DistanceTo(_harbourRoutes[4].Points[^1])<.12f,"Central route must reach the west and close");
        Check(KowloonNorthBounds.Size.Y>2100 && HarbourBounds.Position.Y<=KowloonNorthBounds.Position.Y-80,"North Kowloon extent missing");
        Check(_lots.Count(l=>l.Center.Z < -1200)>1500 && _islandDetails.Count(d=>d.Position.Z < -1200)>80,"North Kowloon buildings or street details missing");
        Check(_harbourRoutes[5].Points[0].Z > -1200 && _harbourRoutes[5].Points[^1].Z < -3200,"Kowloon drive must connect Jordan to Mong Kok");
        Check(HarbourBounds.Position.X<=-2780 && HarbourBounds.Position.Y<=-4880,"Western coastline / Sham Shui Po extent missing");
        Check(_lots.Count(l=>l.Center.Z < -3350)>3000 && _lots.Count(l=>l.Center.X < -1100 && l.Center.Z < 0)>500,"Western / northern building coverage missing");
        Check(KowloonCoastline.Count>0 && KowloonCoastline.SelectMany(p=>p).Min(p=>p.X)<-2500,"Sourced western coast missing");
        Check(_harbourRoutes[6].Points.Min(p=>p.X)<-1800 && _harbourRoutes[6].Points.Min(p=>p.Z)<-3900,"West drive must reach the coast and Sham Shui Po");
        Check(_harbourRoutes[7].Points[0].DistanceTo(_harbourRoutes[5].Points[^1])<.12f && _harbourRoutes[7].Points.Min(p=>p.Z)<-4000,"Mong Kok continuation must join Sham Shui Po");
        using(var mask=((Texture2D)_terrain.GetShaderParameter("harbour_mask").AsGodotObject()).GetImage())
        {
            Color Surface(Vector3 p)
            {
                var uv=(new Vector2(p.X,p.Z)-HarbourBounds.Position)/HarbourBounds.Size;
                // Match the terrain shader's linear sampling at texel centres. A nearest
                // texel can be almost 0.7 m away when the expanded mask reaches its 16K cap.
                var pixel=uv*new Vector2(mask.GetWidth(),mask.GetHeight())-Vector2.One*.5f;
                int x=Mathf.FloorToInt(pixel.X),y=Mathf.FloorToInt(pixel.Y);
                Color At(int a,int b)=>mask.GetPixel(Math.Clamp(a,0,mask.GetWidth()-1),Math.Clamp(b,0,mask.GetHeight()-1));
                return At(x,y).Lerp(At(x+1,y),pixel.X-x).Lerp(At(x,y+1).Lerp(At(x+1,y+1),pixel.X-x),pixel.Y-y);
            }
            int paved=0;
            foreach(var road in HarbourRoads.Where(r=>!r.Tunnel && !r.Elevated))
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
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.K,Pressed=true});
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.L,Pressed=true});
        Check(!HarbourDrive && Bus.Position==start,"map must block the tunnel shortcut");
        MapOpen=false;Paused=true;_UnhandledInput(new InputEventAction {Action="tunnel",Pressed=true});
        _UnhandledInput(new InputEventAction {Action="island",Pressed=true});
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.J,Pressed=true});
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.K,Pressed=true});
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.L,Pressed=true});
        Check(!HarbourDrive && Bus.Position==start,"pause must block the tunnel shortcut");
        Paused=false;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.L,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[6].Points[0])<3,"West shortcut must start at Austin Road West");
        HarbourDrive=false;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.K,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[5].Points[0])<3,"Kowloon shortcut must start at Jordan");
        HarbourDrive=false;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.J,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[4].Points[0])<3,"Central shortcut must start the western loop");
        HarbourDrive=false;_UnhandledInput(new InputEventAction {Action="island",Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[3].Points[0])<3,"island shortcut must start at the scenic route");
        HarbourDrive=false;_UnhandledInput(new InputEventAction {Action="tunnel",Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[0].Points[0])<3,"tunnel shortcut must start at the approach in cab view");
        HarbourDrive=false;SetCab(false);Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        foreach(var (p,land) in new[]{(new Vector3(-1600,0,-700),true),(new Vector3(-700,0,-4000),true),
            (new Vector3(-2000,0,-800),false),(new Vector3(-2600,0,-1000),false)})
        {
            using var ray=PhysicsRayQueryParameters3D.Create(p+Vector3.Up*1,p+Vector3.Down*2,1);
            Check((GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0)==land,$"Western land / sea collision mismatch at {p}");
        }
        int shoreWalls=0;
        foreach(var line in KowloonCoastline.Where((_,i)=>i%25==0))
        {
            var a=line[0];var b=line[1];var middle=(a+b)/2;var normal=(b-a).Orthogonal().Normalized();
            var p=new Vector3(middle.X,.6f,middle.Y);var side=new Vector3(normal.X,0,normal.Y);
            using var ray=PhysicsRayQueryParameters3D.Create(p+side*1.5f,p-side*1.5f,1);
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
            Check(hit.Count>0 && (hit["collider"].AsGodotObject() as Node)!.GetParent().Name=="KowloonSeawall",$"Western seawall collision missing at {p}");shoreWalls++;
        }
        GD.Print($"ANTILA_COAST_COLLISION_OK: 4 land / sea probes; {shoreWalls} seawall probes");
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
        int samples=0;var obstructions=new List<string>();
        foreach(var road in HarbourRoads)
            for(int i=2;i<road.Points.Count-2;i+=3)
            foreach(float lane in road.Elevated?new[]{-1.4f,0,1.4f}:new[]{-1.8f,0,1.8f})
            {
                var p=road.Points[i];var f=(road.Points[i+1]-p).Normalized();
                // Match the bus's floor-following pitch when probing a raised approach.
                var basis=new Basis(Vector3.Up,Mathf.Atan2(-f.X,-f.Z))*new Basis(Vector3.Right,Mathf.Asin(f.Y));
                query.Transform=new(basis,p+f.Cross(Vector3.Up).Normalized()*lane+basis.Y*2.55f);
                var hit=GetWorld3D().DirectSpaceState.IntersectShape(query,1);
                if(hit.Count>0)obstructions.Add($"{road.Name} at {p}; {(hit[0]["collider"].AsGodotObject() as Node)?.GetPath()}");samples++;
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
        GD.Print(obstructions.Count==0?$"ANTILA_HARBOUR_CLEARANCE_OK: {samples} full bus envelope queries":$"ANTILA_HARBOUR_OBSTRUCTIONS ({obstructions.Count}): "+string.Join("; ",obstructions.Distinct()));
        SetPhysicsProcess(false);HarbourDrive=true;Bus.AutomaticTest=true;Engine.TimeScale=4;
        var raisedPoints=HarbourRoads.Where(r=>r.Elevated).SelectMany(r=>r.Points).ToHashSet();
        float LaneWidth(Vector3 p)=>raisedPoints.Contains(p)?1.4f:1.8f;
        var ramp=_harbourRoutes[0].Points.Where(p=>p.Z>1080 && p.Z<1300).ToList();
        var flyovers=HarbourRoads.Where(r=>r.Name=="HOI FAI ROAD" && r.Points.Count>=18 && r.Points.All(p=>p.Y>6.9f))
            .Select((r,i)=>(Name:$"Hoi Fai flyover {i+1}",Points:r.Points));
        // Check the newest districts first, before repeating the longer established drives.
        foreach(var route in flyovers.Concat(new[]{(Name:"Hung Hing ramp bend",Points:_harbourRoutes[3].Points.Skip(130).Take(90).ToList()),(Name:"Wan Chai ramp bend",Points:_harbourRoutes[1].Points.Skip(130).Take(90).ToList()),(Name:"Lin Cheung ramp entry",Points:_harbourRoutes[6].Points.Skip(730).Take(200).ToList()),(Name:"South portal ramp",Points:ramp),(Name:"Hung Hom exit bend",Points:_harbourRoutes[2].Points.Skip(780).ToList())}).Concat(_harbourRoutes.AsEnumerable().Reverse())
            .Where(r=>(!OS.GetCmdlineUserArgs().Contains("--island-check") || r.Name==_harbourRoutes[3].Name) &&
                (!OS.GetCmdlineUserArgs().Contains("--central-check") || r.Name==_harbourRoutes[4].Name) &&
                (!OS.GetCmdlineUserArgs().Contains("--kowloon-check") || r.Name==_harbourRoutes[5].Name) &&
                (!OS.GetCmdlineUserArgs().Contains("--west-check") || r.Name==_harbourRoutes[6].Name || r.Name==_harbourRoutes[7].Name) &&
                (!OS.GetCmdlineUserArgs().Contains("--northwest-check") || r.Name==_harbourRoutes[8].Name) &&
                (!OS.GetCmdlineUserArgs().Contains("--kwai-chung-check") || r.Name==_harbourRoutes[9].Name) &&
                (!OS.GetCmdlineUserArgs().Contains("--tsuen-wan-check") || r.Name==_harbourRoutes[10].Name) &&
                (!OS.GetCmdlineUserArgs().Contains("--west-coast-check") || r.Name==_harbourRoutes[11].Name)))
        {
            var path=route.Points;var f=(path[1]-path[0]).Normalized();
            bool scenic=_harbourRoutes.Skip(3).Any(r=>r.Name==route.Name) || route.Name is "Lin Cheung ramp entry" or "Hung Hing ramp bend";float side=scenic?-1:1;
            Bus.ResetAt(path[0]+f.Cross(Vector3.Up)*side*LaneWidth(path[0]),Mathf.Atan2(-f.X,-f.Z));
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
                bool tightTurn=false;
                if(scenic)
                    for(int i=Math.Max(1,closest-3);i<Math.Min(path.Count-1,closest+9);i++)
                        if((path[i]-path[i-1]).Normalized().Dot((path[i+1]-path[i]).Normalized())<.7f){tightTurn=true;break;}
                // Anticipate sharp source junctions before the steering-error threshold
                // reacts. The long bus needs time to unwind between staggered turns.
                int index=Mathf.Min(path.Count-2,closest+(tightTurn?5:underground?4:scenic?3:2));
                var direction=(path[index+1]-path[index]).Normalized();
                var target=path[index]+direction.Cross(Vector3.Up)*side*LaneWidth(path[index]);
                var delta=target-Bus.Position;float error=Mathf.AngleDifference(Bus.Rotation.Y,Mathf.Atan2(-delta.X,-delta.Z));
                Bus.TestSteer=Mathf.Clamp(Mathf.Atan(12*Mathf.Sin(error)/Mathf.Max(6,delta.Length()))/Mathf.DegToRad(32),-1,1);
                float speed=tightTurn?3:Mathf.Abs(error)>.22f?4.5f:underground?11:6;
                Bus.TestBrake=Bus.Speed>speed?1:0;Bus.TestThrottle=Bus.TestBrake==0?1:0;
                minY=Mathf.Min(minY,Bus.Position.Y);
                if(tick%1500==0)GD.Print($"ANTILA_HARBOUR_PROGRESS: {route.Name} {closest}/{path.Count}, speed {Bus.Kmh:0} km/h");
                Check(Bus.Collisions==contacts,$"Harbour contact on {route.Name}: {Bus.Position}, node {closest}, road {path[closest]}, off-centre {best}, pitch {Bus.Rotation.X}");
                Check(best<8 && Bus.Position.Y>-40 && Mathf.Abs(Bus.Position.Y-path[closest].Y)<1.5f,$"Harbour road departure {route.Name}: {Bus.Position}, node {closest}, road {path[closest]}, off-centre {best}, pitch {Bus.Rotation.X}");
                await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
            }
            Check(Bus.Position.DistanceTo(path[^1])<18 && Bus.Collisions==contacts,$"Harbour drive failed {route.Name}: {Bus.Position}, {closest}/{path.Count}, contacts {Bus.Collisions-contacts}");
            if(route.Name==_harbourRoutes[0].Name || route.Name==_harbourRoutes[2].Name)Check(minY<-30,"bus must descend through the harbour tunnel");
            GD.Print($"ANTILA_HARBOUR_DRIVE_OK: {route.Name}; {Bus.DistanceDriven-driven:0} m; minimum y={minY:0.0}; no contacts");
        }
        Check(obstructions.Count==0,$"Harbour obstructions ({obstructions.Count}): "+string.Join("; ",obstructions.Distinct()));
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
