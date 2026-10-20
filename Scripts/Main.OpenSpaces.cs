using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

public partial class Main
{
    private Node3D _recreation = null!;
    private readonly List<(Vector3 Position,float Radius)> _recreationProps = new();
    private Rect2 _recreationBounds;

    private void BuildMongKokOpenSpaces()
    {
        using var data=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/mong-kok-open-spaces.json"));
        var root=data.RootElement;var bounds=root.GetProperty("bounds");
        _recreationBounds=new(bounds[0].GetSingle(),bounds[1].GetSingle(),bounds[2].GetSingle(),bounds[3].GetSingle());
        Vector2[] Polygon(JsonElement points)=>points.EnumerateArray().Select(p=>new Vector2(p[0].GetSingle(),p[1].GetSingle())).ToArray();
        var surfaces=root.GetProperty("surfaces").EnumerateArray().SelectMany(s=>s.GetProperty("triangles").EnumerateArray()
            .Select(t=>(Polygon(t),s.GetProperty("kind").GetString() switch {"field"=>0,"court"=>1,_=>2}))).ToArray();
        using(var mask=Map.CreateSurfaceMask(Array.Empty<Vector2>(),Array.Empty<(Vector3,Vector3)>(),Array.Empty<Vector2[]>(),
            _recreationBounds,Array.Empty<(Vector2,Vector2,float)>(),2,surfaces))
            _terrain.SetShaderParameter("recreation_mask",ImageTexture.CreateFromImage(mask));
        _terrain.SetShaderParameter("recreation_origin",_recreationBounds.Position);
        _terrain.SetShaderParameter("recreation_size",_recreationBounds.Size);
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
            _islandDetails.Add((at,radius));_recreationProps.Add((at,radius));
        }
        GD.Print($"ANTILA_OPEN_SPACES: 4 sourced sites; {surfaces.Length} surface triangles; {_recreationProps.Count} authored trees and benches");
    }

    private void CheckMongKokOpenSpaces()
    {
        using var data=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/mong-kok-open-spaces.json"));
        var root=data.RootElement;
        if(root.GetProperty("sites").GetArrayLength()!=4 || _recreationProps.Count!=274)
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
        int roofs=0;
        foreach(var building in layout.RootElement.GetProperty("buildings").EnumerateArray().Where(b=>new[]{228041,263953,226983,82955}.Contains(b.GetProperty("id").GetInt32())))
        {
            var c=building.GetProperty("center");float h=building.GetProperty("height").GetSingle();
            var p=new Vector3(c[0].GetSingle(),h,c[1].GetSingle());
            using var ray=PhysicsRayQueryParameters3D.Create(p+Vector3.Up*2,p-Vector3.Up,1);
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
            if(hit.Count==0 || Mathf.Abs(hit["position"].AsVector3().Y-h)>.05f)throw new Exception("Restored Mong Kok roof collision missing at "+p);
            roofs++;
        }
        if(roofs!=5)throw new Exception("Restored Mong Kok building components missing");
        GD.Print($"ANTILA_RESTORED_ROOFS_OK: {roofs} probes across the four reported building IDs");
        GD.Print($"ANTILA_OPEN_SPACES_OK: {samples} sourced surfaces, {_recreationProps.Count} clear fixtures, {colliders.Count} court collision meshes");
    }
}
