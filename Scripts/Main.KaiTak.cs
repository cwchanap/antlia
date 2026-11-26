using Godot;
using System;
using System.Threading.Tasks;

public partial class Main
{
    private const int KaiTakDriveIndex=14;
    private const string KaiTakDriveName="Kai Tak → Kai Tak Cruise Terminal";
    public bool HasKaiTakDrive=>HasHarbourDrive(KaiTakDriveIndex);
    public Vector3 KaiTakDriveEnd=>_harbourRoutes[KaiTakDriveIndex].Points[^1];

    private async Task CheckKaiTak()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        Check(HasKaiTakDrive && _harbourRouteSources.Count>KaiTakDriveIndex,"Kai Tak drive and source itinerary are required");
        var (name,points)=_harbourRoutes[KaiTakDriveIndex];
        var ids=_harbourRouteSources[KaiTakDriveIndex];
        Check(ids.Length>1 && points.Count>2,"Kai Tak needs a multi-section itinerary");
        Check(points[0].X<3150 && points[^1].X>3150 && HarbourBounds.End.X>3230,"Kai Tak must connect established roads to the eastern extension");
        Check(InputMap.HasAction("kai_tak"),"Kai Tak shortcut action is missing");

        int support=CheckSourceDriveLanes(KaiTakDriveIndex);
        GD.Print($"ANTILA_KAI_TAK_READY_OK: {ids.Length} directed sections, {points.Count} itinerary points and {support} lane-support probes");

        void PressShortcut()=>_UnhandledInput(new InputEventKey {Keycode=Key.F,PhysicalKeycode=Key.F,Pressed=true});
        int selected=RouteIndex;
        ShowRouteSelect();
        Check(Menu && !Briefing && !Bus.IsPhysicsProcessing(),"Kai Tak shortcut check must start at route select");
        PressShortcut();
        Check(!Menu && !Briefing && HarbourDrive && CabView && Bus.IsPhysicsProcessing() &&
            Bus.Position.DistanceTo(points[0])<3 && _frontBlind!.Text=="NOT IN SERVICE" && !Hud.MapShowsService,
            "F from route select must start the unscored Kai Tak drive");
        _UnhandledInput(new InputEventKey {Keycode=Key.Tab,PhysicalKeycode=Key.Tab,Pressed=true});
        Check(Menu && !HarbourDrive && RouteIndex==selected && !Bus.IsPhysicsProcessing() && Hud.MapShowsService,
            "Tab from the Kai Tak drive must return to the selected service");
        _harbourRoutes.RemoveAt(KaiTakDriveIndex);
        try
        {
            PressShortcut();
            Check(Menu && !HarbourDrive && !Bus.IsPhysicsProcessing(),"F must leave route select open when the Kai Tak itinerary is unavailable");
        }
        finally{_harbourRoutes.Insert(KaiTakDriveIndex,(name,points));}
        int pending=_pendingRoute;
        BeginRoute(selected);
        _pendingRoute=pending;
        GD.Print("ANTILA_KAI_TAK_MENU_OK: F starts from route select, Tab restores the selected service, missing itinerary leaves the menu open");

        var initial=Bus.Position;
        foreach(int state in new[]{0,1,2})
        {
            MapOpen=state==0;Paused=state==1;Complete=state==2;
            PressShortcut();
            Check(!HarbourDrive && Bus.Position==initial,"F shortcut must respect map, pause and completed-service guards");
        }
        MapOpen=Paused=Complete=false;
        Bus.AutomaticTest=true;Bus.TestThrottle=1;
        for(int i=0;i<45;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(Bus.Kmh>.5f,"Kai Tak moving-shortcut check must move the bus");
        var moving=Bus.Position;PressShortcut();
        Check(!HarbourDrive && Bus.Position==moving,"F shortcut must not teleport a moving bus");

        Bus.TestThrottle=0;Bus.AutomaticTest=false;Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        PressShortcut();
        Check(HarbourDrive && CabView && Bus.Position.DistanceTo(points[0])<3 &&
            _frontBlind!.Text=="NOT IN SERVICE" && !Hud.MapShowsService,"F shortcut must start the unscored Kai Tak drive");
        HarbourDrive=false;SetCab(false);SetBlinds();Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        GD.Print("ANTILA_KAI_TAK_GUARDS_OK: F shortcut blocked by map, pause, completion and motion");
    }

    private async void CaptureKaiTak()
    {
        try
        {
            if(DisplayServer.GetName()=="headless" || !HasKaiTakDrive)
                throw new InvalidOperationException("Kai Tak review requires the native renderer and the Kai Tak itinerary");
            SelfTest=true;SetProcess(false);SetPhysicsProcess(false);Bus.SetPaused(true);
            Hud.Visible=false;Bus.Model.Visible=false;Camera.Far=6500;
            var points=_harbourRoutes[KaiTakDriveIndex].Points;
            var approach=points[Math.Max(0,points.Count-24)];
            // Centre of the surveyed terminal massing.
            var terminal=new Vector3(4084.2f,14,-1369.5f);
            var along=(terminal-approach).Normalized();
            string folder=ProjectSettings.GlobalizePath("res://evidence/kowloon-city-district-2026-11-24");
            DirAccess.MakeDirRecursiveAbsolute(folder);
            foreach(var (name,at,target) in new[]{
                ("kai-tak-overview",new Vector3(2820,2050,-1080),new Vector3(3290,0,-2310)),
                ("kai-tak-terminal-approach",approach+Vector3.Up*12-along*22+along.Cross(Vector3.Up)*6,terminal)})
            {
                EnsureBuildingsAt(target);
                await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
                Camera.Position=at;Camera.LookAt(target);
                await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);RenderingServer.ForceDraw(false);
                using var image=GetViewport().GetTexture().GetImage();
                if(image.IsEmpty() || image.SavePng($"{folder}/{name}.png")!=Error.Ok)
                    throw new Exception("Kai Tak screenshot failed: "+name);
            }
            GD.Print("ANTILA_KAI_TAK_REVIEW_OK: overview and terminal approach captured");
            QuitGame();
        }
        catch(Exception error)
        {
            GD.PushError("ANTILA_KAI_TAK_REVIEW_FAILED: "+error);
            QuitGame(1);
        }
    }
}
