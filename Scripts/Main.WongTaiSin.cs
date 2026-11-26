using Godot;
using System;
using System.Linq;
using System.Threading.Tasks;

public partial class Main
{
    private const int ChoiHungDriveIndex=16;
    private const string ChoiHungDriveName="Choi Hung → Hammer Hill";
    private const string WongTaiSinReliefPath="res://Data/wong-tai-sin-relief.json";
    private bool _fullWongTaiSinDistrict;
    public bool HasChoiHungDrive=>HasHarbourDrive(ChoiHungDriveIndex);
    public Vector3 ChoiHungDriveStart=>_harbourRoutes[ChoiHungDriveIndex].Points[0];
    private static bool HasWongTaiSinRelief=>FileAccess.FileExists(WongTaiSinReliefPath);

    private static void RequireWongTaiSinRelief()
    {
        if(!HasWongTaiSinRelief)
            throw new Exception($"Full Wong Tai Sin district requires {WongTaiSinReliefPath}. Run Tools/import_wong_tai_sin_relief.py before exporting the harbour model.");
    }

    private int CheckChoiHungDistrictDrive()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(HasChoiHungDrive,"The district needs a Choi Hung to Hammer Hill drive");
        var start=ChoiHungDriveStart;
        int selected=RouteIndex,pending=_pendingRoute;
        using var shortcut=new InputEventKey {Keycode=Key.I,PhysicalKeycode=Key.X,Pressed=true};
        ShowRouteSelect();_UnhandledInput(shortcut);
        Check(!Menu && HarbourDrive && Bus.Position.DistanceTo(start)<3 && !Hud.MapShowsService,
            "Physical X must start Choi Hung from route select");
        using var tab=new InputEventKey {Keycode=Key.Tab,PhysicalKeycode=Key.Tab,Pressed=true};
        _UnhandledInput(tab);
        Check(Menu && RouteIndex==selected && Hud.MapShowsService,"Tab from Choi Hung must return to the selected service");
        BeginRoute(selected);_UnhandledInput(shortcut);
        Check(HarbourDrive && Bus.Position.DistanceTo(start)<3 && _frontBlind!.Text=="NOT IN SERVICE",
            "Physical X must start Choi Hung while stopped");
        BeginRoute(selected);_pendingRoute=pending;
        int support=CheckSourceDriveLanes(ChoiHungDriveIndex);
        GD.Print($"ANTILA_CHOI_HUNG_READY_OK: physical X from menu and stopped driving; {_harbourRouteSources[ChoiHungDriveIndex].Length} signed sections; {support} lane-support probes");
        return ChoiHungDriveIndex;
    }

    private async Task CheckWongTaiSinDistrictScenery()
    {
        RequireWongTaiSinRelief();
        var space=GetWorld3D().DirectSpaceState;
        if(_harbourRoadIndex.ContainsKey("TD_103871") && _harbourRoadIndex.ContainsKey("TD_103672"))
        {
            using var mask=((Texture2D)_terrain.GetShaderParameter("harbour_mask").AsGodotObject()).GetImage();
            foreach(var at in new[]{new Vector3(3353.723f,0,-4768.874f),new Vector3(3364.130f,0,-4762.624f)})
            {
                using var upper=PhysicsRayQueryParameters3D.Create(at+Vector3.Up*9,at+Vector3.Up*5,1);
                using var lower=PhysicsRayQueryParameters3D.Create(at+Vector3.Up*.3f,at+Vector3.Down*.3f,1);
                var deck=space.IntersectRay(upper);var ground=space.IntersectRay(lower);
                if(deck.Count==0 || Mathf.Abs(deck["position"].AsVector3().Y-7)>.15f ||
                   ground.Count==0 || Mathf.Abs(ground["position"].AsVector3().Y)>.05f ||
                   SampleHarbourSurface(mask,HarbourBounds,at).R<.9f)
                    throw new Exception($"Hammer Hill lacks separate raised and surface carriageways at {at}");
            }
            GD.Print("ANTILA_HAMMER_HILL_GRADE_OK: both raised crossings retain paved lower carriageways");
        }
        var hillsideProbe=new Vector3(4026.6667f,0,-6410.6667f);
        using var hillsideRay=PhysicsRayQueryParameters3D.Create(hillsideProbe+Vector3.Up*155,hillsideProbe+Vector3.Up*60,1);
        using var belowHillside=PhysicsRayQueryParameters3D.Create(hillsideProbe+Vector3.Up*2,hillsideProbe+Vector3.Down*2,1);
        var hillside=space.IntersectRay(hillsideRay);
        if(hillside.Count==0 || Mathf.Abs(hillside["position"].AsVector3().Y-121.1651f)>.15f ||
           (hillside["collider"].AsGodotObject() as Node)?.GetParent()?.Name!="HarbourGround" ||
           space.IntersectRay(belowHillside).Count!=0)
            throw new Exception("Tsz Wan Shan requires raised hillside collision and no hidden flat floor");
        foreach(var p in new[]{new Vector3(3769.1706f,0,-6712.8057f),new Vector3(3769.1442f,0,-6712.8358f),
            new Vector3(3350.1595f,0,-5949.979f)})
        {
            using var ray=PhysicsRayQueryParameters3D.Create(p+Vector3.Up*.15f,p+Vector3.Down*.15f,1);
            var hit=space.IntersectRay(ray);
            if(hit.Count==0 || Mathf.Abs(hit["position"].AsVector3().Y)>.025f)
                throw new Exception($"Tsz Wan Shan needs continuous ground at {p}");
        }
        GD.Print($"ANTILA_TSZ_WAN_SHAN_RELIEF_OK: hillside collision at {hillside["position"].AsVector3().Y:0.00} m, with supported seam and nearby road");
        if(FileAccess.FileExists("res://Data/ma-chai-hang-building-source.geojson"))
        {
            var at=new Vector3(1613.7103f,0,-5529.2389f);
            bool previous=_buildingStreamingCheck;_buildingStreamingCheck=true;
            try
            {
                if(PrepareBuildingProbe(at))await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
                using var ray=PhysicsRayQueryParameters3D.Create(at+Vector3.Up*16,at+Vector3.Up*5,1);
                var roof=GetWorld3D().DirectSpaceState.IntersectRay(ray);
                if(roof.Count==0 || Mathf.Abs(roof["position"].AsVector3().Y-10)>.1f)
                    throw new Exception("Ma Chai Hang expanded surveyed footprint lacks its roof collider");
            }
            finally{EnsureBuildingsAt(Bus.Position);_buildingStreamingCheck=previous;}
            GD.Print("ANTILA_MA_CHAI_HANG_ROOF_OK: 10 m roof collider on the expanded footprint");
        }
    }

    public void CheckWongTaiSinReady()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(HarbourRoads.Count>=7275,"Harbour road inventory lost established sections");
        Check(_harbourRoutes.Count>13 && _harbourRouteSources.Count==_harbourRoutes.Count,"Wong Tai Sin drive and source itinerary missing");
        Check(Routes.Select(r=>r.Number).SequenceEqual(new[]{"H1","H2","H3"}),"Wong Tai Sin must not add or change scheduled services");
        Check(HarbourBounds.Position==new Vector2(-13880,-11280) && HarbourBounds.End.X>=3230 && HarbourBounds.End.Y==2150,"Wong Tai Sin must remain inside the harbour map and mask bounds");
        Check(KowloonEastLand.Min(p=>p.Y)<=-6399,"Wong Tai Sin northern land extension missing");

        var route=_harbourRoutes[13].Points;var ids=_harbourRouteSources[13];
        float routeLength=0;for(int i=1;i<route.Count;i++)routeLength+=route[i-1].DistanceTo(route[i]);
        Check(_harbourRoutes[13].Name=="Kowloon City → Wong Tai Sin" && route.Count==550 && ids.Length==39 && Mathf.Abs(routeLength-2122.1432f)<.1f,
            $"Wong Tai Sin route definition changed: {route.Count} points, {ids.Length} source sections, {routeLength:0.000} m");
        Check(route[0].DistanceTo(_harbourRoutes[12].Points[^1])<.12f,"Wong Tai Sin route must join the Kowloon City endpoint");
        var expected=new System.Collections.Generic.List<Vector3>();
        for(int member=0;member<ids.Length;member++)
        {
            var id=ids[member];Check(_harbourRoadIndex.TryGetValue(id.TrimStart('-'),out int roadIndex),"Wong Tai Sin source road missing: "+id);
            var points=HarbourRoads[roadIndex].Points;
            expected.AddRange((id.StartsWith('-')?points.AsEnumerable().Reverse():points).Skip(member==0?0:1));
        }
        Check(expected.Count==route.Count && expected.Select((p,i)=>p.DistanceTo(route[i])<.02f).All(ok=>ok),"Wong Tai Sin route must follow its signed source roads in order");
        var terminalId=ids[^1];var terminal=HarbourRoads[_harbourRoadIndex[terminalId.TrimStart('-')]];
        Check(terminal.Name.Contains("WONG TAI SIN",StringComparison.OrdinalIgnoreCase),"Wong Tai Sin route must end on Wong Tai Sin Road");

        int lots=_lots.Count(l=>l.Center.X>550 && l.Center.X<3150 && l.Center.Z<=-4864);
        Check(lots==(HasDiamondHillDrive?1528:HasKaiTakDrive?1503:1509),$"Wong Tai Sin north-of-4,864 m building-center count changed: {lots} buildings");
        Check(_harbourDistrictTrees[10]>0 && _harbourDistrictLamps[10]>0 && _harbourDistrictPeople[10]>0,
            $"Wong Tai Sin clearance-safe street detail missing: {_harbourDistrictTrees[10]} trees, {_harbourDistrictLamps[10]} lamps, {_harbourDistrictPeople[10]} passengers");
        Check(_islandDetails.Count(d=>d.Position.X>550 && d.Position.X<3150 && d.Position.Z<=-4864)>0,"Wong Tai Sin roadside scenery missing");
        var buildingChunks=_buildingChunks.Where(c=>c.Source=="wong-tai-sin-buildings").ToArray();
        Check(buildingChunks.Length==202 && buildingChunks.All(c=>GodotObject.IsInstanceValid(c.Proxy) && c.Proxy.Visible==(c.Instance==null)) &&
            buildingChunks.Select(c=>c.Proxy.GetInstanceId()).Distinct().Count()==buildingChunks.Length,
            "Wong Tai Sin building manifest chunks need matching visible proxies");
        foreach(var chunk in _buildingChunks.Where(c=>c.Instance!=null))
        {
            var parts=chunk.Instance!.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>().ToArray();
            var visual=parts.Count(m=>m.Name.ToString().StartsWith("District"));
            var collision=parts.Where(m=>m.Name.ToString().StartsWith("Collision")).ToArray();
            Check(visual>0 && visual==collision.Length && collision.All(m=>!m.Visible && m.Mesh==null &&
                m.FindChildren("*","CollisionShape3D",true,false).Count==1),
                $"Resident building visual and collision inventory differs for {chunk.Id}");
        }

        if(!HasDiamondHillDrive)
        {
            var north=KowloonEastLand.Min(p=>p.Y);
            var edge=Enumerable.Range(0,KowloonEastLand.Length)
                .Select(i=>(A:KowloonEastLand[i],B:KowloonEastLand[(i+1)%KowloonEastLand.Length]))
                .Where(s=>Mathf.Abs(s.A.Y-north)<.1f && Mathf.Abs(s.B.Y-north)<.1f)
                .OrderByDescending(s=>s.A.DistanceTo(s.B)).FirstOrDefault();
            Check(edge.A.DistanceTo(edge.B)>20,"Wong Tai Sin northern closure edge missing");
            var boundary=(edge.A+edge.B)/2;
            using var wall=PhysicsRayQueryParameters3D.Create(new(boundary.X,2,boundary.Y),new(boundary.X,-1,boundary.Y),1);
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(wall);
            Check(hit.Count>0 && hit["position"].AsVector3().Y>.9f &&
                (hit["collider"].AsGodotObject() as Node)?.GetParent().Name=="KowloonBoundary",
                "Wong Tai Sin northern map cut must have boundary collision");
        }

        using var mask=((Texture2D)_terrain.GetShaderParameter("harbour_mask").AsGodotObject()).GetImage();
        var routeLaneData=RouteLaneData(13);
        int support=0;
        for(int i=0;i<route.Count-1;i+=12)
        {
            var forward=(route[i+1]-route[i]).Normalized();var centre=Carriageway(route[i]);
            Check(centre!=null,$"Wong Tai Sin source centerline leaves its carriageway at {route[i]}");
            var raised=centre.GetValueOrDefault().Raised;var width=routeLaneData.TryGetValue(route[i],out var laneData)?laneData.Width:centre.GetValueOrDefault().Width;
            var lane=route[i]-forward.Cross(Vector3.Up)*BusLaneCenterOffset(width,raised);
            Check(Carriageway(lane)!=null,$"Wong Tai Sin lane leaves its source road at {lane}");
            if(!raised)
            {
                var uv=(new Vector2(lane.X,lane.Z)-HarbourBounds.Position)/HarbourBounds.Size;
                int x=Math.Clamp((int)(uv.X*mask.GetWidth()),0,mask.GetWidth()-1),y=Math.Clamp((int)(uv.Y*mask.GetHeight()),0,mask.GetHeight()-1);
                Check(mask.GetPixel(x,y).R>.95f,$"Wong Tai Sin asphalt missing at {lane}");
            }
            using var ground=PhysicsRayQueryParameters3D.Create(lane+Vector3.Up*2,lane-Vector3.Up,1);
            Check(GetWorld3D().DirectSpaceState.IntersectRay(ground).Count>0,$"Wong Tai Sin lane lacks ground support at {lane}");support++;
        }
        _kerbGrid=null;
        GD.Print($"ANTILA_WONG_TAI_SIN_READY_OK: {route.Count} directed route points, {lots} northern buildings and {support} asphalt / road / ground probes");
    }

    private async Task CheckWongTaiSin()
    {
        CheckWongTaiSinReady();
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        var initial=Bus.Position;
        foreach(int state in new[]{0,1,2})
        {
            MapOpen=state==0;Paused=state==1;Complete=state==2;
            _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.Y,Pressed=true});
            Check(!HarbourDrive && Bus.Position==initial,"Y shortcut must respect map, pause and completed-service guards");
        }
        MapOpen=Paused=Complete=false;
        Bus.AutomaticTest=true;Bus.TestThrottle=1;
        for(int i=0;i<45;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(Bus.Kmh>.5f,"Wong Tai Sin moving-shortcut check must move the bus");
        var moving=Bus.Position;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.Y,Pressed=true});
        Check(!HarbourDrive && Bus.Position==moving,"Y shortcut must not teleport a moving bus");
        Bus.TestThrottle=0;Bus.AutomaticTest=false;Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.Y,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[13].Points[0])<3 &&
            _frontBlind!.Text=="NOT IN SERVICE" && !Hud.MapShowsService,"Y shortcut must start the unscored Wong Tai Sin drive");
        HarbourDrive=false;SetCab(false);SetBlinds();Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        GD.Print("ANTILA_WONG_TAI_SIN_GUARDS_OK: Y shortcut blocked by map, pause, completion and motion; P remains separate");
    }
}
