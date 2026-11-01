using Godot;
using System;
using System.Linq;
using System.Threading.Tasks;

public partial class Main
{
    private async Task CheckMapBufferBudget()
    {
        if(DisplayServer.GetName()=="headless")throw new Exception("Map buffer budget requires the native renderer");
        await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);RenderingServer.ForceDraw(false);
        ulong buffers=RenderingServer.GetRenderingInfo(RenderingServer.RenderingInfo.BufferMemUsed);
        if(buffers==0)throw new Exception("Native rendering-buffer telemetry was unavailable");
        if(buffers>512L*1024*1024)throw new Exception($"Map drawing exceeded the initial render-buffer budget: {buffers/1048576.0:0.0} MiB > 512 MiB");
        GD.Print($"ANTILA_MAP_BUFFER_BUDGET_OK: initial render buffers {buffers/1048576.0:0.0} MiB <= 512 MiB");
        string[] MapHashes()=>Hud.GetChildren().OfType<SubViewport>().Select(view=>{
            using var image=view.GetTexture().GetImage();var data=image.GetData();
            if(!data.Any(b=>b!=0))throw new Exception("Native map canvas did not render");
            return Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(data));
        }).ToArray();
        var hashes=MapHashes();var window=GetWindow();var original=window.Size;
        try
        {
            window.Size=new(2880,1800);
            for(int i=0;i<4;i++)await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);
            RenderingServer.ForceDraw(false);
            var scale=GetViewport().GetStretchTransform().Scale.Abs();
            if(scale.X<1.9f || scale.Y<1.9f)throw new Exception("Native 2x presentation size was not applied: "+scale);
            Hud.CheckMapGeometry();
            if(hashes.SequenceEqual(MapHashes()))throw new Exception("Map textures did not refresh for the larger presentation scale");
            buffers=RenderingServer.GetRenderingInfo(RenderingServer.RenderingInfo.BufferMemUsed);
            if(buffers>512L*1024*1024)throw new Exception("Enlarged maps exceeded the rendering-buffer budget");
            GD.Print($"ANTILA_MAP_RESIZE_OK: {window.Size}, stretch {scale}, map textures refreshed; {buffers/1048576.0:0.0} MiB render buffers");
        }
        finally
        {
            window.Size=original;
            for(int i=0;i<3;i++)await ToSignal(GetTree(),SceneTree.SignalName.ProcessFrame);
        }
    }
}
