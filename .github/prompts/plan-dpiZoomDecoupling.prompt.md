## Plan: DPI 固定 + QGraphicsView Transform + 高 DPI 対応ズーム改修

**概要:** レンダリング DPI を 144 に固定し、ズームは `QGraphicsView.setTransform()` で制御する。`AppConfig.default_dpi` を実際のレンダリングに反映させ、高 DPI モニター (Retina/4K) でもピクセル等倍で鮮明に表示する。

**DPI の役割分担:**
| 用途 | 値 | 使用箇所 |
|------|-----|---------|
| `_base_dpi` | `config.default_dpi` (144) | シーン座標計算、PDF⇔ピクセル座標変換 |
| `_render_dpi` | `_base_dpi × devicePixelRatio` | Model への実レンダリング指示 |

高 DPI モニター (dpr=2.0) の場合、144×2=288 DPI でレンダリングし、`QPixmap.setDevicePixelRatio(2.0)` を設定することで、Qt がシーン上の論理サイズ (144 DPI 相当) に正しくマッピングしつつ物理ピクセルをフル活用する。

---

### Phase A: Config & Presenter（Phase B の前提）

**Step 1.** `DEFAULT_DPI` 定数を `300` → `144` に変更
- [config.py](src/pdf_epub_reader/utils/config.py#L31)

**Step 2.** `IMainView` Protocol に `get_device_pixel_ratio()` を追加
- [view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py)
- `def get_device_pixel_ratio(self) -> float: ...`
- Presenter がレンダリング DPI を計算するために View のスクリーン情報を取得する

**Step 3.** Presenter の DPI 管理を `_base_dpi` / `_render_dpi` に分離
- [main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py#L55)
- 旧: `self._current_dpi: int = DEFAULT_DPI`
- 新:
  ```python
  self._base_dpi: int = self._config.default_dpi
  dpr = self._view.get_device_pixel_ratio()
  self._render_dpi: int = int(self._base_dpi * dpr)
  ```
- プレースホルダー計算 (L109): `scale = self._base_dpi / 72.0`
- レンダリング (L239): `render_page(num, self._render_dpi)`
- extract_content (L166): `dpi=self._render_dpi`（クロップ画像も高解像度で生成）

**Step 4.** `_do_zoom_changed()` から DPI 再計算とプレースホルダー再配置を削除
- [main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py#L201-L204)
- ズーム変更時は `set_zoom_level(level)` を呼ぶだけ。DPI は固定。`display_pages()` の再呼び出しも不要

**Step 5.** `open_file()` のプレースホルダー計算は `self._base_dpi / 72.0` のまま（Step 3 で DPI が固定されるので正しく動く）

---

### Phase B: View 側のトランスフォームズーム + 高 DPI（Phase A に依存）

**Step 6.** `MainWindow` に `get_device_pixel_ratio()` を実装
- [main_window.py](src/pdf_epub_reader/views/main_window.py)
- `return self.devicePixelRatio()` を返す（Qt が OS のスケーリング設定を反映）

**Step 7.** `MainWindow.set_zoom_level()` で `QGraphicsView` のトランスフォームを適用
- [main_window.py](src/pdf_epub_reader/views/main_window.py#L203-L212)
- `self._doc_view._current_dpi = int(DEFAULT_DPI * level)` を **削除**（DPI は固定）
- `self._doc_view._zoom_level = level` は維持
- **追加:** `self._doc_view.resetTransform()` + `self._doc_view.scale(level, level)`

**Step 8.** `update_page_images()` で `setDevicePixelRatio` を設定
- [main_window.py](src/pdf_epub_reader/views/main_window.py#L562-L590)
- `pixmap.loadFromData()` 直後に `pixmap.setDevicePixelRatio(self.devicePixelRatio())` を追加
- これにより Qt は `render_dpi` 分のピクセルを `base_dpi` 分の論理サイズで表示する
- シーン上のプレースホルダー矩形 (base_dpi 基準) と自動的にサイズが一致する

**Step 9.** `_DocumentGraphicsView` の座標変換 — **変更不要**
- ラバーバンド選択 ([main_window.py](src/pdf_epub_reader/views/main_window.py#L786)): `mapToScene()` がトランスフォームを自動考慮。`scale = _current_dpi / 72.0` （= base_dpi / 72.0）で PDF ポイントに正しく変換
- ハイライト描画 ([main_window.py](src/pdf_epub_reader/views/main_window.py#L836)): シーン座標 (base_dpi 基準) で配置するのでトランスフォームが自動適用

**Step 10.** `fit_to_page_height()` の計算式を簡素化
- [main_window.py](src/pdf_epub_reader/views/main_window.py#L892-L910)
- 現在: `base_height = page_height / self._zoom_level` （DPI 変更前提の逆算）
- 修正: `new_zoom = viewport_height / page_height` （シーン上のページ高さは固定なので直接割るだけ）

**Step 11.** `_release_offscreen_pages()`, `_check_visible_pages()`, `scroll_to()` — **変更不要**
- `mapToScene()` がトランスフォームを考慮するため自動的に正しく動作する

---

### Phase C: テスト更新

**Step 12.** `MockMainView` に `get_device_pixel_ratio()` を追加
- [mock_views.py](tests/mocks/mock_views.py)
- テスト環境では `return 1.0` を返す（標準 DPI モニター相当）

**Step 13.** `test_zoom_change_rerenders` の修正
- [test_main_presenter.py](tests/test_presenters/test_main_presenter.py#L225-L253)
- ズームで `display_pages` が呼ばれなくなるので、アサーションを「`set_zoom_level` が呼ばれ、`display_pages` は呼ばれない」に変更

**Step 14.** `test_pages_needed_triggers_render_and_update` 
- [test_main_presenter.py](tests/test_presenters/test_main_presenter.py#L290): `(0, 144)` → MockMainView の dpr=1.0 なので render_dpi=144。変更不要

**Step 15.** 全テスト実行で確認

---

### Relevant files
- [config.py](src/pdf_epub_reader/utils/config.py) — `DEFAULT_DPI` 定数 (L31), `AppConfig.default_dpi` (L74)
- [view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py) — `IMainView` Protocol
- [main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py) — DPI 初期化 (L55), プレースホルダー計算 (L109), ズーム DPI 計算 (L201-204), レンダリング DPI 渡し (L239)
- [main_window.py](src/pdf_epub_reader/views/main_window.py) — `set_zoom_level` (L203-212), `_current_dpi` 初期化 (L507), `update_page_images` (L562), 座標変換 (L786, L836), `fit_to_page_height` (L892)
- [mock_views.py](tests/mocks/mock_views.py) — `MockMainView`
- [test_main_presenter.py](tests/test_presenters/test_main_presenter.py) — ズームテスト (L225-253), 遅延読み込み DPI (L290)

### Verification
1. `pytest tests/` — 全テスト通過
2. 手動: PDF を開いてデフォルトズームで文字がくっきり表示される
3. 手動: Ctrl+ホイールでズームイン/アウト — 画質劣化なし、再レンダリングのちらつきなし
4. 手動: ラバーバンド選択 → PDF 座標が正しくマッピングされている
5. 手動: ハイライトが選択範囲と正確に重なる
6. 手動: Ctrl+H（ページ高さフィット）が正しく動作する
7. 手動: ズームスピンボックスが正しいパーセンテージを表示する
8. 手動 (高 DPI): Windows のスケーリング 150%/200% で文字がぼやけない
