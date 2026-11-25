using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

public partial class Main
{
    private async void RunBuildingLoaderCheck()
    {
        try{await CheckBuildingLoaderRecovery();QuitGame();}
        catch(Exception error){GD.PushError("ANTILA_SELF_TEST_FAILED: "+error);QuitGame(1);}
    }

    private async Task CheckBuildingLoaderRecovery()
    {
        string path="res://evidence/building-streaming-loader-fixture.tscn";
        string absolute=ProjectSettings.GlobalizePath(path);
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(absolute)!);
        var fixture=new BuildingChunk {Id="loader-recovery",Path=path,Bounds=new Rect2(100000,100000,1,1)};
        bool printErrors=Engine.PrintErrorMessages;
        try
        {
            // The missing-file error is deliberate; restore normal diagnostics before reporting any assertion failure.
            Engine.PrintErrorMessages=false;
            if(System.IO.File.Exists(absolute))System.IO.File.Delete(absolute);
            if(ResourceLoader.LoadThreadedRequest(path,"PackedScene")!=Error.Ok)throw new Exception("Could not start missing building fixture");
            fixture.Requested=true;
            for(int i=0;i<600 && ResourceLoader.LoadThreadedGetStatus(path)==ResourceLoader.ThreadLoadStatus.InProgress;i++)
                await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);
            if(ResourceLoader.LoadThreadedGetStatus(path)!=ResourceLoader.ThreadLoadStatus.Failed)throw new Exception("Missing building fixture did not fail");
            bool failed=false;
            try{FinishBuildingRequest(fixture,Vector3.Zero,true);}catch(Exception){failed=true;}
            if(!failed || fixture.Requested || ResourceLoader.LoadThreadedGetStatus(path)!=ResourceLoader.ThreadLoadStatus.InvalidResource)
                throw new Exception("Failed building request retained its native loader token");
            System.IO.File.WriteAllText(absolute,"[gd_scene format=3]\n\n[node name=\"LoaderFixture\" type=\"Node3D\"]\n");
            if(ResourceLoader.LoadThreadedRequest(path,"PackedScene")!=Error.Ok)throw new Exception("Could not retry repaired building fixture");
            fixture.Requested=true;FinishBuildingRequest(fixture,Vector3.Zero,true);
            if(fixture.Requested)throw new Exception("Repaired building fixture retained its loader request");
        }
        finally
        {
            if(ResourceLoader.LoadThreadedGetStatus(path)!=ResourceLoader.ThreadLoadStatus.InvalidResource)ResourceLoader.LoadThreadedGet(path)?.Dispose();
            Engine.PrintErrorMessages=printErrors;
            if(System.IO.File.Exists(absolute))System.IO.File.Delete(absolute);
        }
        GD.Print("ANTILA_BUILDING_LOADER_RECOVERY_OK: failed token drained; repaired asset loads on retry");
    }

    private async Task CheckBuildingStreaming()
    {
        await CheckBuildingLoaderRecovery();
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        bool headless=DisplayServer.GetName()=="headless";
        bool NearbyMissing(Vector3 position)=>_buildingChunks.Any(c=>c.Instance==null && BuildingDistanceSquared(c.Bounds,position)<=BuildingLoadRadius*BuildingLoadRadius);
        int detailed=_city.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>().Count(m=>m.Name.ToString().StartsWith("District"));
        if(detailed>=500)throw new Exception($"Building streaming eagerly retained {detailed} detailed chunks at H1");
        Check(_buildingChunks.Count>=3170 && detailed>50,"Streaming manifest or starting building window missing");
        Check(BuildingDistanceSquared(new Rect2(-128,-128,256,256),new Vector3(-128,0,128))==0 &&
            BuildingDistanceSquared(new Rect2(-128,-128,256,256),new Vector3(-131,0,132))==25,
            "Chunk selection must use conservative mesh bounds at negative cell edges");
        var original=Bus.Position;bool physics=Bus.IsPhysicsProcessing();Bus.SetPaused(true);_buildingStreamingCheck=true;
        int peak=0,teleports=0;
        void Window(Vector3 position)
        {
            Check(_buildingChunks.All(c=>BuildingDistanceSquared(c.Bounds,position)>BuildingLoadRadius*BuildingLoadRadius || c.Instance!=null),"Nearby building chunk missing after destination preparation");
            Check(_buildingChunks.All(c=>c.Instance==null || BuildingDistanceSquared(c.Bounds,position)<=BuildingKeepRadius*BuildingKeepRadius),"Distant detail was not evicted");
            Check(_buildingChunks.All(c=>c.Proxy.Visible==(c.Instance==null)),"Building detail/proxy handoff left a hole or duplicate");
            Check(!headless || !_buildingChunks.Any(c=>c.Requested),"Headless streaming must not create mesh resources on loader threads");
            int count=_buildingChunks.Count(c=>c.Instance!=null);peak=Math.Max(peak,count);
            Check(count<1000,"Streaming retained too much of the detailed city");
        }
        try
        {
            var retired=_buildingChunks.First(c=>c.Instance!=null);
            var oldModel=retired.Instance!;var oldMesh=retired.Resources.OfType<Mesh>().First();
            var destinations=new List<Vector3>{_harbourRoutes[10].Points[^1],_harbourRoutes[13].Points[^1]};
            if(HasKaiTakDrive)destinations.Add(KaiTakDriveEnd);
            destinations.Add(Routes[2].Path.At(Routes[2].Start,Routes[2].LaneAt(Routes[2].Start)));
            destinations.Add(original);
            foreach(var destination in destinations)
            {
                Bus.ResetAt(destination,0);Window(destination);
                await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
                var lot=_lots.Where(l=>new Vector2(l.Center.X-destination.X,l.Center.Z-destination.Z).Length()<700).First(l=>l.Height>12);
                using var ray=PhysicsRayQueryParameters3D.Create(lot.Center+Vector3.Up*(lot.Height+2),lot.Center+Vector3.Up*(lot.Height-1),1);
                Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,"Teleport destination has no real building roof collision");
                if(teleports++==0)Check(!GodotObject.IsInstanceValid(oldModel) && oldMesh.NativeInstance==IntPtr.Zero,"Eviction retained old building nodes or managed mesh ownership");
                GD.Print($"ANTILA_STREAMING_WINDOW: {destination}; {_buildingChunks.Count(c=>c.Instance!=null)} detail chunks");
            }
            // Approach a real chunk boundary through the runtime streaming path.
            var next=_buildingChunks.Where(c=>c.Instance==null).OrderBy(c=>BuildingDistanceSquared(c.Bounds,original)).First();
            var center=new Vector3(next.Bounds.GetCenter().X,0,next.Bounds.GetCenter().Y);
            var approach=original+(center-original).Normalized()*200;
            int beforeApproach=_buildingChunks.Count(c=>c.Instance!=null);
            Bus.Position=approach;_buildingStreamingCheck=false;UpdateBuildingStreaming();_buildingStreamingCheck=true;
            int background=0;
            if(headless)
            {
                Check(!_buildingChunks.Any(c=>c.Requested),"Headless streaming issued a threaded chunk request");
                Check(_buildingChunks.Count(c=>c.Instance!=null)>beforeApproach,"Headless streaming did not load approaching detail synchronously");
                Check(NearbyMissing(approach),"Headless stationary prefetch check needs more approaching detail chunks");
                int previous=_buildingChunks.Count(c=>c.Instance!=null);
                for(int frame=0;frame<3 && NearbyMissing(approach);frame++)
                {
                    await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);
                    _buildingStreamingCheck=false;UpdateBuildingStreaming();_buildingStreamingCheck=true;
                    int current=_buildingChunks.Count(c=>c.Instance!=null);
                    Check(current>previous && !_buildingChunks.Any(c=>c.Requested),"Headless stationary focus stopped synchronous chunk loading");
                    previous=current;
                }
            }
            else
            {
                Check(_buildingChunks.Any(c=>c.Requested),"Approaching a new chunk did not request background loading");
                for(int frame=0;frame<600 && next.Instance==null;frame++)
                {
                    _buildingStreamingCheck=false;UpdateBuildingStreaming();_buildingStreamingCheck=true;
                    background=Math.Max(background,_buildingChunks.Count(c=>c.Instance!=null));
                    await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);
                }
                Check(next.Instance!=null && background>0,"Background chunk did not become detailed before reaching the bus");
            }
            // Leave outstanding requests behind, then immediately return: stale jobs must be drained and discarded.
            Bus.ResetAt(_harbourRoutes[10].Points[^1],0);Window(Bus.Position);Bus.ResetAt(original,Map.Heading(22));Window(original);
            Check(!_buildingChunks.Any(c=>c.Requested),"Teleport retained obsolete background requests");
            GD.Print($"ANTILA_BUILDING_STREAMING_OK: {detailed}/{_buildingChunks.Count} initial detail chunks; peak {peak}; {teleports+2} teleports, real roof collision, {(headless?"main-thread":"background")} approach, eviction and return");
        }
        finally
        {
            Bus.ResetAt(original,Map.Heading(22));_buildingStreamingCheck=false;Bus.SetPaused(!physics);
        }
    }
}
