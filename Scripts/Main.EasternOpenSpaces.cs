using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

public partial class Main
{
    private const string WonderlandSite="1910058892";

    private Node3D _eastRecreation = null!;
    private readonly List<(string Site,Vector3 Position,float Radius)> _eastRecreationProps = new();
    private readonly List<(Rect2 Bounds,Vector2[] Polygon)> _eastParkReservations = new();

    private void BuildEasternOpenSpaces()
    {
        using var data=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/east-kowloon-open-spaces.json"));
        using var mongKok=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/mong-kok-open-spaces.json"));
        var root=data.RootElement;var bounds=root.GetProperty("bounds");
        _recreationBounds=_recreationBounds.Merge(new Rect2(bounds[0].GetSingle(),bounds[1].GetSingle(),bounds[2].GetSingle(),bounds[3].GetSingle()));
        Vector2[] Points(JsonElement row)=>row.EnumerateArray().Select(p=>new Vector2(p[0].GetSingle(),p[1].GetSingle())).ToArray();
        _terrain.SetShaderParameter("recreation_mask",TerrainMask("recreation_mask",_recreationBounds,
            ()=>CreateRecreationMask(_recreationBounds,mongKok.RootElement,root)));
        _terrain.SetShaderParameter("recreation_origin",_recreationBounds.Position);
        _terrain.SetShaderParameter("recreation_size",_recreationBounds.Size);
        foreach(var triangle in root.GetProperty("paving").EnumerateArray())_harbourPaving.Add(Points(triangle));
        foreach(var garden in root.GetProperty("gardens").EnumerateArray())
            foreach(string zone in new[]{"rings","access"})
                foreach(var row in garden.GetProperty(zone).EnumerateArray())
                {
                    var polygon=Points(row[0]);var area=new Rect2(polygon[0],Vector2.Zero);
                    foreach(var point in polygon)area=area.Expand(point);
                    _eastParkReservations.Add((area,polygon));
                }
        _eastRecreation=Asset("east-kowloon-recreation",Vector3.Zero);
        foreach(var mesh in _eastRecreation.FindChildren("Collision*","MeshInstance3D",true,false).Cast<MeshInstance3D>())
        {
            mesh.Visible=false;var body=new StaticBody3D();mesh.AddChild(body);
            body.AddChild(new CollisionShape3D {Shape=mesh.Mesh.CreateTrimeshShape()});
        }
        foreach(var fixture in root.GetProperty("fixtures").EnumerateArray())
        {
            var xy=fixture.GetProperty("position");var at=new Vector3(xy[0].GetSingle(),0,xy[1].GetSingle());
            float radius=fixture.GetProperty("radius").GetSingle(),scale=fixture.GetProperty("scale").GetSingle();
            if(!ClearOfServiceStops(at,radius))continue;
            var asset=Asset(fixture.GetProperty("asset").GetString()!,at,fixture.GetProperty("yaw").GetSingle(),Vector3.One*scale);
            foreach(var mesh in asset.FindChildren("*","MeshInstance3D",true,false).Cast<MeshInstance3D>())mesh.VisibilityRangeEnd=900;
            _islandDetails.Add((at,radius));_eastRecreationProps.Add((fixture.GetProperty("site").GetString()!,at,radius));
        }
        GD.Print($"ANTILA_EAST_OPEN_SPACES: {root.GetProperty("sites").GetArrayLength()} sourced parks/waterfront sites; {_eastRecreationProps.Count} fixtures; {root.GetProperty("sports").GetArrayLength()} fitted courts");
    }

    // Shared by bake/check paths so exports regenerate the exact source mask from bundled JSON.
    private Image CreateRecreationMask(Rect2 bounds)
    {
        using var eastern=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/east-kowloon-open-spaces.json"));
        using var mongKok=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/mong-kok-open-spaces.json"));
        return CreateRecreationMask(bounds,mongKok.RootElement,eastern.RootElement);
    }

    private Image CreateRecreationMask(Rect2 bounds,JsonElement mongKok,JsonElement eastern)
    {
        var eb=eastern.GetProperty("bounds");var mb=mongKok.GetProperty("bounds");
        var currentBounds=new Rect2(eb[0].GetSingle(),eb[1].GetSingle(),eb[2].GetSingle(),eb[3].GetSingle())
            .Merge(new Rect2(mb[0].GetSingle(),mb[1].GetSingle(),mb[2].GetSingle(),mb[3].GetSingle()));
        if(!currentBounds.IsEqualApprox(bounds))throw new Exception("Recreation mask bounds differ from the bundled open-space sources");
        Vector2[] Points(JsonElement row)=>row.EnumerateArray().Select(p=>new Vector2(p[0].GetSingle(),p[1].GetSingle())).ToArray();
        var surfaces=new List<(Vector2[] Polygon,int Channel)>();
        foreach(var region in new[]{mongKok,eastern})
            foreach(var surface in region.GetProperty("surfaces").EnumerateArray())
                foreach(var triangle in surface.GetProperty("triangles").EnumerateArray())
                    surfaces.Add((Points(triangle),surface.GetProperty("kind").GetString() switch {"field"=>0,"court"=>1,_=>2}));
        float resolution=Mathf.Min(2,8192f/Mathf.Max(bounds.Size.X,bounds.Size.Y));
        return Map.CreateSurfaceMask(Array.Empty<Vector2>(),Array.Empty<(Vector3,Vector3)>(),Array.Empty<Vector2[]>(),
            bounds,Array.Empty<(Vector2,Vector2,float)>(),resolution,surfaces);
    }

    // The parks have their own fitted planting; later roadside decoration must leave their interiors and entrances clear.
    private bool ClearOfEasternParks(Vector3 position,float margin)
    {
        var p=new Vector2(position.X,position.Z);
        return !_eastParkReservations.Any(a=>a.Bounds.Grow(margin).HasPoint(p) &&
            (Geometry2D.IsPointInPolygon(p,a.Polygon) || a.Polygon.Select((v,i)=>p.DistanceTo(Geometry2D.GetClosestPointToSegment(p,v,a.Polygon[(i+1)%a.Polygon.Length]))).Min()<margin));
    }

    private void CheckEasternOpenSpaces()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        var model=_eastRecreation??throw new Exception("Eastern parks must load their sourced recreation surfaces and fittings");
        using var data=JsonDocument.Parse(FileAccess.GetFileAsString("res://Data/east-kowloon-open-spaces.json"));
        var root=data.RootElement;
        var metadata=root.GetProperty("metadata");
        bool hasKowloonCity=metadata.GetProperty("source_manifests").EnumerateArray().Any(source=>
            source.GetProperty("path").GetString()=="Data/kowloon-city-open-spaces-source.geojson");
        var sittingOutAreas=new[]{"1503005180","1503005170","1503005157","1503005144","1503005135","1503005123","1503005605","1502005648"};
        var expected=new[]{
            "1503005871","1503005901","1503005881","1503005751","1503005870","1503005863","1503005866","1503005714","1910071209",
            "1503005853","1503005716","1503005939","1503005718","1910059822","1503005810","1503005961","1910064509","1503000381",
            "1503005413","1503000390","1503005076","1503000414","1910069198","1503000199","1810011761","1910053970","1910053968",
            "1503005535","1503005281","1810014504","1810044652","1503005514","1910056230","1810032161","1910062401","1503005115",
            "1503005152","1810015202","1503005628","1503005422",WonderlandSite,
            "1503005112","1503005184","1503005071","1503005077","1503005450","1503005508",
            "1503005539","1503005553","1503005688","1503005627"
        }.Concat(sittingOutAreas).ToArray();
        var sites=root.GetProperty("sites").EnumerateArray().ToDictionary(site=>site.GetProperty("id").GetString()!);
        var sportSurfaces=root.GetProperty("surfaces").EnumerateArray().ToArray();
        if(hasKowloonCity)
        {
            var surveyed=new[]{
                ("1503005642","Carmel Village Street Garden"),
                ("1503005679","Ho Man Tin Park"),("1503005683","Perth Street Sports Ground"),
                ("1503005701","Ho Man Tin East Service Reservoir Playground"),("1810022853","Ho Man Tin East Sitting-out Area No. 1")};
            expected=expected.Concat(surveyed.Select(site=>site.Item1)).ToArray();
            foreach(var (id,name) in surveyed)
                Check(sites.TryGetValue(id,out var site) && site.GetProperty("name").GetString()==name,"Missing surveyed recreation site: "+name);
            foreach(var (id,outline) in new[]{("1503005679","1500002029"),("1503005679","1500002030"),("1503005679","1500004996"),
                ("1503005683","1500002064"),("1503005683","1500002065"),("1503005683","1500002066"),("1503005683","1810060613"),
                ("1503005701","1500004997"),("1503005701","1500004998")})
                Check(sportSurfaces.Any(s=>s.GetProperty("site").GetString()==id && s.GetProperty("source_id").GetString()==outline),
                    "Missing surveyed recreation surface: "+outline);
        }
        Check(sites.Keys.Order().SequenceEqual(expected.Order()),$"All {expected.Length} reviewed open spaces must be present");
        int sourceOutlines=sportSurfaces.Select(s=>s.GetProperty("source_id").GetString()).Distinct().Count();
        Check(sourceOutlines==(hasKowloonCity?161:152),"Every reviewed source sports outline must have a rendered recreation surface");
        Check(metadata.GetProperty("source_feature_count").GetInt32()==(hasKowloonCity?298:284) &&
            metadata.GetProperty("source_site_fragment_count").GetInt32()==(hasKowloonCity?120:115) &&
            metadata.GetProperty("source_sport_fragment_count").GetInt32()==(hasKowloonCity?178:169),"The complete source fragment inventory must be loaded");
        var southwest=metadata.GetProperty("supplemental_site_source");
        Check(southwest.GetProperty("feature_count").GetInt32()==193 && southwest.GetProperty("site_fragment_count").GetInt32()==2,
            "Both source-backed southwest waterfront spaces must be loaded");
        Check(_eastRecreationProps.Count==root.GetProperty("fixtures").GetArrayLength(),"Eastern park furniture must remain clear of every service stop");
        int reservationCount=root.GetProperty("gardens").EnumerateArray().Sum(g=>g.GetProperty("rings").GetArrayLength()+g.GetProperty("access").GetArrayLength());
        Check(_eastParkReservations.Count==reservationCount,"Every sourced park interior and access corridor must reserve roadside scenery");
        Vector2[] Points(JsonElement ring)=>ring.EnumerateArray().Select(p=>new Vector2(p[0].GetSingle(),p[1].GetSingle())).ToArray();
        bool Inside(Vector2 p,JsonElement polygon)=>Geometry2D.IsPointInPolygon(p,Points(polygon[0])) &&
            !polygon.EnumerateArray().Skip(1).Any(h=>Geometry2D.IsPointInPolygon(p,Points(h)));
        float EdgeDistance(Vector2 p,JsonElement polygon)=>polygon.EnumerateArray().SelectMany(r=>
        {
            var points=Points(r);
            return points.Select((a,i)=>p.DistanceTo(Geometry2D.GetClosestPointToSegment(p,a,points[(i+1)%points.Length])));
        }).Min();
        using var paving=((Texture2D)_terrain.GetShaderParameter("harbour_mask").AsGodotObject()).GetImage();
        using var recreation=RecreationMaskForChecks();
        long recreationBytes=(long)recreation.GetWidth()*recreation.GetHeight()*3;
        Check(recreation.GetFormat()==Image.Format.Rgb8 && recreation.GetWidth()<=8192 && recreation.GetHeight()<=8192 && recreationBytes<=192L*1024*1024,
            $"Recreation RGB8 mask exceeds its 8192-pixel / 192 MiB cap: {recreation.GetWidth()}x{recreation.GetHeight()} ({recreationBytes} bytes)");
        CheckEasternPathConnections(root,paving,sittingOutAreas);
        int paths=0,surfaces=0,support=0,infields=0;
        foreach(var garden in root.GetProperty("gardens").EnumerateArray())
        {
            string id=garden.GetProperty("site").GetString()!;
            bool pavedSittingOut=sittingOutAreas.Contains(id);
            var fixtures=_eastRecreationProps.Where(p=>p.Site==id).ToArray();
            if(id==WonderlandSite)
            {
                Check(fixtures.Length==0 && garden.GetProperty("paths").GetArrayLength()==0
                    && garden.GetProperty("access").GetArrayLength()==0,"Wonderland must retain its open event ground");
                var center=new Vector2(-1698,-824);var uv=(center-HarbourBounds.Position)/HarbourBounds.Size;
                Check(garden.GetProperty("rings").EnumerateArray().Any(poly=>Inside(center,poly))
                    && paving.GetPixel((int)(uv.X*paving.GetWidth()),(int)(uv.Y*paving.GetHeight())).G<.1f,
                    "Wonderland's surveyed event centre must stay clear of paving");
                using var ray=PhysicsRayQueryParameters3D.Create(new(center.X,.2f,center.Y),new(center.X,-.2f,center.Y),1);
                Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,"Wonderland event ground must have solid support");support++;
                continue;
            }
            if(id=="1503005422")Check(fixtures.Length==0,"Cultural Centre piazzas must stay clear for events");
            else if(pavedSittingOut)Check(fixtures.Length>=1,"A compact sitting-out area needs seating: "+id);
            else if(id!="1503005184" && id!="1503005688")Check(id=="1910062401" || fixtures.Length>=3,"Open space needs usable furniture and planting: "+id);
            Check(garden.GetProperty("access").GetArrayLength()>0,"Eastern park must retain pedestrian entrances: "+id);
            foreach(var prop in fixtures)
            {
                var p=new Vector2(prop.Position.X,prop.Position.Z);
                Check(garden.GetProperty("rings").EnumerateArray().Any(poly=>Inside(p,poly)) && LotClear(p,prop.Radius) && ClearOfServiceStops(prop.Position,prop.Radius),"Eastern park fixture leaves its source site or obstructs a building/stop: "+id);
                // A compact plaza can seat people on its paving; its path check routes around the benches.
                foreach(string zone in pavedSittingOut?new[]{"access"}:new[]{"paths","access"})
                    Check(!garden.GetProperty(zone).EnumerateArray().Any(poly=>Inside(p,poly) || EdgeDistance(p,poly)<prop.Radius-.01f),"Eastern park furniture obstructs a path or entrance: "+id);
                Check(Map.ClearOfRoads(prop.Position,prop.Radius) && !HarbourRoads.Any(r=>Enumerable.Range(1,r.Points.Count-1).Any(j=>r.Points[j].Y>-6 && p.DistanceTo(Geometry2D.GetClosestPointToSegment(p,new(r.Points[j-1].X,r.Points[j-1].Z),new(r.Points[j].X,r.Points[j].Z)))<Mathf.Max(12,r.Width)/2+prop.Radius)),"Eastern park fixture enters a carriageway: "+id);
                Check(!root.GetProperty("surfaces").EnumerateArray().Any(s=>(s.GetProperty("kind").GetString()=="track"?Geometry2D.IsPointInPolygon(p,Points(s.GetProperty("rings")[0])):Inside(p,s.GetProperty("rings"))) || EdgeDistance(p,s.GetProperty("rings"))<prop.Radius-.01f),"Eastern park fixture enters a playing surface or athletics infield: "+id);
            }
            Check(garden.GetProperty("samples").GetArrayLength()>0,"Eastern open space has no usable pedestrian path: "+id);
            foreach(var sample in garden.GetProperty("samples").EnumerateArray())
            {
                var p=new Vector2(sample[0].GetSingle(),sample[1].GetSingle());var uv=(p-HarbourBounds.Position)/HarbourBounds.Size;
                Check(paving.GetPixel(Math.Clamp((int)(uv.X*paving.GetWidth()),0,paving.GetWidth()-1),Math.Clamp((int)(uv.Y*paving.GetHeight()),0,paving.GetHeight()-1)).G>.9f,"Eastern park paving missing: "+id);paths++;
                using var ray=PhysicsRayQueryParameters3D.Create(new(p.X,.2f,p.Y),new(p.X,-.2f,p.Y),1);
                Check(GetWorld3D().DirectSpaceState.IntersectRay(ray).Count>0,"Eastern park path lacks ground support: "+id);support++;
            }
        }
        Check(root.GetProperty("gardens").GetArrayLength()==expected.Length,"All reviewed source boundaries must remain available");
        foreach(var surface in root.GetProperty("surfaces").EnumerateArray())
        {
            var p=surface.GetProperty("sample");var uv=(new Vector2(p[0].GetSingle(),p[1].GetSingle())-_recreationBounds.Position)/_recreationBounds.Size;
            Check(uv.X>=0 && uv.Y>=0 && uv.X<=1 && uv.Y<=1,"Eastern recreation mask must include the selected sports grounds");
            int channel=surface.GetProperty("kind").GetString() switch {"field"=>0,"court"=>1,_=>2};
            Check(recreation.GetPixel(Math.Clamp((int)(uv.X*recreation.GetWidth()),0,recreation.GetWidth()-1),Math.Clamp((int)(uv.Y*recreation.GetHeight()),0,recreation.GetHeight()-1))[channel]>.9f,"Eastern sport surface missing");surfaces++;
            if(channel==2)foreach(var hole in surface.GetProperty("rings").EnumerateArray().Skip(1))
            {
                var points=Points(hole);var indices=Geometry2D.TriangulatePolygon(points);
                Check(indices.Length>=3,"Athletics infield source boundary must triangulate");
                for(int i=0;i<indices.Length;i+=3)
                {
                    var at=(points[indices[i]]+points[indices[i+1]]+points[indices[i+2]])/3;
                    var pathUv=(at-HarbourBounds.Position)/HarbourBounds.Size;
                    Check(paving.GetPixel(Math.Clamp((int)(pathUv.X*paving.GetWidth()),0,paving.GetWidth()-1),Math.Clamp((int)(pathUv.Y*paving.GetHeight()),0,paving.GetHeight()-1)).G<.1f,"Authored paths must leave the athletics infield clear");infields++;
                }
            }
        }
        Check(surfaces>20,"Eastern sports coverage is incomplete");
        var collision=model.FindChildren("Collision*","MeshInstance3D",true,false).Cast<MeshInstance3D>().ToArray();
        Check(collision.Length==root.GetProperty("sports").GetArrayLength() && collision.All(m=>!m.Visible && m.FindChildren("*","CollisionShape3D",true,false).Count==1),"Eastern sports fittings need matching hidden collision meshes");
        var ownPositions=_eastRecreationProps.Select(p=>p.Position).ToHashSet();
        Check(_islandDetails.Where(d=>!ownPositions.Contains(d.Position)).All(d=>ClearOfEasternParks(d.Position,d.Radius)),"Later roadside decoration must leave eastern park interiors and entrances clear");
        GD.Print($"ANTILA_EAST_OPEN_SPACES_OK: {root.GetProperty("sites").GetArrayLength()} sourced sites; {sourceOutlines} source sports outlines; {paths} paving, {surfaces} sport, {support} support and {infields} clear infield probes; {_eastRecreationProps.Count} clear fixtures; {_eastParkReservations.Count} reservations; {collision.Length} court colliders; recreation mask {recreation.GetWidth()}x{recreation.GetHeight()} / {recreationBytes} bytes");
    }

    private void CheckEasternPathConnections(JsonElement root,Image paving,IReadOnlyCollection<string> sittingOutAreas)
    {
        var pixel=HarbourBounds.Size/new Vector2(paving.GetWidth(),paving.GetHeight());int checkedSamples=0;
        var disconnected=new List<string>();
        var gardens=root.GetProperty("gardens").EnumerateArray().Where(g=>g.GetProperty("site").GetString()!=WonderlandSite).ToArray();
        var groundRoads=HarbourRoads.Where(r=>!r.Tunnel).Select(r=>(Points:r.Points,Width:r.Width))
            .Concat(Map.SideRoads.Select(r=>(Points:r.Points,Width:RoadMap.Width(r.Name))))
            .Append((Points:Map.RoadPoints,Width:RoadMap.Width("NATHAN ROAD")));
        foreach(var garden in gardens)
        {
            string site=garden.GetProperty("site").GetString()!;
            var seating=sittingOutAreas.Contains(site)
                ?_eastRecreationProps.Where(prop=>prop.Site==site).ToArray()
                :Array.Empty<(string Site,Vector3 Position,float Radius)>();
            var bounds=new Rect2(new Vector2(garden.GetProperty("samples")[0][0].GetSingle(),garden.GetProperty("samples")[0][1].GetSingle()),Vector2.Zero);
            foreach(string zone in new[]{"rings","access"})foreach(var polygon in garden.GetProperty(zone).EnumerateArray())
                foreach(var point in polygon[0].EnumerateArray())bounds=bounds.Expand(new(point[0].GetSingle(),point[1].GetSingle()));
            bounds=bounds.Grow(20);
            int x0=Math.Max(0,(int)MathF.Floor((bounds.Position.X-HarbourBounds.Position.X)/pixel.X)),y0=Math.Max(0,(int)MathF.Floor((bounds.Position.Y-HarbourBounds.Position.Y)/pixel.Y));
            int x1=Math.Min(paving.GetWidth(),(int)MathF.Ceiling((bounds.End.X-HarbourBounds.Position.X)/pixel.X)),y1=Math.Min(paving.GetHeight(),(int)MathF.Ceiling((bounds.End.Y-HarbourBounds.Position.Y)/pixel.Y));
            int width=x1-x0,height=y1-y0;var cells=new byte[width*height];var queue=new Queue<int>();
            var lots=_lots.Where(l=>l.Bounds.Intersects(bounds)).ToArray();
            var roads=groundRoads.SelectMany(r=>Enumerable.Range(1,r.Points.Count-1)
                .Where(i=>MathF.Max(r.Points[i-1].Y,r.Points[i].Y)<.05f && MathF.Min(r.Points[i-1].Y,r.Points[i].Y)>-.5f)
                .Select(i=>(A:new Vector2(r.Points[i-1].X,r.Points[i-1].Z),B:new Vector2(r.Points[i].X,r.Points[i].Z),Width:MathF.Max(12,r.Width)/2+4)))
                .Where(r=>new Rect2(r.A,Vector2.Zero).Expand(r.B).Grow(r.Width).Intersects(bounds)).ToArray();
            // Allow one texel for linear mask filtering; actual building interiors stay blocked.
            for(int y=0;y<height;y++)for(int x=0;x<width;x++)
            {
                if(paving.GetPixel(x+x0,y+y0).G<=0)continue;
                for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++)
                {int nx=x+dx,ny=y+dy;if(nx>=0 && ny>=0 && nx<width && ny<height)cells[ny*width+nx]=1;}
            }
            for(int y=0;y<height;y++)for(int x=0;x<width;x++)
            {
                int index=y*width+x;if(cells[index]==0)continue;
                var at=HarbourBounds.Position+new Vector2(x+x0+.5f,y+y0+.5f)*pixel;
                if(lots.Any(l=>l.Bounds.HasPoint(at) && Geometry2D.IsPointInPolygon(at,l.Polygon)) ||
                    seating.Any(prop=>at.DistanceTo(new(prop.Position.X,prop.Position.Z))<prop.Radius+.55f))
                {cells[index]=0;continue;}
                if(roads.Any(r=>at.DistanceTo(Geometry2D.GetClosestPointToSegment(at,r.A,r.B))<=r.Width))
                {cells[index]=2;queue.Enqueue(index);}
            }
            while(queue.TryDequeue(out int index))
            {
                int x=index%width,y=index/width;
                for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++)
                {
                    int nx=x+dx,ny=y+dy;if(nx<0 || ny<0 || nx>=width || ny>=height)continue;
                    int next=ny*width+nx;if(cells[next]!=1)continue;cells[next]=2;queue.Enqueue(next);
                }
            }
            foreach(var sample in garden.GetProperty("samples").EnumerateArray())
            {
                int x=(int)((sample[0].GetSingle()-HarbourBounds.Position.X)/pixel.X)-x0,y=(int)((sample[1].GetSingle()-HarbourBounds.Position.Y)/pixel.Y)-y0;
                if(x<0 || y<0 || x>=width || y>=height || cells[y*width+x]!=2)
                {disconnected.Add($"{garden.GetProperty("site").GetString()} at {sample.GetRawText()} (mask cell {x+x0},{y+y0})");continue;}
                checkedSamples++;
            }
        }
        if(disconnected.Count>0)throw new Exception("Eastern paths disconnected from public pavement: "+string.Join("; ",disconnected));
        GD.Print($"ANTILA_EAST_PATH_CONNECTIONS_OK: {checkedSamples} path/access samples across {gardens.Length} sites reach public pavement");
    }
}
