using Godot;
using System;

public partial class Main
{
    private void CheckSurfaceMasks()
    {
        // A large two-dimensional extract must be bounded by bytes, not just the GPU's axis limit.
        foreach(var size in new[]{new Vector2(18860,13430),new Vector2(8200,1),new Vector2(1,8200)})
        {
            var bounds=size.X>100 && size.Y>100?new Rect2(-13880,-11280,size.X,size.Y):new Rect2(Vector2.Zero,size);
            using(var mask=Map.CreateSurfaceMask(Array.Empty<Vector2>(),Array.Empty<(Vector3,Vector3)>(),Array.Empty<Vector2[]>(),
                bounds,new[]{(new Vector2(3000,2000),new Vector2(3050,2000),6f),
                    (new Vector2(-375.1066f,1843.9841f),new Vector2(-376.6356f,1847.6803f),6f),
                    (new Vector2(-376.6356f,1847.6803f),new Vector2(-378.1646f,1851.3765f),6f),
                    (new Vector2(441.7288f,1579.1021f),new Vector2(445.7283f,1579.0422f),6f),
                    (new Vector2(445.7283f,1579.0422f),new Vector2(449.7206f,1578.8447f),6f)},2))
            {
                if(mask.GetWidth()<1 || mask.GetHeight()<1 || mask.GetWidth()>16384 || mask.GetHeight()>16384 ||
                    (long)mask.GetWidth()*mask.GetHeight()*3>192L*1024*1024)
                    throw new Exception("Terrain mask exceeds the 192 MiB RGB pixel budget");
                if(size.X>100 && size.Y>100)
                {
                    Color At(Vector2 p)
                    {
                        var pixel=(p-bounds.Position)/bounds.Size*new Vector2(mask.GetWidth(),mask.GetHeight())-Vector2.One*.5f;
                        int x=Mathf.FloorToInt(pixel.X),y=Mathf.FloorToInt(pixel.Y);float u=pixel.X-x,v=pixel.Y-y;
                        return mask.GetPixel(x,y).Lerp(mask.GetPixel(x+1,y),u).Lerp(mask.GetPixel(x,y+1).Lerp(mask.GetPixel(x+1,y+1),u),v);
                    }
                    if(At(new(3025,2000)).R<.99f)throw new Exception("Budgeted terrain mask lost the distant road's world-space position");
                    if(At(new(-384.0281f,1844.6223f)).G<=.9f || At(new(-369.2431f,1850.7383f)).G<=.9f)
                        throw new Exception("Coarse terrain sampling lost the TD_286 roadside paving");
                    if(At(new(446.1236f,1587.0324f)).G<=.9f || At(new(445.3330f,1571.0520f)).G<=.9f)
                        throw new Exception("Coarse terrain sampling lost the ID_01272 roadside paving");
                }
            }
        }
        var park=new[]{new Vector2(0,0),new Vector2(0,40),new Vector2(40,40),new Vector2(40,0)};
        using(var mask=Map.CreateSurfaceMask(park,Array.Empty<(Vector3,Vector3)>(),Array.Empty<Vector2[]>(),
            new Rect2(-100,-100,200,200),new[]{(new Vector2(-90,-60),new Vector2(90,-60),6f)},2))
        {
            Color At(Vector2 p)=>mask.GetPixel((int)((p.X+100)/200*mask.GetWidth()),(int)((p.Y+100)/200*mask.GetHeight()));
            if(At(new(20,20)).B<.99f || At(new(-80,-60)).R<.99f || At(new(-80,-52)).G<.99f || At(new(-80,60)).R>0)
                throw new Exception("Surface-mask resizing lost world-space road, pavement or park placement");
        }
        GD.Print("ANTILA_SURFACE_MASKS_OK: bounded RGB images, thin extracts, world-space asphalt / pavement / park");
    }
}
