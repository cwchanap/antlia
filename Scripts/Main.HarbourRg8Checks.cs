using Godot;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using FileAccess=Godot.FileAccess;

public partial class Main
{
    private const int HarbourRg8CheckViewSize=512;
    private const float HarbourRg8CheckThreshold=1f/255;
    private const string HarbourRg8CheckEvidenceRoot="user://harbour-rg8-check/";
    private const string HarbourRg8CheckShaderCode="""
        shader_type spatial;
        render_mode unshaded;
        uniform sampler2D source_rgb : filter_linear_mipmap, repeat_disable;
        uniform sampler2D candidate_rg : filter_linear_mipmap, repeat_disable;
        uniform vec2 sample_center;
        uniform vec2 sample_span;
        uniform float forced_lod = -1.0;
        uniform float error_threshold = 0.0039215686;
        uniform int output_mode = 0;
        void fragment() {
            vec2 uv = clamp(sample_center + (UV - vec2(0.5)) * sample_span, vec2(0.0), vec2(1.0));
            vec3 source = forced_lod >= 0.0 ? textureLod(source_rgb, uv, forced_lod).rgb : texture(source_rgb, uv).rgb;
            vec3 candidate = forced_lod >= 0.0 ? textureLod(candidate_rg, uv, forced_lod).rgb : texture(candidate_rg, uv).rgb;
            if (output_mode == 1) { ALBEDO = source; EMISSION = source; }
            else if (output_mode == 2) { ALBEDO = candidate; EMISSION = candidate; }
            else {
                float delta = max(max(abs(source.r - candidate.r), abs(source.g - candidate.g)), abs(source.b - candidate.b));
                vec3 diagnostic = vec3(step(error_threshold, delta), min(delta * 255.0, 1.0), 0.0);
                ALBEDO = diagnostic; EMISSION = diagnostic;
            }
            ROUGHNESS = 1.0;
            SPECULAR = 0.0;
        }
        """;
    private static readonly JsonSerializerOptions HarbourRg8CheckJsonOptions=new(){PropertyNamingPolicy=JsonNamingPolicy.CamelCase,WriteIndented=true};
    private sealed record HarbourRg8CheckProbe(string Name,Vector2 Uv,float Span,int RequiredChannel=-1,bool ExpectEmpty=false);
    private sealed record HarbourRg8CheckCase(string Name,float Lod,int FailedPixels,int Width,int Height);
    private sealed record HarbourRg8CheckResult(string SourceResource,string SourceTextureClass,int SourceWidth,int SourceHeight,
        string SourceReadbackFormat,int SourceReadbackMipLevels,string SourceMipSha256,int CandidateWidth,int CandidateHeight,
        string CandidateReadbackFormat,int CandidateMipLevels,int ThresholdNumerator,int ThresholdDenominator,
        long ComparedPixels,int FailedPixels,HarbourRg8CheckCase[] Cases,string[] Captures);
    private static readonly HarbourRg8CheckProbe[] HarbourRg8CheckProbes=
    {
        new("full-map",new(.5f,.5f),1),
        new("positive-red",new(.40931213f,.13481675f),8f/9246,0),
        new("positive-green",new(.42748216f,.0057178284f),8f/9246,1),
        new("zero-blue-channel",new(.5f,.5f),8f/9246),
        new("occupied-page-seam",new(.027687648f,.27452466f),8f/9246),
        new("empty-page-seam",new(.013843824f,.008886745f),8f/9246),
        new("empty-page",new(.00697599f,.008886745f),8f/9246,-1,true),
        new("page-x-boundary",new(.013843824f,.5f),8f/9246),
        new("page-y-boundary",new(.5f,.017635712f),8f/9246),
        new("outer-left",new(0,.5f),8f/9246),
        new("outer-right",new(1,.5f),8f/9246),
        new("outer-top",new(.5f,0),8f/9246),
        new("outer-bottom",new(.5f,1),8f/9246)
    };

    private void RunHarbourRg8Check()=>_ = RunHarbourRg8CheckAsync();

    private async Task RunHarbourRg8CheckAsync()
    {
        try
        {
            var result=await CheckHarbourRg8Native();
            GD.Print($"ANTILA_HARBOUR_RG8_NATIVE_CHECK_OK: {result.ComparedPixels} GPU pixels in {result.Cases.Length} windows; 0 differences at 1/255; captures and JSON in {HarbourRg8CheckEvidenceRoot}");
            QuitGame();
        }
        catch(Exception error)
        {
            GD.PushError("ANTILA_HARBOUR_RG8_NATIVE_CHECK_FAILED: "+error);
            QuitGame(1);
        }
    }

    private async Task<HarbourRg8CheckResult> CheckHarbourRg8Native()
    {
        void Check(bool ok,string message){if(!ok)throw new Exception(message);}

        // The check starts before world construction, so use the manifest bounds and production loader.
        _terrainMaskManifest=ReadTerrainMaskManifest();
        var metadata=_terrainMaskManifest.TryGetValue("harbour_mask",out var recorded) && recorded is not null
            ? recorded : throw new Exception("Harbour mask metadata is missing");
        Check(metadata.Bounds.Length==4 && metadata.Bounds.All(float.IsFinite) && metadata.Bounds[2]>0 && metadata.Bounds[3]>0,
            "Harbour source manifest bounds are invalid");
        Check(metadata.Width==9246 && metadata.Height==7258 && metadata.MipLevels==14 && metadata.Format=="Rgb8",
            $"Harbour source manifest is {metadata.Width}x{metadata.Height} {metadata.Format} with {metadata.MipLevels} mip levels");
        var bounds=new Rect2(metadata.Bounds[0],metadata.Bounds[1],metadata.Bounds[2],metadata.Bounds[3]);
        var source=GD.Load<Texture2D>(TerrainMaskAssetPath+"harbour_mask.png")
            ??throw new Exception("Imported harbour_mask.png is missing; import the canonical terrain mask first");
        Check(source is CompressedTexture2D,"Native reference must be the imported CompressedTexture2D harbour_mask.png");
        Check(source.GetWidth()==metadata.Width && source.GetHeight()==metadata.Height,
            $"Imported RGB reference is {source.GetWidth()}x{source.GetHeight()}, expected {metadata.Width}x{metadata.Height}");
        var candidate=LoadHarbourRg8(bounds);
        Check(candidate.GetInstanceId()!=source.GetInstanceId(),"Terrain harbour_mask still points at the imported RGB reference");
        Check(candidate.GetWidth()==metadata.Width && candidate.GetHeight()==metadata.Height,
            $"Bound RG8 candidate is {candidate.GetWidth()}x{candidate.GetHeight()}, expected {metadata.Width}x{metadata.Height}");
        using var sourceImage=source.GetImage();
        using var candidateImage=candidate.GetImage();
        Check(sourceImage.GetWidth()==metadata.Width && sourceImage.GetHeight()==metadata.Height,
            "Imported source texture readback dimensions differ from terrain metadata");
        Check(candidateImage.GetFormat()==Image.Format.Rg8,
            $"Bound harbour candidate readback is {candidateImage.GetFormat()}, expected Rg8");
        Check(candidateImage.HasMipmaps() && candidateImage.GetMipmapCount()+1==metadata.MipLevels,
            $"Bound RG8 candidate exposes {candidateImage.GetMipmapCount()+1} mip levels, expected {metadata.MipLevels}");

        Color SourceAt(Vector2 uv)
        {
            int x=Math.Clamp(Mathf.FloorToInt(uv.X*sourceImage.GetWidth()),0,sourceImage.GetWidth()-1);
            int y=Math.Clamp(Mathf.FloorToInt(uv.Y*sourceImage.GetHeight()),0,sourceImage.GetHeight()-1);
            return sourceImage.GetPixel(x,y);
        }
        foreach(var probe in HarbourRg8CheckProbes)
        {
            var pixel=SourceAt(probe.Uv);
            Check(pixel.B<.001f,$"Imported harbour source violates the zero-blue contract at {probe.Name}: {pixel}");
            if(probe.RequiredChannel>=0)
            {
                float value=probe.RequiredChannel==0?pixel.R:pixel.G;
                Check(value>.001f,$"Imported RGB reference missed positive {(probe.RequiredChannel==0?"red":"green")} probe {probe.Name}: {pixel}");
            }
            if(probe.ExpectEmpty)Check(Mathf.Max(pixel.R,Mathf.Max(pixel.G,pixel.B))<.001f,$"Imported RGB reference expected empty page {probe.Name}: {pixel}");
        }
        if(DisplayServer.GetName()=="headless")throw new Exception("Native GL Compatibility renderer required for harbour RG8 filtering check");

        DirAccess.MakeDirRecursiveAbsolute(ProjectSettings.GlobalizePath(HarbourRg8CheckEvidenceRoot));
        var shader=new Shader{Code=HarbourRg8CheckShaderCode};
        var viewport=new SubViewport{Size=new(HarbourRg8CheckViewSize,HarbourRg8CheckViewSize),World3D=new World3D(),RenderTargetUpdateMode=SubViewport.UpdateMode.Always};
        AddChild(viewport);
        viewport.AddChild(new WorldEnvironment{Environment=new Godot.Environment{BackgroundMode=Godot.Environment.BGMode.Color,BackgroundColor=Colors.Blue}});
        var cases=new List<HarbourRg8CheckCase>();
        var captures=new List<string>();
        long comparedPixels=0;int failedPixels=0;
        try
        {
            var material=new ShaderMaterial{Shader=shader};
            material.SetShaderParameter("source_rgb",source);
            material.SetShaderParameter("candidate_rg",candidate);
            material.SetShaderParameter("error_threshold",HarbourRg8CheckThreshold);
            // Fixed, oversized geometry avoids uncovered border pixels in tiny UV probe windows.
            var plane=new PlaneMesh{Size=Vector2.One*4};
            var ground=new MeshInstance3D{Mesh=plane,MaterialOverride=material};
            viewport.AddChild(ground);
            var camera=new Camera3D{Projection=Camera3D.ProjectionType.Orthogonal,Size=1,Position=new(0,40,0),Current=true};
            viewport.AddChild(camera);
            camera.LookAt(Vector3.Zero,Vector3.Forward);

            async Task Draw()
            {
                for(int i=0;i<3;i++)await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);
                RenderingServer.ForceDraw(false);
            }
            void Place(Vector2 centerUv,float span,Vector2 mapScale,float rollDegrees=0,bool perspective=false)
            {
                material.SetShaderParameter("sample_center",centerUv);
                material.SetShaderParameter("sample_span",new Vector2(span/mapScale.X,span/mapScale.Y)*4);
                camera.Projection=perspective?Camera3D.ProjectionType.Perspective:Camera3D.ProjectionType.Orthogonal;
                if(perspective)
                {
                    camera.Fov=45;camera.Near=.01f;
                    float distance=1/(2*Mathf.Tan(Mathf.DegToRad(camera.Fov*.5f)));
                    camera.Position=new(0,distance*.8660254f,distance*.5f);
                }
                else{camera.Size=1;camera.Near=.05f;camera.Position=new(0,40,0);}
                camera.LookAt(Vector3.Zero,Vector3.Forward);
                if(rollDegrees!=0)camera.RotateObjectLocal(Vector3.Back,Mathf.DegToRad(rollDegrees));
            }
            async Task Capture(string name,HarbourRg8CheckProbe probe)
            {
                Place(probe.Uv,probe.Span,Vector2.One);material.SetShaderParameter("forced_lod",0f);
                foreach(var (mode,suffix) in new[]{(1,"reference"),(2,"rg8")})
                {
                    material.SetShaderParameter("output_mode",mode);await Draw();
                    using var image=viewport.GetTexture().GetImage();
                    string relative=$"{name}-{suffix}.png",path=HarbourRg8CheckEvidenceRoot+relative;
                    Check(image.SavePng(ProjectSettings.GlobalizePath(path))==Error.Ok,$"Could not save native capture {path}");
                    captures.Add(relative);
                }
            }
            async Task<int> Compare(string name,float lod,Vector2 centerUv,float span,Vector2 mapScale,float rollDegrees=0,bool perspective=false)
            {
                material.SetShaderParameter("output_mode",0);material.SetShaderParameter("forced_lod",lod);
                Place(centerUv,span,mapScale,rollDegrees,perspective);await Draw();
                using var image=viewport.GetTexture().GetImage();var data=image.GetData();
                int bpp=data.Length/(image.GetWidth()*image.GetHeight());
                Check(bpp>=3,$"Native difference capture has unexpected {image.GetFormat()} format");
                int windowFailures=0;
                for(int i=0;i<data.Length;i+=bpp)
                {
                    Check(data[i+2]<128,$"Native probe {name} does not cover the viewport at LOD {lod:R}");
                    if(data[i]>=128)windowFailures++;
                }
                cases.Add(new(name,lod,windowFailures,image.GetWidth(),image.GetHeight()));
                comparedPixels+=(long)image.GetWidth()*image.GetHeight();failedPixels+=windowFailures;
                if(windowFailures>0)
                {
                    GD.Print($"ANTILA_HARBOUR_RG8_NATIVE_DIFF: {name} LOD {lod:R}; {windowFailures} pixels >= 1/255");
                    if(!captures.Any(c=>c.StartsWith("first-difference-",StringComparison.Ordinal)))
                    {
                        string safe=string.Concat(name.Select(ch=>char.IsLetterOrDigit(ch)?ch:'-'));
                        string relative=$"first-difference-{safe}.png",path=HarbourRg8CheckEvidenceRoot+relative;
                        Check(image.SavePng(ProjectSettings.GlobalizePath(path))==Error.Ok,$"Could not save native difference capture {path}");
                        captures.Add(relative);
                    }
                }
                return windowFailures;
            }
            foreach(var probe in HarbourRg8CheckProbes)
            {
                if(probe.Name is "full-map" or "positive-red" or "positive-green")await Capture(probe.Name,probe);
                material.SetShaderParameter("output_mode",1);material.SetShaderParameter("forced_lod",0f);
                Place(probe.Uv,probe.Span,Vector2.One);await Draw();
                using var reference=viewport.GetTexture().GetImage();var pixel=reference.GetPixel(HarbourRg8CheckViewSize/2,HarbourRg8CheckViewSize/2);
                if(probe.RequiredChannel>=0)
                {
                    float value=probe.RequiredChannel==0?pixel.R:pixel.G;
                    Check(value>.001f,$"GPU RGB reference missed positive {probe.Name} sample: {pixel}");
                }
                Check(pixel.B<.001f,$"GPU RGB reference violated zero-blue contract at {probe.Name}: {pixel}");
                if(probe.ExpectEmpty)Check(Mathf.Max(pixel.R,Mathf.Max(pixel.G,pixel.B))<.001f,$"GPU RGB reference expected empty page {probe.Name}: {pixel}");
            }
            var lods=new SortedSet<float>();
            for(int mip=0;mip<metadata.MipLevels;mip++)lods.Add(mip);
            for(int mip=0;mip<metadata.MipLevels-1;mip++)lods.Add(mip+.5f);
            for(int mip=1;mip<metadata.MipLevels;mip++){lods.Add(mip-.01f);lods.Add(mip+.01f);}
            foreach(var probe in HarbourRg8CheckProbes)
            foreach(float lod in lods.Append(-1f))await Compare(probe.Name,lod,probe.Uv,probe.Span,Vector2.One);

            var naturalCenter=HarbourRg8CheckProbes.Single(p=>p.Name=="positive-red").Uv;
            foreach(float lod in new[]{.5f,1.5f,3.5f})
            {
                float xSpan=HarbourRg8CheckViewSize*Mathf.Pow(2,lod)/metadata.Width;
                await Compare($"natural-x-{lod:R}",-1,naturalCenter,xSpan,new(1,4));
                float ySpan=HarbourRg8CheckViewSize*Mathf.Pow(2,lod)/metadata.Height;
                await Compare($"natural-y-{lod:R}",-1,naturalCenter,ySpan,new(4,1));
            }
            float obliqueSpan=HarbourRg8CheckViewSize*Mathf.Pow(2,1.5f)/metadata.Width;
            await Compare("natural-rotated-45",-1,naturalCenter,obliqueSpan,new(1,4),45);
            await Compare("natural-perspective",-1,naturalCenter,obliqueSpan,new(1,4),perspective:true);
            var result=new HarbourRg8CheckResult(TerrainMaskAssetPath+"harbour_mask.png",source.GetClass().ToString(),source.GetWidth(),source.GetHeight(),
                sourceImage.GetFormat().ToString(),sourceImage.GetMipmapCount()+1,metadata.Sha256,candidate.GetWidth(),candidate.GetHeight(),
                candidateImage.GetFormat().ToString(),candidateImage.GetMipmapCount()+1,1,255,comparedPixels,failedPixels,cases.ToArray(),captures.ToArray());
            string resultPath=HarbourRg8CheckEvidenceRoot+"result.json";
            using(var file=FileAccess.Open(resultPath,FileAccess.ModeFlags.Write))
            {
                if(file==null)throw new Exception($"Could not write native check record {resultPath}");
                file.StoreString(JsonSerializer.Serialize(result,HarbourRg8CheckJsonOptions));
            }
            Check(failedPixels==0,$"Bound RG8 texture differs from imported compressed RGB reference at {failedPixels} GPU pixels over {comparedPixels}; threshold remains >= 1/255");
            return result;
        }
        finally{viewport.QueueFree();}
    }
}
