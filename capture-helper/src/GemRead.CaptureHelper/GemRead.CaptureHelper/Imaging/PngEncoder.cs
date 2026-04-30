using Windows.Graphics.Imaging;
using Windows.Graphics.DirectX.Direct3D11;
using WinRT;

namespace GemRead.CaptureHelper.Imaging;

internal static class PngEncoder
{
    public static async Task SaveSurfaceAsPngAsync(IDirect3DSurface surface, string outputPath, CancellationToken cancellationToken)
    {
        // WGC から得られるのは GPU 側のサーフェスなので、
        // まず WinRT の SoftwareBitmap にコピーしてエンコード可能な形へ変換する。
        var softwareBitmap = await SoftwareBitmap.CreateCopyFromSurfaceAsync(surface, BitmapAlphaMode.Ignore);

        // WinRT の BitmapEncoder は IRandomAccessStream を要求するため、
        // .NET の FileStream を WinRT ストリームへ変換して渡す。
        using var fileStream = new FileStream(outputPath, FileMode.Create, FileAccess.ReadWrite, FileShare.None);
        using var randomAccessStream = fileStream.AsRandomAccessStream();

        // 出力形式は PNG に固定する。Milestone 0 では可逆保存で中間確認しやすいことを優先する。
        var encoder = await BitmapEncoder.CreateAsync(BitmapEncoder.PngEncoderId, randomAccessStream);
        encoder.SetSoftwareBitmap(softwareBitmap);

        // サムネイルは不要なので生成を明示的に無効化する。
        encoder.IsThumbnailGenerated = false;
        await encoder.FlushAsync().AsTask(cancellationToken);
    }
}
