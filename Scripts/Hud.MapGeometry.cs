using Godot;
using System;
using System.Collections.Generic;
using System.Linq;

public partial class Hud
{
    private const float MapSimplificationTolerance=.35f;
    private Vector2[][][] _rawMapLines=Array.Empty<Vector2[][]>();

    private sealed class MapGeometryBatch
    {
        public Vector2[] Points {get;}
        public int SourceSegments {get;}
        public int VisibleSegments {get;}
        public int RenderedSegments {get;}
        public float MaxErrorPixels {get;}
        public MapGeometryBatch(Vector2[] points,int sourceSegments,int visibleSegments,int renderedSegments,float maxErrorPixels)
            =>(Points,SourceSegments,VisibleSegments,RenderedSegments,MaxErrorPixels)=(points,sourceSegments,visibleSegments,renderedSegments,maxErrorPixels);
    }

    private static Vector2 Flat(Vector3 p)=>new(p.X,p.Z);
    private Vector2 MapPresentationScale=>GetViewport().GetStretchTransform().Scale.Abs();

    private void EnsureRawMapLines()
    {
        if(_rawMapLines.Length>0)return;
        _rawMapLines=new[]{
            Game.KowloonCoastline.Concat(Game.IslandCoastline).Select(line=>line.ToArray()).ToArray(),
            Game.Map.SideRoads.Select(road=>road.Points.Select(Flat).ToArray()).ToArray(),
            Game.HarbourRoads.Where(road=>!road.Tunnel).Select(road=>road.Points.Select(Flat).ToArray()).ToArray(),
            Game.HarbourRoads.Where(road=>road.Tunnel).Select(road=>road.Points.Select(Flat).ToArray()).ToArray()
        };
    }

    private Vector2[][] ProjectMapLines(int group,Vector2 origin,float scale,bool dashedTunnel=false)
    {
        Vector2 Point(Vector2 p)=>origin+p*scale;
        var projected=new List<Vector2[]>();
        foreach(var line in _rawMapLines[group])
        {
            if(!dashedTunnel || group!=3){projected.Add(line.Select(Point).ToArray());continue;}
            List<Vector2>? run=null;
            for(int i=0;i<line.Length-1;i++)
            {
                if((i+1)%5>2){if(run!=null){projected.Add(run.ToArray());run=null;}continue;}
                run??=new(){Point(line[i])};run.Add(Point(line[i+1]));
            }
            if(run!=null)projected.Add(run.ToArray());
        }
        return projected.ToArray();
    }

    private MapGeometryBatch[] BuildMapViewGeometry(bool expanded,Vector2I size)
    {
        EnsureRawMapLines();
        var area=MapArea(expanded);var (origin,scale)=MapTransform(expanded);
        var lines=Enumerable.Range(0,4).Select(i=>ProjectMapLines(i,origin,scale,true)).ToArray();
        var pixels=(Vector2)size/area.Size;var offset=area.Position*pixels;var presentation=MapPresentationScale;
        var widths=new[]{expanded?1.8f:1.2f,expanded?1.6f:1.5f,expanded?1.35f:1.3f,expanded?3f:2f};
        return lines.Select((line,i)=>BuildMapGeometry(line,pixels,offset,(Vector2)size,widths[i]*Mathf.Max(pixels.X,pixels.Y),presentation)).ToArray();
    }

    private static MapGeometryBatch BuildMapGeometry(Vector2[][] source,Vector2 pixelScale,Vector2 pixelOffset,Vector2 viewportPixels,float strokeWidthPixels,Vector2 presentationScale)
    {
        float presentationMax=Mathf.Max(presentationScale.X,presentationScale.Y);
        float tolerance=MapSimplificationTolerance/Mathf.Max(.0001f,presentationMax);
        float margin=strokeWidthPixels/2+1+tolerance;
        var clip=new Rect2(-margin,-margin,viewportPixels.X+margin*2,viewportPixels.Y+margin*2);
        var rendered=new List<Vector2>();int sourceSegments=0,visibleSegments=0,renderedSegments=0;float maxErrorPixels=0;
        foreach(var line in source)
        {
            sourceSegments+=Math.Max(0,line.Length-1);
            if(line.Length<2)continue;
            var pixels=line.Select(p=>p*pixelScale-pixelOffset).ToArray();
            var kept=SimplifyMapLine(pixels,tolerance);
            maxErrorPixels=Mathf.Max(maxErrorPixels,MapLineError(pixels,kept)*presentationMax);
            for(int i=0;i<pixels.Length-1;i++)if(SegmentBoundsIntersect(pixels[i],pixels[i+1],clip))visibleSegments++;
            for(int i=0;i<kept.Length-1;i++)
            {
                int a=kept[i],b=kept[i+1];
                if(!SegmentBoundsIntersect(pixels[a],pixels[b],clip))continue;
                rendered.Add(line[a]);rendered.Add(line[b]);
                renderedSegments++;
            }
        }
        return new(rendered.ToArray(),sourceSegments,visibleSegments,renderedSegments,maxErrorPixels);
    }

    private static int[] SimplifyMapLine(Vector2[] points,float tolerance)
    {
        if(points.Length<=2)return Enumerable.Range(0,points.Length).ToArray();
        bool closed=points[0].DistanceSquaredTo(points[^1])<.000001f;
        if(!closed)return SimplifyMapLineRange(points,0,points.Length-1,tolerance);
        if(points.Take(points.Length-1).Distinct().Count()<3)return Enumerable.Range(0,points.Length).ToArray();
        int second=1;
        for(int i=2;i<points.Length-1;i++)if(points[i].DistanceSquaredTo(points[0])>points[second].DistanceSquaredTo(points[0]))second=i;
        int third=-1;float farthest=-1;
        for(int i=1;i<points.Length-1;i++)
        {
            if(i==second)continue;
            float distance=PointSegmentDistanceSquared(points[i],points[0],points[second]);
            if(distance>farthest){farthest=distance;third=i;}
        }
        if(third<0 || farthest<.000001f)return Enumerable.Range(0,points.Length).ToArray();
        var anchors=new[]{0,second,third,points.Length-1}.Distinct().Order().ToArray();
        var keep=new bool[points.Length];
        foreach(int anchor in anchors)keep[anchor]=true;
        for(int i=1;i<anchors.Length;i++)SimplifyMapLineRange(points,anchors[i-1],anchors[i],tolerance,keep);
        return Enumerable.Range(0,keep.Length).Where(i=>keep[i]).ToArray();
    }

    private static int[] SimplifyMapLineRange(Vector2[] points,int start,int end,float tolerance)
    {
        var keep=new bool[points.Length];keep[start]=keep[end]=true;
        SimplifyMapLineRange(points,start,end,tolerance,keep);
        return Enumerable.Range(0,keep.Length).Where(i=>keep[i]).ToArray();
    }

    private static void SimplifyMapLineRange(Vector2[] points,int start,int end,float tolerance,bool[] keep)
    {
        float toleranceSquared=tolerance*tolerance;var pending=new Stack<(int Start,int End)>();pending.Push((start,end));
        while(pending.Count>0)
        {
            var (a,b)=pending.Pop();float max=toleranceSquared;int farthest=-1;
            for(int i=a+1;i<b;i++)
            {
                float distance=PointSegmentDistanceSquared(points[i],points[a],points[b]);
                if(distance>max){max=distance;farthest=i;}
            }
            if(farthest<0)continue;
            keep[farthest]=true;pending.Push((a,farthest));pending.Push((farthest,b));
        }
    }

    private static float PointSegmentDistanceSquared(Vector2 point,Vector2 a,Vector2 b)
    {
        var delta=b-a;float length=delta.LengthSquared();
        if(length<.000001f)return point.DistanceSquaredTo(a);
        float t=Mathf.Clamp((point-a).Dot(delta)/length,0,1);
        return point.DistanceSquaredTo(a+delta*t);
    }

    private static float MapLineError(Vector2[] points,int[] kept)
    {
        if(kept.Length<2)return 0;
        int segment=0;float errorSquared=0;
        for(int i=0;i<points.Length;i++)
        {
            while(segment<kept.Length-2 && i>kept[segment+1])segment++;
            errorSquared=Mathf.Max(errorSquared,PointSegmentDistanceSquared(points[i],points[kept[segment]],points[kept[segment+1]]));
        }
        return Mathf.Sqrt(errorSquared);
    }

    private static bool SegmentBoundsIntersect(Vector2 a,Vector2 b,Rect2 bounds)
        =>Mathf.Max(a.X,b.X)>=bounds.Position.X && Mathf.Min(a.X,b.X)<=bounds.End.X &&
            Mathf.Max(a.Y,b.Y)>=bounds.Position.Y && Mathf.Min(a.Y,b.Y)<=bounds.End.Y;

    public void CheckMapGeometry()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        if(Game.HasKaiTakDrive)
            foreach(var route in Game.Routes)
            {
                var (districts,stops)=ExpandedMapLabels(route);
                for(int i=MapDistricts.Length;i<districts.Length;i++)
                {
                    var label=districts[i];
                    Check(ExpandedMapArea.Encloses(label) && !districts.Where((_,index)=>index!=i).Any(d=>d.Grow(3).Intersects(label)) &&
                        !stops.Any(s=>s.Grow(3).Intersects(label)),"New Kai Tak map label must stay inside the map and clear of existing labels: "+label);
                }
            }
        var straight=Enumerable.Range(0,1001).Select(i=>new Vector2(i,0)).ToArray();
        var straightKept=SimplifyMapLine(straight,MapSimplificationTolerance);
        Check(straightKept.Length==2 && straightKept[0]==0 && straightKept[^1]==straight.Length-1,"Dense straight map line must keep only its endpoints");
        var turn=new[]{Vector2.Zero,new Vector2(10,0),new Vector2(10,10)};var turnKept=SimplifyMapLine(turn,MapSimplificationTolerance);
        Check(turnKept.SequenceEqual(new[]{0,1,2}),"Map simplification must retain a visible turn corner");
        var loop=new List<Vector2>();
        for(int x=0;x<=10;x++)loop.Add(new(x,0));for(int y=1;y<=10;y++)loop.Add(new(10,y));
        for(int x=9;x>=0;x--)loop.Add(new(x,10));for(int y=9;y>0;y--)loop.Add(new(0,y));loop.Add(Vector2.Zero);
        var loopPoints=loop.ToArray();var loopKept=SimplifyMapLine(loopPoints,MapSimplificationTolerance);
        Check(loopKept[0]==0 && loopKept[^1]==loopPoints.Length-1 && loopKept.Select(i=>loopPoints[i]).Distinct().Count()>=3,
            "Closed map loops must retain their closure and at least three vertices");
        var degenerate=new[]{new Vector2(4,7),new Vector2(4,7),new Vector2(9,7)};var degenerateKept=SimplifyMapLine(degenerate,MapSimplificationTolerance);
        Check(degenerateKept[0]==0 && degenerateKept[^1]==degenerate.Length-1 && MapLineError(degenerate,degenerateKept)<=MapSimplificationTolerance,
            "Short and duplicate map points must simplify without losing endpoints");
        Check(MapLineError(turn,turnKept)<=MapSimplificationTolerance,"Synthetic turn exceeds the map error budget");
        var junction=BuildMapGeometry(new[]{new[]{Vector2.Zero,new Vector2(10,0)},new[]{new Vector2(10,0),new Vector2(10,10)}},
            Vector2.One,Vector2.Zero,new Vector2(20,20),1,Vector2.One);
        var visibleTurn=BuildMapGeometry(new[]{turn},Vector2.One,Vector2.Zero,new Vector2(20,20),1,Vector2.One);
        Check(junction.Points.Length==4 && junction.Points.Length==junction.RenderedSegments*2 &&
            junction.Points.Count(p=>p==new Vector2(10,0))==2 &&
            visibleTurn.Points.Length==4 && visibleTurn.RenderedSegments==2 &&
            visibleTurn.Points.Contains(Vector2.Zero) && visibleTurn.Points.Contains(new Vector2(10,0)) && visibleTurn.Points.Contains(new Vector2(10,10)),
            "Map batches must keep separate junction segments as even endpoint pairs and retain a visible 3-point turn");

        var crossing=new[]{new Vector2(-110,-5),new Vector2(20,-5)};
        var clipped=BuildMapGeometry(new[]{crossing},Vector2.One,new Vector2(-100,-100),new Vector2(100,100),2,Vector2.One);
        var outside=BuildMapGeometry(new[]{new[]{new Vector2(-500,-500),new Vector2(-400,-400)}},Vector2.One,new Vector2(-100,-100),new Vector2(100,100),2,Vector2.One);
        Check(clipped.RenderedSegments==1 && clipped.VisibleSegments==1 && outside.RenderedSegments==0,
            "Viewport clipping must retain crossing segments under negative route bounds and reject distant segments");
        var scaledCurve=BuildMapGeometry(new[]{new[]{new Vector2(0,10),new Vector2(1,10.2f),new Vector2(2,10)}},
            Vector2.One,Vector2.Zero,new Vector2(100,100),2,new Vector2(2,2));
        var paddedEdge=BuildMapGeometry(new[]{new[]{new Vector2(-2.1f,50),new Vector2(-1.9f,50)}},
            Vector2.One,Vector2.Zero,new Vector2(100,100),2,new Vector2(2,2));
        Check(scaledCurve.Points.Length==4 && scaledCurve.Points.Contains(new Vector2(1,10.2f)) && scaledCurve.MaxErrorPixels<=.35f &&
            paddedEdge.RenderedSegments==1,"Physical-pixel scaling must tighten RDP and retain strokes at the padded viewport edge");

        EnsureRawMapLines();
        int originalDashedTunnelSegments=_rawMapLines[3].Sum(line=>Enumerable.Range(1,line.Length-1).Count(i=>i%5<=2));
        int preparedDashedTunnelSegments=ProjectMapLines(3,Vector2.Zero,1,true).Sum(line=>line.Length-1);
        Check(preparedDashedTunnelSegments==originalDashedTunnelSegments,
            $"Mini/full-map tunnel dash changed from {originalDashedTunnelSegments} to {preparedDashedTunnelSegments} segments");
        var mini=BuildMapViewGeometry(false,_miniMap.Size);var full=BuildMapViewGeometry(true,_fullMap.Size);
        Report("mini",mini);Report("full",full);
        foreach(var route in Game.Routes)
        {
            var bounds=RouteMapBounds(route);var geometry=BuildRouteMapGeometry(bounds,_routeMap.Size);
            int before=geometry.Sum(batch=>batch.SourceSegments),visible=geometry.Sum(batch=>batch.VisibleSegments),after=geometry.Sum(batch=>batch.RenderedSegments);
            float error=geometry.Max(batch=>batch.MaxErrorPixels);
            Check(before>0 && visible>0 && after>0 && after<before && geometry.All(batch=>batch.Points.Length==batch.RenderedSegments*2) &&
                error<=MapSimplificationTolerance+.0001f,
                $"{route.Number} visible road geometry failed its {MapSimplificationTolerance:0.00} px map error budget: {before}/{visible}/{after}, max {error:0.000}");
            var scale=RouteMapArea.Size.X/bounds.Size.X;var pixel=(Vector2)_routeMap.Size/RouteMapArea.Size;
            var viewport=(Vector2)_routeMap.Size;
            Check(route.Path.Points.All(p=>{
                var at=(Flat(p)-bounds.Position)*scale*pixel.X;
                return at.X>=0 && at.Y>=0 && at.X<=viewport.X && at.Y<=viewport.Y;
            }),$"{route.Number} preview route fell outside its dynamic map bounds");
            GD.Print($"ANTILA_MAP_GEOMETRY_ROUTE: {route.Number} {visible}/{before} visible source segments; {after} drawn; max {error:0.000} px");
        }
        GD.Print("ANTILA_MAP_GEOMETRY_OK: endpoint, turn, loop, degenerate, negative-bounds clipping and H1/H2/H3 coverage");

        void Report(string name,MapGeometryBatch[] batches)
        {
            int before=batches.Sum(batch=>batch.SourceSegments),visible=batches.Sum(batch=>batch.VisibleSegments),after=batches.Sum(batch=>batch.RenderedSegments);
            float error=batches.Max(batch=>batch.MaxErrorPixels);
            Check(before>0 && visible>0 && after>0 && after<before && batches.All(batch=>batch.Points.Length==batch.RenderedSegments*2) &&
                error<=MapSimplificationTolerance+.0001f,
                $"{name} map geometry failed its {MapSimplificationTolerance:0.00} px error budget: {before}/{visible}/{after}, max {error:0.000}");
            GD.Print($"ANTILA_MAP_GEOMETRY_{name.ToUpperInvariant()}: {visible}/{before} visible source segments; {after} drawn; max {error:0.000} px");
        }
    }
}
