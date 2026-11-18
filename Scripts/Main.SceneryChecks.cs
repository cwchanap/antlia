using Godot;
using System;
using System.Collections.Generic;
using System.Linq;

public partial class Main
{
    private void CheckSharedBoxMeshes()
    {
        var root=new Node3D();AddChild(root);
        try
        {
            var size=new Vector3(1.25f,2.5f,3.75f);
            var a=Box(root,Vector3.Down*1000,size,"ff0000");
            var b=Box(root,Vector3.Down*1000,size,"0000ff");
            var c=Box(root,Vector3.Down*1000,size+Vector3.Up,"0000ff",true);
            if(a.Mesh.GetInstanceId()!=b.Mesh.GetInstanceId() || a.Mesh.GetInstanceId()==c.Mesh.GetInstanceId() ||
                a.MaterialOverride.GetInstanceId()==b.MaterialOverride.GetInstanceId() ||
                ((BoxMesh)c.Mesh).Size!=size+Vector3.Up ||
                ((BoxShape3D)root.FindChildren("*","CollisionShape3D",true,false).Cast<CollisionShape3D>().Single().Shape).Size!=size+Vector3.Up)
                throw new Exception("Equal-size boxes must share render geometry while retaining instance materials and collision dimensions");
        }
        finally{root.Free();}
        GD.Print("ANTILA_SHARED_BOX_MESHES_OK: shared geometry, independent materials and collision sizes");
    }

    private void CheckHarbourSceneryFiltering()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}
        var lotBounds=new[]{new Rect2(new(-140,-140),new(30,30)),new Rect2(new(250,250),new(8,8)),new Rect2(new(-2,126),new(5,5))};
        var lots=new Dictionary<long,List<int>>();
        for(int i=0;i<lotBounds.Length;i++)AddHarbourSceneryBounds(lots,lotBounds[i].Grow(3),i);
        foreach(var (p,margin) in new[]{(new Vector2(-128,-128),.6f),(new Vector2(-.01f,-.01f),0f),(new Vector2(128,128),1f),(new Vector2(-128.1f,-127.9f),3f),(new Vector2(1,128),3f)})
        {
            bool expected=false,actual=false;int previous=-1;
            lots.TryGetValue(HarbourSceneryCellKey(p),out var candidates);
            if(candidates!=null)foreach(int id in candidates)
            {
                Check(id>previous,"Harbour scenery cell candidates must keep source ordering");previous=id;
                if(lotBounds[id].Grow(margin).HasPoint(p))actual=true;
            }
            foreach(var bounds in lotBounds)if(bounds.Grow(margin).HasPoint(p))expected=true;
            Check(expected==actual,"Harbour lot bounds index must retain negative-coordinate and cell-edge matches");
            Check(candidates==null || candidates.Count<lotBounds.Length,"Harbour lot bounds query must filter distant fixtures");
        }
        Check(HarbourSceneryCellKey(new Vector2(-.01f,0))!=HarbourSceneryCellKey(new Vector2(0,0)) &&
            HarbourSceneryCellKey(new Vector2(-128,0))!=HarbourSceneryCellKey(new Vector2(-128.01f,0)),
            "Harbour scenery grid must floor negative coordinates at exact cell edges");

        var roads=new[]{(new Vector2(-260,-128),new Vector2(-100,-128)),(new Vector2(128,250),new Vector2(128,270)),(new Vector2(255,255),new Vector2(260,255))};
        var roadIndex=new Dictionary<long,List<int>>();
        for(int i=0;i<roads.Length;i++)AddHarbourSceneryBounds(roadIndex,new Rect2(roads[i].Item1,Vector2.Zero).Expand(roads[i].Item2).Grow(9),i);
        foreach(var (p,margin) in new[]{(new Vector2(-128,-120),3f),(new Vector2(128,244),1f),(new Vector2(247,255),3f),(new Vector2(0,0),.6f)})
        {
            bool expected=false,actual=false;
            foreach(var (a,b) in roads)if(p.DistanceTo(Geometry2D.GetClosestPointToSegment(p,a,b))<6+margin)expected=true;
            if(roadIndex.TryGetValue(HarbourSceneryCellKey(p),out var candidates))
                foreach(int id in candidates)if(p.DistanceTo(Geometry2D.GetClosestPointToSegment(p,roads[id].Item1,roads[id].Item2))<6+margin)actual=true;
            Check(expected==actual,"Harbour road bounds index must retain negative-coordinate and cell-edge clearance hits");
        }

        var details=new[]{(new Vector2(-128,-128),2.7f),(new Vector2(128,128),3f),(new Vector2(255,255),.3f)};
        var detailIndex=new Dictionary<long,List<int>>();
        for(int i=0;i<details.Length;i++)AddHarbourSceneryBounds(detailIndex,new Rect2(details[i].Item1,Vector2.Zero).Grow(details[i].Item2+4),i);
        foreach(var (p,margin) in new[]{(new Vector2(-122,-128),3f),(new Vector2(128,122),3f),(new Vector2(251,255),3f),(new Vector2(0,0),.6f)})
        {
            bool expected=false,actual=false;
            foreach(var (position,radius) in details)if(p.DistanceTo(position)<radius+margin+1)expected=true;
            if(detailIndex.TryGetValue(HarbourSceneryCellKey(p),out var candidates))
                foreach(int id in candidates)if(p.DistanceTo(details[id].Item1)<details[id].Item2+margin+1)actual=true;
            Check(expected==actual,"Harbour dynamic detail index must retain negative-coordinate and cell-edge collision hits");
        }
        // The restored Sham Shui Po lots and park entrances reserve space from roadside props.
        Check(_harbourSceneryCounts==(1268,4531,544,138),
            $"Harbour scenery placement changed: {_harbourSceneryCounts.Trees} trees, {_harbourSceneryCounts.Lamps} lamps, {_harbourSceneryCounts.People} pedestrians, {_harbourSceneryCounts.Kiosks} kiosks");
        GD.Print("ANTILA_HARBOUR_SCENERY_FILTER_OK: negative coordinates, cell edges, exact road/lot/detail matches and deterministic source ordering");
    }
}
