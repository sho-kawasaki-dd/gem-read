using System.Runtime.InteropServices;
using Windows.Graphics.Capture;
using WinRT;

namespace GemRead.CaptureHelper.Interop;

internal static class GraphicsCaptureItemInterop
{
    // GraphicsCaptureItem の WinRT クラス ID。
    // COM interop 経由で GraphicsCaptureItem を生成するときに必要になる。
    private static readonly Guid GraphicsCaptureItemGuid = new("79C3F95B-31F7-4EC2-A464-632EF5D30760");

    public static GraphicsCaptureItem CreateForMonitor(IntPtr monitorHandle)
    {
        // GraphicsCaptureItem は通常の public API だけでは HMONITOR から直接生成できないため、
        // interop インターフェイスを使って Win32 ハンドルから作成する。
        var interop = GraphicsCaptureItem.As<IGraphicsCaptureItemInterop>();
        var result = interop.CreateForMonitor(monitorHandle, GraphicsCaptureItemGuid, out var itemPointer);
        Marshal.ThrowExceptionForHR(result);

        // COM から返された ABI ポインタを .NET / WinRT のオブジェクトへ変換する。
        return MarshalInterface<GraphicsCaptureItem>.FromAbi(itemPointer);
    }

    [ComImport]
    [Guid("3628E81B-3CAC-4C60-B7F4-23CE0E0C3356")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IGraphicsCaptureItemInterop
    {
        // 将来ウィンドウ単位キャプチャを入れる場合に使う定義。
        int CreateForWindow(IntPtr window, in Guid iid, out IntPtr result);

        // HMONITOR から GraphicsCaptureItem を生成するための定義。
        int CreateForMonitor(IntPtr monitor, in Guid iid, out IntPtr result);
    }
}
