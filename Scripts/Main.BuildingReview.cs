using Godot;
using System;
using System.Linq;

public partial class Main
{
    private void BuildGovernmentBuildings()
    {
        using var data=System.Text.Json.JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/building-layout.json"));
        foreach(var patch in data.RootElement.GetProperty("pavement_patches").EnumerateArray())
        {
            var center=patch.GetProperty("center");
            _pavementPatches.Add((new(center[0].GetSingle(),center[1].GetSingle()),patch.GetProperty("polygon").EnumerateArray()
                .Select(p=>new Vector2(p[0].GetSingle(),p[1].GetSingle())).ToArray()));
        }
        foreach(var b in data.RootElement.GetProperty("buildings").EnumerateArray())
        {
            var polygon=b.GetProperty("rings")[0].EnumerateArray()
                .Select(p=>new Vector2(p[0].GetSingle(),p[1].GetSingle())).ToArray();
            var center=b.GetProperty("center");
            var bounds=new Rect2(polygon[0],Vector2.Zero);
            foreach(var point in polygon)bounds=bounds.Expand(point);
            // Courtyards remain paved; street furniture conservatively avoids the outer ring.
            _lots.Add((new(center[0].GetSingle(),0,center[1].GetSingle()),b.GetProperty("height").GetSingle(),polygon,bounds));
        }
        _city=GD.Load<PackedScene>("res://Assets/Models/kowloon-buildings.glb").Instantiate<Node3D>();
        AddChild(_city);
        foreach(MeshInstance3D mesh in _city.FindChildren("*","MeshInstance3D",true,false))
        {
            foreach(var material in Enumerable.Range(0,mesh.Mesh.GetSurfaceCount()).Select(mesh.Mesh.SurfaceGetMaterial).OfType<StandardMaterial3D>())
                material.AlbedoColor=material.ResourceName switch {
                    "CSDI_facade_1"=>new(.82f,.88f,.88f),"CSDI_facade_2"=>new(1,.91f,.79f),
                    "CSDI_facade_3"=>new(.86f,.91f,.86f),_=>material.AlbedoColor};
            if(mesh.Name.ToString().StartsWith("Collision"))
            {
                mesh.Visible=false;
                var body=new StaticBody3D();mesh.AddChild(body);
                body.AddChild(new CollisionShape3D {Shape=mesh.Mesh.CreateTrimeshShape()});
            }
        }
        GD.Print($"ANTILA_SCENERY: {_lots.Count} CSDI building parts; surveyed footprints and roof heights; generated facade atlas");
    }

    private async System.Threading.Tasks.Task CheckBuildings()
    {
        var meshes=_city.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>().ToArray();
        var visual=meshes.Where(m=>m.Name.ToString().StartsWith("District")).ToArray();
        var collision=meshes.Where(m=>m.Name.ToString().StartsWith("Collision")).ToArray();
        var materials=visual.SelectMany(m=>Enumerable.Range(0,m.Mesh.GetSurfaceCount()).Select(m.Mesh.SurfaceGetMaterial))
            .OfType<StandardMaterial3D>().Where(m=>m.ResourceName.StartsWith("CSDI_facade")).Distinct().ToArray();
        if(visual.Length<50 || visual.Length!=collision.Length || materials.Length!=4 || materials.Any(m=>m.AlbedoTexture==null)
            || collision.Any(m=>m.Visible || m.FindChildren("*","CollisionShape3D",true,false).Count!=1))
            throw new Exception("Government building chunks need textured facades and matching collision meshes");
        if(_lots.Count<1500 || _lots.Count(l=>l.Height>75)<70 || _lots.Max(l=>l.Height)<240)
            throw new Exception("Government building density or height variation lost");
        int facadeEdges=0;
        foreach(var mesh in visual)
            for(int surface=0;surface<mesh.Mesh.GetSurfaceCount();surface++)
            {
                if(!mesh.Mesh.SurfaceGetMaterial(surface).ResourceName.StartsWith("CSDI_facade"))continue;
                using var arrays=mesh.Mesh.SurfaceGetArrays(surface);
                var points=arrays[(int)Mesh.ArrayType.Vertex].AsVector3Array();
                var uv=arrays[(int)Mesh.ArrayType.TexUV].AsVector2Array();
                var indices=arrays[(int)Mesh.ArrayType.Index].AsInt32Array();
                // Sample triangles across every chunk, including partial tiles at narrow corners.
                int step=Math.Max(3,indices.Length/600*3);
                for(int i=0;i+2<indices.Length;i+=step)
                    for(int edge=0;edge<3;edge++)
                    {
                        int a=indices[i+edge],b=indices[i+(edge+1)%3];
                        var textureMetres=(uv[b]-uv[a])*new Vector2(6/.496f,6.4f/.496f);
                        if(Mathf.Abs(points[a].DistanceTo(points[b])-textureMetres.Length())>.04f)
                            throw new Exception($"Facade windows stretch at {mesh.Name}, surface {surface}");
                        facadeEdges++;
                    }
            }
        if(facadeEdges<5000)throw new Exception("Too few facade edges checked");
        using(var mask=((Texture2D)_terrain.GetShaderParameter("surface_mask").AsGodotObject()).GetImage())
            foreach(var patch in _pavementPatches)
            {
                var uv=(patch.Center-Map.Bounds.Position)/Map.Bounds.Size;
                if(mask.GetPixel((int)(uv.X*mask.GetWidth()),(int)(uv.Y*mask.GetHeight())).G<.99f)
                    throw new Exception("Unpaved gap between building pads at " + patch.Center);
            }
        GD.Print($"ANTILA_PAVING_OK: {_pavementPatches.Count} small enclosed pavement gaps filled");
        await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        int checkedRoofs=0;
        foreach(var lot in _lots.Where((_,i)=>i%41==0).Concat(_lots.OrderByDescending(l=>l.Height).Take(10)))
        {
            var ray=PhysicsRayQueryParameters3D.Create(lot.Center+Vector3.Up*(lot.Height+2),lot.Center+Vector3.Up*(lot.Height-1),1);
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
            ray.Dispose();
            if(hit.Count==0 || Mathf.Abs(hit["position"].AsVector3().Y-lot.Height)>.05f)
                throw new Exception($"Surveyed roof collision mismatch at {lot.Center}, height={lot.Height}");
            checkedRoofs++;
        }
        GD.Print($"ANTILA_BUILDINGS_OK: {_lots.Count} derived CSDI parts, {visual.Length} spatial chunks, 4 textured materials, heights {_lots.Min(l=>l.Height):0.0}–{_lots.Max(l=>l.Height):0.0} m, {checkedRoofs} roof collision probes, {facadeEdges} facade edges at consistent window scale");
    }

    private async void ReviewScenery()
    {
        SelfTest=true;SetProcess(false);SetPhysicsProcess(false);Bus.SetPaused(true);
        SetCab(false);Bus.Model.Visible=false;Hud.Visible=false;
        bool footpaths=OS.GetCmdlineUserArgs().Contains("--footpath-review");
        bool roads=OS.GetCmdlineUserArgs().Contains("--road-review");
        string folder=(OS.GetCmdlineUserArgs().Contains("--before")?"before-":"")+(roads?"road-review":footpaths?"footpath-review":"building-review");
        System.IO.Directory.CreateDirectory(ProjectSettings.GlobalizePath("res://evidence/"+folder));
        await ToSignal(GetTree().CreateTimer(1),SceneTreeTimer.SignalName.Timeout);
        float parkStop=Map.Stops[1].Distance;
        var chatham=Map.NearestStreet(new(390,0,-545),"CHATHAM ROAD SOUTH");
        var axis=chatham.Forward.Z<0?chatham.Forward:-chatham.Forward;
        var carriageway=Map.Carriageway(chatham.Point,axis,chatham.Name);
        var driver=carriageway.Center-axis.Cross(Vector3.Up)*carriageway.Width*3/8;
        var views=roads?new[] {
            ("nathan-approach",Map.At(305,-7.3f)+Vector3.Up*3,Map.At(350,-5)),
            ("haiphong-junction",Map.At(325,-8)+Vector3.Up*30,Map.At(350)),
            ("park-bus-bay",Map.At(505,-3)+Vector3.Up*32,Map.At(529,-5)),
            ("canton-lanes",new Vector3(-414,25,-651),new Vector3(-406,0,-706)),
            ("chatham-junction",new Vector3(420,60,-565),new Vector3(397,0,-611)),
            ("chatham-driver",driver-axis*12+Vector3.Up*3,driver+axis*55+Vector3.Up),
            ("chatham-crossing",new Vector3(397,75,-601),new Vector3(397,0,-611)),
            ("side-street",new Vector3(-218,2,-344),new Vector3(-245,.5f,-345))
        }:footpaths?new[] {
            ("haiphong-crossing",Map.At(327,-11.8f)+Vector3.Up*2,Map.At(340,-8)+Vector3.Up*.6f),
            ("side-street",new Vector3(-218,2,-344),new Vector3(-245,.5f,-345)),
            ("bus-stop",Map.At(parkStop+7,-10.9f)+Vector3.Up*1.8f,Map.At(parkStop-2,-11.5f)+Vector3.Up*.3f),
            ("park-entrance",Map.At(555,-10.8f)+Vector3.Up*2.5f,Map.At(560,-25)+Vector3.Up*.3f),
            ("crossing-overview",Map.At(330,-6.5f)+Vector3.Up*2.5f,Map.At(338,-11)+Vector3.Up*.3f),
            ("park-connections",Map.At(560,-30)+Vector3.Up*45,Map.At(560,-40)),
            ("tactile-detail",Map.At(parkStop+7,-11.5f)+Vector3.Up*.9f,Map.At(parkStop+4,-10.7f))
        }:new[] {
            ("nathan-front",Map.At(135,-5)+Vector3.Up*3,Map.At(162,20)+Vector3.Up*12),
            ("haiphong-street",new Vector3(-220,3,-337),new Vector3(-270,12,-345)),
            ("chatham-rear",driver-axis*30+Vector3.Up*3.2f,driver+axis*70+Vector3.Up*18),
            ("granville-corner",new Vector3(397,25,-601),new Vector3(365,15,-643)),
            ("jordan-block",new Vector3(15,230,-850),new Vector3(-140,0,-1030)),
            ("west-block",new Vector3(-250,280,-680),new Vector3(-510,0,-930)),
            ("district-skyline",new Vector3(600,330,110),new Vector3(0,0,-600)) };
        foreach(var (name,position,target) in views)
        {
            Camera.Near=.7f;Camera.Position=position;Camera.LookAt(target);
            await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);
            RenderingServer.ForceDraw(false); // Review captures must also render when the desktop window is occluded.
            using var picture=GetViewport().GetTexture().GetImage();
            picture.SavePng(ProjectSettings.GlobalizePath($"res://evidence/{folder}/{name}.png"));
        }
        GD.Print($"ANTILA_SCENERY_CAPTURE_OK: {views.Length} views in evidence/{folder}");
        QuitGame();
    }
}
