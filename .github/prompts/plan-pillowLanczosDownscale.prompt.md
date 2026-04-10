## Plan: Pillow LANCZOS リサイズ導入（View 内部に閉じる方式）

ズーム縮小時 (zoom < 1.0) の文字ジャギーを解消するため、`_DocumentGraphicsView` 内部で Pillow LANCZOS リサイズを適用する。ビュー変換 (`QGraphicsView.scale()`) は維持し、座標変換コードに影響なし。設定ダイアログに ON/OFF トグル（デフォルト ON）を追加。

---

### Phase A: AppConfig + Settings 拡張

1. `AppConfig` に `high_quality_downscale: bool = True` を追加
2. `ISettingsDialogView` に `get_high_quality_downscale() / set_high_quality_downscale()` を追加
3. `SettingsDialog` の Rendering タブに "High-quality downscale (Lanczos)" チェックボックスを追加
4. `SettingsPresenter` の `_populate_view` / `_read_config_from_view` にフィールド追加
5. `IMainView` に `set_high_quality_downscale(value: bool)` を追加
6. `MainPresenter._apply_config_changes()` で `high_quality_downscale` 変更時に `view.set_high_quality_downscale()` を呼ぶ

### Phase B: View 内部の Pillow リサイズ実装（本体）

7. `_DocumentGraphicsView.__init__` に `_original_images: dict[int, bytes]` と `_high_quality_downscale: bool` を追加
8. `update_page_images()` で元画像を `_original_images` に保存。zoom < 1.0 & 設定 ON 時は LANCZOS 経由で QPixmap 生成
9. 新規 `_apply_lanczos_resize(image_data, zoom)` — Pillow `resize(LANCZOS)` → PNG bytes → QPixmap。`setDevicePixelRatio(dpr * zoom)` で二重スケーリングを回避
10. `MainWindow.set_zoom_level()` に、縮小時の LANCZOS 差し替え呼び出しを追加
11. 新規 `apply_zoom_resize(level)` — 可視ページ + バッファの画像を LANCZOS リサイズまたは元画像に差し替え
12. `_release_offscreen_pages()` で `_original_images` の該当エントリも削除
13. `setup_pages()` で `_original_images.clear()`
14. `MainWindow.set_high_quality_downscale()` — 設定のパススルーと即時反映

### Phase C: テスト・Mock 更新

15. `MockMainView` に `set_high_quality_downscale()` 追加
16. `MockSettingsDialogView` に getter/setter 追加
17. 既存テスト修正不要（Pillow リサイズは View 層内で完結、Presenter テストのアサーションに影響なし）

### Phase D: 検証

18. `uv run python -m pytest tests/ -x -q` — 全テストパス
19. 手動: zoom 50% で文字品質確認、設定 ON/OFF 切替で即反映確認

---

**Relevant files**
- `src/pdf_epub_reader/utils/config.py` — `AppConfig` にフィールド追加
- `src/pdf_epub_reader/interfaces/view_interfaces.py` — `IMainView`, `ISettingsDialogView` にメソッド追加
- `src/pdf_epub_reader/views/main_window.py` — LANCZOS リサイズロジック本体
- `src/pdf_epub_reader/views/settings_dialog.py` — チェックボックス追加
- `src/pdf_epub_reader/presenters/settings_presenter.py` — 1フィールド追加
- `src/pdf_epub_reader/presenters/main_presenter.py` — 設定変更通知追加
- `tests/mocks/mock_views.py` — Mock 更新

**二重スケーリング回避の仕組み**: Pillow でリサイズ後の QPixmap に `setDevicePixelRatio(dpr × zoom)` を設定 → Qt がシーン上で `1/(dpr×zoom)` 倍で表示 → ビュー変換の `zoom` 倍と合わせて `1/dpr` 倍 = base_dpi 相当に帰着。
