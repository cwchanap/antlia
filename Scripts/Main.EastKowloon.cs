using Godot;
using System;
using System.Linq;
using System.Threading.Tasks;

public partial class Main
{
    private static readonly Vector3 EastBoundaryProbe=new(3150,0,-2355.5f);

    private void CheckEastMapFixes()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        var seam=new Vector3(Map.Bounds.End.X+22,0,-550);
        using(var query=new PhysicsShapeQueryParameters3D {
            Shape=new BoxShape3D {Size=new(1.2f,1.2f,1.2f)},Transform=new(Basis.Identity,seam+Vector3.Up),CollisionMask=1})
            Check(GetWorld3D().DirectSpaceState.IntersectShape(query,1).Count==0,"Former eastern district fence must not divide the expanded mainland");
        using(var ray=PhysicsRayQueryParameters3D.Create(seam+Vector3.Up*.2f,seam+Vector3.Down*.2f,1))
            Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,"Removing the internal fence must preserve mainland ground");
        foreach(var edge in new[]{EastBoundaryProbe,new Vector3(0,0,Map.Bounds.End.Y+120)})
        {
            using var ray=PhysicsRayQueryParameters3D.Create(edge+Vector3.Up*2,edge+Vector3.Down,1);
            var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
            Check(hit.Count>0 && hit["position"].AsVector3().Y>.9f &&
                (hit["collider"].AsGodotObject() as Node)!.GetParent().Name=="KowloonBoundary","True outer map boundary must retain its collision wall at "+edge);
        }
        using var mask=((Texture2D)_terrain.GetShaderParameter("harbour_mask").AsGodotObject()).GetImage();
        int samples=0;
        foreach(var ids in new[]{new[]{"TD_107211","TD_107576","TD_107598","TD_107575","TD_107601"},new[]{"TD_107564","TD_107580","TD_107235"}})
        {
            Check(ids.All(_harbourRoadIndex.ContainsKey),"Missing government roundabout sections");
            for(int k=0;k<ids.Length;k++)
            {
                var road=HarbourRoads[_harbourRoadIndex[ids[k]]];
                Check(road.Points[^1].DistanceTo(HarbourRoads[_harbourRoadIndex[ids[(k+1)%ids.Length]]].Points[0])<.12f,"Government roundabout ring must close");
                for(int i=0;i<road.Points.Count-1;i++)foreach(float lane in new[]{-1.8f,0,1.8f})
                {
                    var a=road.Points[i];var b=road.Points[i+1];var at=(a+b)/2+(b-a).Normalized().Cross(Vector3.Up)*lane;
                    var uv=(new Vector2(at.X,at.Z)-HarbourBounds.Position)/HarbourBounds.Size;
                    Check(mask.GetPixel(Math.Clamp((int)(uv.X*mask.GetWidth()),0,mask.GetWidth()-1),Math.Clamp((int)(uv.Y*mask.GetHeight()),0,mask.GetHeight()-1)).R>.95f,
                        "Roundabout asphalt missing at "+at);
                    using var ray=PhysicsRayQueryParameters3D.Create(at+Vector3.Up*.2f,at+Vector3.Down*.2f,1);
                    Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,"Roundabout lane lacks ground support at "+at);samples++;
                }
            }
        }
        GD.Print($"ANTILA_EAST_MAP_FIXES_OK: two closed government roundabouts; {samples} asphalt/support probes; former fence clear; true outer wall retained");
    }

    private async Task CheckEastKowloon()
    {
        CheckEastMapFixes();
        CheckEasternOpenSpaces();
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(InputMap.HasAction("east_kowloon"),"East Kowloon shortcut action missing");
        var initial=Bus.Position;
        foreach(int state in new[]{0,1,2})
        {
            MapOpen=state==0;Paused=state==1;Complete=state==2;
            _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.P,Pressed=true});
            Check(!HarbourDrive && Bus.Position==initial,"East Kowloon shortcut must respect map, pause and completed service");
        }
        MapOpen=Paused=Complete=false;
        Bus.AutomaticTest=true;Bus.TestThrottle=1;
        for(int i=0;i<45;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(Bus.Kmh>.5f,"East Kowloon moving-shortcut check must move the bus");
        var moving=Bus.Position;_UnhandledInput(new InputEventKey {PhysicalKeycode=Key.P,Pressed=true});
        Check(!HarbourDrive && Bus.Position==moving,"East Kowloon shortcut must not teleport a moving bus");
        Bus.TestThrottle=0;Bus.AutomaticTest=false;Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        _UnhandledInput(new InputEventKey {PhysicalKeycode=Key.P,Pressed=true});
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(_harbourRoutes[12].Points[0])<3,"P shortcut must start the East Kowloon drive");
        HarbourDrive=false;SetCab(false);Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        Check(HarbourBounds.End.X>=3230,"East Kowloon map extent missing");
        Check(_lots.Count(l=>l.Center.X>650 && l.Center.Z<0)>100,"East Kowloon building coverage missing");
        Check(_islandDetails.Count(d=>d.Position.X>650 && d.Position.Z<0)>80,"East Kowloon street detail missing");
        var route=_harbourRoutes[12].Points;
        Check(route[0].DistanceTo(_harbourRoutes[0].Points[0])<.12f && route.Max(p=>p.X)>1900 && route.Min(p=>p.Z)<-3900,"East Kowloon drive must connect Hung Hom, Whampoa, To Kwa Wan and Kowloon City");
        int support=0;
        for(int i=0;i<route.Count-1;i+=7)
            foreach(float lane in new[]{-1.8f,0,1.8f})
            {
                var at=route[i]+(route[i+1]-route[i]).Normalized().Cross(Vector3.Up)*lane;
                using var ray=PhysicsRayQueryParameters3D.Create(at+Vector3.Up*.2f,at+Vector3.Down*.2f,1);
                Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,$"East Kowloon route lacks ground support at {at}");support++;
            }
        var coast=KowloonCoastline.SelectMany(line=>Enumerable.Range(1,line.Length-1)
            .Where(i=>line[i-1].DistanceTo(line[i])>=5).Select(i=>(line[i-1]+line[i])/2))
            .Where(p=>p.X>1000 && p.Y< -500).ToArray();
        Check(coast.Length>=25,"Eastern coastline probe coverage missing");
        int shore=0;
        foreach(var p in coast.Where((_,i)=>i%Math.Max(1,coast.Length/25)==0).Take(25))
            {
                using var ray=PhysicsRayQueryParameters3D.Create(new(p.X,2,p.Y),new(p.X,-1,p.Y),1);
                var hit=GetWorld3D().DirectSpaceState.IntersectRay(ray);
                Check(hit.Count>0 && hit["position"].AsVector3().Y>.9f,$"Eastern seawall lacks collision at {p}");shore++;
            }
        Check(shore==25,"Eastern coastline probe coverage missing");
        GD.Print($"ANTILA_EAST_KOWLOON_READY_OK: P shortcut and four guards; regional massing/detail; {support} lane-support and {shore} seawall probes");
    }

    private async void CaptureEastKowloon()
    {
        await CheckEastKowloon();
        SelfTest=true;SetProcess(false);SetPhysicsProcess(false);Bus.SetPaused(true);Hud.Visible=false;Bus.Model.Visible=false;
        Routes[2].Waiting[0].Visible=true;
        Camera.Far=6000;
        string folder=ProjectSettings.GlobalizePath("res://evidence/east-kowloon-expansion-2026-10-21");
        DirAccess.MakeDirRecursiveAbsolute(folder);
        foreach(var (name,p,target) in new[]{
            ("hung-hom",new Vector3(1000,400,-600),new Vector3(1450,0,-1550)),
            ("whampoa",new Vector3(2210,230,-700),new Vector3(1770,0,-1210)),
            ("to-kwa-wan",new Vector3(2450,270,-2210),new Vector3(1810,0,-2650)),
            ("kowloon-city",new Vector3(2150,220,-3510),new Vector3(1750,0,-3910)),
            ("eastern-waterfront",new Vector3(3450,1600,-900),new Vector3(1550,0,-2350)),
            ("whampoa-street",new Vector3(1864,3,-1058),new Vector3(1827,3,-1081)),
            ("hong-chong-stop",Routes[2].Path.At(Routes[2].Stops[0].Distance-22,Routes[2].Stops[0].Lane+6)+Vector3.Up*9,
                Routes[2].Path.At(Routes[2].Stops[0].Distance,Routes[2].Stops[0].Lane-3.8f)+Vector3.Up*2)})
        {
            Camera.Position=p;Camera.LookAt(target);
            await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);RenderingServer.ForceDraw(false);
            using var image=GetViewport().GetTexture().GetImage();
            if(image.SavePng($"{folder}/{name}.png")!=Error.Ok)throw new Exception("East Kowloon capture failed");
        }
        Hud.Visible=true;HarbourDrive=true;MapOpen=true;NoticeTime=0;Hud.QueueRedraw();
        await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);RenderingServer.ForceDraw(false);
        using(var image=GetViewport().GetTexture().GetImage())
            if(image.SavePng($"{folder}/map.png")!=Error.Ok)throw new Exception("East Kowloon map capture failed");
        GD.Print("ANTILA_EAST_KOWLOON_CAPTURE_OK: seven district/stop views and map");QuitGame();
    }
}
