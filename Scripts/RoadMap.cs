using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

public sealed class RoadMap
{
    public readonly List<Vector3> Points = new();
    public readonly List<Vector3> RoadPoints = new();
    public int SourceSections { get; private set; }
    private readonly List<(int Road,string Name,Vector2 A,Vector2 B,float HalfWidth)> _segments = new();
    public readonly List<(string Name, List<Vector3> Points)> SideRoads = new();
    public readonly List<(string Name, string Chinese, float Distance, int Passengers)> Stops = new();
    public Rect2 Bounds { get; private set; }
    public float Length => (Points.Count - 1) * 5;

    public RoadMap()
    {
        using var doc = JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/nathan-road.json"));
        var bounds = doc.RootElement.GetProperty("bounds");
        Bounds = new(bounds[0].GetSingle(), bounds[1].GetSingle(),
            bounds[2].GetSingle()-bounds[0].GetSingle(), bounds[3].GetSingle()-bounds[1].GetSingle());
        foreach (var p in doc.RootElement.GetProperty("points").EnumerateArray())
            Points.Add(new(p[0].GetSingle(), 0, p[1].GetSingle()));
        foreach(var p in doc.RootElement.GetProperty("road_points").EnumerateArray())
            RoadPoints.Add(new(p[0].GetSingle(),0,p[1].GetSingle()));
        foreach (var road in doc.RootElement.GetProperty("side_roads").EnumerateArray())
        {
            var line = new List<Vector3>();
            foreach (var p in road.GetProperty("points").EnumerateArray())
                line.Add(new(p[0].GetSingle(), 0, p[1].GetSingle()));
            SideRoads.Add((road.GetProperty("name").GetString()!, line));
        }
        SourceSections=SideRoads.Count;
        JoinStreets();
        void AddSegments(int id,string name,List<Vector3> line,float width)
        {
            for(int i=0;i<line.Count-1;i++)
                if(line[i].DistanceTo(line[i+1])>.01f)
                    _segments.Add((id,name,new(line[i].X,line[i].Z),new(line[i+1].X,line[i+1].Z),width/2));
        }
        AddSegments(-1,"NATHAN ROAD",RoadPoints,20);
        for(int i=0;i<SideRoads.Count;i++)AddSegments(i,SideRoads[i].Name,SideRoads[i].Points,Width(SideRoads[i].Name));
        foreach (var s in doc.RootElement.GetProperty("stops").EnumerateArray())
            Stops.Add((s.GetProperty("name").GetString()!, s.GetProperty("zh").GetString()!,
                s.GetProperty("distance").GetSingle(), s.GetProperty("passengers").GetInt32()));
        if (Points.Count < 2 || Stops.Count == 0)
            throw new InvalidOperationException("Map needs a corridor and passenger stops.");
    }

    public Vector3 At(float distance, float lane = 0)
    {
        float index = Mathf.Clamp(distance / 5, 0, Points.Count - 1.001f);
        int i = (int)index;
        var forward = (Points[i + 1] - Points[i]).Normalized();
        return Points[i].Lerp(Points[i + 1], index - i) + forward.Cross(Vector3.Up) * lane;
    }

    public Vector3 Forward(float distance) => (At(distance + 2) - At(distance - 2)).Normalized();
    public float Heading(float distance) => Mathf.Atan2(-Forward(distance).X, -Forward(distance).Z);

    public (float Distance, float Lateral) Project(Vector3 position)
    {
        float best = float.MaxValue, along = 0, lateral = 0;
        for (int i = 0; i < Points.Count - 1; i++)
        {
            var delta = Points[i + 1] - Points[i];
            var flat = new Vector3(position.X, 0, position.Z) - Points[i];
            float t = Mathf.Clamp(flat.Dot(delta) / delta.LengthSquared(), 0, 1);
            var offset = flat - t * delta;
            if (offset.LengthSquared() >= best) continue;
            best = offset.LengthSquared();
            along = (i + t) * 5;
            lateral = offset.Dot(delta.Normalized().Cross(Vector3.Up));
        }
        return (along, lateral);
    }

    public static float Width(string name) => name == "NATHAN ROAD" ? 20 : name is "CANTON ROAD" or "CHATHAM ROAD SOUTH" or
        "KOWLOON PARK DRIVE" or "AUSTIN ROAD" or "AUSTIN ROAD WEST" or "JORDAN ROAD" or
        "SALISBURY ROAD" or "SCIENCE MUSEUM ROAD" or "MODY ROAD" ? 18 : 12;

    private void JoinStreets()
    {
        // Source features split at arbitrary survey nodes; keep real forks, join degree-two ends.
        bool changed=true;
        while(changed)
        {
            changed=false;
            for(int i=0;i<SideRoads.Count && !changed;i++)
                for(int j=i+1;j<SideRoads.Count && !changed;j++)
                {
                    var a=SideRoads[i];var b=SideRoads[j];
                    if(a.Name!=b.Name)continue;
                    foreach(bool reverse in new[]{false,true})
                    {
                        var end=reverse?a.Points[0]:a.Points[^1];
                        if(end.DistanceTo(b.Points[0])>.02f && end.DistanceTo(b.Points[^1])>.02f)continue;
                        int degree=SideRoads.Where(r=>r.Name==a.Name).Sum(r=>(r.Points[0].DistanceTo(end)<.02f?1:0)+(r.Points[^1].DistanceTo(end)<.02f?1:0));
                        if(degree!=2)continue;
                        if(reverse)a.Points.Reverse();
                        if(end.DistanceTo(b.Points[^1])<.02f)b.Points.Reverse();
                        a.Points.AddRange(b.Points.Skip(1));SideRoads.RemoveAt(j);
                        changed=true;break;
                    }
                }
        }
    }

    private static Vector2 Closest(Vector2 p,Vector2 a,Vector2 b)
    {
        var d=b-a;
        return a+d*Mathf.Clamp((p-a).Dot(d)/d.LengthSquared(),0,1);
    }

    public IEnumerable<(string Name,Vector3 Point,Vector3 Forward,int Road)> StreetSamples(float spacing)
    {
        for(int roadId=0;roadId<SideRoads.Count;roadId++)
        {
            var road=SideRoads[roadId];float next=spacing/2;
            for(int i=0;i<road.Points.Count-1;i++)
            {
                var delta=road.Points[i+1]-road.Points[i];float length=delta.Length();
                if(length<.01f)continue;
                for(;next<length;next+=spacing)
                    yield return (road.Name,road.Points[i]+delta*(next/length),delta/length,roadId);
                next-=length;
            }
        }
    }

    public bool NearSideRoad(Vector3 position,float clearance,string? exceptName=null)
    {
        var p=new Vector2(position.X,position.Z);
        return _segments.Any(s=>s.Road>=0 && s.Name!=exceptName && p.DistanceTo(Closest(p,s.A,s.B))<clearance);
    }

    public bool NearOtherRoad(Vector3 position,int road,float margin)
    {
        var p=new Vector2(position.X,position.Z);
        return _segments.Any(s=>s.Road!=road && p.DistanceTo(Closest(p,s.A,s.B))<s.HalfWidth+margin);
    }

    public static int LanesPerDirection(float width) => width>=26?3:width>=16?2:1;

    public (Vector3 Center,float Width,int Owner) Carriageway(Vector3 position,Vector3 forward,string name)
    {
        // Paint the connected road surface once, even where the extract has parallel centrelines.
        // ponytail: local cross-sections suit the flat prototype; surveyed lanes would replace this approximation.
        var f=new Vector2(forward.X,forward.Z).Normalized();
        if(Mathf.Abs(f.Y)>Mathf.Abs(f.X)?f.Y>0:f.X<0)f=-f;
        var right=new Vector2(-f.Y,f.X);var p=new Vector2(position.X,position.Z);
        var spans=new List<(float Left,float Right,int Road)>();
        foreach(var s in _segments)
        {
            if(s.Name!=name)continue;
            var d=s.B-s.A;float alignment=Mathf.Abs(d.Normalized().Dot(f));
            if(alignment<.96f)continue;
            float t=(p-s.A).Dot(f)/d.Dot(f);
            if(t<-.0001f || t>1.0001f)continue;
            float across=(s.A+d*t-p).Dot(right);
            spans.Add((across-s.HalfWidth/alignment,across+s.HalfWidth/alignment,s.Road));
        }
        spans.Sort((a,b)=>a.Left!=b.Left?a.Left.CompareTo(b.Left):a.Road.CompareTo(b.Road));
        for(int i=0;i<spans.Count;i++)
        {
            float left=spans[i].Left,end=spans[i].Right;int owner=spans[i].Road;
            while(i+1<spans.Count && spans[i+1].Left<=end)
                end=Mathf.Max(end,spans[++i].Right);
            if(left<=.01f && end>=-.01f)
            {
                var center=p+right*(left+end)/2;
                return (new(center.X,0,center.Y),end-left,owner);
            }
        }
        throw new InvalidOperationException("No road cross-section at "+name+": "+position);
    }

    public IEnumerable<(string Name,Vector3 Point,Vector3 Forward,int Road,float Width)> LaneSamples(float spacing)
    {
        foreach(var (name,p,f,id) in StreetSamples(spacing))
        {
            var lane=Carriageway(p,f,name);
            if(lane.Owner==id)yield return (name,lane.Center,f,id,lane.Width);
        }
    }

    public bool CanPaintLane(Vector3 position,Vector3 forward,int road)
    {
        var p=new Vector2(position.X,position.Z);var f=new Vector2(forward.X,forward.Z);
        string name=road<0?"NATHAN ROAD":SideRoads[road].Name;
        foreach(var s in _segments)
        {
            if(s.Road==road)continue;
            float distance=p.DistanceTo(Closest(p,s.A,s.B));
            if(distance>s.HalfWidth+4)continue;
            // Parallel same-name segments share one lane layout; preserve real forks and crossings.
            if(s.Name==name && Mathf.Abs(f.Dot((s.B-s.A).Normalized()))>=.96f)continue;
            if(Mathf.Abs(f.Dot((s.B-s.A).Normalized()))<.94f || (distance<2 && s.Road<road))return false;
        }
        return true;
    }

    public bool ClearOfRoads(Vector3 position,float margin)
    {
        var p=new Vector2(position.X,position.Z);
        return _segments.All(s=>p.DistanceTo(Closest(p,s.A,s.B))>s.HalfWidth+margin);
    }

    public (string Name,float Distance,Vector3 Point,Vector3 Forward) NearestStreet(Vector3 position,string? name=null)
    {
        var p=new Vector2(position.X,position.Z);
        var nearest=(Name:"NATHAN ROAD",Distance:float.MaxValue,Point:Vector3.Zero,Forward:Vector3.Forward);
        foreach(var s in _segments)
        {
            if(name!=null && s.Name!=name)continue;
            var point=Closest(p,s.A,s.B);float distance=p.DistanceTo(point);
            if(distance>=nearest.Distance)continue;
            var f=(s.B-s.A).Normalized();
            nearest=(s.Name,distance,new(point.X,0,point.Y),new(f.X,0,f.Y));
        }
        return nearest;
    }

    public bool LotClear(Vector3 center,float heading,Vector2 halfSize,float margin=2.5f)
    {
        var p=new Vector2(center.X,center.Z);
        float radius=halfSize.Length()+12+margin;
        foreach(var s in _segments)
        {
            if(p.DistanceTo(Closest(p,s.A,s.B))>radius)continue;
            var a=(s.A-p).Rotated(heading);var b=(s.B-p).Rotated(heading);
            if(SegmentHitsBox(a,b,halfSize+Vector2.One*(s.HalfWidth+margin)))return false;
        }
        return true;
    }

    public Image CreateSurfaceMask(Vector2[] park,IEnumerable<(Vector3 A,Vector3 B)> paths,IEnumerable<Vector2[]> lots,
        Rect2? region=null,IEnumerable<(Vector2 A,Vector2 B,float HalfWidth)>? roads=null,float resolution=3)
    {
        // RGB is map data: road, pavement, park. One surface avoids coplanar depth fighting.
        var bounds=region??Bounds;
        int width=Mathf.CeilToInt(bounds.Size.X*resolution),height=Mathf.CeilToInt(bounds.Size.Y*resolution);
        float sx=width/bounds.Size.X,sy=height/bounds.Size.Y;
        var pixels=new byte[width*height*3];
        Vector2 Pixel(Vector2 p)=>(p-bounds.Position)*new Vector2(sx,sy);
        void Polygon(Vector2[] polygon,int channel)
        {
            if(polygon.Length<3)return;
            var points=polygon.Select(Pixel).ToArray();
            int ymin=Math.Max(0,Mathf.FloorToInt(points.Min(p=>p.Y))),ymax=Math.Min(height-1,Mathf.CeilToInt(points.Max(p=>p.Y)));
            var crossings=new List<float>();
            for(int y=ymin;y<=ymax;y++)
            {
                crossings.Clear();float row=y+.5f;
                for(int i=0;i<points.Length;i++)
                {
                    var a=points[i];var b=points[(i+1)%points.Length];
                    if((a.Y>row)==(b.Y>row))continue;
                    crossings.Add(a.X+(b.X-a.X)*(row-a.Y)/(b.Y-a.Y));
                }
                crossings.Sort();
                for(int i=0;i+1<crossings.Count;i+=2)
                    for(int x=Math.Max(0,Mathf.CeilToInt(crossings[i]-.5f));x<=Math.Min(width-1,Mathf.FloorToInt(crossings[i+1]-.5f));x++)
                        pixels[(y*width+x)*3+channel]=255;
            }
        }
        void Stroke(Vector2 a,Vector2 b,float roadRadius,float pavingRadius)
        {
            float pixelsPerMetre=Mathf.Min(sx,sy),feather=.5f/pixelsPerMetre;
            var lo=Pixel(a.Min(b)-Vector2.One*(pavingRadius+feather));var hi=Pixel(a.Max(b)+Vector2.One*(pavingRadius+feather));
            int xmin=Math.Max(0,Mathf.FloorToInt(lo.X)),xmax=Math.Min(width-1,Mathf.CeilToInt(hi.X));
            int ymin=Math.Max(0,Mathf.FloorToInt(lo.Y)),ymax=Math.Min(height-1,Mathf.CeilToInt(hi.Y));
            for(int y=ymin;y<=ymax;y++)
                for(int x=xmin;x<=xmax;x++)
                {
                    var p=bounds.Position+new Vector2((x+.5f)/sx,(y+.5f)/sy);
                    float distance=p.DistanceTo(Closest(p,a,b));
                    int index=(y*width+x)*3;
                    byte Coverage(float radius)=>(byte)Mathf.RoundToInt(Mathf.Clamp((radius-distance)*pixelsPerMetre+.5f,0,1)*255);
                    pixels[index+1]=Math.Max(pixels[index+1],Coverage(pavingRadius));
                    if(roadRadius>0)pixels[index]=Math.Max(pixels[index],Coverage(roadRadius));
                }
        }
        Polygon(park,2);
        foreach(var polygon in lots)Polygon(polygon,1);
        foreach(var (a,b) in paths)Stroke(new(a.X,a.Z),new(b.X,b.Z),-1,1.5f);
        foreach(var s in roads??_segments.Select(s=>(s.A,s.B,s.HalfWidth)))Stroke(s.A,s.B,s.HalfWidth,s.HalfWidth+3);
        var image=Image.CreateFromData(width,height,false,Image.Format.Rgb8,pixels);
        image.GenerateMipmaps();return image;
    }

    private static bool SegmentHitsBox(Vector2 a,Vector2 b,Vector2 half)
    {
        float lo=0,hi=1;var d=b-a;
        for(int axis=0;axis<2;axis++)
        {
            if(Mathf.Abs(d[axis])<.00001f){if(Mathf.Abs(a[axis])>half[axis])return false;continue;}
            float t0=(-half[axis]-a[axis])/d[axis],t1=(half[axis]-a[axis])/d[axis];
            lo=Mathf.Max(lo,Mathf.Min(t0,t1));hi=Mathf.Min(hi,Mathf.Max(t0,t1));
            if(lo>hi)return false;
        }
        return true;
    }
}
