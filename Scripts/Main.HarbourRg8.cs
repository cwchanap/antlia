using Godot;
using System;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using FileAccess=Godot.FileAccess;

public partial class Main
{
    private const string HarbourRg8SourcePath=TerrainMaskAssetPath+"harbour_mask.png";
    private const string HarbourRg8ResourcePath=TerrainMaskAssetPath+"harbour-rg8.res";
    private const string HarbourRg8MetadataPath="res://Data/harbour-rg8.json";
    private const int HarbourRg8SchemaVersion=1,HarbourRg8MaxMips=15,HarbourRg8MaxTextureEdge=16384;
    private const long HarbourRg8PayloadLimit=192L*1024*1024,HarbourRg8ResourceFileLimit=HarbourRg8PayloadLimit+4L*1024*1024;
    private sealed record HarbourRg8AssetInfo(int SchemaVersion,float[] Bounds,int Width,int Height,string SourcePath,string SourceFormat,string SourceRgbSha256,
        string Format,int MipLevels,long PayloadBytes,string CompactMipSha256,string ResourcePath,long ResourceBytes,string ResourceSha256);
    private sealed record HarbourRg8Conversion(ImageTexture Texture,string SourceRgbSha256,string CompactMipSha256,long PayloadBytes);

    private void CheckHarbourRg8Binding()
    {
        var source=GetTerrainMaskMetadata("harbour_mask",HarbourBounds);
        if(_terrain.GetShaderParameter("harbour_mask").AsGodotObject() is not ImageTexture texture)
            throw new Exception("Harbour mask binding is not an ImageTexture/RG8 resource");
        using var image=texture.GetImage();
        if(texture.GetFormat()!=Image.Format.Rg8 || texture.GetWidth()!=source.Width || texture.GetHeight()!=source.Height ||
           image.GetFormat()!=Image.Format.Rg8 || image.GetWidth()!=source.Width || image.GetHeight()!=source.Height ||
           image.GetMipmapCount()+1!=source.MipLevels)
            throw new Exception($"Harbour mask binding differs from RGB manifest metadata: {texture.GetFormat()} {texture.GetWidth()}x{texture.GetHeight()}, {image.GetMipmapCount()+1} mips");
        CheckHarbourRg8RejectsBlueChannel();
        GD.Print($"ANTILA_HARBOUR_RG8_BINDING_OK: {source.Width}x{source.Height}, {source.MipLevels} mips");
    }

    private void CheckHarbourRg8RejectsBlueChannel()
    {
        using var fixture=Image.CreateEmpty(4,4,false,Image.Format.Rgb8);
        fixture.SetPixel(1,1,new Color(.25f,.5f,1,1));
        if(fixture.GenerateMipmaps()!=Error.Ok)throw new Exception("Could not prepare the tiny nonzero-blue RG8 guard fixture");
        try
        {
            var converted=ConvertHarbourRg8(fixture);
            converted.Texture.Dispose();
        }
        catch(Exception error) when(error.Message.Contains("blue channel is nonzero",StringComparison.Ordinal)){return;}
        throw new Exception("Harbour RG8 conversion accepted a nonzero blue channel");
    }

    private void BakeHarbourRg8()
    {
        var expected=ReadTerrainMaskManifest()["harbour_mask"];
        ValidateHarbourRg8SourceMetadata(expected);
        var bounds=new Rect2(expected.Bounds[0],expected.Bounds[1],expected.Bounds[2],expected.Bounds[3]);
        using var image=Image.LoadFromFile(ProjectSettings.GlobalizePath(HarbourRg8SourcePath));
        if(image.IsEmpty() || image.HasMipmaps() || image.GetFormat()!=Image.Format.Rgb8)
            throw new Exception($"Canonical harbour PNG is missing or not base-level RGB8; run ./run.command --headless -- --bake-terrain: {HarbourRg8SourcePath}");
        if(image.GenerateMipmaps()!=Error.Ok || !image.HasMipmaps() || image.GetMipmapCount()+1!=expected.MipLevels)
            throw new Exception("Could not generate the canonical harbour mip chain; run ./run.command --headless -- --bake-terrain");

        var converted=ConvertHarbourRg8(image);
        var generated=new TerrainMaskMetadata((float[])expected.Bounds.Clone(),image.GetWidth(),image.GetHeight(),"Rgb8",image.GetMipmapCount()+1,converted.SourceRgbSha256);
        RequireSameTerrainMask(expected,generated,"harbour_mask","canonical PNG + generated mips");
        if(converted.PayloadBytes>HarbourRg8PayloadLimit)
            throw new Exception($"Harbour RG8 mip payload exceeds {HarbourRg8PayloadLimit} bytes: {converted.PayloadBytes}");

        var resource=SaveHarbourRg8Texture(converted.Texture);
        var asset=new HarbourRg8AssetInfo(HarbourRg8SchemaVersion,(float[])expected.Bounds.Clone(),expected.Width,expected.Height,
            HarbourRg8SourcePath,"Rgb8",converted.SourceRgbSha256,"Rg8",expected.MipLevels,converted.PayloadBytes,converted.CompactMipSha256,
            HarbourRg8ResourcePath,resource.Bytes,resource.Sha256);
        SaveHarbourRg8Metadata(asset);
        GD.Print($"ANTILA_HARBOUR_RG8_BAKED: {expected.Width}x{expected.Height}, {expected.MipLevels} mips, {converted.PayloadBytes} decoded bytes, source SHA-256 {converted.SourceRgbSha256}, compact SHA-256 {converted.CompactMipSha256}");
    }

    private ImageTexture LoadHarbourRg8(Rect2 bounds)
    {
        var source=GetTerrainMaskMetadata("harbour_mask",bounds);
        ValidateHarbourRg8SourceMetadata(source);
        var asset=ReadHarbourRg8Metadata();
        if(asset.SchemaVersion!=HarbourRg8SchemaVersion || asset.Bounds is null || !asset.Bounds.SequenceEqual(source.Bounds) ||
           asset.Width!=source.Width || asset.Height!=source.Height || asset.MipLevels!=source.MipLevels ||
           asset.SourcePath!=HarbourRg8SourcePath || asset.SourceFormat!=source.Format || asset.SourceRgbSha256!=source.Sha256 ||
           asset.Format!="Rg8" || asset.ResourcePath!=HarbourRg8ResourcePath || !IsSha256(asset.CompactMipSha256) || !IsSha256(asset.ResourceSha256))
            throw new Exception("Harbour RG8 metadata differs from the canonical RGB8 mask; run ./run.command --headless -- --harbour-rg8-bake (or --bake-terrain after source changes)");

        long expectedPayload=HarbourRg8MipPayloadBytes(source.Width,source.Height,source.MipLevels);
        if(asset.PayloadBytes!=expectedPayload || asset.PayloadBytes>HarbourRg8PayloadLimit)
            throw new Exception("Harbour RG8 payload metadata is invalid or exceeds 192 MiB; rerun the harbour RG8 bake");

        var resource=HashHarbourRg8Resource();
        if(asset.ResourceBytes!=resource.Bytes || asset.ResourceSha256!=resource.Sha256)
            throw new Exception("Harbour RG8 resource size or SHA-256 differs from metadata; rerun the harbour RG8 bake");

        var texture=GD.Load<ImageTexture>(HarbourRg8ResourcePath)
            ??throw new Exception("Harbour RG8 resource is missing or unreadable; run ./run.command --headless -- --harbour-rg8-bake");
        if(texture.GetFormat()!=Image.Format.Rg8 || texture.GetWidth()!=source.Width || texture.GetHeight()!=source.Height)
            throw new Exception("Loaded harbour RG8 format or dimensions differ from metadata; rerun the harbour RG8 bake");
        // Godot 4.6 ImageTexture has no HasMipmaps API; the hashed resource links the validated mip metadata to this texture.
        return texture;
    }

    private HarbourRg8Conversion ConvertHarbourRg8(Image image)
    {
        int width=image.GetWidth(),height=image.GetHeight(),mipLevels=image.GetMipmapCount()+1;
        if(image.GetFormat()!=Image.Format.Rgb8 || !image.HasMipmaps() ||
           width<=0 || height<=0 || width>HarbourRg8MaxTextureEdge || height>HarbourRg8MaxTextureEdge ||
           mipLevels<2 || mipLevels>HarbourRg8MaxMips)
            throw new Exception($"Harbour source image must be bounded RGB8 with its full mip chain: {width}x{height}, {mipLevels} mips");
        int fullMipLevels=1,mipWidth=width,mipHeight=height;
        while(mipWidth>1 || mipHeight>1){mipWidth=Math.Max(1,mipWidth/2);mipHeight=Math.Max(1,mipHeight/2);fullMipLevels++;}
        if(mipLevels!=fullMipLevels)throw new Exception($"Harbour source image has {mipLevels} mips, expected full chain of {fullMipLevels}");
        long expectedPayload=HarbourRg8MipPayloadBytes(width,height,mipLevels);
        if(expectedPayload>HarbourRg8PayloadLimit)throw new Exception($"Harbour RG8 mip payload exceeds {HarbourRg8PayloadLimit} bytes: {expectedPayload}");

        byte[] rgbBytes=image.GetData();
        long expectedRgbBytes=checked(expectedPayload/2*3);
        if(rgbBytes.LongLength!=expectedRgbBytes)throw new Exception("Harbour RGB8 data length differs from its dimensions and mip count");
        string sourceRgbSha256=Convert.ToHexString(SHA256.HashData(rgbBytes));
        // RG8 is lossless only while harbour B stays zero; use RGB8 if that channel gains data.
        for(int i=0;i<rgbBytes.Length;i+=3)
            if(rgbBytes[i+2]!=0)throw new Exception($"Harbour blue channel is nonzero at RGB data offset {i+2}; use RGB8 instead of RG8");

        image.Convert(Image.Format.Rg8);
        if(image.GetFormat()!=Image.Format.Rg8 || !image.HasMipmaps() || image.GetWidth()!=width || image.GetHeight()!=height ||
           image.GetMipmapCount()+1!=mipLevels)
            throw new Exception("Harbour RG8 conversion changed format, dimensions or mip count");
        byte[] rgBytes=image.GetData();
        if(rgBytes.LongLength!=expectedPayload)throw new Exception("Harbour RG8 data length differs from its dimensions and mip count");
        for(int rgb=0,rg=0;rgb<rgbBytes.Length;rgb+=3,rg+=2)
            if(rgbBytes[rgb]!=rgBytes[rg] || rgbBytes[rgb+1]!=rgBytes[rg+1])
                throw new Exception($"Harbour RG8 conversion changed an R/G byte at source offset {rgb}");
        string compactMipSha256=Convert.ToHexString(SHA256.HashData(rgBytes));
        var texture=ImageTexture.CreateFromImage(image);
        long payloadBytes=rgBytes.LongLength;
        rgbBytes=Array.Empty<byte>();rgBytes=Array.Empty<byte>();
        GD.Print($"ANTILA_HARBOUR_RG8_CONVERTED: {width}x{height}, {mipLevels} mips, B=0 and all R/G bytes preserved");
        return new HarbourRg8Conversion(texture,sourceRgbSha256,compactMipSha256,payloadBytes);
    }

    private static void ValidateHarbourRg8SourceMetadata(TerrainMaskMetadata source)
    {
        if(source.Bounds is null || source.Bounds.Length!=4 || source.Bounds.Any(value=>!float.IsFinite(value)) ||
           source.Bounds[2]<=0 || source.Bounds[3]<=0 || source.Width<=0 || source.Height<=0 ||
           source.Width>HarbourRg8MaxTextureEdge || source.Height>HarbourRg8MaxTextureEdge ||
           source.Format!="Rgb8" || !IsSha256(source.Sha256))
            throw new Exception("Canonical harbour RGB8 metadata has invalid bounds, dimensions, format, mip count or SHA-256; run ./run.command --headless -- --bake-terrain");
        int expectedMipLevels=1,mipWidth=source.Width,mipHeight=source.Height;
        while(mipWidth>1 || mipHeight>1){mipWidth=Math.Max(1,mipWidth/2);mipHeight=Math.Max(1,mipHeight/2);expectedMipLevels++;}
        if(source.MipLevels<2 || source.MipLevels>HarbourRg8MaxMips || source.MipLevels!=expectedMipLevels)
            throw new Exception("Canonical harbour RGB8 metadata has invalid bounds, dimensions, format, mip count or SHA-256; run ./run.command --headless -- --bake-terrain");
    }

    private static long HarbourRg8MipPayloadBytes(int width,int height,int mipLevels)
    {
        long pixels=0;
        for(int mip=0;mip<mipLevels;mip++)
        {
            pixels=checked(pixels+(long)width*height);
            width=Math.Max(1,width/2);height=Math.Max(1,height/2);
        }
        return checked(pixels*2);
    }

    private static bool IsSha256(string? value)=>value is {Length:64} && value.All(Uri.IsHexDigit);

    private static HarbourRg8AssetInfo ReadHarbourRg8Metadata()
    {
        if(!FileAccess.FileExists(HarbourRg8MetadataPath))
            throw new Exception("Harbour RG8 metadata is missing; run ./run.command --headless -- --harbour-rg8-bake");
        try
        {
            return JsonSerializer.Deserialize<HarbourRg8AssetInfo>(FileAccess.GetFileAsString(HarbourRg8MetadataPath),TerrainMaskJsonOptions)
                ??throw new Exception("metadata is empty");
        }
        catch(Exception error){throw new Exception($"Invalid harbour RG8 metadata at {HarbourRg8MetadataPath}; rerun the harbour RG8 bake",error);}
    }

    private static (long Bytes,string Sha256) SaveHarbourRg8Texture(ImageTexture texture)
    {
        string absolute=ProjectSettings.GlobalizePath(HarbourRg8ResourcePath);
        string temporaryPath=HarbourRg8ResourcePath+".tmp.res",temporaryAbsolute=ProjectSettings.GlobalizePath(temporaryPath);
        Directory.CreateDirectory(Path.GetDirectoryName(absolute)!);
        try
        {
            var error=ResourceSaver.Save(texture,temporaryPath,ResourceSaver.SaverFlags.Compress);
            if(error!=Error.Ok)throw new Exception($"Could not save harbour RG8 texture: {error}");
            File.Move(temporaryAbsolute,absolute,true);
            return HashHarbourRg8Resource();
        }
        finally{if(File.Exists(temporaryAbsolute))File.Delete(temporaryAbsolute);}
    }

    private static (long Bytes,string Sha256) HashHarbourRg8Resource()
    {
        using var file=FileAccess.Open(HarbourRg8ResourcePath,FileAccess.ModeFlags.Read)
            ??throw new Exception("Harbour RG8 resource is missing; run ./run.command --headless -- --harbour-rg8-bake");
        ulong fileLength=file.GetLength();
        if(fileLength==0 || fileLength>(ulong)HarbourRg8ResourceFileLimit)
            throw new Exception($"Harbour RG8 resource file size is invalid: {fileLength}; rerun the harbour RG8 bake");
        long length=checked((long)fileLength);
        return (length,Convert.ToHexString(SHA256.HashData(file.GetBuffer(length))));
    }

    private static void SaveHarbourRg8Metadata(HarbourRg8AssetInfo asset)
    {
        string absolute=ProjectSettings.GlobalizePath(HarbourRg8MetadataPath),temporary=absolute+".tmp";
        Directory.CreateDirectory(Path.GetDirectoryName(absolute)!);
        try
        {
            File.WriteAllText(temporary,JsonSerializer.Serialize(asset,TerrainMaskJsonOptions));
            File.Move(temporary,absolute,true);
        }
        finally{if(File.Exists(temporary))File.Delete(temporary);}
    }
}
