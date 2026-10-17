using Godot;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;

public partial class Hud
{
    private static readonly Rect2 RouteMapArea=new(640,116,724,540);
    private SubViewport _routeMap=null!;
    private Rect2 _routeBounds=new(-1000,-1200,2000,1500);
    private float RouteScale=>RouteMapArea.Size.X/_routeBounds.Size.X;
    public Rect2 StartButton=>new(60,764,520,52);
    public Rect2 RouteCard(int i)=>new(60,190+i*124,520,108);
    public Vector2 Virtual(Vector2 p)=>p*new Vector2(1440,900)/GetViewportRect().Size;
    private static string TitleCase(string name)=>CultureInfo.InvariantCulture.TextInfo.ToTitleCase(name.ToLowerInvariant());
    private static string Clock(float seconds)=>$"{(int)seconds/60:00}:{(int)seconds%60:00}";
    private Vector2 MapPoint(Vector3 p)=>RouteMapArea.Position+(new Vector2(p.X,p.Z)-_routeBounds.Position)*RouteScale;

    private void BuildRouteMap()
    {
        // World-space lines, re-rendered once whenever route select previews another route.
        Vector2 Flat(Vector3 p)=>new(p.X,p.Z);
        var lines=new[]{new List<Vector2>(),new List<Vector2>(),new List<Vector2>(),new List<Vector2>()};
        foreach(var line in Game.KowloonCoastline.Concat(Game.IslandCoastline))
            for(int i=1;i<line.Length;i++){lines[0].Add(line[i-1]);lines[0].Add(line[i]);}
        foreach(var road in Game.Map.SideRoads)
            for(int i=1;i<road.Points.Count;i++){lines[1].Add(Flat(road.Points[i-1]));lines[1].Add(Flat(road.Points[i]));}
        foreach(var road in Game.HarbourRoads)
            for(int i=1;i<road.Points.Count;i++){var batch=lines[road.Tunnel?3:2];batch.Add(Flat(road.Points[i-1]));batch.Add(Flat(road.Points[i]));}
        var arrays=lines.Select(l=>l.ToArray()).ToArray();
        var colors=new[]{new Color("72a9aa"),new Color("526e67"),new Color("d4b26e"),new Color("7ed8dc")};
        var widths=new[]{1.8f,2.2f,1.6f,2.6f};
        _routeMap=new SubViewport {Size=(Vector2I)RouteMapArea.Size,TransparentBg=true,Disable3D=true,RenderTargetUpdateMode=SubViewport.UpdateMode.Once};
        AddChild(_routeMap);
        var canvas=new Control();_routeMap.AddChild(canvas);
        canvas.Draw+=()=>
        {
            var pixels=(Vector2)_routeMap.Size/RouteMapArea.Size;
            float scale=RouteScale*pixels.X;
            canvas.DrawSetTransform(-_routeBounds.Position*scale,0,Vector2.One*scale);
            for(int i=0;i<arrays.Length;i++)
                if(arrays[i].Length>1)canvas.DrawMultiline(arrays[i],colors[i],widths[i]*pixels.X/scale,true);
        };
    }

    public void ShowRouteMap(ServiceRoute route)
    {
        var points=route.Path.Points;
        var low=new Vector2(points.Min(p=>p.X),points.Min(p=>p.Z));var high=new Vector2(points.Max(p=>p.X),points.Max(p=>p.Z));
        float aspect=RouteMapArea.Size.X/RouteMapArea.Size.Y;
        float width=Mathf.Max(1600,Mathf.Max(high.X-low.X,(high.Y-low.Y)*aspect)*1.3f);
        var size=new Vector2(width,width/aspect);
        _routeBounds=new((low+high)/2-size/2,size);
        _routeMap.GetChild<Control>(0).QueueRedraw();
        _routeMap.RenderTargetUpdateMode=SubViewport.UpdateMode.Once;
    }

    private void Card(Rect2 r,bool selected)
    {
        var style=new StyleBoxFlat {BgColor=selected?new Color(.07f,.15f,.15f,.97f):_panel,CornerRadiusTopLeft=5,CornerRadiusTopRight=5,
            CornerRadiusBottomLeft=5,CornerRadiusBottomRight=5,BorderColor=_mint,BorderWidthLeft=selected?2:0,BorderWidthTop=selected?2:0,
            BorderWidthRight=selected?2:0,BorderWidthBottom=selected?2:0};
        DrawStyleBox(style,r);
    }

    private void DrawRouteSelect()
    {
        var route=Game.Route;
        DrawRect(new(0,0,1440,900),new Color(.03f,.08f,.08f,.5f));
        Text("ANTILA  /  BUS DRIVING",60,62,14,_mint);
        Text(Game.Briefing?"Route briefing":"Choose a route",60,110,36);
        Text(Game.Briefing?"Check the stops, pick a camera, then start.":"Drive to the terminus, then see your trip statistics.",60,144,16,_muted);
        if(Game.Briefing)DrawBriefing(route);
        else
        {
            for(int i=0;i<Game.Routes.Count;i++)
            {
                var r=RouteCard(i);var card=Game.Routes[i];
                Card(r,i==Game.RouteIndex);
                DrawRect(new(r.Position,new(76,r.Size.Y)),card.Color);
                Text(card.Number,r.Position.X+12,r.Position.Y+67,34);
                Text(card.Name,r.Position.X+96,r.Position.Y+34,20);
                Text($"{i+1}",r.End.X-26,r.Position.Y+32,14,_muted);
                Text(card.Chinese,r.Position.X+96,r.Position.Y+57,14,_muted);
                Text($"{card.Path.Length/1000:0.00} km   •   {card.Stops.Count} stops   •   {card.Difficulty}",r.Position.X+96,r.Position.Y+80,13,_mint);
                Text(card.Summary,r.Position.X+96,r.Position.Y+99,12,_muted);
            }
            var free=RouteCard(Game.Routes.Count);
            Card(free,false);
            DrawRect(new(free.Position,new(76,free.Size.Y)),new Color("41504b"));
            Text("HK",free.Position.X+16,free.Position.Y+64,26);
            Text("Free drive",free.Position.X+96,free.Position.Y+34,20);
            Text("No stops or scoring. Press a key while stopped:",free.Position.X+96,free.Position.Y+57,13,_muted);
            Text("T Tunnel   I Island   J Central   K Nathan   L West",free.Position.X+96,free.Position.Y+80,12,_paper);
            Text("N Lai Chi Kok   B Kwai Chung   U Tsuen Wan   O Coast",free.Position.X+96,free.Position.Y+99,12,_paper);
        }
        Panel(620,64,760,756);
        Text($"{route.Number}   {route.Name}",640,98,18);
        var pixels=(Vector2I)(RouteMapArea.Size*GetViewportRect().Size/new Vector2(1440,900)).Ceil();
        if(_routeMap.Size!=pixels)
        {
            _routeMap.Size=pixels;_routeMap.GetChild<Control>(0).QueueRedraw();
            _routeMap.RenderTargetUpdateMode=SubViewport.UpdateMode.Once;
        }
        DrawRect(RouteMapArea,new Color(.03f,.07f,.07f,.9f));
        DrawTextureRect(_routeMap.GetTexture(),RouteMapArea,false);
        DrawRouteOverlay(route);
        Text("N ↑",RouteMapArea.End.X-34,RouteMapArea.Position.Y+22,13,_mint);
        Text($"STOPS   •   {route.Path.Length/1000:0.00} km   •   {route.TotalPassengers} passengers waiting",640,690,12,_mint);
        for(int i=0;i<route.Stops.Count;i++)
            Text($"{i+1}   {route.Stops[i].Name}",640+(i%2)*362,718+(i/2)*24,14,i==route.Stops.Count-1?_paper:_muted);
        Panel(60,836,1320,40);
        Text(Game.Briefing?"ENTER  Start driving        C  Camera        ESC  Back to routes        V  Sound":
            $"↑ / ↓  Choose        1–{Game.Routes.Count}  Pick        ENTER  Briefing        Click a card to select        V  "+(AudioServer.IsBusMute(0)?"Unmute":"Sound"),80,862,13,_paper);
        Text("Roads / buildings / coast © HKSAR Govt · TD / LandsD · 15 Oct 2026",31,889,9,_muted);
    }

    private void DrawBriefing(ServiceRoute route)
    {
        Card(new(60,190,520,560),false);
        DrawRect(new(60,190,76,84),route.Color);
        Text(route.Number,72,249,34);
        Text(route.Name,156,226,20);
        Text(route.Chinese,156,252,14,_muted);
        Text($"{route.Path.Length/1000:0.00} km   •   {route.Stops.Count} stops   •   {route.Difficulty}",80,304,14,_mint);
        Text("STOPS IN ORDER",80,340,12,_mint);
        for(int i=0;i<route.Stops.Count;i++)
        {
            var stop=route.Stops[i];float y=368+i*26;
            Text($"{i+1}",84,y,14,_mint);
            Text(stop.Name+"   "+stop.Chinese,110,y,15,i==route.Stops.Count-1?_paper:_muted);
            Text($"{stop.Distance-route.Start:0} m",490,y,13,_muted);
        }
        Text("CAMERA",80,600,12,_mint);
        Text(Game.BriefingCab?"C   Right-hand cab":"C   Chase camera",80,626,16);
        Text("Stop in the green bay, align with the kerb and press E.",80,666,13,_muted);
        Text("Close the doors before you pull away. The last stop ends the trip.",80,688,13,_muted);
        Text("ESC   Back to routes",80,726,13,_muted);
        DrawRect(StartButton,_mint);
        Text("ENTER   Start driving",StartButton.Position.X+20,StartButton.Position.Y+34,19,new Color("12201f"));
    }

    private void DrawRouteOverlay(ServiceRoute route)
    {
        var line=route.Path.Points.Select(MapPoint).ToArray();
        DrawPolyline(line,new Color(0,0,0,.5f),9,true);
        DrawPolyline(line,route.Color,5,true);
        DrawCircle(line[0],6,_paper);
        for(int i=0;i<route.Stops.Count;i++)
        {
            var p=MapPoint(route.Path.At(route.Stops[i].Distance));
            DrawCircle(p,10,_panel);DrawCircle(p,8,i==route.Stops.Count-1?_mint:_paper);
            string label=$"{i+1}";
            DrawString(_font,p+new Vector2(-_font.GetStringSize(label,HorizontalAlignment.Left,-1,11).X/2,4),label,HorizontalAlignment.Left,-1,11,new Color("12201f"));
        }
        var end=MapPoint(route.Path.At(route.Stops[^1].Distance));
        Text(route.Stops[^1].Name.ToUpper(),end.X+14,end.Y-10,12,_paper);
    }

    private void DrawTurnBanner(float distance)
    {
        if(!Game.NearRoute(distance,20) || Game.Route.Path.NextTurn(distance,220) is not { } turn)return;
        float metres=Mathf.Max(0,turn.Distance-distance);float side=turn.Direction>0?-1:1;
        Panel(540,28,360,64);
        var c=new Vector2(580,60);
        DrawRect(new(c.X-(side<0?2:10),c.Y-3,12,6),_mint);
        DrawColoredPolygon(new[]{c+new Vector2(16*side,0),c+new Vector2(2*side,-12),c+new Vector2(2*side,12)},_mint);
        Text($"TURN {(turn.Direction>0?"LEFT":"RIGHT")}   {(metres<10?"NOW":$"{metres:0} m")}",612,55,15);
        Text(turn.Street==""?"Follow the route line":TitleCase(turn.Street),612,79,13,_muted);
    }

    private void DrawResults()
    {
        var route=Game.Route;
        DrawRect(new(0,0,1440,900),new Color(.03f,.08f,.08f,.7f));
        Panel(370,92,700,720);
        Text(Game.Abandoned?"ROUTE ENDED EARLY":"END OF THE LINE",405,136,14,_mint);
        Text(Game.Abandoned?$"{route.Number} stopped short of the terminus.":$"Welcome to {route.Stops[^1].Name}.",405,182,30);
        Text($"{route.Number}   {route.Name}",405,214,16,_muted);
        var served=Game.StopLog.Where(s=>!s.Missed).ToList();
        float speed=Game.Elapsed>1?Game.TripDistance/Game.Elapsed*3.6f:0;
        var stats=new (string Label,string Value)[]{
            ("JOURNEY TIME",Clock(Game.Elapsed)),("DISTANCE",$"{Game.TripDistance/1000:0.00} km"),
            ("AVERAGE SPEED",$"{speed:0} km/h"),("STOPS SERVED",$"{served.Count} / {route.Stops.Count}"+(Game.StopsMissed>0?$"   ({Game.StopsMissed} missed)":"")),
            ("PASSENGERS CARRIED",$"{Game.Passengers}"),("BAY ACCURACY",served.Count>0?$"{served.Average(s=>s.Offset):0.0} m from the mark":"—"),
            ("CONTACTS",$"{Game.TripContacts}"),("RED LIGHTS CROSSED",$"{Game.TripRedLights}")};
        for(int k=0;k<stats.Length;k++)
        {
            float x=405+k%2*330,y=262+k/2*58;
            Text(stats[k].Label,x,y,12,_muted);
            Text(stats[k].Value,x,y+27,21,k>=6 && stats[k].Value!="0"?new Color("f2b16c"):_paper);
        }
        DrawRect(new(405,494,630,1),new Color(.84f,.90f,.83f,.18f));
        foreach(var (label,x) in new[]{("STOP",405f),("ARRIVED",720f),("BAY",830f),("BOARDED",930f)})Text(label,x,518,12,_mint);
        for(int j=0;j<Game.StopLog.Count && j<9;j++)
        {
            var stop=Game.StopLog[j];float y=546+j*25;
            Text($"{j+1}   {stop.Name}",405,y,14,stop.Missed?_muted:_paper);
            if(stop.Missed){Text("missed",720,y,14,new Color("f2b16c"));continue;}
            Text(Clock(stop.Time),720,y,14,_paper);
            Text($"{stop.Offset:0.0} m",830,y,14,_paper);
            Text($"{stop.Boarded}",930,y,14,_paper);
        }
        Text("R   Drive again",405,784,18,_mint);
        Text("ENTER   Choose another route",620,784,18,_mint);
    }
}
