using Godot;
using System;
using System.Collections.Generic;
using System.Linq;

public partial class Hud : Control
{
    public Main Game = null!;
    private readonly SystemFont _font = new() { FontNames = new[] { "Avenir Next", "Noto Sans", "sans-serif" } };
    private readonly Color _paper = new("f4edda"), _muted = new("afc0b8"), _mint = new("95dbc0");
    private readonly Color _panel = new(.047f,.095f,.102f,.94f);
    private SubViewport _miniMap = null!, _fullMap = null!;

    public override void _Ready()
    {
        MouseFilter=MouseFilterEnum.Ignore;SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect);
        _miniMap=BuildMapRoads(false);_fullMap=BuildMapRoads(true);
        BuildRouteMap();
    }

    public bool OncomingLaneWarning
    {
        get
        {
            var p=Game.Bus.GlobalPosition;var projection=Game.Map.Project(p);
            float heading=(-Game.Bus.GlobalBasis.Z).Dot(Game.Map.Forward(projection.Distance));
            float lane=projection.Lateral*Mathf.Sign(heading);
            return Game.NoticeTime<=0 && !Game.Complete && Mathf.Abs(heading)>.5f && lane>1 && lane<10 &&
                NearServiceCorridor(projection.Distance,12) && !Game.Map.NearSideRoad(p,12);
        }
    }

    // Lateral projection alone extends the Nathan Road strip beyond its endpoints.
    private bool NearServiceCorridor(float distance,float clearance)
        => Game.Bus.GlobalPosition.DistanceTo(Game.Map.At(distance))<clearance;

    public string ServiceInstruction
    {
        get
        {
            if(Game.Complete)return "";
            var bus=Game.Bus;var route=Game.Route;var projection=route.Path.Project(bus.GlobalPosition);
            var stop=route.Stops[Game.StopIndex];
            float metres=Mathf.Max(0,stop.Distance-projection.Distance);
            string street=TitleCase(route.Path.StreetAt(projection.Distance));
            return !Game.NearRoute(projection.Distance,20) ? $"Exploring • M map • R returns to {route.Number}" :
                Game.IsAtStop() ? bus.DoorsOpen ? "Boarding passengers…" : "Stop & press E to open doors" :
                projection.Distance>stop.Distance+7 ? "Stop missed — reverse carefully or press R" :
                $"{metres:0} m   •   "+(street==""?"Follow the route line":$"Keep left on {street}");
        }
    }

    private static Rect2 MapArea(bool expanded)=>expanded?new(135,190,1170,540):new(1106,607,288,218);
    public static Rect2 ExpandedMapArea=>MapArea(true);

    // Expanded-map stop labels keep their 600 px top; long routes rise only as far as needed to end inside the map, above the footer.
    public static float MapStopLabelY(int count,int i)
    {
        float spacing=count>4?24:28;
        return Mathf.Min(600,MapArea(true).End.Y-18-(count-1)*spacing)+(count-1-i)*spacing;
    }

    private (Vector2 Origin,float Scale) MapTransform(bool expanded)
    {
        var area=MapArea(expanded);
        var bounds=Game.HarbourBounds;
        float scale=Mathf.Min(area.Size.X/bounds.Size.X,area.Size.Y/bounds.Size.Y);
        return (area.GetCenter()-bounds.Size*scale/2-bounds.Position*scale,scale);
    }

    private SubViewport BuildMapRoads(bool expanded)
    {
        // The offline map is immutable; virtual HUD coordinates also survive window resizing.
        var (origin,scale)=MapTransform(expanded);
        Vector2 Point(Vector3 p)=>origin+new Vector2(p.X,p.Z)*scale;
        var lines=new[]{new List<Vector2>(),new List<Vector2>(),new List<Vector2>()};
        foreach(var road in Game.Map.SideRoads)
            for(int i=1;i<road.Points.Count;i++)
            { lines[0].Add(Point(road.Points[i-1]));lines[0].Add(Point(road.Points[i])); }
        foreach(var road in Game.HarbourRoads)
            for(int i=0;i<road.Points.Count-1;i++)
            {
                if(road.Tunnel && i%5>2)continue;
                var batch=lines[road.Tunnel?2:1];batch.Add(Point(road.Points[i]));batch.Add(Point(road.Points[i+1]));
            }
        var roads=new[]{lines[0].ToArray(),lines[1].ToArray(),lines[2].ToArray()};
        var coast=new List<Vector2>();
        foreach(var line in Game.KowloonCoastline.Concat(Game.IslandCoastline))for(int i=1;i<line.Length;i++)
        { coast.Add(origin+line[i-1]*scale);coast.Add(origin+line[i]*scale); }
        var coastPoints=coast.ToArray();
        var area=MapArea(expanded);
        var viewport=new SubViewport {Size=(Vector2I)area.Size,TransparentBg=true,Disable3D=true,
            RenderTargetUpdateMode=SubViewport.UpdateMode.Once};
        AddChild(viewport);
        var canvas=new Control();viewport.AddChild(canvas);
        canvas.Draw+=()=>
        {
            var pixels=(Vector2)viewport.Size/area.Size;
            canvas.DrawSetTransform(-area.Position*pixels,0,pixels);
            canvas.DrawMultiline(coastPoints,new Color("72a9aa"),expanded?1.8f:1.2f,true);
            canvas.DrawMultiline(roads[0],new Color("526e67"),expanded?1.6f:1.5f,true);
            canvas.DrawMultiline(roads[1],new Color("d4b26e"),expanded?1.35f:1.3f,true);
            canvas.DrawMultiline(roads[2],new Color("7ed8dc"),expanded?3:2,true);
        };
        return viewport;
    }

    private void Text(string value,float x,float y,int size,Color? color=null)
        => DrawString(_font,new(x,y),value,HorizontalAlignment.Left,-1,size,color??_paper);

    private void Panel(float x,float y,float w,float h)
    {
        var style=new StyleBoxFlat {BgColor=_panel,CornerRadiusTopLeft=5,CornerRadiusTopRight=5,CornerRadiusBottomLeft=5,CornerRadiusBottomRight=5};
        DrawStyleBox(style,new(x,y,w,h));
    }

    private void Chip(string key,string caption,float x,float y)
    {
        DrawRect(new(x,y-19,30,26),new Color(.84f,.90f,.83f,.13f));
        Text(key,x+(key.Length>1?2:8),y,key.Length>1?11:14);
        Text(caption,x+38,y,14,_muted);
    }

    public override void _Draw()
    {
        if(Game.Bus==null)return;
        var viewport=GetViewportRect().Size;
        DrawSetTransform(Vector2.Zero,0,new(viewport.X/1440,viewport.Y/900));
        if(Game.Menu){DrawRouteSelect();return;}
        var bus=Game.Bus;
        var projection=Game.Route.Path.Project(bus.GlobalPosition);
        string street=Game.HarbourDrive || !Game.MapOpen?Game.CurrentStreet():"";
        Panel(30,28,382,80);
        DrawRect(new(30,28,76,80),Game.HarbourDrive?new Color("c75236"):Game.Route.Color);
        Text(Game.HarbourDrive?"HK":Game.Route.Number,Game.HarbourDrive?34:44,81,Game.HarbourDrive?26:37);
        Text(Game.HarbourDrive?"FREE DRIVE":Game.Route.Area,123,61,22);
        Text(Game.HarbourDrive?"KOWLOON · WEST COAST · HK ISLAND":Game.Route.Heading,124,87,13,_muted);
        Panel(1118,28,292,60);
        Text("ANTILA  /  BUS DRIVING",1135,51,16);
        Text("10:24 AM     •     HONG KONG",1135,73,12,_muted);
        if(Game.HarbourDrive)
        {
            Panel(30,121,382,95);Text("FREE DRIVE  /  REAL-SCALE ALIGNMENT",48,149,12,_mint);
            Text(street,48,178,15);Text($"Follow signs • M map • R returns to {Game.Route.Number}",48,200,14,_muted);
        }
        else if(!Game.Complete)
        {
            var stop=Game.Route.Stops[Game.StopIndex];
            Panel(30,121,382,113);
            Text($"NEXT STOP   {Game.StopIndex+1} / {Game.Route.Stops.Count}",48,149,12,_mint);
            Text(stop.Name,48,180,25);
            Text(ServiceInstruction,48,208,14,_muted);
            if(Game.Boarding>0)
            {
                DrawRect(new(48,221,346,3),new Color("354b48"));
                DrawRect(new(48,221,346*Game.Boarding/4,3),_mint);
            }
        }
        Panel(30,733,278,134);
        var (signal,signalDistance)=Game.NextSignal(bus.GlobalTransform);
        if(signal!=null && !Game.Complete)
        {
            Panel(30,247,382,78);
            for(int i=0;i<3;i++)
            {
                bool on=i==0?signal.Aspect is SignalAspect.Red or SignalAspect.RedAmber:
                    i==1?signal.Aspect is SignalAspect.Amber or SignalAspect.RedAmber:signal.Aspect==SignalAspect.Green;
                DrawCircle(new(53,264+i*22),7,on?new Color(new[]{"ff6551","ffc453","71edac"}[i]):new Color("34423e"));
            }
            string action=signal.Aspect switch {SignalAspect.Green=>"PROCEED IF CLEAR",SignalAspect.Amber=>"STOP IF SAFE",
                SignalAspect.RedAmber=>"WAIT • PREPARE TO GO",_=>"STOP AT THE WHITE LINE"};
            Text(action,76,274,13,_paper);
            Text($"{signalDistance:0} m  •  {signal.Name}",76,304,13,_muted);
        }
        Text($"{bus.Kmh:00}",48,800,57);
        Text("km/h",140,798,17,_muted);
        DrawCircle(new(262,770),23,_paper);
        DrawArc(new(262,770),23,0,Mathf.Tau,48,new Color("c75236"),4,true);
        Text("50",247,778,20,new Color("253735"));
        Text(bus.Reverse?"R":"D",51,837,23,_mint);
        Text(bus.DoorsOpen?"DOORS OPEN":"DOORS CLOSED",87,834,12,bus.DoorsOpen?_mint:_muted);
        Text($"{Game.Passengers} passengers",87,852,12,_muted);
        if(!Game.MapOpen)DrawMap(projection.Distance,street);
        Panel(330,823,722,44);
        Chip("W","Throttle",346,851);Chip("S","Brake",464,851);Chip("A/D","Steer",568,851);
        Chip("E","Doors",684,851);Chip("C","Camera",788,851);Chip("Q","Gear",912,851);
        Text("SPACE Handbrake    H Horn    V "+(AudioServer.IsBusMute(0)?"Unmute":"Sound")+"    M Map & free drives    "+(Game.HarbourDrive?"TAB Routes":"TAB End route")+"    R Restart    ESC Pause",382,889,11,_paper);
        if(!Game.HarbourDrive && !Game.Complete && !Game.MapOpen)DrawTurnBanner(projection.Distance);
        if(Game.NoticeTime>0 && !Game.Complete)
        {
            float x=Game.CabView?438:350;
            float y=Game.CabView?130:753;
            Panel(x,y,Game.CabView?654:702,50);
            Text(Game.Notice,x+20,y+31,16,_paper);
        }
        else if(OncomingLaneWarning)
        {
            Panel(420,757,565,46);
            Text("ONCOMING LANE  —  Drive on the left",459,786,17,new Color("f2b16c"));
        }
        Text("Roads / buildings / coast © HKSAR Govt · TD / LandsD · 15 Oct 2026",31,889,9,_muted);
        if(Game.Complete)DrawResults();
        else if(Game.Paused)
        {
            DrawRect(new(0,0,1440,900),new Color(.03f,.08f,.08f,.65f));
            Panel(460,282,520,302);
            Text("TAKE A BREATHER",495,330,14,_mint);
            Text("Service paused.",495,377,32);
            Text("Your bus is safely paused.",495,417,17,_muted);
            Text("ESC   Resume     R   Restart",495,462,19,_paper);
            Text(Game.HarbourDrive?"TAB   Back to route select":$"TAB   End {Game.Route.Number} and see your stats",495,496,15,_paper);
            Text("W / S  Throttle / brake     A / D  Steer",495,530,14,_muted);
            Text("E  Doors    C  Camera    Q  Gear    H  Horn",495,557,14,_muted);
        }
        if(Game.MapOpen)DrawMap(projection.Distance,street,true);
    }

    private void DrawMap(float distance,string street,bool expanded=false)
    {
        if(expanded)
        {
            DrawRect(new(0,0,1440,900),new Color(.03f,.08f,.08f,.78f));
            Panel(80,100,1280,700);
            Text("KOWLOON · TSUEN WAN · WEST COAST · HONG KONG ISLAND",112,147,24,_paper);
            Text("M / ESC  Close map • Driving paused",995,146,15,_muted);
        }
        else
        {
            Panel(1090,553,320,314);
            Text("HONG KONG   /   M MAP",1109,583,14,_paper);
        }
        var bounds=Game.HarbourBounds;
        var (origin,scale)=MapTransform(expanded);
        Vector2 Point(Vector3 p)=>origin+new Vector2(p.X,p.Z)*scale;
        Text("N ↑",expanded?1292:1363,expanded?179:606,13,_mint);
        var area=MapArea(expanded);var map=expanded?_fullMap:_miniMap;
        var pixels=(Vector2I)(area.Size*GetViewportRect().Size/new Vector2(1440,900)).Ceil();
        if(map.Size!=pixels)
        {
            map.Size=pixels;map.GetChild<Control>(0).QueueRedraw();
            map.RenderTargetUpdateMode=SubViewport.UpdateMode.Once;
        }
        DrawTextureRect(map.GetTexture(),area,false);
        var path=Game.Route.Path;
        var line=path.Points.Select(Point).ToArray();
        int reached=path.Along.FindLastIndex(a=>a<distance);
        DrawPolyline(line,new Color("5e897c"),expanded?6:3,true);
        if(reached>0)DrawPolyline(line[..(reached+1)],_mint,expanded?3:2,true);
        var stops=Game.Route.Stops;
        for(int i=0;i<stops.Count;i++)
        {
            var stop=stops[i];var p=Point(path.At(stop.Distance));
            DrawCircle(p,expanded?6:4,i<Game.StopIndex?_mint:_paper);
            if(expanded)
            {
                var labelAt=new Vector2(1085,MapStopLabelY(stops.Count,i));
                DrawLine(p,labelAt+new Vector2(-8,-4),new Color(.55f,.66f,.62f,.6f),1,true);
                Text($"{Game.Route.Number} · {stop.Name}",labelAt.X,labelAt.Y,13,i==Game.StopIndex?_paper:_muted);
            }
        }
        if(expanded)
        {
            foreach(var (label,at,offset) in new[]{
                ("SHAM TSENG",new Vector3(-11720,0,-7940),new Vector2(-100,65)),
                ("TING KAU",new Vector3(-9400,0,-8260),new Vector2(-110,50)),
                ("TSUEN WAN",new Vector3(-6250,0,-8870),new Vector2(-150,-5)),
                ("KWAI CHUNG",new Vector3(-4630,0,-7300),new Vector2(80,-10)),
                ("LAI KING",new Vector3(-4400,0,-6250),new Vector2(-202,-17)),
                ("MEI FOO",new Vector3(-3500,0,-5100),new Vector2(-239,-29)),
                ("LAI CHI KOK",new Vector3(-3370,0,-4830),new Vector2(-244,-5)),
                ("CHEUNG SHA WAN",new Vector3(-2190,0,-4770),new Vector2(80,-50)),
                ("SHAM SHUI PO",new Vector3(-1180,0,-4000),new Vector2(-255,-12)),
                ("TAI KOK TSUI",new Vector3(-1000,0,-2850),new Vector2(-245,0)),
                ("WEST KOWLOON",new Vector3(-1420,0,-870),new Vector2(-265,-8)),
                ("MONG KOK",new Vector3(-300,0,-2930),new Vector2(120,-5)),
                ("YAU MA TEI",new Vector3(-140,0,-1940),new Vector2(135,0)),
                ("JORDAN",new Vector3(-70,0,-1110),new Vector2(205,-20)),
                ("TSIM SHA TSUI",new Vector3(-180,0,-470),new Vector2(-200,10)),
                ("TSIM SHA TSUI EAST",new Vector3(590,0,-460),new Vector2(170,62)),
                ("CROSS-HARBOUR TUNNEL · 1.86 km",new Vector3(975,0,400),new Vector2(100,55)),
                ("CENTRAL",new Vector3(-1700,0,1680),new Vector2(-125,32)),
                ("ADMIRALTY",new Vector3(-850,0,1680),new Vector2(-65,32)),
                ("WAN CHAI",new Vector3(150,0,1680),new Vector2(35,32)),
                ("CAUSEWAY BAY",new Vector3(1570,0,1680),new Vector2(65,32))})
            {
                var p=Point(at);var labelAt=p+offset;
                float width=_font.GetStringSize(label,HorizontalAlignment.Left,-1,13).X;
                DrawLine(p,labelAt+new Vector2(offset.X<0?width+6:-6,-4),new Color(.55f,.66f,.62f,.6f),1,true);
                Text(label,labelAt.X,labelAt.Y,13,_muted);
            }
            Text($"Approx. {bounds.Size.X/1000:0.00} km east–west  ×  {bounds.Size.Y/1000:0.00} km north–south",112,759,16,_paper);
            Text("T Tunnel • I Island • J Central • K Nathan • L West • N Lai Chi Kok • B Kwai Chung • U Tsuen Wan • O Coast (stopped)",112,784,13,_mint);
        }
        var bus=Point(Game.Bus.GlobalPosition);
        DrawCircle(bus,9,_panel);
        float yaw=Game.Bus.Rotation.Y;
        var f=new Vector2(-Mathf.Sin(yaw),-Mathf.Cos(yaw));
        var r=new Vector2(-f.Y,f.X);
        DrawColoredPolygon(new[]{bus+f*10,bus-f*6+r*6,bus-f*6-r*6},new Color("ffd084"));
        if(!expanded)Text(street,1109,850,12,_muted);
    }
}
