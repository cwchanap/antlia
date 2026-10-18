using Godot;
using System;
using System.Linq;
using System.Threading.Tasks;

public partial class Main
{
    private AudioStreamPlayer AudioClip(string name)=>Bus.GetNode<AudioStreamPlayer>("Audio_"+name);

    private async Task CheckAudio()
    {
        void Check(bool ok,string message) { if(!ok)throw new Exception("audio: "+message); }
        var players=Bus.GetChildren().OfType<AudioStreamPlayer>().ToArray();
        Check(players.Length==11 && players.Where(p=>p!=Bus.Voice).All(p=>p.Stream.GetLength()>.4),"all generated clips must import");
        var music=AudioClip("music");
        Check(music.Playing && music.Stream is AudioStreamOggVorbis {Loop:true} && music.Stream.GetLength()>85,
            "full music track must start and loop independently");
        foreach(string name in new[]{"engine","rolling","city"})
        {
            var player=AudioClip(name);var stream=(AudioStreamWav)player.Stream;
            Check(player.Playing && stream.LoopMode==AudioStreamWav.LoopModeEnum.Forward &&
                stream.LoopEnd>210000,"full generated loop must play: "+name);
        }
        Bus.ToggleDoors();Bus.Horn();
        for(int i=0;i<4;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(music.VolumeDb<-16.2f,"boarding must lower music beneath the effects");
        Check(AudioClip("door-open").Playing && AudioClip("horn").Playing && AudioClip("engine").Playing,
            "effects must overlap without replacing the engine");
        _UnhandledInput(new InputEventAction {Action="map",Pressed=true});
        Check(players.Where(p=>p.HasStreamPlayback()).All(p=>p.StreamPaused),"map must pause every active audio layer");
        _UnhandledInput(new InputEventAction {Action="map",Pressed=true});
        Check(players.All(p=>!p.StreamPaused),"map close must resume audio");
        Bus.ToggleDoors();
        Check(AudioClip("door-close").Playing && !AudioClip("door-open").Playing,"door reversal must cancel the old sound");
        for(int i=0;i<30;i++)await ToSignal(GetTree(),SceneTree.SignalName.PhysicsFrame);
        Check(music.VolumeDb>-17,"music must recover after the doors close");
        bool muted=AudioServer.IsBusMute(0);
        _UnhandledInput(new InputEventAction {Action="mute",Pressed=true});
        Check(AudioServer.IsBusMute(0)!=muted,"mute must affect the master bus");
        _UnhandledInput(new InputEventAction {Action="mute",Pressed=true});
        Bus.ResetAt(Map.At(22,-7.3f),Map.Heading(22));
        Check(!AudioClip("horn").Playing && !AudioClip("door-close").Playing,"reset must stop stale one-shots");
        Check(music.Playing,"reset must preserve background music");
        GD.Print("ANTILA_AUDIO_CHECKS_OK: 9 SFX, 1 music track and Mio's voice channel, full loops, overlapping effects, map pause/resume, mute and reset cleanup");
    }

    private async void ReviewAudio()
    {
        try
        {
            SelfTest=true;Bus.AutomaticTest=true;
            async Task Wait(float seconds)=>await ToSignal(GetTree().CreateTimer(seconds),SceneTreeTimer.SignalName.Timeout);
            await Wait(1);
            var recorder=new AudioEffectRecord {Format=AudioStreamWav.FormatEnum.Format16Bits};
            int index=AudioServer.GetBusEffectCount(0);AudioServer.AddBusEffect(0,recorder);
            recorder.SetRecordingActive(true);
            await Wait(2);Bus.Horn();await Wait(1.5f);
            Bus.ToggleDoors();await Wait(1.4f);Bus.ToggleDoors();await Wait(1.4f);
            Bus.TestThrottle=1;await Wait(3.5f);
            Bus.TestThrottle=0;Bus.TestBrake=1;await Wait(2);Bus.TestBrake=0;
            Bus.ResetAt(Map.At(Map.Stops[0].Distance,-7.3f),Map.Heading(Map.Stops[0].Distance));
            Bus.ToggleDoors();await Wait(1.4f);AdvanceService(4.1f);await Wait(1.5f);
            Bus.ToggleDoors();await Wait(1.4f);
            _UnhandledInput(new InputEventAction {Action="map",Pressed=true});await Wait(1.5f);
            _UnhandledInput(new InputEventAction {Action="map",Pressed=true});await Wait(1);
            Bus.ResetAt(new(Map.Bounds.End.X+14,0,-550),-Mathf.Pi/2);
            Bus.TestThrottle=1;await Wait(3);Bus.TestThrottle=0;
            Bus.StopAudio();await Wait(1);
            recorder.SetRecordingActive(false);
            string path=ProjectSettings.GlobalizePath("res://evidence/game-audio-review.wav");
            if(recorder.GetRecording().SaveToWav(path)!=Error.Ok)throw new Exception("recording could not be saved");
            recorder.SetRecordingActive(true);
            var music=AudioClip("music");
            music.Play((float)music.Stream.GetLength()-1.2f);
            await Wait(3);
            if(!music.Playing || music.GetPlaybackPosition()>4)throw new Exception("music did not wrap to its beginning");
            Bus.SetPaused(true);await Wait(1.2f);Bus.SetPaused(false);await Wait(1);
            Bus.StopAudio();await Wait(1);
            recorder.SetRecordingActive(false);
            if(recorder.GetRecording().SaveToWav(ProjectSettings.GlobalizePath("res://evidence/music-loop-review.wav"))!=Error.Ok)
                throw new Exception("music loop recording could not be saved");
            AudioServer.RemoveBusEffect(0,index);
            GD.Print("ANTILA_AUDIO_REVIEW_OK: native game mix saved to "+path+"; music wrap/pause/resume recorded separately");
            QuitGame();
        }
        catch(Exception error) {GD.PushError("ANTILA_AUDIO_REVIEW_FAILED: "+error);QuitGame(1);}
    }
}
