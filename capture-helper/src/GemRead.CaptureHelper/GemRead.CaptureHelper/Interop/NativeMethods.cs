using System.Runtime.InteropServices;

namespace GemRead.CaptureHelper.Interop;

internal static class NativeMethods
{
    // 指定地点がどのモニターにも属さない場合でも、プライマリモニターを返す指定。
    private const int MonitorDefaultToPrimary = 1;

    public static IntPtr GetPrimaryMonitorHandle()
    {
        // 原点に対する MonitorFromPoint を使う簡易実装で、
        // Milestone 0 の固定対象であるプライマリモニターのハンドルを得る。
        var handle = MonitorFromPoint(new POINT(0, 0), MonitorDefaultToPrimary);
        if (handle == IntPtr.Zero)
        {
            throw new InvalidOperationException("Failed to resolve the primary monitor.");
        }

        return handle;
    }

    // Win32 API: 座標から対応するモニターの HMONITOR を取得する。
    [DllImport("user32.dll")]
    private static extern IntPtr MonitorFromPoint(POINT point, uint flags);

    // DXGI デバイスを WinRT の IDirect3DDevice へラップするための API。
    // WGC のフレームプール作成時に必要になる。
    [DllImport("d3d11.dll")]
    internal static extern int CreateDirect3D11DeviceFromDXGIDevice(IntPtr dxgiDevice, out IntPtr graphicsDevice);

    // MonitorFromPoint に渡す Win32 POINT 構造体。
    [StructLayout(LayoutKind.Sequential)]
    private readonly record struct POINT(int X, int Y);
}
