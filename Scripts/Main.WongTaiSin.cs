using Godot;
using System;
using System.Linq;
using System.Threading.Tasks;

public partial class Main
{
    public void CheckWongTaiSinReady()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(HarbourRoads.Count==7227,"Wong Tai Sin road section count changed");
        Check(_harbourRoutes.Count==14 && _harbourRouteSources.Count==14,"Wong Tai Sin drive and source itinerary missing");
        Check(Routes.Select(r=>r.Number).SequenceEqual(new[]{"H1","H2","H3"}),"Wong Tai Sin must not add or change scheduled services");
        Check(HarbourBounds.Position==new Vector2(-13880,-11280) && HarbourBounds.End==new Vector2(3230,2150),"Wong Tai Sin must preserve the harbour map and mask bounds");
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
        Check(lots==1509,$"Wong Tai Sin north-of-4,864 m building-center count changed: {lots} buildings");
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

        var north=KowloonEastLand.Min(p=>p.Y);
        var edge=Enumerable.Range(0,KowloonEastLand.Length)
            .Select(i=>(A:KowloonEastLand[i],B:KowloonEastLand[(i+1)%KowloonEastLand.Length]))
            .Where(s=>Mathf.Abs(s.A.Y-north)<.1f && Mathf.Abs(s.B.Y-north)<.1f)
            .OrderByDescending(s=>s.A.DistanceTo(s.B)).FirstOrDefault();
        Check(edge.A.DistanceTo(edge.B)>20,"Wong Tai Sin northern closure edge missing");
        var boundary=(edge.A+edge.B)/2;using(var wall=PhysicsRayQueryParameters3D.Create(new(boundary.X,2,boundary.Y),new(boundary.X,-1,boundary.Y),1))
        {
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
