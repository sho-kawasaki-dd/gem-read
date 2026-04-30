using System.Runtime.InteropServices;
using SharpDX.Direct3D;
using Windows.Graphics.DirectX.Direct3D11;
using WinRT;

namespace GemRead.CaptureHelper.Interop;

internal static class Direct3D11DeviceFactory
{
    public static IDirect3DDevice Create()
    {
        // WGC は BGRA 対応の D3D11 デバイスを必要とするため、
        // DeviceCreationFlags.BgraSupport を付けて初期化する。
        using var d3dDevice = new SharpDX.Direct3D11.Device(
            DriverType.Hardware,
            SharpDX.Direct3D11.DeviceCreationFlags.BgraSupport);

        // WinRT 側の API へ橋渡しするため、DXGI デバイス インターフェイスを取得する。
        using var dxgiDevice = d3dDevice.QueryInterface<SharpDX.DXGI.Device>();

        // Win32/DXGI のデバイスを WinRT の IDirect3DDevice へ変換する。
        var result = NativeMethods.CreateDirect3D11DeviceFromDXGIDevice(dxgiDevice.NativePointer, out var direct3DDevicePointer);
        Marshal.ThrowExceptionForHR(result);

        try
        {
            // 返却された ABI ポインタを .NET から扱える WinRT オブジェクトへ包み直す。
            return MarshalInterface<IDirect3DDevice>.FromAbi(direct3DDevicePointer);
        }
        finally
        {
            // FromAbi 後は参照を移し終えているため、元の COM 参照を解放する。
            Marshal.Release(direct3DDevicePointer);
        }
    }
}
