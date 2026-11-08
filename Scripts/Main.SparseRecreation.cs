using Godot;
using System.Buffers.Binary;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using System.Threading.Tasks;
using FileAccess=Godot.FileAccess;

public partial class Main
{
    private const string SparseRecreationRoot="res://Assets/Textures/TerrainMasks/";
    private const string SparseRecreationEvidenceRoot="user://sparse-recreation-check/";
    private const string SparseRecreationMetadataPath="res://Data/sparse-recreation.json";
    private const string SparseRecreationAtlasPath=SparseRecreationRoot+"recreation-sparse-atlas.res";
    private const string SparseRecreationLookupPath=SparseRecreationRoot+"recreation-sparse-lookup.res";
    private const string SparseRecreationLodPath=SparseRecreationRoot+"recreation-sparse-lod.res";
    private const int SparseMetadataVersion=1,SparsePageSize=128,SparseGutter=1,SparsePaddedPage=SparsePageSize+2*SparseGutter,
        SparseMipLimit=14,SparseLodRampWidth=8192,SparseLodRampPayloadBytes=65532;
    private const long SparsePayloadLimit=32L*1024*1024;
    private static readonly JsonSerializerOptions SparseJsonOptions=new(){PropertyNamingPolicy=JsonNamingPolicy.CamelCase,WriteIndented=true};
    private sealed record SparseMipInfo(int Width,int Height,int LookupOffset,int PageColumns,int PageRows,int ActivePages);
    private sealed record SparseAssetInfo(int SchemaVersion,float[] SourceBounds,int Width,int Height,int MipLevels,string SourceSha256,string SourceDataSha256,string AuthoredMipSha256,
        int AtlasWidth,int AtlasHeight,int AtlasColumns,int AtlasRows,int LookupWidth,int LookupHeight,int ActivePages,long TexturePayloadBytes,
        string AtlasSha256,string LookupSha256,string LodRampSha256,SparseMipInfo[] Mips);

    private Texture2D LoadSparseRecreation(Rect2 bounds)
    {
        var sparse=ReadSparseRecreation();var source=GetTerrainMaskMetadata("recreation_mask",bounds);
        var (atlas,lookup,lodRamp)=LoadSparseTextures(sparse,source,bounds);
        ConfigureSparseRecreation(_terrain,sparse,atlas,lookup,lodRamp);
        GD.Print($"ANTILA_SPARSE_RECREATION_LOADED: {sparse.ActivePages} padded pages; atlas {sparse.AtlasWidth}x{sparse.AtlasHeight}; {sparse.TexturePayloadBytes} decoded texture bytes");
        return atlas;
    }

    private static (Texture2D Atlas,Texture2D Lookup,Texture2D LodRamp) LoadSparseTextures(SparseAssetInfo sparse,TerrainMaskMetadata source,Rect2 bounds)
    {
        ValidateSparseMetadata(sparse,source,bounds);
        VerifySparseResourceHash(SparseRecreationAtlasPath,sparse.AtlasSha256);
        VerifySparseResourceHash(SparseRecreationLookupPath,sparse.LookupSha256);
        VerifySparseResourceHash(SparseRecreationLodPath,sparse.LodRampSha256);
        var atlas=GD.Load<Texture2D>(SparseRecreationAtlasPath)??throw new Exception("Sparse recreation atlas is missing; run --sparse-recreation-bake");
        var lookup=GD.Load<Texture2D>(SparseRecreationLookupPath)??throw new Exception("Sparse recreation lookup is missing; run --sparse-recreation-bake");
        var lodRamp=GD.Load<Texture2D>(SparseRecreationLodPath)??throw new Exception("Sparse recreation LOD ramp is missing; run --sparse-recreation-bake");
        if(atlas.GetWidth()!=sparse.AtlasWidth || atlas.GetHeight()!=sparse.AtlasHeight ||
           lookup.GetWidth()!=sparse.LookupWidth || lookup.GetHeight()!=sparse.LookupHeight ||
           lodRamp.GetWidth()!=SparseLodRampWidth || lodRamp.GetHeight()!=1)
            throw new Exception("Sparse recreation resource dimensions differ from their metadata");
        return (atlas,lookup,lodRamp);
    }

    private static void ValidateSparseMetadata(SparseAssetInfo sparse,TerrainMaskMetadata source,Rect2 bounds)
    {
        if(sparse.SchemaVersion!=SparseMetadataVersion)throw new Exception("Sparse recreation metadata schema version is unsupported; rerun --sparse-recreation-bake");
        if(source.Bounds is null || source.Bounds.Length!=4 || source.Width<=0 || source.Height<=0 || source.Width>16384 || source.Height>16384 || source.MipLevels!=SparseMipLimit ||
           source.Bounds.Any(v=>!float.IsFinite(v)) || source.Bounds[2]<=0 || source.Bounds[3]<=0)
            throw new Exception("Terrain mask source bounds or mip dimensions are invalid");
        if(sparse.SourceBounds is null || sparse.SourceBounds.Length!=4 || !sparse.SourceBounds.SequenceEqual(source.Bounds) ||
           sparse.Width!=source.Width || sparse.Height!=source.Height || sparse.MipLevels!=source.MipLevels || sparse.SourceSha256!=source.Sha256)
            throw new Exception("Sparse recreation metadata does not match Data/terrain-masks.json; rerun --sparse-recreation-bake");
        if(sparse.SourceDataSha256!=RecreationSourceSha256())
            throw new Exception("Sparse recreation metadata does not match the bundled recreation source JSON; rerun --sparse-recreation-bake");
        if(!bounds.IsEqualApprox(new Rect2(source.Bounds[0],source.Bounds[1],source.Bounds[2],source.Bounds[3])))
            throw new Exception("Sparse recreation bounds differ from the current source data");
        bool Sha(string? value)=>value is {Length:64} && value.All(Uri.IsHexDigit);
        if(!Sha(sparse.SourceSha256) || !Sha(sparse.SourceDataSha256) || !Sha(sparse.AuthoredMipSha256) || !Sha(sparse.AtlasSha256) || !Sha(sparse.LookupSha256) || !Sha(sparse.LodRampSha256))
            throw new Exception("Sparse recreation metadata contains an invalid SHA-256");
        if(sparse.Mips is null || sparse.Mips.Length!=SparseMipLimit)
            throw new Exception($"Sparse recreation metadata must describe exactly {SparseMipLimit} source mip levels");
        int width=source.Width,height=source.Height,lookupWidth=0,lookupOffset=0,activePages=0;
        for(int mip=0;mip<SparseMipLimit;mip++)
        {
            var info=sparse.Mips[mip]??throw new Exception($"Sparse recreation mip {mip} metadata is missing");
            int columns=(width+SparsePageSize-1)/SparsePageSize,rows=(height+SparsePageSize-1)/SparsePageSize;
            if(info.Width!=width || info.Height!=height || info.LookupOffset!=lookupOffset || info.PageColumns!=columns || info.PageRows!=rows ||
               info.ActivePages<0 || info.ActivePages>columns*rows)
                throw new Exception($"Sparse recreation mip {mip} grid is invalid");
            lookupWidth=Math.Max(lookupWidth,columns);lookupOffset=checked(lookupOffset+rows);activePages=checked(activePages+info.ActivePages);
            width=Math.Max(1,width/2);height=Math.Max(1,height/2);
        }
        if(activePages<=0 || activePages>=ushort.MaxValue || sparse.ActivePages!=activePages ||
           sparse.LookupWidth!=lookupWidth || sparse.LookupHeight!=lookupOffset || lookupWidth>16384 || lookupOffset>16384)
            throw new Exception("Sparse recreation active-page or lookup dimensions are invalid");
        int atlasColumns=(int)Math.Ceiling(Math.Sqrt(activePages+1)),atlasRows=(activePages+atlasColumns)/atlasColumns;
        int atlasWidth=(int)System.Numerics.BitOperations.RoundUpToPowerOf2((uint)(atlasColumns*SparsePaddedPage));
        int atlasHeight=(int)System.Numerics.BitOperations.RoundUpToPowerOf2((uint)(atlasRows*SparsePaddedPage));
        if(atlasWidth>16384 || atlasHeight>16384 || sparse.AtlasColumns!=atlasColumns || sparse.AtlasRows!=atlasRows ||
           sparse.AtlasWidth!=atlasWidth || sparse.AtlasHeight!=atlasHeight)
            throw new Exception("Sparse recreation atlas dimensions exceed the Compatibility renderer limit or differ from the page grid");
        long payloadBytes=(long)atlasWidth*atlasHeight*3+(long)lookupWidth*lookupOffset*3+SparseLodRampPayloadBytes;
        if(payloadBytes>SparsePayloadLimit)throw new Exception($"Sparse recreation decoded texture payload exceeds {SparsePayloadLimit} bytes");
        if(sparse.TexturePayloadBytes!=payloadBytes)throw new Exception("Sparse recreation decoded payload size differs from its metadata");
    }

    private static void VerifySparseResourceHash(string path,string expectedSha256)
    {
        using var file=FileAccess.Open(path,FileAccess.ModeFlags.Read)??throw new Exception($"Sparse recreation resource is missing: {path}; run --sparse-recreation-bake");
        ulong fileLength=file.GetLength();
        if(fileLength==0 || fileLength>(ulong)(SparsePayloadLimit+4*1024*1024))throw new Exception($"Sparse recreation resource size is invalid: {path}");
        long length=checked((long)fileLength);
        if(Convert.ToHexString(SHA256.HashData(file.GetBuffer(length)))!=expectedSha256)
            throw new Exception($"Sparse recreation resource hash differs from Data/sparse-recreation.json: {path}; rerun --sparse-recreation-bake");
    }

    private static string RecreationSourceSha256()
    {
        var eastern=FileAccess.GetFileAsBytes("res://Data/east-kowloon-open-spaces.json");
        var mongKok=FileAccess.GetFileAsBytes("res://Data/mong-kok-open-spaces.json");
        using var hash=IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        var length=new byte[4];
        BinaryPrimitives.WriteInt32LittleEndian(length,eastern.Length);hash.AppendData(length);hash.AppendData(eastern);
        BinaryPrimitives.WriteInt32LittleEndian(length,mongKok.Length);hash.AppendData(length);hash.AppendData(mongKok);
        return Convert.ToHexString(hash.GetHashAndReset());
    }

    private static void ConfigureSparseRecreation(ShaderMaterial material,SparseAssetInfo sparse,Texture2D atlas,Texture2D lookup,Texture2D lodRamp)
    {
        var mips=new Godot.Collections.Array<Vector4>();
        foreach(var mip in sparse.Mips)mips.Add(new Vector4(mip.Width,mip.Height,mip.LookupOffset,mip.PageColumns));
        material.SetShaderParameter("sparse_recreation_atlas",atlas);
        material.SetShaderParameter("sparse_recreation_lookup",lookup);
        material.SetShaderParameter("sparse_recreation_lod_ramp",lodRamp);
        material.SetShaderParameter("sparse_recreation_size",new Vector2(sparse.Width,sparse.Height));
        material.SetShaderParameter("sparse_recreation_atlas_size",new Vector2(sparse.AtlasWidth,sparse.AtlasHeight));
        material.SetShaderParameter("sparse_recreation_lookup_size",new Vector2(sparse.LookupWidth,sparse.LookupHeight));
        material.SetShaderParameter("sparse_recreation_page_columns",sparse.AtlasColumns);
        material.SetShaderParameter("sparse_recreation_mip_count",sparse.MipLevels);
        material.SetShaderParameter("sparse_recreation_mips",mips);
        material.SetShaderParameter("sparse_recreation_enabled",true);
    }

    private SparseAssetInfo ReadSparseRecreation()
    {
        if(!FileAccess.FileExists(SparseRecreationMetadataPath))throw new Exception("Sparse recreation metadata is missing; run --sparse-recreation-bake");
        return JsonSerializer.Deserialize<SparseAssetInfo>(FileAccess.GetFileAsString(SparseRecreationMetadataPath),SparseJsonOptions)
            ??throw new Exception("Sparse recreation metadata is empty");
    }

    private void BakeSparseRecreation()
    {
        _terrainMaskManifest=ReadTerrainMaskManifest();
        var expected=_terrainMaskManifest["recreation_mask"];
        var sourceBounds=new Rect2(expected.Bounds[0],expected.Bounds[1],expected.Bounds[2],expected.Bounds[3]);
        using var source=CreateRecreationMask(sourceBounds);
        RequireSameTerrainMask(expected,DescribeTerrainMask(sourceBounds,source),"recreation_mask","generated source");
        if(source.GetFormat()!=Image.Format.Rgb8 || source.GetMipmapCount()+1!=expected.MipLevels || !source.HasMipmaps())
            throw new Exception("Generated recreation mask must expose its complete RGB8 mip chain");
        var sourceBytes=source.GetData();
        string sourceDataSha256=RecreationSourceSha256();
        string authoredMipSha256=Convert.ToHexString(SHA256.HashData(sourceBytes));
        int mipCount=source.GetMipmapCount()+1;
        if(mipCount!=SparseMipLimit)throw new Exception($"Expected {SparseMipLimit} imported mip levels, found {mipCount}");
        var mipInfo=new SparseMipInfo[mipCount];int lookupWidth=0,lookupHeight=0,width=source.GetWidth(),height=source.GetHeight();
        for(int mip=0;mip<mipCount;mip++)
        {
            int cols=(width+SparsePageSize-1)/SparsePageSize,rows=(height+SparsePageSize-1)/SparsePageSize;
            if(mip==0)lookupWidth=cols;else if(cols>lookupWidth)throw new Exception("Sparse lookup mip grid unexpectedly grows");
            mipInfo[mip]=new(width,height,lookupHeight,cols,rows,0);lookupHeight+=rows;
            width=Math.Max(1,width/2);height=Math.Max(1,height/2);
        }
        long lookupPayloadBytes=(long)lookupWidth*lookupHeight*3;
        if(lookupWidth<=0 || lookupHeight<=0 || lookupWidth>16384 || lookupHeight>16384 || lookupPayloadBytes>SparsePayloadLimit)
            throw new Exception("Sparse recreation lookup exceeds the Compatibility renderer or 32 MiB payload limit");
        var lookupBytes=new byte[checked((int)lookupPayloadBytes)];int activePages=0;
        for(int mip=0;mip<mipCount;mip++)
        {
            var info=mipInfo[mip];int sourceOffset=checked((int)source.GetMipmapOffset(mip)),levelPages=0;
            for(int py=0;py<info.PageRows;py++)for(int px=0;px<info.PageColumns;px++)
            {
                bool active=false;
                for(int ty=0;ty<SparsePaddedPage && !active;ty++)
                {
                    int sy=Math.Clamp(py*SparsePageSize+ty-SparseGutter,0,info.Height-1);
                    for(int tx=0;tx<SparsePaddedPage && !active;tx++)
                    {
                        int sx=Math.Clamp(px*SparsePageSize+tx-SparseGutter,0,info.Width-1),at=sourceOffset+(sy*info.Width+sx)*3;
                        active=sourceBytes[at]!=0 || sourceBytes[at+1]!=0 || sourceBytes[at+2]!=0;
                    }
                }
                if(!active)continue;
                int id=++activePages,lookupAt=((info.LookupOffset+py)*lookupWidth+px)*3;
                lookupBytes[lookupAt]=(byte)(id&255);lookupBytes[lookupAt+1]=(byte)(id>>8);levelPages++;
            }
            mipInfo[mip]=info with{ActivePages=levelPages};
        }
        if(activePages>=ushort.MaxValue)throw new Exception($"Sparse atlas lookup supports at most {ushort.MaxValue-1} active pages; found {activePages}");
        int atlasColumns=(int)Math.Ceiling(Math.Sqrt(activePages+1)),atlasRows=(activePages+atlasColumns)/atlasColumns;
        int atlasWidth=(int)System.Numerics.BitOperations.RoundUpToPowerOf2((uint)(atlasColumns*SparsePaddedPage));
        int atlasHeight=(int)System.Numerics.BitOperations.RoundUpToPowerOf2((uint)(atlasRows*SparsePaddedPage));
        if(atlasWidth>16384 || atlasHeight>16384)throw new Exception($"Sparse atlas exceeds the GL Compatibility 16,384 texture edge: {atlasWidth}x{atlasHeight}");
        long texturePayloadBytes=(long)atlasWidth*atlasHeight*3+lookupPayloadBytes+SparseLodRampPayloadBytes;
        if(texturePayloadBytes>SparsePayloadLimit)throw new Exception($"Sparse recreation payload exceeds the 32 MiB cap: {texturePayloadBytes} bytes");
        var atlasBytes=new byte[checked((int)((long)atlasWidth*atlasHeight*3))];
        for(int mip=0;mip<mipCount;mip++)
        {
            var info=mipInfo[mip];int sourceOffset=checked((int)source.GetMipmapOffset(mip));
            for(int py=0;py<info.PageRows;py++)for(int px=0;px<info.PageColumns;px++)
            {
                int lookupAt=((info.LookupOffset+py)*lookupWidth+px)*3,id=lookupBytes[lookupAt]|lookupBytes[lookupAt+1]<<8;
                if(id==0)continue;
                int originX=id%atlasColumns*SparsePaddedPage,originY=id/atlasColumns*SparsePaddedPage;
                for(int ty=0;ty<SparsePaddedPage;ty++)
                {
                    int sy=Math.Clamp(py*SparsePageSize+ty-SparseGutter,0,info.Height-1);
                    for(int tx=0;tx<SparsePaddedPage;tx++)
                    {
                        int sx=Math.Clamp(px*SparsePageSize+tx-SparseGutter,0,info.Width-1);
                        int from=sourceOffset+(sy*info.Width+sx)*3,to=((originY+ty)*atlasWidth+originX+tx)*3;
                        atlasBytes[to]=sourceBytes[from];atlasBytes[to+1]=sourceBytes[from+1];atlasBytes[to+2]=sourceBytes[from+2];
                    }
                }
            }
        }
        using var atlasImage=Image.CreateFromData(atlasWidth,atlasHeight,false,Image.Format.Rgb8,atlasBytes);
        using var lookupImage=Image.CreateFromData(lookupWidth,lookupHeight,false,Image.Format.Rgb8,lookupBytes);
        var lodRampBytes=new byte[SparseLodRampPayloadBytes];int lodRampOffset=0;
        for(int mip=0;mip<SparseMipLimit;mip++)
        {
            int levelWidth=SparseLodRampWidth>>mip,gray=mip^(mip>>1);
            for(int x=0;x<levelWidth;x++)
            {
                lodRampBytes[lodRampOffset++]=(gray&1)!=0?(byte)255:(byte)0;
                lodRampBytes[lodRampOffset++]=(gray&2)!=0?(byte)255:(byte)0;
                lodRampBytes[lodRampOffset++]=(gray&4)!=0?(byte)255:(byte)0;
                lodRampBytes[lodRampOffset++]=(gray&8)!=0?(byte)255:(byte)0;
            }
        }
        using var lodRampImage=Image.CreateFromData(SparseLodRampWidth,1,true,Image.Format.Rgba8,lodRampBytes);
        var atlas=ImageTexture.CreateFromImage(atlasImage);var lookup=ImageTexture.CreateFromImage(lookupImage);
        var lodRamp=ImageTexture.CreateFromImage(lodRampImage);
        string atlasSha256=SaveSparseTexture(atlas,SparseRecreationAtlasPath);
        string lookupSha256=SaveSparseTexture(lookup,SparseRecreationLookupPath);
        string lodRampSha256=SaveSparseTexture(lodRamp,SparseRecreationLodPath);
        var sparse=new SparseAssetInfo(SparseMetadataVersion,(float[])expected.Bounds.Clone(),expected.Width,expected.Height,mipCount,expected.Sha256,sourceDataSha256,authoredMipSha256,
            atlasWidth,atlasHeight,atlasColumns,atlasRows,lookupWidth,lookupHeight,activePages,texturePayloadBytes,
            atlasSha256,lookupSha256,lodRampSha256,mipInfo);
        SaveSparseMetadata(sparse);
        GD.Print($"ANTILA_SPARSE_RECREATION_BAKED: {activePages} padded pages/{mipCount} mips; atlas {atlasWidth}x{atlasHeight}; lookup {lookupWidth}x{lookupHeight}; {sparse.TexturePayloadBytes} decoded texture bytes");
    }

    private static string SaveSparseTexture(Resource resource,string path)
    {
        string absolute=ProjectSettings.GlobalizePath(path),temporaryPath=path+".tmp.res",temporaryAbsolute=ProjectSettings.GlobalizePath(temporaryPath);
        Directory.CreateDirectory(Path.GetDirectoryName(absolute)!);
        try
        {
            var error=ResourceSaver.Save(resource,temporaryPath,ResourceSaver.SaverFlags.Compress);
            if(error!=Error.Ok)throw new Exception($"Could not save sparse terrain texture '{path}': {error}");
            File.Move(temporaryAbsolute,absolute,true);
            return HashSparseResource(path);
        }
        finally{if(File.Exists(temporaryAbsolute))File.Delete(temporaryAbsolute);}
    }

    private static string HashSparseResource(string path)
    {
        using var file=FileAccess.Open(path,FileAccess.ModeFlags.Read)??throw new Exception($"Could not read sparse terrain texture '{path}'");
        ulong fileLength=file.GetLength();
        if(fileLength==0 || fileLength>(ulong)(SparsePayloadLimit+4*1024*1024))throw new Exception($"Sparse terrain texture file size is invalid: '{path}'");
        long length=checked((long)fileLength);
        return Convert.ToHexString(SHA256.HashData(file.GetBuffer(length)));
    }

    private static void SaveSparseMetadata(SparseAssetInfo sparse)
    {
        string absolute=ProjectSettings.GlobalizePath(SparseRecreationMetadataPath),temporary=absolute+".tmp";
        Directory.CreateDirectory(Path.GetDirectoryName(absolute)!);
        try
        {
            File.WriteAllText(temporary,JsonSerializer.Serialize(sparse,SparseJsonOptions));
            File.Move(temporary,absolute,true);
        }
        finally{if(File.Exists(temporary))File.Delete(temporary);}
    }

    private void RunSparseRecreationCheck()
    {
        _=RunSparseRecreationCheckAsync();
    }

    private async Task RunSparseRecreationCheckAsync()
    {
        try
        {
            if(DisplayServer.GetName()=="headless")throw new Exception("Native GL Compatibility renderer required for sparse recreation sampling checks");
            _terrainMaskManifest=ReadTerrainMaskManifest();var sourceInfo=_terrainMaskManifest["recreation_mask"];
            var bounds=new Rect2(sourceInfo.Bounds[0],sourceInfo.Bounds[1],sourceInfo.Bounds[2],sourceInfo.Bounds[3]);
            var sparse=ReadSparseRecreation();
            var (atlas,lookup,lodRamp)=LoadSparseTextures(sparse,sourceInfo,bounds);
            using var source=CreateRecreationMask(bounds);
            RequireSameTerrainMask(sourceInfo,DescribeTerrainMask(bounds,source),"recreation_mask","generated source");
            var sourceTexture=GD.Load<Texture2D>(TerrainMaskAssetPath+"recreation_mask.png")??throw new Exception("Imported recreation reference is missing");
            using var atlasImage=atlas.GetImage();using var lookupImage=lookup.GetImage();
            if(Convert.ToHexString(SHA256.HashData(source.GetData()))!=sparse.AuthoredMipSha256)
                throw new Exception("Authored recreation mip bytes changed since --sparse-recreation-bake; rerun the bake");
            long checkedPixels=CheckSparseRoundTrip(source,atlasImage,lookupImage,sparse);
            GD.Print($"ANTILA_SPARSE_ROUNDTRIP_OK: {checkedPixels} authored mip pixels");
            var shader=GD.Load<Shader>("res://Assets/Materials/terrain.gdshader")??throw new Exception("Terrain shader is missing");
            var viewport=new SubViewport {Size=new(512,512),World3D=new World3D(),RenderTargetUpdateMode=SubViewport.UpdateMode.Always};AddChild(viewport);
            try
            {
                var material=new ShaderMaterial {Shader=shader};material.SetShaderParameter("recreation_mask",sourceTexture);
                ConfigureSparseRecreation(material,sparse,atlas,lookup,lodRamp);
                material.SetShaderParameter("recreation_origin",Vector2.Zero);material.SetShaderParameter("recreation_size",Vector2.One);
                material.SetShaderParameter("map_origin",Vector2.Zero);material.SetShaderParameter("map_size",Vector2.One);
                material.SetShaderParameter("sparse_recreation_check_mode",2);material.SetShaderParameter("sparse_recreation_forced_lod",-1f);
                material.SetShaderParameter("sparse_recreation_error_threshold",1f/255);
                ImageTexture Solid(Color color){using var image=Image.CreateEmpty(2,2,false,Image.Format.Rgb8);image.Fill(color);return ImageTexture.CreateFromImage(image);}
                material.SetShaderParameter("surface_mask",Solid(Colors.Black));material.SetShaderParameter("harbour_mask",Solid(Colors.Black));
                material.SetShaderParameter("asphalt",Solid(Colors.White));material.SetShaderParameter("paving",Solid(Colors.White));
                material.SetShaderParameter("grass",Solid(Colors.White));material.SetShaderParameter("stone",Solid(Colors.White));
                viewport.AddChild(new WorldEnvironment {Environment=new Godot.Environment {
                    BackgroundMode=Godot.Environment.BGMode.Color,BackgroundColor=Colors.Black,
                    AmbientLightSource=Godot.Environment.AmbientSource.Color,AmbientLightColor=Colors.White,AmbientLightEnergy=1,
                    ReflectedLightSource=Godot.Environment.ReflectionSource.Disabled}});
                var ground=new MeshInstance3D {Mesh=new PlaneMesh {Size=Vector2.One},Position=new(.5f,0,.5f),MaterialOverride=material};viewport.AddChild(ground);
                var camera=new Camera3D {Projection=Camera3D.ProjectionType.Orthogonal,Size=1,Position=new(.5f,40,.5f),Current=true};
                viewport.AddChild(camera);camera.LookAt(new(.5f,0,.5f),Vector3.Forward);
                async Task Draw(){for(int i=0;i<3;i++)await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);RenderingServer.ForceDraw(false);}
                async Task<int> Compare(float lod,Vector2 center,float span)
                {
                    material.SetShaderParameter("sparse_recreation_forced_lod",lod);ground.Position=new(center.X,0,center.Y);
                    ((PlaneMesh)ground.Mesh).Size=new(span,span);camera.Size=span;camera.Position=new(center.X,40,center.Y);camera.LookAt(new(center.X,0,center.Y),Vector3.Forward);
                    await Draw();using var image=viewport.GetTexture().GetImage();int failures=0;
                    for(int y=0;y<image.GetHeight();y++)for(int x=0;x<image.GetWidth();x++)if(image.GetPixel(x,y).R>.5f)failures++;
                    return failures;
                }
                void PlaceNaturalView(Vector2 centerUv,float span,Vector2 mapScale,float rollDegrees=0f,bool perspective=false)
                {
                    var center=new Vector2(centerUv.X*mapScale.X,centerUv.Y*mapScale.Y);
                    material.SetShaderParameter("recreation_size",mapScale);ground.Position=new(center.X,0,center.Y);((PlaneMesh)ground.Mesh).Size=new(span,span);
                    camera.Projection=perspective?Camera3D.ProjectionType.Perspective:Camera3D.ProjectionType.Orthogonal;
                    if(perspective)
                    {
                        camera.Fov=45f;camera.Near=Mathf.Max(span*.01f,.0001f);
                        float distance=span/(2*Mathf.Tan(Mathf.DegToRad(camera.Fov*.5f)));
                        camera.Position=new(center.X,distance*.8660254f,center.Y+distance*.5f);
                    }
                    else{camera.Size=span;camera.Near=.05f;camera.Position=new(center.X,40,center.Y);}
                    camera.LookAt(new(center.X,0,center.Y),Vector3.Forward);
                    if(rollDegrees!=0f)camera.RotateObjectLocal(Vector3.Back,Mathf.DegToRad(rollDegrees));
                }
                async Task<int> CompareNatural(string name,Vector2 centerUv,float span,Vector2 mapScale,float rollDegrees=0f,bool perspective=false)
                {
                    material.SetShaderParameter("sparse_recreation_forced_lod",-1f);material.SetShaderParameter("sparse_recreation_check_mode",1);
                    material.SetShaderParameter("sparse_recreation_enabled",false);PlaceNaturalView(centerUv,span,mapScale,rollDegrees,perspective);await Draw();
                    using(var dense=viewport.GetTexture().GetImage())
                    {
                        var sample=dense.GetPixel(dense.GetWidth()/2,dense.GetHeight()/2);
                        if(Mathf.Max(sample.R,Mathf.Max(sample.G,sample.B))<.01f)throw new Exception($"Dense natural-LOD view '{name}' missed its positive recreation-mask sample");
                    }
                    material.SetShaderParameter("sparse_recreation_check_mode",2);material.SetShaderParameter("sparse_recreation_enabled",true);await Draw();
                    using var image=viewport.GetTexture().GetImage();int failures=0;
                    for(int y=0;y<image.GetHeight();y++)for(int x=0;x<image.GetWidth();x++)if(image.GetPixel(x,y).R>.5f)failures++;
                    if(failures>0)GD.Print($"ANTILA_SPARSE_DIFF: natural {name}; {failures} pixels >= 1/255");
                    return failures;
                }
                var levels=new SortedSet<float>();
                for(int i=0;i<sparse.MipLevels;i++)levels.Add(i);
                for(int i=0;i<sparse.MipLevels-1;i++)levels.Add(i+.5f);
                for(int i=1;i<sparse.MipLevels;i++){levels.Add(i-.01f);levels.Add(i+.01f);}
                var probes=new List<(string Name,Vector2 Uv,float Span)>{("full-map",new(.5f,.5f),1f)};
                float pageSpan=8f/sourceInfo.Width;
                var sportSamples=SparseRecreationSportSamples(bounds).ToArray();
                foreach(var uv in sportSamples)probes.Add(("sport",uv,pageSpan));
                probes.Add(("page-x",new(128f/sourceInfo.Width,.5f),pageSpan));
                probes.Add(("page-y",new(.5f,128f/sourceInfo.Height),pageSpan));
                probes.Add(("page-mid-x",new(.5f,.5f),pageSpan));
                probes.Add(("outer-left",new(0,.5f),pageSpan));probes.Add(("outer-right",new(1,.5f),pageSpan));
                probes.Add(("outer-top",new(.5f,0),pageSpan));probes.Add(("outer-bottom",new(.5f,1),pageSpan));
                var baseMip=sparse.Mips[0];var sourceBytes=source.GetData();Vector2 activePageSeam=Vector2.Zero;bool foundActiveSeam=false;
                for(int x=SparsePageSize;x<baseMip.Width && !foundActiveSeam;x+=SparsePageSize)for(int y=0;y<baseMip.Height && !foundActiveSeam;y++)
                {
                    for(int dx=-1;dx<=1;dx++)
                    {
                        int at=(y*baseMip.Width+x+dx)*3;
                        if(sourceBytes[at]==0 && sourceBytes[at+1]==0 && sourceBytes[at+2]==0)continue;
                        activePageSeam=new(x/(float)baseMip.Width,(y+.5f)/baseMip.Height);foundActiveSeam=true;break;
                    }
                }
                if(!foundActiveSeam)throw new Exception("Sparse base mip has no active page seam to probe");
                probes.Add(("active-page-seam",activePageSeam,pageSpan));
                long comparisons=0;int failedSamples=0;
                foreach(var probe in probes)foreach(float lod in levels.Append(-1f))
                {int failures=await Compare(lod,probe.Uv,probe.Span);failedSamples+=failures;comparisons+=512L*512;
                    if(failures>0)GD.Print($"ANTILA_SPARSE_DIFF: {probe.Name} lod {lod}; {failures} pixels >= 1/255");}
                foreach(float lod in new[]{.5f,1.5f,3.5f})
                {failedSamples+=await Compare(-1f,sportSamples.First(),512f*Mathf.Pow(2,lod)/sourceInfo.Width);comparisons+=512L*512;}
                var sport=sportSamples.First();var yDominantScale=new Vector2(4,1);
                foreach(float lod in new[]{.5f,1.5f,3.5f})
                {
                    float span=512f*Mathf.Pow(2,lod)/sourceInfo.Width;
                    failedSamples+=await CompareNatural($"y-dominant lod {lod}",sport,span,yDominantScale);comparisons+=512L*512;
                }
                float rotatedSpan=512f*Mathf.Pow(2,1.5f)/sourceInfo.Width;
                failedSamples+=await CompareNatural("y-dominant rotated-45 lod 1.5",sport,rotatedSpan,yDominantScale,45f);comparisons+=512L*512;
                failedSamples+=await CompareNatural("y-dominant perspective lod 1.5",sport,rotatedSpan,yDominantScale,perspective:true);comparisons+=512L*512;
                material.SetShaderParameter("sparse_recreation_check_mode",1);material.SetShaderParameter("sparse_recreation_forced_lod",-1f);
                material.SetShaderParameter("recreation_size",Vector2.One);camera.Projection=Camera3D.ProjectionType.Orthogonal;camera.Near=.05f;
                ground.Position=new(sport.X,0,sport.Y);((PlaneMesh)ground.Mesh).Size=new(pageSpan,pageSpan);camera.Size=pageSpan;camera.Position=new(sport.X,40,sport.Y);camera.LookAt(new(sport.X,0,sport.Y),Vector3.Forward);
                material.SetShaderParameter("sparse_recreation_enabled",false);await Draw();
                string output=ProjectSettings.GlobalizePath(SparseRecreationEvidenceRoot);Directory.CreateDirectory(output);
                GD.Print($"ANTILA_SPARSE_RECREATION_CAPTURE_PATH: {output}");
                using(var image=viewport.GetTexture().GetImage())
                {
                    var sample=image.GetPixel(image.GetWidth()/2,image.GetHeight()/2);
                    if(Mathf.Max(sample.R,Mathf.Max(sample.G,sample.B))<.01f)throw new Exception("Dense render missed the selected positive recreation-mask sample");
                    if(image.SavePng(output+"dense-before.png")!=Error.Ok)throw new Exception("Dense sparse-recreation capture failed");
                }
                material.SetShaderParameter("sparse_recreation_enabled",true);await Draw();
                using(var image=viewport.GetTexture().GetImage())
                {
                    var sample=image.GetPixel(image.GetWidth()/2,image.GetHeight()/2);
                    if(Mathf.Max(sample.R,Mathf.Max(sample.G,sample.B))<.01f)throw new Exception("Sparse render missed the selected positive recreation-mask sample");
                    if(image.SavePng(output+"sparse-after.png")!=Error.Ok)throw new Exception("Sparse sparse-recreation capture failed");
                }
                if(failedSamples!=0)throw new Exception($"Native sparse renderer differs at {failedSamples} pixel samples over {comparisons}; GPU gate flags channel deltas >= 1/255");
                GD.Print($"ANTILA_SPARSE_RECREATION_CHECK_OK: {checkedPixels} exact mip pixels; {probes.Count} probe windows; {levels.Count} forced integer/fraction/transition LODs plus natural; {comparisons} GPU-comparison pixels; {sparse.ActivePages} padded pages; {sparse.TexturePayloadBytes} decoded texture bytes");
            }
            finally{viewport.QueueFree();}
            QuitGame();
        }
        catch(Exception error){GD.PushError("ANTILA_SPARSE_RECREATION_CHECK_FAILED: "+error);QuitGame(1);}
    }

    private static long CheckSparseRoundTrip(Image source,Image atlas,Image lookup,SparseAssetInfo sparse)
    {
        if(source.GetFormat()!=Image.Format.Rgb8 || atlas.GetFormat()!=Image.Format.Rgb8 || lookup.GetFormat()!=Image.Format.Rgb8 || source.GetMipmapCount()+1!=sparse.MipLevels || atlas.HasMipmaps() || lookup.HasMipmaps())
            throw new Exception("Sparse resources must preserve native RGB8 source mips and use mipless RGB8 atlas/lookup textures");
        var sourceBytes=source.GetData();var atlasBytes=atlas.GetData();var lookupBytes=lookup.GetData();long pixels=0;
        for(int mip=0;mip<sparse.MipLevels;mip++)
        {
            var info=sparse.Mips[mip];int offset=checked((int)source.GetMipmapOffset(mip));
            for(int y=0;y<info.Height;y++)for(int x=0;x<info.Width;x++)
            {
                int px=x/SparsePageSize,py=y/SparsePageSize,lookupAt=((info.LookupOffset+py)*sparse.LookupWidth+px)*3;
                int id=lookupBytes[lookupAt]|lookupBytes[lookupAt+1]<<8,sourceAt=offset+(y*info.Width+x)*3,atlasAt=0;
                if(id!=0)
                {
                    int ax=id%sparse.AtlasColumns*SparsePaddedPage+x%SparsePageSize+SparseGutter;
                    int ay=id/sparse.AtlasColumns*SparsePaddedPage+y%SparsePageSize+SparseGutter;
                    atlasAt=(ay*sparse.AtlasWidth+ax)*3;
                }
                for(int c=0;c<3;c++)if(sourceBytes[sourceAt+c]!=(id==0?(byte)0:atlasBytes[atlasAt+c]))
                    throw new Exception($"Sparse atlas roundtrip differs at mip {mip} pixel {x},{y} channel {c}");
                pixels++;
            }
        }
        return pixels;
    }

    private static IEnumerable<Vector2> SparseRecreationSportSamples(Rect2 bounds)
    {
        foreach(string path in new[]{"res://Data/mong-kok-open-spaces.json","res://Data/east-kowloon-open-spaces.json"})
        {
            using var data=JsonDocument.Parse(FileAccess.GetFileAsString(path));
            foreach(var surface in data.RootElement.GetProperty("surfaces").EnumerateArray().GroupBy(s=>s.GetProperty("kind").GetString()).Select(g=>g.First()))
            {
                var p=surface.GetProperty("sample");yield return (new Vector2(p[0].GetSingle(),p[1].GetSingle())-bounds.Position)/bounds.Size;
            }
        }
    }
}
