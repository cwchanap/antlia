using Godot;
using System;
using System.Threading.Tasks;

public partial class Main
{
    private const int DiamondHillDriveIndex=15;
    private const string DiamondHillDriveName="Wong Tai Sin → Diamond Hill";
    public bool HasDiamondHillDrive=>HasHarbourDrive(DiamondHillDriveIndex);
    public Vector3 DiamondHillDriveEnd=>_harbourRoutes[DiamondHillDriveIndex].Points[^1];

    private void PressDiamondHillShortcut()=>_UnhandledInput(new InputEventKey {Keycode=Key.G,PhysicalKeycode=Key.G,Pressed=true});

    private async Task CheckDiamondHill()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(HasDiamondHillDrive && _harbourRouteSources.Count==_harbourRoutes.Count,"Diamond Hill drive and source itinerary are required");
        var (name,points)=_harbourRoutes[DiamondHillDriveIndex];
        var ids=_harbourRouteSources[DiamondHillDriveIndex];
        Check(points.Count>2 && ids.Length>1,"Diamond Hill drive needs a multi-section itinerary");
        Check(points[0].DistanceTo(_harbourRoutes[13].Points[^1])<.02f,"Diamond Hill must start at the existing Wong Tai Sin endpoint");
        Check(_harbourRoadIndex.TryGetValue(ids[^1].TrimStart('-'),out int lastRoad) &&
            HarbourRoads[lastRoad].Name=="LUNG POON STREET","Diamond Hill drive must reach the Lung Poon Street frontage");
        CheckDiamondHillTerrain();
        int support=CheckSourceDriveLanes(DiamondHillDriveIndex);
        GD.Print($"ANTILA_DIAMOND_HILL_READY_OK: {ids.Length} directed sections, {points.Count} itinerary points and {support} lane-support probes");

        int selected=RouteIndex,pending=_pendingRoute;
        ShowRouteSelect();
        Check(Menu && !Briefing && !Bus.IsPhysicsProcessing(),"Diamond Hill shortcut check must start at route select");
        PressDiamondHillShortcut();
        Check(!Menu && !Briefing && HarbourDrive && CabView && Bus.IsPhysicsProcessing() &&
            Bus.Position.DistanceTo(points[0])<3 && _frontBlind!.Text=="NOT IN SERVICE" && !Hud.MapShowsService && Notice.Contains(name,StringComparison.Ordinal),
            "G from route select must start the unscored Diamond Hill drive");
        _UnhandledInput(new InputEventKey {Keycode=Key.Tab,PhysicalKeycode=Key.Tab,Pressed=true});
        Check(Menu && !HarbourDrive && RouteIndex==selected && !Bus.IsPhysicsProcessing() && Hud.MapShowsService,
            "Tab from Diamond Hill must return to the selected service");
        _harbourRoutes.RemoveAt(DiamondHillDriveIndex);
        try
        {
            PressDiamondHillShortcut();
            Check(Menu && !HarbourDrive && !Bus.IsPhysicsProcessing(),"G must leave route select open when the Diamond Hill itinerary is unavailable");
        }
        finally{_harbourRoutes.Insert(DiamondHillDriveIndex,(name,points));}
        BeginRoute(selected);_pendingRoute=pending;
        GD.Print("ANTILA_DIAMOND_HILL_MENU_OK: G starts from route select, Tab restores the selected service, missing itinerary leaves the menu open");

        var initial=Bus.Position;float heading=Bus.Rotation.Y;
        foreach(int state in new[]{0,1,2})
        {
            MapOpen=state==0;Paused=state==1;Complete=state==2;
            PressDiamondHillShortcut();
            Check(!HarbourDrive && Bus.Position==initial,"G must respect map, pause and completed-service guards");
        }
        MapOpen=Paused=Complete=false;
        Bus.AutomaticTest=true;Bus.TestThrottle=1;
        for(int i=0;i<45;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(Bus.Kmh>.5f,"Diamond Hill moving-shortcut check must move the bus");
        var moving=Bus.Position;PressDiamondHillShortcut();
        Check(!HarbourDrive && Bus.Position==moving,"G must leave a moving bus on its current route");
        Bus.TestThrottle=0;Bus.AutomaticTest=false;Bus.ResetAt(initial,heading);
        PressDiamondHillShortcut();
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(points[0])<3 &&
            _frontBlind!.Text=="NOT IN SERVICE" && !Hud.MapShowsService,"G must launch Diamond Hill when stopped");
        BeginRoute(selected);_pendingRoute=pending;
        GD.Print("ANTILA_DIAMOND_HILL_GUARDS_OK: G blocked by map, pause, completion and motion");
    }

    private void CheckDiamondHillTerrain()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        var space=GetWorld3D().DirectSpaceState;
        float groundRayStart=HasWongTaiSinRelief?180:.25f;
        // These hills were outside the previous inland cut. The final two samples straddle its old north seam.
        foreach(var point in new[]{new Vector3(4300,0,-6600),new Vector3(5000,0,-5950),new Vector3(5100,0,-5150),
            new Vector3(3450,0,-6390),new Vector3(3450,0,-6410)})
        {
            using var ray=PhysicsRayQueryParameters3D.Create(point+Vector3.Up*groundRayStart,point+Vector3.Down*.25f,1);
            var hit=space.IntersectRay(ray);
            Check(hit.Count>0 && (hit["collider"].AsGodotObject() as Node)?.GetParent()?.Name=="HarbourGround",
                "Diamond Hill inland ground is missing at "+point);
        }
        using(var seam=PhysicsRayQueryParameters3D.Create(new(3450,.5f,-6390),new(3450,.5f,-6410),1))
            Check(space.IntersectRay(seam).Count==0,"The former Wong Tai Sin north cut must be free of internal walls");

        var inside=new Vector3(4953.160f,.5f,-7092.100f);
        var outside=new Vector3(4952.745f,.5f,-7098.086f);
        using(var boundary=PhysicsRayQueryParameters3D.Create(inside,outside,1))
        {
            var hit=space.IntersectRay(boundary);
            Check(hit.Count>0 && hit["position"].AsVector3().DistanceTo((inside+outside)/2)<.6f &&
                (hit["collider"].AsGodotObject() as Node)?.GetParent()?.Name=="KowloonBoundary",
                "Diamond Hill's new northern district edge must retain a boundary collider");
        }
        using(var exterior=PhysicsRayQueryParameters3D.Create(outside,outside+Vector3.Down,1))
            Check(space.IntersectRay(exterior).Count==0,"The ground must end outside the northern Diamond Hill district edge");
        GD.Print("ANTILA_DIAMOND_HILL_TERRAIN_OK: five mainland probes, former north seam, new district wall and exterior");
    }

    private async void CaptureDiamondHill()
    {
        try
        {
            if(DisplayServer.GetName()=="headless" || !HasDiamondHillDrive)
                throw new InvalidOperationException("Diamond Hill review requires the native renderer and the Diamond Hill itinerary");
            SelfTest=true;SetProcess(false);SetPhysicsProcess(false);
            string folder=ProjectSettings.GlobalizePath("res://evidence/diamond-hill-2026-11-25");
            DirAccess.MakeDirRecursiveAbsolute(folder);
            async Task Save(string name)
            {
                Hud.QueueRedraw();
                for(int frame=0;frame<4;frame++)
                {
                    await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);
                    RenderingServer.ForceDraw(false);
                }
                using var image=GetViewport().GetTexture().GetImage();
                if(image.IsEmpty() || image.SavePng($"{folder}/{name}.png")!=Error.Ok)
                    throw new Exception($"Diamond Hill capture failed: {name}");
            }

            ShowRouteSelect();await Save("diamond-hill-menu");
            PressDiamondHillShortcut();
            if(Menu || !HarbourDrive)throw new Exception("Diamond Hill review must launch through the G key");
            var points=_harbourRoutes[DiamondHillDriveIndex].Points;
            int approach=Math.Max(0,points.Count-25);
            var at=points[approach];var forward=(points[approach+1]-at).Normalized();
            var (width,elevated)=RouteLaneData(DiamondHillDriveIndex)[at];
            Bus.ResetAt(at-forward.Cross(Vector3.Up)*BusLaneCenterOffset(width,elevated),Mathf.Atan2(-forward.X,-forward.Z));
            Bus.SetPaused(true);SetCab(true);UpdateCamera(1,true);
            await Save("diamond-hill-driving-cab");
            MapOpen=true;await Save("diamond-hill-map");MapOpen=false;

            SetCab(false);Hud.Visible=false;Bus.Model.Visible=false;Camera.Far=3400;
            // Frame the Lung Poon Street arrival with Nan Lian, Chi Lin and Hammer Hill to the east.
            var overview=DiamondHillDriveEnd+new Vector3(415,12,125);
            EnsureBuildingsAt(overview);
            Camera.Position=overview+new Vector3(180,750,620);Camera.LookAt(overview);
            await Save("diamond-hill-overview");
            GD.Print("ANTILA_DIAMOND_HILL_REVIEW_OK: route select, G launch, cab, map and overview captured");
            QuitGame();
        }
        catch(Exception error){GD.PushError("ANTILA_DIAMOND_HILL_REVIEW_FAILED: "+error);QuitGame(1);}
    }
}
