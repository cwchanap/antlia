using Godot;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text.Json;
using FileAccess=Godot.FileAccess;

public partial class Main
{
    private const string TerrainMaskManifestPath="res://Data/terrain-masks.json";
    private const string TerrainMaskAssetPath="res://Assets/Textures/TerrainMasks/";
    private static readonly string[] TerrainMaskNames={"surface_mask","harbour_mask","recreation_mask"};
    private static readonly JsonSerializerOptions TerrainMaskJsonOptions=new(){PropertyNamingPolicy=JsonNamingPolicy.CamelCase,WriteIndented=true};
    private sealed record TerrainMaskMetadata(float[] Bounds,int Width,int Height,string Format,int MipLevels,string Sha256);
    private enum TerrainMaskMode { Runtime,Bake,Check }
    private readonly HashSet<string> _terrainMasksUsed=new(StringComparer.Ordinal);
    private readonly Dictionary<string,TerrainMaskMetadata> _terrainMasksBaked=new(StringComparer.Ordinal);
    private Dictionary<string,TerrainMaskMetadata> _terrainMaskManifest=null!;
    private TerrainMaskMode _terrainMaskMode;
    private bool _terrainMaskModeSelected;

    private Texture2D TerrainMask(string name,Rect2 bounds,Func<Image> generate)
    {
        SelectTerrainMaskMode();
        if(!TerrainMaskNames.Contains(name,StringComparer.Ordinal))throw new Exception($"Unknown terrain mask '{name}'");
        if(!_terrainMasksUsed.Add(name))throw new Exception($"Terrain mask '{name}' was requested more than once");
        var path=TerrainMaskAssetPath+name+".png";
        if(_terrainMaskMode==TerrainMaskMode.Runtime)return name switch
        {
            "recreation_mask"=>LoadSparseRecreation(bounds),
            "harbour_mask"=>LoadHarbourRg8(bounds),
            _=>LoadTerrainMask(name,bounds)
        };

        using var image=generate();
        var generated=DescribeTerrainMask(bounds,image);
        if(_terrainMaskMode==TerrainMaskMode.Bake)
        {
            SaveTerrainMask(image,path);
            WriteTerrainMaskImport(path+".import");
            _terrainMasksBaked.Add(name,generated);
            return ImageTexture.CreateFromImage(image);
        }

        var recorded=GetTerrainMaskMetadata(name,bounds);
        RequireSameTerrainMask(recorded,generated,name,"generated source");
        var texture=LoadTerrainMask(name,bounds);
        using var imported=texture.GetImage();
        // Native texture readback can normalize mip 1 differently, so compare through the same renderer.
        using var referenceTexture=ImageTexture.CreateFromImage(image);
        using var reference=referenceTexture.GetImage();
        RequireSameTerrainMask(DescribeTerrainMask(bounds,reference),DescribeTerrainMask(bounds,imported),name,"imported texture");
        GD.Print($"ANTILA_TERRAIN_MASK_OK: {name} {generated.Width}x{generated.Height} RGB8, {generated.MipLevels} mip levels, SHA-256 {generated.Sha256}");
        if(name=="harbour_mask")
        {
            var compact=ConvertHarbourRg8(image);
            if(compact.SourceRgbSha256!=recorded.Sha256)throw new Exception("Harbour RG8 source does not match the canonical RGB8 manifest");
            var rg8=ReadHarbourRg8Metadata();
            if(compact.CompactMipSha256!=rg8.CompactMipSha256)throw new Exception("Harbour RG8 mip bytes differ from Data/harbour-rg8.json; rebake the harbour RG8 resource");
            var loaded=LoadHarbourRg8(bounds);
            using var expectedRg8=compact.Texture.GetImage();using var loadedRg8=loaded.GetImage();
            if(expectedRg8.GetFormat()!=Image.Format.Rg8 || loadedRg8.GetFormat()!=Image.Format.Rg8 ||
               expectedRg8.GetWidth()!=recorded.Width || expectedRg8.GetHeight()!=recorded.Height ||
               expectedRg8.GetMipmapCount()+1!=recorded.MipLevels || loadedRg8.GetWidth()!=recorded.Width || loadedRg8.GetHeight()!=recorded.Height ||
               loadedRg8.GetMipmapCount()+1!=recorded.MipLevels || !expectedRg8.GetData().SequenceEqual(loadedRg8.GetData()))
                throw new Exception("Harbour RG8 resource readback differs from the fresh canonical conversion");
            GD.Print($"ANTILA_HARBOUR_RG8_CHECK_OK: {recorded.Width}x{recorded.Height}, {recorded.MipLevels} mips; canonical RGB8 manifest unchanged");
            return loaded;
        }
        if(name!="recreation_mask")return texture;
        var sparse=ReadSparseRecreation();
        var (atlas,lookup,lodRamp)=LoadSparseTextures(sparse,recorded,bounds);
        using var atlasImage=atlas.GetImage();using var lookupImage=lookup.GetImage();
        long checkedPixels=CheckSparseRoundTrip(image,atlasImage,lookupImage,sparse);
        GD.Print($"ANTILA_SPARSE_ROUNDTRIP_OK: {checkedPixels} generated source mip pixels");
        ConfigureSparseRecreation(_terrain,sparse,atlas,lookup,lodRamp);
        if(!_terrain.GetShaderParameter("sparse_recreation_enabled").AsBool())
            throw new Exception("Recreation terrain mask check did not bind the sparse resources");
        return atlas;
    }

    private bool FinishTerrainMasks()
    {
        SelectTerrainMaskMode();
        if(_terrainMasksUsed.Count!=TerrainMaskNames.Length || TerrainMaskNames.Any(name=>!_terrainMasksUsed.Contains(name)))
            throw new Exception("Terrain mask setup did not visit surface_mask, harbour_mask and recreation_mask");
        if(_terrainMaskMode==TerrainMaskMode.Bake)
        {
            SaveTerrainMaskManifest();
            BakeHarbourRg8();
            BakeSparseRecreation();
            GD.Print("ANTILA_TERRAIN_MASKS_BAKED: 3 masks with bounds, dimensions, RGB8 mip levels and SHA-256 in Data/terrain-masks.json");
            QuitGame();
            return true;
        }
        if(_terrainMaskMode==TerrainMaskMode.Check && OS.GetCmdlineUserArgs().Contains("--terrain-mask-check"))
        {
            GD.Print("ANTILA_TERRAIN_MASK_CHECK_OK: 3 masks match generated RGB/mipmap data and Data/terrain-masks.json");
            QuitGame();
            return true;
        }
        return false;
    }

    private void SelectTerrainMaskMode()
    {
        if(_terrainMaskModeSelected)return;
        var args=OS.GetCmdlineUserArgs();
        bool bake=args.Contains("--bake-terrain"),check=args.Contains("--terrain-mask-check")||args.Contains("--self-test");
        if(bake&&check)throw new Exception("Use only one of --bake-terrain, --terrain-mask-check or --self-test");
        _terrainMaskMode=bake?TerrainMaskMode.Bake:check?TerrainMaskMode.Check:TerrainMaskMode.Runtime;
        if(_terrainMaskMode!=TerrainMaskMode.Bake)_terrainMaskManifest=ReadTerrainMaskManifest();
        _terrainMaskModeSelected=true;
    }

    private Dictionary<string,TerrainMaskMetadata> ReadTerrainMaskManifest()
    {
        if(!FileAccess.FileExists(TerrainMaskManifestPath))throw new Exception($"Terrain mask metadata is missing; run `./run.command --headless -- --bake-terrain` first ({TerrainMaskManifestPath})");
        try
        {
            var manifest=JsonSerializer.Deserialize<Dictionary<string,TerrainMaskMetadata>>(FileAccess.GetFileAsString(TerrainMaskManifestPath),TerrainMaskJsonOptions)
                ??throw new Exception("manifest is empty");
            if(manifest.Count!=TerrainMaskNames.Length || TerrainMaskNames.Any(name=>!manifest.ContainsKey(name)))throw new Exception("manifest must contain exactly surface_mask, harbour_mask and recreation_mask");
            foreach(var entry in manifest)
                if(entry.Value is null || entry.Value.Bounds is null || entry.Value.Sha256 is null || entry.Value.Bounds.Length!=4 || entry.Value.Width<=0 || entry.Value.Height<=0 || entry.Value.Format!="Rgb8" || entry.Value.MipLevels<2 || entry.Value.Sha256.Length!=64 || !entry.Value.Sha256.All(Uri.IsHexDigit))
                    throw new Exception($"manifest entry '{entry.Key}' has invalid bounds or image metadata");
            return manifest;
        }
        catch(Exception error){throw new Exception($"Invalid terrain mask metadata at {TerrainMaskManifestPath}: {error.Message}; run `./run.command --headless -- --bake-terrain`",error);}
    }

    private Texture2D LoadTerrainMask(string name,Rect2 bounds)
    {
        var metadata=GetTerrainMaskMetadata(name,bounds);
        var texture=GD.Load<Texture2D>(TerrainMaskAssetPath+name+".png")
            ??throw new Exception($"Terrain mask asset '{name}.png' is missing or unimported; run `./run.command --headless -- --bake-terrain` then reimport");
        if(texture.GetWidth()!=metadata.Width || texture.GetHeight()!=metadata.Height)
            throw new Exception($"Terrain mask '{name}' dimensions are {texture.GetWidth()}x{texture.GetHeight()}, expected {metadata.Width}x{metadata.Height}; reimport after baking");
        return texture;
    }

    private Image RecreationMaskForChecks()=>CreateRecreationMask(_recreationBounds);

    private TerrainMaskMetadata GetTerrainMaskMetadata(string name,Rect2 bounds)
    {
        if(!_terrainMaskManifest.TryGetValue(name,out var metadata))throw new Exception($"Terrain mask metadata is missing '{name}'");
        var expected=new[]{bounds.Position.X,bounds.Position.Y,bounds.Size.X,bounds.Size.Y};
        if(!metadata.Bounds.SequenceEqual(expected))throw new Exception($"Terrain mask '{name}' bounds differ from the current source; run `./run.command --headless -- --bake-terrain`");
        return metadata;
    }

    private static TerrainMaskMetadata DescribeTerrainMask(Rect2 bounds,Image image)
    {
        if(image.GetFormat()!=Image.Format.Rgb8 || !image.HasMipmaps())throw new Exception("Generated terrain masks must be RGB8 with mipmaps");
        return new(new[]{bounds.Position.X,bounds.Position.Y,bounds.Size.X,bounds.Size.Y},image.GetWidth(),image.GetHeight(),image.GetFormat().ToString(),image.GetMipmapCount()+1,
            Convert.ToHexString(SHA256.HashData(image.GetData())));
    }

    private static void RequireSameTerrainMask(TerrainMaskMetadata expected,TerrainMaskMetadata actual,string name,string source)
    {
        if(expected.Width!=actual.Width || expected.Height!=actual.Height || expected.Format!=actual.Format || expected.MipLevels!=actual.MipLevels || expected.Sha256!=actual.Sha256)
            throw new Exception($"Terrain mask '{name}' {source} differs from metadata; run `./run.command --headless -- --bake-terrain` and reimport");
    }

    private void SaveTerrainMask(Image image,string resourcePath)
    {
        string path=ProjectSettings.GlobalizePath(resourcePath),temporary=path+".tmp";
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var error=image.SavePng(temporary);
        if(error!=Error.Ok)throw new Exception($"Could not save terrain mask '{resourcePath}': {error}");
        try{File.Move(temporary,path,true);}
        finally{if(File.Exists(temporary))File.Delete(temporary);}
    }

    private static void WriteTerrainMaskImport(string resourcePath)
    {
        var config=new ConfigFile();
        if(FileAccess.FileExists(resourcePath))
        {
            var load=config.Load(resourcePath);
            if(load!=Error.Ok)throw new Exception($"Could not read terrain mask import settings '{resourcePath}': {load}");
        }
        else
        {
            config.SetValue("remap","importer","texture");
            config.SetValue("remap","type","CompressedTexture2D");
        }
        config.SetValue("params","compress/mode",0);
        config.SetValue("params","mipmaps/generate",true);
        config.SetValue("params","mipmaps/limit",-1);
        config.SetValue("params","process/fix_alpha_border",false);
        config.SetValue("params","detect_3d/compress_to",0);
        var error=config.Save(resourcePath);
        if(error!=Error.Ok)throw new Exception($"Could not write terrain mask import settings '{resourcePath}': {error}");
    }

    private void SaveTerrainMaskManifest()
    {
        if(_terrainMasksBaked.Count!=TerrainMaskNames.Length || TerrainMaskNames.Any(name=>!_terrainMasksBaked.ContainsKey(name)))
            throw new Exception("Cannot write terrain mask metadata before all three masks are baked");
        var json=JsonSerializer.Serialize(_terrainMasksBaked,TerrainMaskJsonOptions);
        string path=ProjectSettings.GlobalizePath(TerrainMaskManifestPath),temporary=path+".tmp";
        try{File.WriteAllText(temporary,json);File.Move(temporary,path,true);}
        finally{if(File.Exists(temporary))File.Delete(temporary);}
    }
}
