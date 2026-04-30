using GemRead.CaptureHelper.Imaging;
using GemRead.CaptureHelper.Interop;
using Windows.Foundation;
using Windows.Graphics.Capture;
using Windows.Graphics.DirectX;
using Windows.Graphics.DirectX.Direct3D11;

namespace GemRead.CaptureHelper.Capture;

internal sealed class WgcCaptureService
{
    public async Task<string> CapturePrimaryMonitorToPngAsync(CancellationToken cancellationToken)
    {
        // WGC を利用できない環境では、この先の WinRT / D3D 初期化を進めても成功しないため、
        // 入口で即座に判定する。
        if (!GraphicsCaptureSession.IsSupported())
        {
            throw new NotSupportedException("Windows Graphics Capture is not supported on this environment.");
        }

        // Milestone 0 では「固定対象を 1 つキャプチャする」ことが目的なので、
        // 対象はプライマリモニターに固定している。
        var monitorHandle = NativeMethods.GetPrimaryMonitorHandle();

        // WGC の API は GraphicsCaptureItem を対象として受け取るため、
        // HMONITOR から WinRT オブジェクトへ変換する。
        var item = GraphicsCaptureItemInterop.CreateForMonitor(monitorHandle);

        // フレームプール作成には WinRT 形式の Direct3D デバイスが必要になる。
        var device = Direct3D11DeviceFactory.Create();

        // 1 フレームだけ欲しいため、バッファ数は 1 にして最小構成で作る。
        // ピクセル形式は一般的な BGRA8 を使う。
        using var framePool = Direct3D11CaptureFramePool.CreateFreeThreaded(
            device,
            DirectXPixelFormat.B8G8R8A8UIntNormalized,
            1,
            item.Size);

        // セッションを開始し、最初に到着したフレームを回収する。
        using var session = framePool.CreateCaptureSession(item);
        using var frame = await CaptureSingleFrameAsync(framePool, session, cancellationToken);

        // PoC ではローカルの artifacts 配下に PNG を保存し、
        // 目視で結果確認できるようにする。
        var outputPath = BuildOutputPath();
        await PngEncoder.SaveSurfaceAsPngAsync(frame.Surface, outputPath, cancellationToken);

        return outputPath;
    }

    private static async Task<Direct3D11CaptureFrame> CaptureSingleFrameAsync(
        Direct3D11CaptureFramePool framePool,
        GraphicsCaptureSession session,
        CancellationToken cancellationToken)
    {
        // FrameArrived イベントを await 可能にするため TaskCompletionSource を使う。
        var completion = new TaskCompletionSource<Direct3D11CaptureFrame>(TaskCreationOptions.RunContinuationsAsynchronously);
        TypedEventHandler<Direct3D11CaptureFramePool, object>? handler = null;

        handler = (sender, _) =>
        {
            try
            {
                // 到着済みフレームを 1 枚だけ取り出す。
                var frame = sender.TryGetNextFrame();
                if (frame is null)
                {
                    return;
                }

                // 1 回だけ使う PoC なので、フレーム取得後はすぐイベント購読を解除する。
                sender.FrameArrived -= handler;
                completion.TrySetResult(frame);
            }
            catch (Exception ex)
            {
                // イベント側で起きた例外も await 側へ伝播させる。
                sender.FrameArrived -= handler;
                completion.TrySetException(ex);
            }
        };

        framePool.FrameArrived += handler;

        // StartCapture 以降にフレーム到着が始まる。
        session.StartCapture();

        using var registration = cancellationToken.Register(() =>
        {
            // キャンセル時はイベントを外し、待機中 Task を終了させる。
            framePool.FrameArrived -= handler;
            completion.TrySetCanceled(cancellationToken);
        });

        return await completion.Task;
    }

    private static string BuildOutputPath()
    {
        // 実機確認しやすいよう、出力先は作業ディレクトリ配下の artifacts/captures に固定する。
        var outputDirectory = Path.Combine(Environment.CurrentDirectory, "artifacts", "captures");
        Directory.CreateDirectory(outputDirectory);

        // タイムスタンプ付きにして、複数回実行しても上書きされないようにする。
        return Path.Combine(
            outputDirectory,
            $"wgc-poc-{DateTime.Now:yyyyMMdd-HHmmss}.png");
    }
}
