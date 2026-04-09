# Phase 2 実装プロンプト — PySide6 View + qasync 統合

## 概要

Phase 1 で定義済みの `IMainView` / `ISidePanelView` Protocol を満たす PySide6 実装、qasync によるイベントループ統合、`app.py` のワイヤリングを実装する。通じてスタブ Model を使用し、Phase 3-4 のバックエンド未実装でも GUI が起動・操作できる状態をゴールとする。

> **Phase 2 のスコープ外:** PyMuPDF による実レンダリング (Phase 3)、Gemini API 通信 (Phase 4)、Context Caching (Phase 5)

---

## ⚠️ 厳守ルール（Phase 1 から継続）

1. **Passive View の徹底:** View 内にデータ加工・API 呼び出し・PDF 解析のロジックを一切書かない。
2. **PySide6 クラスは Presenter / Model にインポート禁止。** データは `bytes`, `str`, `dataclass` で渡す。
3. **Model の公開メソッドはすべて `async def`。** Presenter は `await` で呼び出す。
4. **`src` レイアウト維持。** テスト・実装の import 汚染を防ぐ。
5. **docstring / inline comment:** 新規参加のジュニアエンジニアが Why まで理解できる粒度を維持する。
6. **型ヒント:** すべての公開メソッドに付与する。

---

## 設計上の決定事項

| 項目 | 決定 |
|---|---|
| メインレイアウト | `QSplitter` (左: ドキュメント / 右: サイドパネル) |
| ドキュメント描画 | `QGraphicsView` + `QGraphicsScene` |
| テキスト範囲選択 | マウスドラッグで矩形選択 (`QRubberBand`) |
| ファイルを開く方法 | メニューバー「開く」+ ドラッグ&ドロップ + 最近開いたファイルリスト |
| サイドパネルタブ | 2 タブ: 翻訳 / カスタムプロンプト |
| 初期ウィンドウサイズ | 1280×800、スプリッター比率 70:30 |
| ズーム操作 | Ctrl+マウスホイール + ステータスバーにズームスピンボックス |
| 翻訳ボタン | 「翻訳」ボタン + 「解説付き翻訳」ボタンの 2 つ |
| ステータスバー | メッセージ + 現在ページ/総ページ数 + ズームスピンボックス |
| テーマ | Fusion スタイル |
| 座標変換 | **View 側**でピクセル→PDF 座標 (72dpi 基準) に変換し、Presenter には `RectCoords` を渡す |
| 遅延読み込み | **ビューポート基準** — View がスクロール位置を監視し、必要ページ番号を Presenter にコールバックで要求 |
| `display_pages()` 役割 | 全ページの **プレースホルダー配置用** に変更。`PageData.image_data` は空 `bytes` で渡す（新 DTO は作らない）|
| ビューポート外画像 | **即座に解放**（LRU キャッシュなし） |
| 最近開いたファイル | `QSettings` で永続化、最大 10 件 |
| ページ番号表示 | ステータスバーの `QSpinBox` でジャンプ機能付き |
| ローディング表示 | `QProgressBar` (indeterminate) + ボタン無効化 |
| エラー表示 | 軽微: ステータスバー / 重大: `QMessageBox` |

---

## Step 1: IMainView インターフェース拡張

**ファイル:** `src/pdf_epub_reader/interfaces/view_interfaces.py`

### 追加するメソッド

`IMainView` Protocol に以下の 3 メソッドを追加する:

```python
def set_on_pages_needed(
    self, cb: Callable[[list[int]], None]
) -> None: ...
```

- View がビューポート内に未レンダリングのページを検出したとき、そのページ番号のリストを引数に Presenter を呼び出すためのコールバック登録。
- **Why:** 遅延読み込みを View 主導で行うため。Presenter はどのページが必要かを知らず、View がスクロール位置から判断する。

```python
def update_pages(self, pages: list[PageData]) -> None: ...
```

- Presenter が遅延レンダリング結果を差分で View に供給するためのメソッド。
- `display_pages()` がプレースホルダー配置用であるのに対し、こちらは **画像データを含む** `PageData` を渡してプレースホルダーを実画像に差し替える。

```python
def show_error_dialog(self, title: str, message: str) -> None: ...
```

- 重大エラー発生時にモーダルダイアログを表示する。Phase 3-4 でファイル読み込み失敗・API エラー等が発生した際に使用するため、先にインターフェースだけ定義しておく。

### `display_pages()` の docstring 更新

既存の `display_pages(self, pages: list[PageData]) -> None` の docstring を以下の意味に更新する:

> 全ページ分のレイアウト空間（プレースホルダー）を設定する。`PageData.image_data` は空 `bytes` が渡される場合があり、その場合はプレースホルダー表示にする。実際の画像は後から `update_pages()` で供給される。

---

## Step 2: MockMainView 更新

**ファイル:** `tests/mocks/mock_views.py`

`MockMainView` クラスに以下を追加する:

1. `__init__` に `self._on_pages_needed: Callable[[list[int]], None] | None = None` を追加
2. Display commands に以下を追加:
   ```python
   def update_pages(self, pages: list[PageData]) -> None:
       self.calls.append(("update_pages", (pages,)))
   
   def show_error_dialog(self, title: str, message: str) -> None:
       self.calls.append(("show_error_dialog", (title, message)))
   ```
3. Callback registration に以下を追加:
   ```python
   def set_on_pages_needed(self, cb: Callable[[list[int]], None]) -> None:
       self._on_pages_needed = cb
   ```
4. Simulation helpers に以下を追加:
   ```python
   def simulate_pages_needed(self, page_numbers: list[int]) -> None:
       if self._on_pages_needed:
           self._on_pages_needed(page_numbers)
   ```

---

## Step 3: MainPresenter の遅延読み込み対応

**ファイル:** `src/pdf_epub_reader/presenters/main_presenter.py`

### 3a. `__init__` にコールバック登録追加

既存のコールバック登録ブロックに以下を追加:

```python
self._view.set_on_pages_needed(self._on_pages_needed)
```

### 3b. `open_file()` の修正

**変更前（現在の実装）:** `render_page_range()` で全ページをレンダリングして `display_pages()` に渡している。

**変更後:** 全ページのメタデータ（サイズのみ、画像なし）を計算して `display_pages()` に渡す形にする。

具体的には:
1. `render_page_range()` の呼び出しを削除する。
2. 代わりに、各ページの `PageData` を `image_data=b""` で生成して `display_pages()` に渡す。
3. ページサイズを取得するため、`render_page()` を **1 ページだけ** 呼び出してサイズを取得し、全ページ同サイズと仮定してメタデータリストを組み立てる。

```python
async def open_file(self, file_path: str) -> None:
    self._view.show_status_message(f"Opening {file_path}...")
    doc_info = await self._document_model.open_document(file_path)
    self._view.set_window_title(doc_info.title or doc_info.file_path)

    # 1 ページ目のサイズを取得し、全ページ同サイズとしてプレースホルダーを配置。
    # 実際の画像は View がビューポートに基づいて後から要求する。
    sample = await self._document_model.render_page(0, self._current_dpi)
    placeholders = [
        PageData(
            page_number=i,
            image_data=b"",
            width=sample.width,
            height=sample.height,
        )
        for i in range(doc_info.total_pages)
    ]
    self._view.display_pages(placeholders)
    self._view.show_status_message(
        f"Loaded {doc_info.total_pages} pages"
    )
```

> **注意:** Phase 3 で PDF の各ページサイズが異なる場合の対応を考慮するが、Phase 2 では全ページ同サイズと仮定して問題ない。

### 3c. 遅延読み込みハンドラの追加

```python
def _on_pages_needed(self, page_numbers: list[int]) -> None:
    """View からページ画像の要求を受け取り、非同期レンダリングを開始する。"""
    asyncio.ensure_future(self._do_render_pages(page_numbers))

async def _do_render_pages(self, page_numbers: list[int]) -> None:
    """要求されたページをレンダリングし、View に供給する。

    View のビューポート監視により呼ばれる。各ページを個別に
    render_page() で取得し、まとめて update_pages() で返す。
    """
    pages: list[PageData] = []
    for num in page_numbers:
        page = await self._document_model.render_page(num, self._current_dpi)
        pages.append(page)
    self._view.update_pages(pages)
```

### 3d. `_do_zoom_changed()` の修正

ズーム変更時もプレースホルダー方式に変更する:

```python
async def _do_zoom_changed(self, level: float) -> None:
    self._zoom_level = level
    self._view.set_zoom_level(level)

    doc_info = self._document_model.get_document_info()
    if doc_info is None:
        return

    effective_dpi = int(DEFAULT_DPI * level)
    self._current_dpi = effective_dpi

    # ズーム変更後もプレースホルダーを再配置し、View に遅延読み込みを任せる。
    sample = await self._document_model.render_page(0, effective_dpi)
    placeholders = [
        PageData(
            page_number=i,
            image_data=b"",
            width=sample.width,
            height=sample.height,
        )
        for i in range(doc_info.total_pages)
    ]
    self._view.display_pages(placeholders)
```

---

## Step 4: Presenter テスト更新

**ファイル:** `tests/test_presenters/test_main_presenter.py`

### 4a. `TestOpenFileFlow` の修正

`test_open_file_displays_pages` を修正:
- `render_page_range` の呼び出しチェックを削除し、代わりに `render_page` (サイズ取得用の 1 回) を確認する。
- `display_pages` に渡される `PageData` の `image_data` が空 `bytes` であることを確認する。

### 4b. 遅延読み込みテスト追加

```python
class TestLazyLoadingFlow:
    """ビューポート基準の遅延読み込みを検証する。"""

    @pytest.mark.asyncio
    async def test_pages_needed_triggers_render_and_update(
        self,
        main_presenter: MainPresenter,
        mock_main_view: MockMainView,
        mock_document_model: MockDocumentModel,
    ) -> None:
        """View からの要求でページがレンダリングされ update_pages で返ること。"""
        await main_presenter.open_file("/fake/doc.pdf")
        mock_main_view.calls.clear()
        mock_document_model.calls.clear()

        await main_presenter._do_render_pages([0, 1])

        render_calls = mock_document_model.get_calls("render_page")
        assert len(render_calls) == 2
        assert render_calls[0] == (0, 144)     # DEFAULT_DPI
        assert render_calls[1] == (1, 144)

        update_calls = mock_main_view.get_calls("update_pages")
        assert len(update_calls) == 1
        assert len(update_calls[0][0]) == 2    # 2 ページ分返却
```

### 4c. `TestZoomFlow` の修正

`test_zoom_change_rerenders` を修正:
- `render_page_range` チェックを `render_page` (サイズ取得 1 回) に変更。
- `display_pages` にプレースホルダーが渡されることを確認。

---

## Step 5: `utils/config.py` 設定定数

**ファイル:** `src/pdf_epub_reader/utils/config.py`

```python
"""アプリケーション全体のデフォルト設定値を定義するモジュール。

秘匿情報は含めず、レイアウトやデフォルト倍率など
コード上で共有するパラメータをここに集約する。
実行時に変更される設定は別途管理し、ここは初期値のみ扱う。
"""

# --- ウィンドウ ---
DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 800
SPLITTER_RATIO = (70, 30)

# --- レンダリング ---
DEFAULT_DPI = 144

# --- ズーム ---
ZOOM_MIN = 0.25
ZOOM_MAX = 4.0
ZOOM_STEP = 0.25

# --- ドキュメント表示 ---
PAGE_GAP = 10               # ページ間の余白 (ピクセル)
VIEWPORT_BUFFER_PAGES = 2   # ビューポート前後に先読みするページ数

# --- 最近のファイル ---
MAX_RECENT_FILES = 10

# --- 環境変数名 ---
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
```

> **`DEFAULT_DPI = 144` の重複について:** `main_presenter.py` にも `DEFAULT_DPI = 144` が定義されている。Phase 2 でこのモジュールを作成後、`main_presenter.py` の定数を `from pdf_epub_reader.utils.config import DEFAULT_DPI` に差し替えてインポートを一元化すること。

---

## Step 6: `infrastructure/event_loop.py` — qasync イベントループ統合

**ファイル:** `src/pdf_epub_reader/infrastructure/event_loop.py`

```python
"""Qt イベントループと asyncio を qasync で統合するモジュール。

本アプリは Qt のメインスレッドで asyncio の await を使いたいため、
qasync を用いて両者のイベントループを一本化する。
この橋渡しコードは infrastructure 層に隔離し、
Model / Presenter が Qt に依存しないアーキテクチャを維持する。
"""
```

### 公開 API

```python
def run_app(app_main: Callable[[], Awaitable[None]]) -> None:
```

- `QApplication(sys.argv)` を生成する。
- `app.setStyle("Fusion")` を適用する。
- `qasync.QEventLoop(app)` を作成し `asyncio.set_event_loop()` で登録する。
- `app_main` コルーチンを `asyncio.ensure_future()` で投入する。
- `loop.run_forever()` で Qt + asyncio の統合ループを開始する。
- ループ終了後、`loop.run_until_complete(loop.shutdown_asyncgens())` でクリーンアップする。

### 実装上の注意

- `QApplication` が既に存在する場合（テスト時等）は `QApplication.instance()` を先にチェックして重複生成を防ぐ。
- `sys.argv` を渡すことで Qt のコマンドライン引数処理を維持する。

---

## Step 7: SidePanelView — `ISidePanelView` 実装

**ファイル:** `src/pdf_epub_reader/views/side_panel_view.py`

### クラス: `SidePanelView(QWidget)`

`ISidePanelView` Protocol を満たす PySide6 実装。

### レイアウト構成 (上から順に)

```
┌─────────────────────────────────┐
│  選択テキスト表示                  │  ← QTextEdit (read-only, 最大高さ 120px)
│  (QLabel "選択テキスト:" ヘッダ)    │
├─────────────────────────────────┤
│  QProgressBar (indeterminate)    │  ← 通常は非表示。show_loading(True) で表示
├─────────────────────────────────┤
│  ┌─ QTabWidget ──────────────┐  │
│  │ [翻訳] [カスタムプロンプト]   │  │
│  │                            │  │
│  │  (翻訳タブの場合)            │  │
│  │  [翻訳] [解説付き翻訳]       │  │  ← QPushButton × 2 (横並び QHBoxLayout)
│  │  ┌──────────────────────┐ │  │
│  │  │  結果表示エリア         │ │  │  ← QTextEdit (read-only, 残り全高)
│  │  │                      │ │  │
│  │  └──────────────────────┘ │  │
│  │                            │  │
│  │  (カスタムプロンプトタブの場合)│  │
│  │  ┌──────────────────────┐ │  │
│  │  │  プロンプト入力         │ │  │  ← QTextEdit (200 行まで, 最大高さ 100px)
│  │  └──────────────────────┘ │  │
│  │  [送信]                    │  │  ← QPushButton
│  │  ┌──────────────────────┐ │  │
│  │  │  結果表示エリア         │ │  │  ← QTextEdit (read-only)
│  │  └──────────────────────┘ │  │
│  └────────────────────────────┘  │
├─────────────────────────────────┤
│  キャッシュステータス: ---         │  ← QLabel (1 行)
└─────────────────────────────────┘
```

### Protocol メソッド実装

| Protocol メソッド | PySide6 実装 |
|---|---|
| `set_selected_text(text)` | 選択テキスト QTextEdit の内容を差し替え |
| `update_result_text(text)` | **現在アクティブなタブ** の結果表示 QTextEdit の内容を差し替え |
| `show_loading(True)` | QProgressBar を表示 + 全ボタン(翻訳/解説付き翻訳/送信) を `setEnabled(False)` |
| `show_loading(False)` | QProgressBar を非表示 + 全ボタンを `setEnabled(True)` |
| `update_cache_status_brief(text)` | キャッシュステータス QLabel のテキストを差し替え |
| `set_active_tab(mode)` | mode 文字列 → タブインデックス変換 → `QTabWidget.setCurrentIndex()` |
| `set_on_translate_requested(cb)` | コールバックを保持。翻訳ボタン `.clicked` → `cb(False)`、解説付き翻訳ボタン `.clicked` → `cb(True)` |
| `set_on_custom_prompt_submitted(cb)` | 送信ボタン `.clicked` → `cb(prompt_text_edit.toPlainText())` |
| `set_on_tab_changed(cb)` | `QTabWidget.currentChanged` → インデックスをタブ名に変換 → `cb(tab_name)` |

### タブ名マッピング

```python
_TAB_NAMES = {0: "translation", 1: "custom_prompt"}
```

これは `AnalysisMode` の `.value` と一致させる。

---

## Step 8: MainWindow — `IMainView` 実装

**ファイル:** `src/pdf_epub_reader/views/main_window.py`

### クラス: `MainWindow(QMainWindow)`

`IMainView` Protocol を満たす PySide6 実装。

### コンストラクタ

```python
def __init__(self, side_panel: QWidget) -> None:
```

- `side_panel` は外部からインジェクトする。MainWindow は SidePanelView の具体型を知らない。

### レイアウト構成

```
┌──────────────────────────────────────────────────────┐
│  メニューバー: [ファイル]                                │
│    ├─ 開く (Ctrl+O)                                    │
│    ├─ 最近開いたファイル ▶ (サブメニュー)                 │
│    └─ 終了                                             │
├──────────────────────────────────────────────────────┤
│  QSplitter (水平)                                      │
│  ┌────────────── 70% ──────────────┬──── 30% ────┐    │
│  │  _DocumentGraphicsView          │ SidePanelView│    │
│  │  (QGraphicsView)                │ (injected)   │    │
│  │                                 │              │    │
│  └─────────────────────────────────┴──────────────┘    │
├──────────────────────────────────────────────────────┤
│  ステータスバー:                                        │
│  [メッセージ          ] [ページ: [__1] / 10] [🔍 100%]│
│                                                        │
│  左: QLabel (ステータスメッセージ, stretch=1)            │
│  中央: QLabel "ページ:" + QSpinBox(1〜total) + QLabel "/ N"│
│  右: QLabel "🔍" + QSpinBox(25%〜400%, step=25)        │
└──────────────────────────────────────────────────────┘
```

### メニューバー

- **ファイルメニュー:**
  - 「開く(O)...」 — ショートカット `Ctrl+O` — `QFileDialog.getOpenFileName()` でファイル選択ダイアログを開く。フィルタ: `"Documents (*.pdf *.epub)"` — 選択後 `_on_file_open_requested` コールバック内で `_on_file_dropped` コールバックにパスを渡す（open と drop を統合）。
  - 「最近開いたファイル」 — `QMenu` サブメニュー。`_recent_files_menu` として保持し、ファイル開閉時に動的に更新する。
  - セパレータ
  - 「終了」 — `self.close()`

### ドラッグ&ドロップ

- `self.setAcceptDrops(True)`
- `dragEnterEvent`: MIME が `text/uri-list` かつ拡張子が `.pdf` / `.epub` なら `accept()`
- `dropEvent`: ファイルパスを抽出して `_on_file_dropped` コールバックを発火

### ステータスバー

- **ページナビゲーション (`QSpinBox`):**
  - `display_pages()` 呼び出し時に `setRange(1, total_pages)` で範囲設定
  - `valueChanged` シグナルで `scroll_to_page(value - 1)` を内部呼び出し（0-indexed に変換）
  - View 内のスクロール位置変更時にスピンボックスの値を逆更新する（`_DocumentGraphicsView` から通知）
- **ズームスピンボックス (`QSpinBox`):**
  - 範囲: 25〜400 (%)、ステップ: 25
  - `valueChanged` → `_on_zoom_changed(value / 100.0)` コールバック発火
  - `set_zoom_level(level)` → `spinbox.setValue(int(level * 100))`

### 最近開いたファイル管理

- `QSettings("pdf-epub-reader", "pdf-epub-reader")` で永続化
- キー: `"recent_files"` → `list[str]` (最大 10 件)
- `_add_to_recent(file_path)`: 重複削除 → 先頭に追加 → 10 件超過分を削除 → QSettings 保存 → メニュー更新
- `_rebuild_recent_menu()`: サブメニューをクリアして再構築。各 QAction のクリックで `_on_recent_file_selected(path)` 発火
- `update_recent_files(files)`: 外部（Presenter）からのリスト差し替え用

### Protocol メソッド実装

| Protocol メソッド | PySide6 実装 |
|---|---|
| `display_pages(pages)` | `_DocumentGraphicsView.setup_pages(pages)` を呼び出し。ページスピンボックスの範囲を更新。 |
| `update_pages(pages)` | `_DocumentGraphicsView.update_page_images(pages)` を呼び出し |
| `scroll_to_page(page_number)` | `_DocumentGraphicsView.scroll_to(page_number)` を呼び出し |
| `set_zoom_level(level)` | ズームスピンボックスの値を更新（シグナルループ防止に `blockSignals` 使用） |
| `show_selection_highlight(page, rect)` | `_DocumentGraphicsView.add_highlight(page, rect)` |
| `clear_selection()` | `_DocumentGraphicsView.clear_highlight()` |
| `set_window_title(title)` | `self.setWindowTitle(title)` |
| `show_status_message(message)` | ステータスメッセージ QLabel のテキストを更新 |
| `update_recent_files(files)` | 最近のファイルリストを差し替え → メニュー再構築 |
| `show_error_dialog(title, message)` | `QMessageBox.critical(self, title, message)` |
| `set_on_file_open_requested(cb)` | コールバック保持 |
| `set_on_file_dropped(cb)` | コールバック保持 |
| `set_on_recent_file_selected(cb)` | コールバック保持 |
| `set_on_area_selected(cb)` | `_DocumentGraphicsView` に委譲 |
| `set_on_zoom_changed(cb)` | コールバック保持 |
| `set_on_pages_needed(cb)` | `_DocumentGraphicsView` に委譲 |
| `set_on_cache_management_requested(cb)` | コールバック保持 (Phase 5 用) |

---

## Step 9: `_DocumentGraphicsView` — ドキュメント表示ウィジェット

**定義場所:** `src/pdf_epub_reader/views/main_window.py` 内のプライベートクラス

### クラス: `_DocumentGraphicsView(QGraphicsView)`

MainWindow の内部に閉じた実装クラス。外部公開しない。

### 内部状態

```python
_scene: QGraphicsScene
_page_items: list[QGraphicsPixmapItem | QGraphicsRectItem]  # ページごとのアイテム
_page_rects: list[QRectF]   # 各ページのシーン上の配置矩形
_page_sizes: list[tuple[int, int]]  # 各ページの (width, height)
_rendered_pages: set[int]    # 画像がセット済みのページ番号
_highlight_item: QGraphicsRectItem | None  # 選択ハイライト

# コールバック
_on_area_selected: Callable[[int, RectCoords], None] | None
_on_zoom_changed: Callable[[float], None] | None
_on_pages_needed: Callable[[list[int]], None] | None
_on_visible_page_changed: Callable[[int], None] | None  # ステータスバー連携用

_current_dpi: int  # 座標変換に使用
_zoom_level: float
```

### `setup_pages(pages: list[PageData])` — プレースホルダー配置

1. `_scene.clear()` で既存アイテムをすべて除去。
2. 前回の状態（`_rendered_pages` 等）をリセット。
3. 各ページについて:
   - `y_offset` を累計計算 (ページ高さ + `PAGE_GAP`)。
   - `QGraphicsRectItem(0, y_offset, width, height)` でプレースホルダーを配置。
     - 背景色: 薄い灰色 (`#E0E0E0`)
     - ボーダー: 薄い線
   - `_page_rects` と `_page_sizes` に位置情報を保存。
4. `_scene.setSceneRect()` でシーン全体のサイズを設定。
5. `_check_visible_pages()` を呼んで初期表示分のページ要求を発火。

### `update_page_images(pages: list[PageData])` — 画像差し替え

1. 各 `PageData` について:
   - `page_number` からシーン上の位置を特定。
   - `QPixmap` を `image_data` から生成: `QPixmap.loadFromData(page.image_data)`
   - 既存のプレースホルダー `QGraphicsRectItem` を `QGraphicsPixmapItem` に差し替え。
   - `_rendered_pages` に追加。
2. **ビューポート外の画像解放:** `_release_offscreen_pages()` を呼び出す。

### ビューポート監視: `_check_visible_pages()`

1. `self.mapToScene(self.viewport().rect())` でビューポートのシーン座標を取得。
2. 各ページの `_page_rects` と交差判定し、可視ページ番号を算出。
3. 前後 `VIEWPORT_BUFFER_PAGES` ページを加算してバッファ範囲を決定。
4. `_rendered_pages` に含まれないページ番号だけをフィルタ。
5. 未レンダリングのページがあれば `_on_pages_needed(page_numbers)` コールバック発火。
6. 最も上に見えているページ番号を `_on_visible_page_changed` で通知（ステータスバー更新用）。

### ビューポート監視のトリガー

`scrollContentsBy()` をオーバーライドし、スクロールのたびに `_check_visible_pages()` を呼ぶ。加えて `resizeEvent()` でもウィンドウリサイズ時に呼ぶ。

### ビューポート外画像の即座解放: `_release_offscreen_pages()`

1. 現在のバッファ範囲 (可視 ± `VIEWPORT_BUFFER_PAGES`) を計算。
2. `_rendered_pages` のうちバッファ範囲外のページを特定。
3. 該当ページの `QGraphicsPixmapItem` を灰色プレースホルダーの `QGraphicsRectItem` に差し戻す。
4. `_rendered_pages` から除去。

### 矩形選択 (Rubber Band)

```
mousePressEvent(event):
  左ボタン → _drag_start = event.pos() を記録、QRubberBand を表示開始

mouseMoveEvent(event):
  ドラッグ中 → QRubberBand.setGeometry() を更新

mouseReleaseEvent(event):
  1. QRubberBand を非表示にする
  2. ドラッグ開始・終了位置をシーン座標に変換 (mapToScene)
  3. シーン座標がどのページ上かを判定 (_page_rects から検索)
  4. ページ内のローカル座標に変換
  5. ピクセル座標 → PDF ポイント座標に変換:
     pdf_x = local_pixel_x / (_current_dpi / 72.0)
     pdf_y = local_pixel_y / (_current_dpi / 72.0)
  6. RectCoords(x0, y0, x1, y1) を生成
  7. _on_area_selected(page_number, rect) コールバック発火
```

### ズーム (Ctrl+ホイール)

```
wheelEvent(event):
  if event.modifiers() == Qt.ControlModifier:
    delta = event.angleDelta().y()
    if delta > 0:
      new_zoom = min(_zoom_level + ZOOM_STEP, ZOOM_MAX)
    else:
      new_zoom = max(_zoom_level - ZOOM_STEP, ZOOM_MIN)
    if new_zoom != _zoom_level:
      _on_zoom_changed(new_zoom) コールバック発火
    event.accept()
  else:
    super().wheelEvent(event)  # 通常スクロール
```

> **注意:** ズーム変更時の実際の再描画は Presenter が `set_zoom_level()` → `display_pages()` → ビューポート監視 → `update_pages()` の流れで処理する。View は `_on_zoom_changed` でコールバックを飛ばすだけ。

### 選択ハイライト

```python
def add_highlight(self, page_number: int, rect: RectCoords) -> None:
    """指定ページの指定矩形に半透明のハイライトを重ねる。"""
    self.clear_highlight()
    # PDF 座標 → ピクセル座標に逆変換
    scale = self._current_dpi / 72.0
    px_rect = QRectF(rect.x0 * scale, rect.y0 * scale,
                     (rect.x1 - rect.x0) * scale, (rect.y1 - rect.y0) * scale)
    # ページのシーン上の位置にオフセット
    page_rect = self._page_rects[page_number]
    px_rect.translate(page_rect.x(), page_rect.y())
    self._highlight_item = self._scene.addRect(
        px_rect, QPen(QColor(0, 120, 215)), QBrush(QColor(0, 120, 215, 60))
    )

def clear_highlight(self) -> None:
    if self._highlight_item:
        self._scene.removeItem(self._highlight_item)
        self._highlight_item = None
```

### ページジャンプ

```python
def scroll_to(self, page_number: int) -> None:
    """指定ページが見えるようにスクロールする。"""
    if 0 <= page_number < len(self._page_rects):
        self.ensureVisible(self._page_rects[page_number], 0, 50)
```

---

## Step 10: スタブ Model 作成

Phase 3-4 が未実装のため、GUI の動作確認用にスタブを用意する。

### `src/pdf_epub_reader/models/document_model.py`

```python
class DocumentModel:
    """IDocumentModel のスタブ実装。Phase 3 で PyMuPDF に差し替える。"""
```

| メソッド | スタブの振る舞い |
|---|---|
| `open_document(file_path)` | `DocumentInfo(file_path=file_path, total_pages=5, title=Path(file_path).stem)` を返す |
| `render_page(page_number, dpi)` | 灰色の PNG 画像バイト列を動的生成して `PageData` を返す。画像にはページ番号のテキストを描画する（`QImage` は使わず、最小限の PNG バイト列を生成）。サイズは `int(612 * dpi / 72) × int(792 * dpi / 72)` |
| `render_page_range(start, end, dpi)` | 上記を range で呼び出すだけ |
| `extract_text(page_number, rect)` | `TextSelection(page_number, rect, f"[Stub] Selected text from page {page_number+1}")` |
| `extract_all_text()` | 固定文字列を返す |
| `close_document()` | 内部状態を None にリセット |
| `get_document_info()` | 保持中の DocumentInfo を返す |

> **PNG 生成について:** PySide6 を Model にインポートできないため、Python 標準ライブラリの `struct` + `zlib` で最小限の単色 PNG バイト列を生成するか、1×1 ピクセルの固定 PNG を引き延ばして返す。もしくは Phase 2 限定で簡易的に対応する方法として、`image_data` に数バイトの非空プレースホルダーを入れ、View 側で `QPixmap.loadFromData()` が失敗したらフォールバック表示する設計も許容する。

### `src/pdf_epub_reader/models/ai_model.py`

```python
class AIModel:
    """IAIModel のスタブ実装。Phase 4 で Gemini API に差し替える。"""
```

| メソッド | スタブの振る舞い |
|---|---|
| `analyze(request)` | mode に応じて固定のダミー翻訳/応答テキストを返す |
| `create_cache(full_text)` | `CacheStatus(is_active=True, ttl_seconds=3600, token_count=len(full_text.split()))` |
| `get_cache_status()` | `CacheStatus(is_active=False)` |
| `invalidate_cache()` | no-op |
| `count_tokens(text)` | `len(text.split())` |

---

## Step 11: `app.py` — MVP コンポーネントのワイヤリング

**ファイル:** `src/pdf_epub_reader/app.py`

```python
def main() -> None:
    """Model, View, Presenter を組み立ててアプリケーションを起動する。"""
    dotenv.load_dotenv()                        # .env から環境変数を読み込み
    run_app(_app_main)                          # qasync 統合ループで起動


async def _app_main() -> None:
    """非同期コンテキスト内で MVP コンポーネントを生成・結合する。"""
    # --- Models ---
    document_model = DocumentModel()
    ai_model = AIModel()

    # --- Views ---
    side_panel_view = SidePanelView()
    main_window = MainWindow(side_panel=side_panel_view)

    # --- Presenters ---
    panel_presenter = PanelPresenter(view=side_panel_view, ai_model=ai_model)
    _main_presenter = MainPresenter(                    # noqa: F841
        view=main_window,
        document_model=document_model,
        panel_presenter=panel_presenter,
    )

    main_window.show()
```

> **`_main_presenter` の `noqa: F841` について:** MainPresenter は `__init__` で View のコールバックを登録するため、変数に代入しなくても動作するが、GC で回収されないよう変数に保持しておく必要がある。lint 警告を抑制する。

---

## 実装順序（依存関係を考慮）

```
Step 1: IMainView インターフェース拡張
  ↓
Step 2: MockMainView 更新
  ↓
Step 3: MainPresenter 遅延読み込み対応
  ↓
Step 4: Presenter テスト更新 → pytest 全パス確認
  ↓
Step 5: utils/config.py
  ↓ (並行可能)
Step 6: infrastructure/event_loop.py
  ↓ (並行可能)
Step 7: SidePanelView
  ↓ (並行可能)
Step 10: スタブ Model
  ↓
Step 8-9: MainWindow + _DocumentGraphicsView  ← 最大のステップ
  ↓
Step 11: app.py ワイヤリング
  ↓
手動検証: python -m pdf_epub_reader で起動確認
```

---

## 検証チェックリスト

### 自動テスト

- [ ] `pytest tests/` — 既存テスト全パス + 新規テストパス
- [ ] `MockMainView` / `MockSidePanelView` が更新後も `isinstance(..., IMainView)` / `isinstance(..., ISidePanelView)` をパスする

### 手動検証

- [ ] `python -m pdf_epub_reader` でウィンドウ起動、空の状態でメニュー・ステータスバー・サイドパネルが表示される
- [ ] メニュー「ファイル → 開く(O)」→ QFileDialog が開き `*.pdf *.epub` フィルタが適用されている
- [ ] 任意の PDF/EPUB ファイルをウィンドウにドラッグ&ドロップ → スタブの灰色ページが表示される
- [ ] スクロール時、ビューポート近辺のページのみレンダリング要求が発生する（スタブ Model のログ等で確認）
- [ ] マウスドラッグで矩形選択 → サイドパネルの選択テキスト欄にスタブテキストが表示される
- [ ] 翻訳ボタン押下 → ローディングバー表示 → スタブの翻訳結果が結果エリアに表示 → ローディング非表示
- [ ] 解説付き翻訳ボタン → 結果に `---` 区切りで解説テキストが付く
- [ ] カスタムプロンプトタブでプロンプト入力 → 送信 → スタブ結果表示
- [ ] Ctrl+マウスホイールでズーム → ステータスバーのズーム値が追従
- [ ] ステータスバーのズームスピンボックスで値変更 → ドキュメント表示が更新される
- [ ] ステータスバーのページスピンボックスで番号変更 → その場所までスクロールする
- [ ] ファイルを開いた後、「最近開いたファイル」メニューにパスが追加されている
- [ ] アプリ再起動後も「最近開いたファイル」メニューに前回のパスが残っている
- [ ] ウィンドウタイトルに開いた文書のタイトル（またはファイルパス）が表示される
- [ ] Fusion スタイルが適用されている（OS デフォルトと見た目が異なる）
