using Godot;
using System;
using System.Collections.Generic;
using System.Linq;

public partial class Main
{
    private readonly List<(Vector3 P,Vector3 F,float Width,float Length,bool Lane)> _roadPaintChecks = new();
    private readonly List<(Vector3 Center,Vector3 P,Vector3 F)> _arrowChecks = new();
    private int _roadArrows, _junctionBoxes;

    private static bool MarkingOverlaps(Vector3 p,Vector3 f,float width,float length,
        Vector3 center,Vector3 axis,float halfWidth,float back,float front)
    {
        var right=axis.Cross(Vector3.Up);var r=f.Cross(Vector3.Up);var delta=p-center;
        float along=Mathf.Abs(f.Dot(axis))*length/2+Mathf.Abs(r.Dot(axis))*width/2;
        float across=Mathf.Abs(f.Dot(right))*length/2+Mathf.Abs(r.Dot(right))*width/2;
        return Mathf.Abs(delta.Dot(right))<halfWidth+across && delta.Dot(axis)+along>back && delta.Dot(axis)-along<front;
    }

    private bool ClearOfCrossingPaint(Vector3 p,Vector3 f,float width,float length)
    {
        foreach(var signal in _signals)
            if(MarkingOverlaps(p,f,width,length,signal.Stop,signal.Forward,signal.Width/2+.3f,-.7f,6.3f))return false;
        foreach(float distance in new[]{110f,740f})
            if(MarkingOverlaps(p,f,width,length,Map.At(distance),Map.Forward(distance),10,-7.6f,2.5f))return false;
        return true;
    }

    private bool PaintOnRoad(Vector3 p,Vector3 f,float width,float length)
    {
        // A merged carriageway can taper at a fork; keep the whole marking on its actual surface.
        for(int x=-1;x<=1;x++)for(int z=-1;z<=1;z++)
            if(Map.ClearOfRoads(p+f.Cross(Vector3.Up)*x*width/2+f*z*length/2,-.2f))return false;
        return true;
    }

    private bool LanePaintClear(Vector3 p,Vector3 f,float width,float length,int road)
    {
        if(!ClearOfCrossingPaint(p,f,width,length) || !PaintOnRoad(p,f,width,length))return false;
        foreach(var stop in Map.Stops)
            if(MarkingOverlaps(p,f,width,length,Map.At(stop.Distance,-7.3f),Map.Forward(stop.Distance),2.6f,-9,9))return false;
        return Map.CanPaintLane(p,f,road) && Map.CanPaintLane(p-f*length/2,f,road) && Map.CanPaintLane(p+f*length/2,f,road);
    }

    private void LaneStripe(Vector3 p,Vector3 f,float width,float length,int road,string color="e3dfc9")
    {
        if(!LanePaintClear(p,f,width,length,road))return;
        Stripe(p,f,width,length,color);
        if(SelfTest)_roadPaintChecks.Add((p,f,width,length,true));
    }

    private void RoadArrows(Vector3 center,Vector3 forward,float width,int road)
    {
        int lanes=RoadMap.LanesPerDirection(width);
        foreach(int direction in new[]{-1,1})
            for(int lane=0;lane<lanes;lane++)
            {
                var f=forward*direction;var right=f.Cross(Vector3.Up);
                var p=center-right*(lane+.5f)*width/(lanes*2);
                if(!LanePaintClear(p,f,1.5f,4.5f,road))continue;
                Stripe(p-f*.7f,f,.25f,3.1f,"e3dfc9");
                p.Y=.072f;
                Triangle(_paint["e3dfc9"],p+f*.6f-right*.75f,p+f*2.25f,p+f*.6f+right*.75f);
                _roadArrows++;
                if(SelfTest) { _roadPaintChecks.Add((p,f,1.5f,4.5f,true)); _arrowChecks.Add((center,p,f)); }
            }
    }

    private void BuildRoadDetails()
    {
        for(float distance=85;distance<Map.Length-30;distance+=95)
            RoadArrows(Map.At(distance),Map.Forward(distance),20,-1);
        foreach(var (name,p,f,id,width) in Map.LaneSamples(95))
            if(width>=16)RoadArrows(p,f,width,id);

        // ponytail: three authored box junctions; use surveyed polygons if exact junction layouts are needed.
        foreach(float distance in new[]{350f,600f,920f})
        {
            var center=Map.At(distance);var forward=Map.Forward(distance);var right=forward.Cross(Vector3.Up);
            const float halfWidth=9.1f,halfLength=5;
            void Line(Vector2 a,Vector2 b)
            {
                var start=center+right*a.X+forward*a.Y;var end=center+right*b.X+forward*b.Y;
                var p=(start+end)/2;var f=(end-start).Normalized();float length=start.DistanceTo(end);
                Stripe(p,f,.15f,length,"e5bd58");
                if(SelfTest)_roadPaintChecks.Add((p,f,.15f,length,false));
            }
            foreach(int side in new[]{-1,1})
            {
                Line(new(-halfWidth,side*halfLength),new(halfWidth,side*halfLength));
                Line(new(side*halfWidth,-halfLength),new(side*halfWidth,halfLength));
                for(float c=-12;c<=12;c+=3)
                {
                    float a=Mathf.Max(-halfWidth,Mathf.Min((-halfLength-c)*side,(halfLength-c)*side));
                    float b=Mathf.Min(halfWidth,Mathf.Max((-halfLength-c)*side,(halfLength-c)*side));
                    if(b-a>.1f)Line(new(a,side*a+c),new(b,side*b+c));
                }
            }
            _junctionBoxes++;
        }
        foreach(var stop in Map.Stops)
        {
            var text=Label(this,"BUS\nSTOP",Map.At(stop.Distance,-7.3f)+Vector3.Up*.078f,.022f,64);
            text.Rotation=new(-Mathf.Pi/2,Map.Heading(stop.Distance),0);
            text.Scale=new(1,1.55f,1);text.Modulate=new("e5bd58");
        }
        GD.Print($"ANTILA_ROAD_DETAILS: {_roadArrows} lane arrows, {_junctionBoxes} yellow boxes, {Map.Stops.Count} labelled bus bays");
    }

    private void CheckRoadMarkings()
    {
        if(_crossingStudChecks.Count<1000)throw new Exception("Missing crossing boundary studs");
        foreach(var (p,f) in _crossingStudChecks)
            foreach(int x in new[]{-1,1})foreach(int z in new[]{-1,1})
                if(Map.ClearOfRoads(p+f.Cross(Vector3.Up)*x*.15f+f*z*.15f,-.15f))
                    throw new Exception("Crossing stud extends onto pavement at "+p);
        foreach(var signal in _signals)
        {
            var r=signal.Forward.Cross(Vector3.Up);var p=signal.Stop-r*signal.Width/4;
            foreach(int x in new[]{-1,1})foreach(int z in new[]{-1,1})
                if(Map.ClearOfRoads(p+r*x*(signal.Width/2-.3f)/2+signal.Forward*z*.175f,-.02f))
                    throw new Exception("Stop line extends onto pavement at "+signal.Name);
        }
        var chatham=Map.NearestStreet(new(390,0,-545),"CHATHAM ROAD SOUTH");
        var combined=Map.Carriageway(chatham.Point,chatham.Forward,chatham.Name);
        var reversed=Map.Carriageway(chatham.Point,-chatham.Forward,chatham.Name);
        if(combined.Width<26 || combined.Width>40 || combined.Center.DistanceTo(reversed.Center)>.01f ||
            Mathf.Abs(combined.Width-reversed.Width)>.01f || combined.Owner!=reversed.Owner)
            throw new Exception("Parallel Chatham segments must produce one direction-independent carriageway");
        GD.Print($"ANTILA_CARRIAGEWAY_OK: Chatham width {combined.Width:0.0} m, {RoadMap.LanesPerDirection(combined.Width)*2} lanes, consistent centre in both directions");
        if(_roadArrows<30 || _junctionBoxes!=3 || _roadPaintChecks.Count<500)
            throw new Exception("Missing road detail coverage");
        foreach(var (p,f,width,length,lane) in _roadPaintChecks)
        {
            if(!ClearOfCrossingPaint(p,f,width,length))throw new Exception("Road paint overlaps crossing/stop line at "+p);
            foreach(int x in new[]{-1,1})foreach(int z in new[]{-1,1})
                if(Map.ClearOfRoads(p+f.Cross(Vector3.Up)*x*width/2+f*z*length/2,-.15f))
                    throw new Exception("Road paint leaves asphalt at "+p);
            if(lane && Map.Stops.Any(s=>MarkingOverlaps(p,f,width,length,Map.At(s.Distance,-7.3f),Map.Forward(s.Distance),2.6f,-9,9)))
                throw new Exception("Lane guides overlap bus bay at "+p);
        }
        foreach(var (center,p,f) in _arrowChecks)
            if((p-center).Dot(f.Cross(Vector3.Up))>=0)throw new Exception("Arrow faces against left-hand traffic");
        for(int i=0;i<_arrowChecks.Count;i++)for(int j=0;j<i;j++)
        {
            var a=_arrowChecks[i];var b=_arrowChecks[j];
            if(a.P.DistanceSquaredTo(b.P)<25 &&
                MarkingOverlaps(a.P,a.F,1.5f,4.5f,b.P,b.F,.75f,-2.25f,2.25f) &&
                MarkingOverlaps(b.P,b.F,1.5f,4.5f,a.P,a.F,.75f,-2.25f,2.25f))
                throw new Exception("Duplicate arrow footprints at "+a.P);
        }
        foreach(var stop in Map.Stops)
            if(!ClearOfCrossingPaint(Map.At(stop.Distance,-7.3f),Map.Forward(stop.Distance),4.4f,16))
                throw new Exception("Bus bay obstructs pedestrian crossing: "+stop.Name);
        var approach=_signals.First();
        if(LanePaintClear(approach.Stop-approach.Forward.Cross(Vector3.Up)*5,approach.Forward,.14f,3,-1))
            throw new Exception("Stop line must interrupt lane guides");
        using var mask=((Texture2D)_terrain.GetShaderParameter("surface_mask").AsGodotObject()).GetImage();
        bool feathered=false;
        for(float lane=9.5f;lane<10.5f;lane+=.05f)
        {
            var p=Map.At(250,lane);var uv=(new Vector2(p.X,p.Z)-Map.Bounds.Position)/Map.Bounds.Size;
            float coverage=mask.GetPixel((int)(uv.X*mask.GetWidth()),(int)(uv.Y*mask.GetHeight())).R;
            feathered|=coverage>0 && coverage<1;
        }
        if(!feathered)throw new Exception("Road mask edge must retain fractional pixel coverage");
        GD.Print($"ANTILA_ROADS_OK: {_roadPaintChecks.Count} markings on asphalt; {_crossingStudChecks.Count} crossing studs inside kerbs; crossing/bay clearance; left-hand arrows; all bus bays clear");
    }
}
