using GemRead.CaptureHelper.Capture;

// Milestone 0 の PoC では、アプリ起動後に 1 回だけキャプチャを実行して終了する。
// まだ CLI 引数や stdout/stderr の正式契約は入れず、
// 「WGC で画像が取得でき、PNG 保存まで通るか」を確認することだけに集中する。
var captureService = new WgcCaptureService();

try
{
    // WGC が応答しないケースでプロセスが無限待機しないよう、
    // PoC 段階でもタイムアウトを設けておく。
    using var cancellationTokenSource = new CancellationTokenSource(TimeSpan.FromSeconds(10));
    var outputPath = await captureService.CapturePrimaryMonitorToPngAsync(cancellationTokenSource.Token);

    // Milestone 0 ではファイル保存先を人が確認できれば十分なので、
    // 成功時は保存先パスを標準出力へ表示する。
    Console.WriteLine($"WGC capture saved to: {outputPath}");
}
catch (NotSupportedException ex)
{
    // OS / GPU / SDK 条件によって WGC 自体が使えない環境があるため、
    // 非対応は通常の失敗と分けて扱う。
    Console.Error.WriteLine(ex.Message);
    return 2;
}
catch (OperationCanceledException)
{
    // タイムアウト時はハングではなく制御された失敗として終了する。
    Console.Error.WriteLine("Capture timed out.");
    return 3;
}
catch (Exception ex)
{
    // PoC なので詳細例外をそのまま表示し、実機検証時の切り分けを優先する。
    Console.Error.WriteLine($"Capture failed: {ex}");
    return 1;
}

return 0;
