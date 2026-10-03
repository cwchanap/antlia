using Godot;
using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

public partial class Main
{
    private static RestartLog? _restartLog;
    private static int _restartCycle, _restartMeshes, _restartShapes;

    private partial class RestartLog : Logger
    {
        public int Errors;
        public override void _LogError(string function,string file,int line,string code,string rationale,
            bool editorNotify,int errorType,Godot.Collections.Array<ScriptBacktrace> scriptBacktraces)
        {
            if(errorType!=(int)ErrorType.Warning)Interlocked.Increment(ref Errors);
        }
    }

    private async Task CheckRestart()
    {
        int meshes=_city.FindChildren("*","MeshInstance3D",true,false).Count;
        int shapes=_city.FindChildren("*","CollisionShape3D",true,false).Count;
        if(_restartLog==null)
        {
            _restartLog=new RestartLog();OS.AddLogger(_restartLog);
            _restartMeshes=meshes;_restartShapes=shapes;
        }
        if(Volatile.Read(ref _restartLog.Errors)>0)
            throw new Exception($"Restart emitted {_restartLog.Errors} engine errors on cycle {_restartCycle}");
        if(meshes!=_restartMeshes || shapes!=_restartShapes || Complete || Paused || MapOpen || HarbourDrive ||
            StopIndex!=0 || Passengers!=0 || Bus.DoorsOpen || Bus.Reverse || !Bus.IsPhysicsProcessing() ||
            !Hud.ServiceInstruction.StartsWith("33 m"))throw new Exception("Restart did not restore H1/world state");
        await CheckBuildings();
        if(DisplayServer.GetName()!="headless")
        {
            RenderingServer.ForceDraw(false);
            string folder=ProjectSettings.GlobalizePath("res://evidence/restart-check");
            DirAccess.MakeDirRecursiveAbsolute(folder);
            using var image=GetViewport().GetTexture().GetImage();
            if(image.SavePng($"{folder}/restart-{_restartCycle}.png")!=Error.Ok)throw new Exception("Restart capture failed");
        }
        if(Volatile.Read(ref _restartLog.Errors)>0)throw new Exception("Restart world validation emitted engine errors");
        GD.Print($"ANTILA_RESTART_STATE_OK: cycle {_restartCycle}; {meshes} meshes / {shapes} collision shapes; H1 ready");
        if(_restartCycle==3)
        {
            OS.RemoveLogger(_restartLog);_restartLog.Dispose();_restartLog=null;
            GD.Print("ANTILA_RESTART_CHECKS_OK: 3 reloads from paused map, island drive and completed service; no engine errors");
            QuitGame();return;
        }
        if(_restartCycle==0)
        {
            _UnhandledInput(new InputEventAction {Action="pause",Pressed=true});
            _UnhandledInput(new InputEventAction {Action="map",Pressed=true});
        }
        else if(_restartCycle==1)StartHarbourDrive(3);
        else
        {
            foreach(var stop in Map.Stops)
            {
                Bus.ResetAt(Map.At(stop.Distance,-7.3f),Map.Heading(stop.Distance));
                Bus.ToggleDoors();AdvanceService(4);
            }
            if(!Complete || Passengers!=26)throw new Exception("Restart completion setup failed");
        }
        _restartCycle++;
        _UnhandledInput(new InputEventAction {Action="restart",Pressed=true});
    }
}
