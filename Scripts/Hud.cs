using Godot;
using System;

public partial class Hud : Control
{
    public Main Game = null!;
    private readonly SystemFont _font = new() { FontNames = new[] { "Avenir Next", "Noto Sans", "sans-serif" } };
    private readonly Color _paper = new("f4edda"), _muted = new("afc0b8"), _mint = new("95dbc0");
    private readonly Color _panel = new(.047f,.095f,.102f,.94f);

    public override void _Ready() { MouseFilter=MouseFilterEnum.Ignore; SetAnchorsAndOffsetsPreset(LayoutPreset.FullRect); }

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
        var bus=Game.Bus;
        var projection=Game.Map.Project(bus.GlobalPosition);
        Panel(30,28,382,80);
        DrawRect(new(30,28,76,80),new Color("c75236"));
        Text("H1",44,81,37);
        Text("KOWLOON",123,61,22);
        Text("TSIM SHA TSUI  →  JORDAN",124,87,13,_muted);
        Panel(1118,28,292,60);
        Text("ANTILA  /  BUS DRIVING",1135,51,16);
        Text("10:24 AM     •     HONG KONG",1135,73,12,_muted);
        if(!Game.Complete)
        {
            var stop=Game.Map.Stops[Game.StopIndex];
            float metres=Mathf.Max(0,stop.Distance-projection.Distance);
            Panel(30,121,382,113);
            Text($"NEXT STOP   {Game.StopIndex+1} / 3",48,149,12,_mint);
            Text(stop.Name,48,180,25);
            string instruction=Mathf.Abs(projection.Lateral)>20 ? "Exploring Kowloon • M map / R restart" : Game.IsAtStop() ? bus.DoorsOpen ? "Boarding passengers…" : "Stop & press E to open doors" :
                projection.Distance>stop.Distance+7 ? "Stop missed — reverse carefully or press R" : $"{metres:0} m   •   Keep left on Nathan Road";
            Text(instruction,48,208,14,_muted);
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
        if(Game.CabView)
        {
            Text($"{bus.Kmh:00}   km/h",661,678,20,_mint);
            Text(bus.Reverse?"R":"D",786,678,20,_mint);
        }
        if(!Game.MapOpen)DrawMap(projection.Distance);
        Panel(330,823,722,44);
        Chip("W","Throttle",346,851);Chip("S","Brake",464,851);Chip("A/D","Steer",568,851);
        Chip("E","Doors",684,851);Chip("C","Camera",788,851);Chip("Q","Gear",912,851);
        Text("SPACE  Handbrake    H  Horn    V  "+(AudioServer.IsBusMute(0)?"Unmute":"Sound")+"    M  Map    R  Restart    ESC  Pause",382,889,12,_paper);
        if(Game.NoticeTime>0 && !Game.Complete)
        {
            float x=Game.CabView?438:350;
            float y=Game.CabView?130:753;
            Panel(x,y,Game.CabView?654:702,50);
            Text(Game.Notice,x+20,y+31,16,_paper);
        }
        else if(projection.Lateral>1 && projection.Lateral<10 && !Game.Map.NearSideRoad(bus.GlobalPosition,12) && !Game.Complete)
        {
            Panel(420,757,565,46);
            Text("ONCOMING LANE  —  Drive on the left",459,786,17,new Color("f2b16c"));
        }
        Text("Map © HKSAR Government · Transport Dept / DATA.GOV.HK · Lands Dept / CSDI Portal",31,889,9,_muted);
        if(Game.Paused || Game.Complete)
        {
            DrawRect(new(0,0,1440,900),new Color(.03f,.08f,.08f,.65f));
            Panel(460,282,520,302);
            Text(Game.Complete?"END OF THE LINE":"TAKE A BREATHER",495,330,14,_mint);
            Text(Game.Complete?"Welcome to Jordan.":"Service paused.",495,377,32);
            Text(Game.Complete?$"3 stops served  •  {Game.Passengers} passengers aboard":"Your bus is safely paused.",495,417,17,_muted);
            if(Game.Complete)
            {
                Text($"Journey   {(int)Game.Elapsed/60:00}:{(int)Game.Elapsed%60:00}     Contacts   {bus.Collisions}",495,453,17,_paper);
                Text($"Red lights crossed   {Game.RedLightCrossings}",495,482,17,_paper);
                Text("R   Drive again",495,530,20,_mint);
            }
            else
            {
                Text("ESC   Resume     R   Restart",495,462,19,_paper);
                Text("W / S  Throttle / brake     A / D  Steer",495,505,14,_muted);
                Text("E  Doors    C  Camera    Q  Gear    H  Horn",495,535,14,_muted);
            }
        }
        if(Game.MapOpen)DrawMap(projection.Distance,true);
    }

    private void DrawMap(float distance,bool expanded=false)
    {
        if(expanded)
        {
            DrawRect(new(0,0,1440,900),new Color(.03f,.08f,.08f,.78f));
            Panel(80,100,1280,700);
            Text("EXPLORE KOWLOON",112,147,24,_paper);
            Text("M / ESC  Close map • Driving paused",995,146,15,_muted);
        }
        else
        {
            Panel(1090,553,320,314);
            Text("KOWLOON   /   M MAP",1109,583,14,_paper);
        }
        var area=expanded?new Rect2(135,190,1170,540):new Rect2(1106,607,288,218);
        var bounds=Game.Map.Bounds;
        float scale=Mathf.Min(area.Size.X/bounds.Size.X,area.Size.Y/bounds.Size.Y);
        var origin=area.GetCenter()-bounds.Size*scale/2;
        Vector2 Point(Vector3 p)=>origin+(new Vector2(p.X,p.Z)-bounds.Position)*scale;
        Text("N ↑",expanded?1292:1363,expanded?179:606,13,_mint);
        foreach(var road in Game.Map.SideRoads)
            for(int i=0;i<road.Points.Count-1;i++)
                DrawLine(Point(road.Points[i]),Point(road.Points[i+1]),new Color("526e67"),expanded?3:1.5f,true);
        for(int i=0;i<Game.Map.Points.Count-1;i++)
        {
            var a=Point(Game.Map.Points[i]);var b=Point(Game.Map.Points[i+1]);
            DrawLine(a,b,new Color("5e897c"),expanded?6:3,true);
            if(i*5<distance)DrawLine(a,b,_mint,expanded?3:2,true);
        }
        for(int i=0;i<Game.Map.Stops.Count;i++)
        {
            var stop=Game.Map.Stops[i];var p=Point(Game.Map.At(stop.Distance));
            DrawCircle(p,expanded?6:4,i<Game.StopIndex?_mint:_paper);
            if(expanded)Text($"H1 · {stop.Name}",p.X+13,p.Y+5,15,i==Game.StopIndex?_paper:_muted);
        }
        if(expanded)
        {
            foreach(var (label,at) in new[]{("CANTON ROAD",new Vector3(-560,0,-600)),
                ("KOWLOON PARK",new Vector3(-310,0,-740)),("TSIM SHA TSUI EAST",new Vector3(370,0,-290)),
                ("SCIENCE MUSEUM RD",new Vector3(540,0,-770)),("JORDAN",new Vector3(-420,0,-1110))})
            {
                var p=Point(at);Text(label,p.X,p.Y,13,_muted);
            }
            Text($"{bounds.Size.X/1000:0.00} km east–west  ×  {bounds.Size.Y/1000:0.00} km north–south",112,759,16,_paper);
            Text("H1 service on Nathan Road • Side streets open for exploration",112,784,13,_mint);
        }
        var bus=Point(Game.Bus.GlobalPosition);
        DrawCircle(bus,9,_panel);
        float yaw=Game.Bus.Rotation.Y;
        var f=new Vector2(-Mathf.Sin(yaw),-Mathf.Cos(yaw));
        var r=new Vector2(-f.Y,f.X);
        DrawColoredPolygon(new[]{bus+f*10,bus-f*6+r*6,bus-f*6-r*6},new Color("ffd084"));
        if(!expanded)Text(Game.Map.NearestStreet(Game.Bus.GlobalPosition).Name,1109,850,12,_muted);
    }
}
