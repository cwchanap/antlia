using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

public partial class Main
{
    private readonly List<(float Distance,Vector3 A,Vector3 B)> _parkEntrances = new();
    private readonly List<(string Model,Transform3D Pose,Vector2 Half)> _footpathDetails = new();
    private readonly List<Transform3D> _crossingLandings = new();
    private readonly List<(Vector3 Center,float Radius)> _footpathObstacles = new();

    private IEnumerable<(Vector3 A,Vector3 B)> ParkPaths() => _parkPath.Zip(_parkPath.Skip(1),(a,b)=>(a,b))
        .Concat(_parkEntrances.Select(e=>(e.A,e.B)));

    private void PrepareParkEntrances()
    {
        foreach(float distance in new[]{560f,735f})
        {
            var entrance=Map.At(distance,-12.8f);
            var join=_parkPath.Zip(_parkPath.Skip(1),(a,b)=>Geometry3D.GetClosestPointToSegment(entrance,a,b))
                .MinBy(p=>p.DistanceSquaredTo(entrance));
            _parkEntrances.Add((distance,entrance,join));
        }
    }

    private bool NearParkEntrance(Vector3 p,float radius) => _parkEntrances.Any(e=>
        p.DistanceTo(Geometry3D.GetClosestPointToSegment(p,e.A,e.B))<radius);

    private void ParkWall(float start,float end)
    {
        if(end-start<.1f)return;
        var wall=Box(this,Map.At((start+end)/2,-15)+Vector3.Up*.65f,new(1.2f,1.3f,end-start),"7c7360",true);
        wall.Rotation=new(0,Map.Heading((start+end)/2),0);
    }

    private static Vector2[] FootpathPolygon(Transform3D pose,Vector2 half) =>
        new[]{new Vector3(-half.X,0,-half.Y),new(half.X,0,-half.Y),new(half.X,0,half.Y),new(-half.X,0,half.Y)}
            .Select(p=>pose*p).Select(p=>new Vector2(p.X,p.Z)).ToArray();

    private bool FootpathClear(Transform3D pose,Vector2 half)
    {
        for(int x=-1;x<=1;x++)for(int z=-1;z<=1;z++)
        {
            var p=pose*new Vector3(x*half.X,0,z*half.Y);
            if(!Map.Bounds.HasPoint(new(p.X,p.Z)) || !Map.ClearOfRoads(p,.08f))return false;
        }
        var polygon=FootpathPolygon(pose,half);
        var poleClearance=FootpathPolygon(pose,half+Vector2.One*.35f);
        var bounds=new Rect2(polygon[0],Vector2.Zero);
        foreach(var p in polygon)bounds=bounds.Expand(p);
        var inverse=pose.AffineInverse();
        if(_footpathObstacles.Any(o=>{
            var local=inverse*o.Center;var p=new Vector2(local.X,local.Z);
            return p.DistanceTo(p.Clamp(-half,half))<o.Radius+.1f;
        }))return false;
        return !_lots.Any(l=>bounds.Intersects(l.Bounds) && Geometry2D.IntersectPolygons(polygon,l.Polygon).Count>0)
            && !_signalPoles.Any(p=>Geometry2D.IsPointInPolygon(new(p.X,p.Z),poleClearance));
    }

    private bool AddFootpathDetail(string model,Vector3 p,float heading,Vector2 half)
    {
        var pose=new Transform3D(new Basis(Vector3.Up,heading),p);
        if(!FootpathClear(pose,half))return false;
        var polygon=FootpathPolygon(pose,half);
        if(_footpathDetails.Any(d=>d.Pose.Origin.DistanceSquaredTo(p)<16 &&
            Geometry2D.IntersectPolygons(polygon,FootpathPolygon(d.Pose,d.Half)).Count>0))return false;
        _footpathDetails.Add((model,pose,half));return true;
    }

    private void BuildFootpaths()
    {
        foreach(var signal in _signals)
        {
            float heading=Mathf.Atan2(-signal.Forward.X,-signal.Forward.Z);
            var right=signal.Forward.Cross(Vector3.Up);
            foreach(int side in new[]{-1,1})
            {
                var p=signal.Stop+signal.Forward*4+right*side*(signal.Width/2+.85f);
                var pose=new Transform3D(new Basis(Vector3.Up,heading),p);
                if(!FootpathClear(pose,new(.65f,1.55f)))continue;
                _crossingLandings.Add(pose);
                for(int tile=-2;tile<=2;tile++)
                    AddFootpathDetail("tactile-paver",p+signal.Forward*tile*.6f,heading,new(.299f,.299f));
            }
        }
        // These two existing mid-block crossings also need visible pavement landings.
        foreach(float distance in new[]{110f,740f})foreach(int side in new[]{-1,1})
        {
            var p=Map.At(distance,side*10.85f);
            var pose=new Transform3D(new Basis(Vector3.Up,Map.Heading(distance)),p);
            if(!FootpathClear(pose,new(.65f,1.8f)))continue;
            _crossingLandings.Add(pose);
            for(int tile=-2;tile<=2;tile++)
                AddFootpathDetail("tactile-paver",p+Map.Forward(distance)*tile*.6f,Map.Heading(distance),new(.299f,.299f));
        }
        foreach(var stop in Map.Stops)foreach(float door in new[]{.45f,4.2f})foreach(float tile in new[]{-.3f,.3f})
            AddFootpathDetail("tactile-paver",Map.At(stop.Distance+door+tile,-10.7f),Map.Heading(stop.Distance),new(.299f,.299f));

        foreach(var landing in _crossingLandings)
            foreach(float offset in new[]{-5.6f,-3.4f,3.4f,5.6f})
            {
                var p=landing*new Vector3(0,0,offset);
                if(_crossingLandings.Any(other=>Mathf.Abs((other.AffineInverse()*p).X)<1 &&
                    Mathf.Abs((other.AffineInverse()*p).Z)<2.8f) || NearParkEntrance(p,4))continue;
                var projected=Map.Project(p);
                if(Mathf.Abs(projected.Lateral)<15 && Map.Stops.Any(s=>Mathf.Abs(s.Distance-projected.Distance)<18))continue;
                AddFootpathDetail("pedestrian-railing",p,landing.Basis.GetEuler().Y,new(.09f,1.06f));
            }
        var roadSamples=Map.StreetSamples(42).Select(s=>(s.Name,s.Point,s.Forward))
            .Concat(Enumerable.Range(1,27).Select(i=>("NATHAN ROAD",Map.At(i*42),Map.Forward(i*42))));
        foreach(var (name,p,f) in roadSamples)foreach(int side in new[]{-1,1})
        {
            var at=p+f.Cross(Vector3.Up)*side*(RoadMap.Width(name)/2+.45f);
            if(_crossingLandings.Any(l=>l.Origin.DistanceTo(at)<2.5f))continue;
            AddFootpathDetail("drain-grate",at,Mathf.Atan2(-f.X,-f.Z),new(.24f,.34f));
        }
        // ponytail: three shared meshes suit this decoration count; spatial batches if the map grows substantially.
        foreach(var group in _footpathDetails.GroupBy(d=>d.Model))
        {
            var template=GD.Load<PackedScene>($"res://Assets/Models/{group.Key}.glb").Instantiate<Node3D>();
            var mesh=template as MeshInstance3D ?? template.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>().Single();
            var multi=new MultiMesh {TransformFormat=MultiMesh.TransformFormatEnum.Transform3D,Mesh=mesh.Mesh,InstanceCount=group.Count()};
            int index=0;foreach(var detail in group)multi.SetInstanceTransform(index++,detail.Pose);
            AddChild(new MultiMeshInstance3D {Multimesh=multi});template.Free();
        }
        GD.Print($"ANTILA_FOOTPATHS: {_crossingLandings.Count} crossing landings; "+
            string.Join(", ",_footpathDetails.GroupBy(d=>d.Model).Select(g=>$"{g.Count()} {g.Key}"))+"; two park entrances");
    }

    private async Task CheckFootpaths()
    {
        void Check(bool ok,string message) {if(!ok)throw new Exception(message);}
        Check(_crossingLandings.Count>=30,"crossing landings must cover the expanded map");
        Check(_footpathDetails.Count(d=>d.Model=="pedestrian-railing")>=30,"pedestrian railings must be present");
        Check(_footpathDetails.All(d=>FootpathClear(d.Pose,d.Half)),"footpath furniture must clear roads, building lots and signal poles");
        foreach(var detail in _footpathDetails.Where(d=>d.Model=="pedestrian-railing"))
            Check(!_crossingLandings.Any(l=>Geometry2D.IntersectPolygons(FootpathPolygon(l,new(.65f,1.55f)),
                FootpathPolygon(detail.Pose,detail.Half)).Count>0),"railings must not close a crossing landing");
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        using var shape=new BoxShape3D {Size=new(2.4f,1.8f,2.4f)};
        using var query=new PhysicsShapeQueryParameters3D {Shape=shape,CollisionMask=1};
        using var mask=((Texture2D)_terrain.GetShaderParameter("surface_mask").AsGodotObject()).GetImage();
        foreach(var detail in _footpathDetails)
        {
            var p=detail.Pose.Origin;var uv=(new Vector2(p.X,p.Z)-Map.Bounds.Position)/Map.Bounds.Size;
            var surface=mask.GetPixel((int)(uv.X*mask.GetWidth()),(int)(uv.Y*mask.GetHeight()));
            Check(surface.G>.99f && surface.R<.01f,"pedestrian detail must sit on the pavement");
        }
        foreach(var entrance in _parkEntrances)
            for(float t=0;t<=1;t+=.05f)
            {
                var p=entrance.A.Lerp(entrance.B,t);
                Check(_footpathObstacles.All(o=>o.Center.DistanceTo(p)>o.Radius+1.2f),"park entrance must leave room beside tree trunks and furniture");
                query.Transform=new(Basis.Identity,p+Vector3.Up);
                Check(GetWorld3D().DirectSpaceState.IntersectShape(query,1).Count==0,"park entrance must pass through an open wall gap");
                var uv=(new Vector2(p.X,p.Z)-Map.Bounds.Position)/Map.Bounds.Size;
                var surface=mask.GetPixel((int)(uv.X*mask.GetWidth()),(int)(uv.Y*mask.GetHeight()));
                Check(surface.G>.99f && surface.R<.01f,"park entry path must be paved and clear of the road");
            }
        GD.Print("ANTILA_FOOTPATHS_OK: pavement furniture clearance; open crossing landings; two connected park paths and wall gaps");
    }
}
