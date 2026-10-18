using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

// Mio, the onboard guide: Japanese lines and English captions from Data/mio.json, voiced by the active ElevenLabs cast.
public partial class Main
{
    public readonly Dictionary<string,(string Ja,string En,AudioStream Clip)> MioLines=new();
    public readonly List<string> MioLog=new();
    public string MioCast="",MioCaption="";
    private readonly Queue<string> _mioQueue=new();
    private bool _mioDoorsOpen,_mioDeparting;
    private int _mioContacts;
    private static readonly string[] MioEvents={"doors.open","doors.close","missed","red-light","contact","complete","abandoned"};

    private void LoadMio()
    {
        using var doc=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/mio.json"));
        MioCast=doc.RootElement.GetProperty("cast").EnumerateArray().Single(c=>c.TryGetProperty("active",out var a) && a.GetBoolean()).GetProperty("id").GetString()!;
        foreach(var line in doc.RootElement.GetProperty("lines").EnumerateArray())
        {
            string id=line.GetProperty("id").GetString()!;
            MioLines[id]=(line.GetProperty("ja").GetString()!,line.GetProperty("en").GetString()!,GD.Load<AudioStream>($"res://Assets/Audio/Mio/{MioCast}/{id}.ogg"));
        }
        Bus.Voice.Finished+=MioNext;
    }

    public static string MioNextStop(ServiceRoute route,int stop)=>$"{route.Number}.next.{route.Stops[stop].Name.ToLowerInvariant().Replace(' ','-')}";

    // Announcements play in order; an aside to the driver is dropped while Mio is already talking.
    public void MioSay(string id,bool aside=false)
    {
        if(aside && (Bus.Voice.Playing || _mioQueue.Count>0))return;
        _mioQueue.Enqueue(id);MioLog.Add(id);
        if(!Bus.Voice.Playing)MioNext();
    }

    private void MioNext()
    {
        MioCaption="";
        if(!_mioQueue.TryDequeue(out var id))return;
        var line=MioLines[id];
        Bus.Voice.Stream=line.Clip;Bus.Voice.Play();MioCaption=line.En;
    }

    private void MioReset()
    {
        _mioQueue.Clear();Bus.Voice.Stop();MioCaption="";MioLog.Clear();
        _mioDoorsOpen=_mioDeparting=false;_mioContacts=Bus.Collisions;
    }

    // Doors and contacts are read from the bus, so the player's keys and the scripted test driver both reach Mio.
    private void UpdateMio()
    {
        if(Bus.Collisions>_mioContacts){_mioContacts=Bus.Collisions;MioSay("contact",true);}
        if(_mioDoorsOpen && !Bus.DoorsOpen && _mioDeparting){_mioDeparting=false;MioSay("doors.close");MioSay(MioNextStop(Route,StopIndex));}
        _mioDoorsOpen=Bus.DoorsOpen;
    }

    private void CheckMio()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception("mio: "+message);}
        var ids=Routes.SelectMany(r=>r.Stops.Select((_,i)=>MioNextStop(r,i)).Prepend($"{r.Number}.welcome")).Concat(MioEvents).ToArray();
        Check(MioLines.Count==25 && ids.Length==25 && ids.All(MioLines.ContainsKey),
            "every route, stop and event needs a line: "+string.Join(", ",ids.Where(id=>!MioLines.ContainsKey(id))));
        foreach(var (id,line) in MioLines)
        {
            Check(line.Ja.Any(c=>c is >='぀' and <='ヿ'),$"{id} must keep its Japanese text");
            Check(line.Clip is AudioStreamOggVorbis {Loop:false} && line.Clip.GetLength() is >.4 and <12,$"{id} needs a one-shot {MioCast} clip: {line.Clip?.GetLength():0.0} s");
            Check(Hud.CaptionLines(line.En) is 1 or 2,$"{id} caption must fit two lines: {Hud.CaptionLines(line.En)}");
        }
        GD.Print($"ANTILA_MIO_LINES_OK: {MioLines.Count} Japanese lines with English captions, voiced by the {MioCast} cast, {MioLines.Values.Sum(l=>l.Clip.GetLength()):0} s in all");
    }

    // The order a clean service hears: welcome and first stop, doors and the next stop at every bay, then the end of service.
    private List<string> MioService(ServiceRoute route)
    {
        var lines=new List<string>{$"{route.Number}.welcome",MioNextStop(route,0)};
        for(int i=1;i<route.Stops.Count;i++)lines.AddRange(new[]{"doors.open","doors.close",MioNextStop(route,i)});
        lines.Add("complete");
        return lines;
    }
}
