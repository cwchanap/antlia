using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

public partial class Main
{
    private const float BuildingLoadRadius=1000, BuildingKeepRadius=1500;
    private sealed class BuildingChunk
    {
        public string Id="",Path="",Source="";
        public Rect2 Bounds;
        public MeshInstance3D Proxy=null!;
        public Node3D? Instance;
        public bool Requested;
        public readonly List<Resource> Resources=new();
    }
    private readonly List<BuildingChunk> _buildingChunks=new();
    private readonly Dictionary<string,Texture2D> _buildingTextures=new();
    private Vector3 _buildingFocus=new(float.PositiveInfinity,0,0);
    private bool _buildingStreamingCheck;

    private static float BuildingDistanceSquared(Rect2 bounds,Vector3 position)
    {
        float x=Mathf.Max(bounds.Position.X-position.X,Mathf.Max(0,position.X-bounds.End.X));
        float z=Mathf.Max(bounds.Position.Y-position.Z,Mathf.Max(0,position.Z-bounds.End.Y));
        return x*x+z*z;
    }

    private void BuildBuildingStreaming()
    {
        using var manifest=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/building-chunks.json"));
        if(manifest.RootElement.GetProperty("version").GetInt32()!=1)throw new Exception("Unsupported building chunk manifest");
        var proxies=new Dictionary<string,Dictionary<string,MeshInstance3D>>();
        foreach(var source in manifest.RootElement.GetProperty("sources").EnumerateArray())
        {
            using var scene=GD.Load<PackedScene>(source.GetProperty("proxy").GetString()!);
            var model=scene.Instantiate<Node3D>();_city.AddChild(model);
            string name=System.IO.Path.GetFileNameWithoutExtension(source.GetProperty("path").GetString()!);
            proxies[name]=model.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>().ToDictionary(m=>m.Name.ToString());
        }
        foreach(var row in manifest.RootElement.GetProperty("chunks").EnumerateArray())
        {
            var min=row.GetProperty("min");var max=row.GetProperty("max");
            var chunk=new BuildingChunk {Id=row.GetProperty("id").GetString()!,Path=row.GetProperty("path").GetString()!,Source=row.GetProperty("source").GetString()!,
                Bounds=new Rect2(new Vector2(min[0].GetSingle(),min[2].GetSingle()),new Vector2(max[0].GetSingle()-min[0].GetSingle(),max[2].GetSingle()-min[2].GetSingle()))};
            // Godot's glTF importer replaces Blender's .001 suffix separator with an underscore.
            chunk.Proxy=proxies[chunk.Source][row.GetProperty("proxy_name").GetString()!.Replace('.','_')];
            _buildingChunks.Add(chunk);
        }
        if(_buildingChunks.Count!=3135 || _buildingChunks.Select(c=>c.Id).Distinct().Count()!=3135 || proxies.Sum(p=>p.Value.Count)!=3135 ||
            _buildingChunks.Select(c=>c.Proxy.GetInstanceId()).Distinct().Count()!=3135)
            throw new Exception("Building chunk/proxy inventory changed; regenerate and validate the manifest");
    }

    private void InstantiateBuilding(BuildingChunk chunk,PackedScene scene)
    {
        var model=scene.Instantiate<Node3D>();
        chunk.Instance=model;_city.AddChild(model);
        foreach(var mesh in model.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>())
        {
            var geometry=mesh.Mesh;
            if(mesh.Name.ToString().StartsWith("Collision"))
            {
                mesh.Visible=false;
                var shape=geometry.CreateTrimeshShape();chunk.Resources.Add(shape);
                var body=new StaticBody3D();mesh.AddChild(body);body.AddChild(new CollisionShape3D {Shape=shape});
                mesh.Mesh=null!;geometry.Dispose();
            }
            else
            {
                chunk.Resources.Add(geometry);
                for(int i=0;i<geometry.GetSurfaceCount();i++)
                    if(geometry.SurfaceGetMaterial(i) is StandardMaterial3D material)
                    {
                        chunk.Resources.Add(material);
                        material.AlbedoColor=material.ResourceName switch {
                            "CSDI_facade_1"=>new(.82f,.88f,.88f),"CSDI_facade_2"=>new(1,.91f,.79f),
                            "CSDI_facade_3"=>new(.86f,.91f,.86f),_=>material.AlbedoColor};
                        string family=material.ResourceName.StartsWith("CSDI_facade_")?"facade":material.ResourceName.StartsWith("CSDI_shopfront_variety")?"variety":material.ResourceName.StartsWith("CSDI_shopfront")?"shopfront":"";
                        if(family!="" && material.AlbedoTexture is Texture2D texture)
                        {
                            if(_buildingTextures.TryGetValue(family,out var shared))
                            {
                                material.AlbedoTexture=shared;
                                if(texture.GetInstanceId()!=shared.GetInstanceId())texture.Dispose();
                            }
                            else _buildingTextures[family]=texture;
                        }
                    }
            }
        }
        chunk.Proxy.Visible=false;
    }

    private void ReleaseBuilding(BuildingChunk chunk)
    {
        if(chunk.Instance==null)return;
        chunk.Instance.Free();chunk.Instance=null;
        foreach(var resource in chunk.Resources.DistinctBy(r=>r.GetInstanceId()).ToArray())resource.Dispose();
        chunk.Resources.Clear();chunk.Proxy.Visible=true;
    }

    private void FinishBuildingRequest(BuildingChunk chunk,Vector3 position,bool wait)
    {
        if(!chunk.Requested)return;
        var status=ResourceLoader.LoadThreadedGetStatus(chunk.Path);
        if(!wait && status==ResourceLoader.ThreadLoadStatus.InProgress)return;
        if(status==ResourceLoader.ThreadLoadStatus.InvalidResource)
        {
            chunk.Requested=false;
            throw new Exception("Could not load building chunk "+chunk.Id);
        }
        using var resource=ResourceLoader.LoadThreadedGet(chunk.Path);
        chunk.Requested=false;
        if(resource is not PackedScene scene)throw new Exception("Could not load building chunk "+chunk.Id);
        if(chunk.Instance==null && BuildingDistanceSquared(chunk.Bounds,position)<=BuildingKeepRadius*BuildingKeepRadius)
            InstantiateBuilding(chunk,scene);
    }

    // Teleports prepare real collision before ResetAt moves the bus; obsolete requests never instantiate at the old destination.
    private void EnsureBuildingsAt(Vector3 position)
    {
        foreach(var chunk in _buildingChunks)
            if(BuildingDistanceSquared(chunk.Bounds,position)>BuildingKeepRadius*BuildingKeepRadius)ReleaseBuilding(chunk);
        foreach(var chunk in _buildingChunks.Where(c=>c.Requested).ToArray())FinishBuildingRequest(chunk,position,true);
        foreach(var chunk in _buildingChunks)
            if(chunk.Instance==null && BuildingDistanceSquared(chunk.Bounds,position)<=BuildingLoadRadius*BuildingLoadRadius)
            {
                using var scene=GD.Load<PackedScene>(chunk.Path);
                InstantiateBuilding(chunk,scene);
            }
        _buildingFocus=position;
    }

    private bool PrepareBuildingProbe(Vector3 position)
    {
        if(!_buildingChunks.Any(c=>c.Instance==null && BuildingDistanceSquared(c.Bounds,position)<=32*32))return false;
        EnsureBuildingsAt(position);return true;
    }

    private void UpdateBuildingStreaming()
    {
        if(_buildingStreamingCheck)return;
        bool headless=DisplayServer.GetName()=="headless";
        var position=Bus.GlobalPosition;
        int completed=0;
        foreach(var chunk in _buildingChunks.Where(c=>c.Requested).ToArray())
        {
            if(ResourceLoader.LoadThreadedGetStatus(chunk.Path)==ResourceLoader.ThreadLoadStatus.InProgress)continue;
            FinishBuildingRequest(chunk,position,false);
            if(++completed==2)break;
        }
        // A failed/slow background load must never let physics outrun the collision window.
        if(_buildingChunks.Any(c=>c.Instance==null && BuildingDistanceSquared(c.Bounds,position)<250*250))EnsureBuildingsAt(position);
        bool headlessWork=headless && _buildingChunks.Any(c=>c.Instance==null && BuildingDistanceSquared(c.Bounds,position)<=BuildingLoadRadius*BuildingLoadRadius);
        if(_buildingFocus.DistanceSquaredTo(position)<50*50 && completed==0 && !headlessWork)return;
        _buildingFocus=position;
        foreach(var chunk in _buildingChunks)
            if(BuildingDistanceSquared(chunk.Bounds,position)>BuildingKeepRadius*BuildingKeepRadius)ReleaseBuilding(chunk);
        int pending=_buildingChunks.Count(c=>c.Requested);
        var nearby=_buildingChunks.Where(c=>c.Instance==null && !c.Requested && BuildingDistanceSquared(c.Bounds,position)<=BuildingLoadRadius*BuildingLoadRadius)
            .OrderBy(c=>BuildingDistanceSquared(c.Bounds,position));
        if(headless)
        {
            // shortcut: Godot 4.6.2 dummy mesh RIDs race threaded loads; recheck after an engine upgrade.
            foreach(var chunk in nearby.Take(2))
            {
                using var scene=GD.Load<PackedScene>(chunk.Path);
                InstantiateBuilding(chunk,scene);
            }
            return;
        }
        foreach(var chunk in nearby)
        {
            if(pending>=8)break;
            var error=ResourceLoader.LoadThreadedRequest(chunk.Path,"PackedScene");
            if(error!=Error.Ok)throw new Exception($"Could not request building chunk {chunk.Id}: {error}");
            chunk.Requested=true;pending++;
        }
    }

    public override void _ExitTree()
    {
        // Drain native loader jobs before freeing a scene; they otherwise retain resources across R reloads.
        foreach(var chunk in _buildingChunks)
        {
            if(chunk.Requested)
            {
                if(ResourceLoader.LoadThreadedGetStatus(chunk.Path)!=ResourceLoader.ThreadLoadStatus.InvalidResource)
                    ResourceLoader.LoadThreadedGet(chunk.Path)?.Dispose();
                chunk.Requested=false;
            }
            ReleaseBuilding(chunk);
        }
        _buildingChunks.Clear();
        foreach(var texture in _buildingTextures.Values)texture.Dispose();
        _buildingTextures.Clear();
    }
}
