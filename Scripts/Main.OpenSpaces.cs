using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Text.Json;

public partial class Main
{
    private Node3D _recreation = null!;
    private readonly List<(string Site,Vector3 Position,float Radius)> _recreationProps = new();
    private Rect2 _recreationBounds;

    private void BuildMongKokOpenSpaces()
    {
        using var data=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/mong-kok-open-spaces.json"));
        var root=data.RootElement;var bounds=root.GetProperty("bounds");
        _recreationBounds=new(bounds[0].GetSingle(),bounds[1].GetSingle(),bounds[2].GetSingle(),bounds[3].GetSingle());
        Vector2[] Polygon(JsonElement points)=>points.EnumerateArray().Select(p=>new Vector2(p[0].GetSingle(),p[1].GetSingle())).ToArray();
        int surfaceTriangles=root.GetProperty("surfaces").EnumerateArray().Sum(s=>s.GetProperty("triangles").GetArrayLength());
        // BuildEasternOpenSpaces creates the one combined recreation texture after both datasets are ready.
        var play=root.GetProperty("play_areas").EnumerateArray().Single();var pc=play.GetProperty("center");var pf=play.GetProperty("forward");
        _terrain.SetShaderParameter("play_area",new Vector4(pc[0].GetSingle(),pc[1].GetSingle(),play.GetProperty("width").GetSingle()/2,play.GetProperty("length").GetSingle()/2));
        _terrain.SetShaderParameter("play_forward",new Vector2(pf[0].GetSingle(),pf[1].GetSingle()));
        foreach(var triangle in root.GetProperty("paving").EnumerateArray())_harbourPaving.Add(Polygon(triangle));
        _recreation=Asset("mong-kok-recreation",Vector3.Zero);
        foreach(var mesh in _recreation.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>())
        {
            if(!mesh.Name.ToString().StartsWith("Collision"))continue;
            mesh.Visible=false;var body=new StaticBody3D();mesh.AddChild(body);
            body.AddChild(new CollisionShape3D {Shape=mesh.Mesh.CreateTrimeshShape()});
        }
        foreach(var fixture in root.GetProperty("fixtures").EnumerateArray())
        {
            var xy=fixture.GetProperty("position");var at=new Vector3(xy[0].GetSingle(),0,xy[1].GetSingle());
            float radius=fixture.GetProperty("radius").GetSingle(),scale=fixture.GetProperty("scale").GetSingle();
            if(!ClearOfServiceStops(at,radius))continue;
            var asset=Asset(fixture.GetProperty("asset").GetString()!,at,fixture.GetProperty("yaw").GetSingle(),Vector3.One*scale);
            foreach(var mesh in asset.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>())mesh.VisibilityRangeEnd=900;
            _islandDetails.Add((at,radius));_recreationProps.Add((fixture.GetProperty("site").GetString()!,at,radius));
        }
        GD.Print($"ANTILA_OPEN_SPACES: {root.GetProperty("sites").GetArrayLength()} sourced sites; {surfaceTriangles} sports surface triangles; 1 authored play pad; {_recreationProps.Count} authored fixtures");
    }

    private async Task CheckMongKokOpenSpaces()
    {
        using var data=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/mong-kok-open-spaces.json"));
        var root=data.RootElement;
        if(root.GetProperty("sites").GetArrayLength()!=9 || _recreationProps.Count!=root.GetProperty("fixtures").GetArrayLength())
            throw new Exception("Mong Kok recreation sites or furniture lost");
        using var mask=((Texture2D)_terrain.GetShaderParameter("recreation_mask").AsGodotObject()).GetImage();
        int samples=0;
        foreach(var surface in root.GetProperty("surfaces").EnumerateArray())
        {
            var p=surface.GetProperty("sample");var uv=(new Vector2(p[0].GetSingle(),p[1].GetSingle())-_recreationBounds.Position)/_recreationBounds.Size;
            var pixel=mask.GetPixel(Math.Clamp((int)(uv.X*mask.GetWidth()),0,mask.GetWidth()-1),Math.Clamp((int)(uv.Y*mask.GetHeight()),0,mask.GetHeight()-1));
            int channel=surface.GetProperty("kind").GetString() switch {"field"=>0,"court"=>1,_=>2};
            if(pixel[channel]<.9f)throw new Exception("Missing recreation surface at "+p);
            samples++;
        }
        foreach(var prop in _recreationProps)
            if(!LotClear(new(prop.Position.X,prop.Position.Z),prop.Radius))throw new Exception("Recreation furniture intersects a building at "+prop.Position);
        CheckPocketGardens(root);
        var colliders=_recreation.FindChildren("*","CollisionShape3D",true,false);
        if(colliders.Count!=root.GetProperty("sports").GetArrayLength())throw new Exception("Recreation fittings need matching collision");
        // Probe the exported goal frames, not just the authored rectangle dimensions.
        var anchor=root.GetProperty("sports").EnumerateArray().Single(s=>s.GetProperty("source_id").GetString()=="1500002062");
        var ac=anchor.GetProperty("center");var af=anchor.GetProperty("forward");
        var center=new Vector2(ac[0].GetSingle(),ac[1].GetSingle());var forward=new Vector2(af[0].GetSingle(),af[1].GetSingle());var across=new Vector2(forward.Y,-forward.X);
        float length=anchor.GetProperty("length").GetSingle(),width=anchor.GetProperty("width").GetSingle();
        var goals=_recreation.FindChildren("Collision_1500002062*","MeshInstance3D",true,false).Cast<MeshInstance3D>().Single();
        using(var arrays=goals.Mesh.SurfaceGetArrays(0))
            foreach(var vertex in arrays[(int)Mesh.ArrayType.Vertex].AsVector3Array())
            {
                var world=goals.GlobalTransform*vertex;var p=new Vector2(world.X,world.Z)-center;
                if(Mathf.Abs(p.Dot(forward))>=length/2 || Mathf.Abs(p.Dot(across))>=width/2)
                    throw new Exception("Anchor Street goal frame leaves its source outline");
            }
        foreach(int half in new[]{-1,1})foreach(int end in new[]{-1,1})
        {
            var p=center+forward*(half*length/4)+across*(end*(width/2-1.4f));
            using var ray=PhysicsRayQueryParameters3D.Create(new(p.X,3,p.Y),new(p.X,1.8f,p.Y),1);
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
            if(hit.Count==0 || Mathf.Abs(hit["position"].AsVector3().Y-2.1f)>.07f)
                throw new Exception("Anchor Street split pitch goal is on the wrong playing axis");
        }
        GD.Print("ANTILA_ANCHOR_PITCHES_OK: four goal frames across the combined outline; fittings inside source bounds");
        using var layout=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/kowloon-north-layout.json"));
        var original=Bus.Position;bool priorStreamingCheck=_buildingStreamingCheck;_buildingStreamingCheck=true;
        int roofs=0;
        try
        {
            foreach(var building in layout.RootElement.GetProperty("buildings").EnumerateArray().Where(b=>new[]{228041,263953,226983,82955}.Contains(b.GetProperty("id").GetInt32())))
            {
                var c=building.GetProperty("center");float h=building.GetProperty("height").GetSingle();
                var p=new Vector3(c[0].GetSingle(),h,c[1].GetSingle());
                if(PrepareBuildingProbe(p))await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
                using var ray=PhysicsRayQueryParameters3D.Create(p+Vector3.Up*2,p-Vector3.Up,1);
                var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
                if(hit.Count==0 || Mathf.Abs(hit["position"].AsVector3().Y-h)>.05f)throw new Exception("Restored Mong Kok roof collision missing at "+p);
                roofs++;
            }
            if(roofs!=5)throw new Exception("Restored Mong Kok building components missing");
        }
        finally
        {
            try { EnsureBuildingsAt(original);await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame); }
            finally { _buildingStreamingCheck=priorStreamingCheck; }
        }
        GD.Print($"ANTILA_RESTORED_ROOFS_OK: {roofs} probes across the four reported building IDs");
        GD.Print($"ANTILA_OPEN_SPACES_OK: {samples} sourced surfaces, 1 authored play pad, {_recreationProps.Count} clear fixtures, {colliders.Count} court collision meshes");
    }

    private void CheckPocketGardens(JsonElement root)
    {
        var expected=new[]{"1503005143","1503005266","1503005193","1503005468","1810041992"};
        var gardens=root.GetProperty("gardens").EnumerateArray().ToArray();
        if(!gardens.Select(g=>g.GetProperty("site").GetString()).Order().SequenceEqual(expected.Order()))
            throw new Exception("Five mapped pocket gardens required");
        if(_recreationProps.Count(p=>!expected.Contains(p.Site))!=273)
            throw new Exception("Existing recreation furniture changed");
        Vector2[] Points(JsonElement ring)=>ring.EnumerateArray().Select(p=>new Vector2(p[0].GetSingle(),p[1].GetSingle())).ToArray();
        bool Inside(Vector2 p,JsonElement polygon)=>Geometry2D.IsPointInPolygon(p,Points(polygon[0])) &&
            !polygon.EnumerateArray().Skip(1).Any(h=>Geometry2D.IsPointInPolygon(p,Points(h)));
        float EdgeDistance(Vector2 p,JsonElement polygon)=>polygon.EnumerateArray().SelectMany(r=>
        {
            var points=Points(r);
            return points.Select((a,i)=>p.DistanceTo(Geometry2D.GetClosestPointToSegment(p,a,points[(i+1)%points.Length])));
        }).Min();
        using var paving=((Texture2D)_terrain.GetShaderParameter("harbour_mask").AsGodotObject()).GetImage();
        int samples=0;
        foreach(var garden in gardens)
        {
            string id=garden.GetProperty("site").GetString()!;
            var fixtures=_recreationProps.Where(p=>p.Site==id).ToArray();
            if(fixtures.Length<3)throw new Exception("Pocket garden furniture missing: "+id);
            foreach(var prop in fixtures)
            {
                var p=new Vector2(prop.Position.X,prop.Position.Z);
                if(!garden.GetProperty("rings").EnumerateArray().Any(poly=>Inside(p,poly)) ||
                   !ClearOfServiceStops(prop.Position,prop.Radius))
                    throw new Exception("Pocket garden fixture leaves its site or obstructs a stop: "+id);
                if(garden.GetProperty("access").EnumerateArray().Any(poly=>Inside(p,poly) || EdgeDistance(p,poly)<prop.Radius-.01f))
                    throw new Exception("Pocket garden entrance obstructed: "+id);
                if(HarbourRoads.Any(r=>Enumerable.Range(1,r.Points.Count-1).Any(j=>r.Points[j].Y>-6 &&
                    p.DistanceTo(Geometry2D.GetClosestPointToSegment(p,new(r.Points[j-1].X,r.Points[j-1].Z),new(r.Points[j].X,r.Points[j].Z)))<Mathf.Max(12,r.Width)/2+prop.Radius)))
                    throw new Exception("Pocket garden furniture enters a road: "+id);
            }
            foreach(var sample in garden.GetProperty("samples").EnumerateArray())
            {
                var uv=(new Vector2(sample[0].GetSingle(),sample[1].GetSingle())-HarbourBounds.Position)/HarbourBounds.Size;
                if(paving.GetPixel(Math.Clamp((int)(uv.X*paving.GetWidth()),0,paving.GetWidth()-1),Math.Clamp((int)(uv.Y*paving.GetHeight()),0,paving.GetHeight()-1)).G<.9f)
                    throw new Exception("Pocket garden paving missing: "+id);
                samples++;
            }
        }
        if(root.GetProperty("surfaces").GetArrayLength()!=17 || root.GetProperty("play_areas").GetArrayLength()!=1 ||
           _recreation.FindChildren("Play_1503005266*","MeshInstance3D",true,false).Count!=1)
            throw new Exception("Sourced sports or authored playground markings missing");
        var play=root.GetProperty("play_areas")[0];var pc=play.GetProperty("center");var pf=play.GetProperty("forward");
        if(!_terrain.GetShaderParameter("play_area").AsVector4().IsEqualApprox(new Vector4(pc[0].GetSingle(),pc[1].GetSingle(),play.GetProperty("width").GetSingle()/2,play.GetProperty("length").GetSingle()/2)) ||
           !_terrain.GetShaderParameter("play_forward").AsVector2().IsEqualApprox(new Vector2(pf[0].GetSingle(),pf[1].GetSingle())))
            throw new Exception("Rendered play-pad bounds differ from the authored layout");
        GD.Print($"ANTILA_POCKET_GARDENS_OK: five sourced sites; {samples} paving probes; furniture clear of entrances, roads, buildings and stops");
    }

    private async System.Threading.Tasks.Task CheckPocketGardenRendering()
    {
        if(DisplayServer.GetName()=="headless")
        {GD.Print("ANTILA_PLAY_RENDER_SKIPPED: native renderer required for combined terrain edge probes");return;}
        using var data=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/mong-kok-open-spaces.json"));
        var play=data.RootElement.GetProperty("play_areas").EnumerateArray().Single();
        var c=play.GetProperty("center");var f=play.GetProperty("forward");
        var center=new Vector2(c[0].GetSingle(),c[1].GetSingle());var forward=new Vector2(f[0].GetSingle(),f[1].GetSingle());
        var right=new Vector2(forward.Y,-forward.X);float width=play.GetProperty("width").GetSingle(),length=play.GetProperty("length").GetSingle();
        // Render the real terrain shader and masks in an isolated viewport. Flat test
        // textures distinguish paving from the play surface without scene shadows/paint.
        var viewport=new SubViewport {Size=new(1024,1024),World3D=new World3D(),RenderTargetUpdateMode=SubViewport.UpdateMode.Always};
        AddChild(viewport);
        try
        {
            var material=(ShaderMaterial)_terrain.Duplicate();
            ImageTexture Solid(Color color)
            {using var image=Image.CreateEmpty(2,2,false,Image.Format.Rgb8);image.Fill(color);return ImageTexture.CreateFromImage(image);}
            material.SetShaderParameter("paving",Solid(Colors.Green));material.SetShaderParameter("stone",Solid(Colors.Green));
            material.SetShaderParameter("asphalt",Solid(Colors.Black));material.SetShaderParameter("grass",Solid(Colors.Blue));
            viewport.AddChild(new WorldEnvironment {Environment=new Godot.Environment {
                BackgroundMode=Godot.Environment.BGMode.Color,BackgroundColor=Colors.Black,
                AmbientLightSource=Godot.Environment.AmbientSource.Color,AmbientLightColor=Colors.White,AmbientLightEnergy=1,
                ReflectedLightSource=Godot.Environment.ReflectionSource.Disabled}});
            viewport.AddChild(new MeshInstance3D {Mesh=new PlaneMesh {Size=new(32,32)},Position=new(center.X,0,center.Y),MaterialOverride=material});
            var camera=new Camera3D {Projection=Camera3D.ProjectionType.Orthogonal,Size=24,Position=new(center.X,40,center.Y),Current=true};
            viewport.AddChild(camera);camera.LookAt(new(center.X,0,center.Y),Vector3.Forward);
            async System.Threading.Tasks.Task Draw()
            {for(int i=0;i<3;i++)await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);RenderingServer.ForceDraw(false);}
            Color Sample(Image image,Vector2 p)
            {var pixel=camera.UnprojectPosition(new(p.X,0,p.Y));return image.GetPixel((int)pixel.X,(int)pixel.Y);}
            bool IsPlay(Color color)=>color.R>.1f && color.R>color.G*1.3f && color.R>color.B*1.3f;
            await Draw();
            using(var image=viewport.GetTexture().GetImage())
            {
                string folder=ProjectSettings.GlobalizePath("res://evidence/open-space-render-check");DirAccess.MakeDirRecursiveAbsolute(folder);
                string prefix=OS.GetCmdlineUserArgs().Contains("--before")?"before-":"";
                if(image.SavePng($"{folder}/{prefix}play-boundary.png")!=Error.Ok)throw new Exception("Play boundary capture failed");
                int probes=0;
                foreach(int axis in new[]{0,1})foreach(int sign in new[]{-1,1})for(int along=-4;along<=4;along++)
                {
                    var normal=(axis==0?right:forward)*sign;var tangent=axis==0?forward:right;
                    float half=(axis==0?width:length)/2,span=(axis==0?length:width)/2;
                    var edge=center+normal*half+tangent*(along*.2f*span);
                    if(!IsPlay(Sample(image,edge-normal*.25f)))throw new Exception("Paving erases the play-pad edge at "+(edge-normal*.25f));
                    var outside=Sample(image,edge+normal*.25f);
                    if(outside.G<.1f || outside.G<outside.R*1.3f)throw new Exception("Play surface spills onto its paving at "+(edge+normal*.25f));
                    probes+=2;
                }
                if(!IsPlay(Sample(image,center)))throw new Exception("Play-pad centre missing in final terrain");
                GD.Print($"ANTILA_PLAY_BOUNDARY_OK: {probes} rendered inside/outside probes across all four edges; centre retained");
            }
            // A road covering this same point must still win after play/paving blending.
            material.SetShaderParameter("harbour_mask",Solid(new Color(1,1,0)));await Draw();
            using(var image=viewport.GetTexture().GetImage())
            {
                var road=Sample(image,center);
                if(Mathf.Max(road.R,Mathf.Max(road.G,road.B))>.05f)throw new Exception("Play surface overrides asphalt");
            }
            GD.Print("ANTILA_PLAY_RENDER_OK: final terrain boundary and asphalt priority");
        }
        finally{viewport.QueueFree();}
    }
}
