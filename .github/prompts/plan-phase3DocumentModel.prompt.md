## Plan: DocumentModel PyMuPDF本実装

スタブの`DocumentModel`をPyMuPDF(fitz)ベースに全面差し替え。PDF/EPUB両対応、LRUキャッシュ付きレンダリング、パスワード保護PDF対応、ToC抽出、設定のJSON永続化を含む。影響範囲はDTO・例外・Protocol・config・Model・Presenter・Mock・テストの計12ファイル変更＋4ファイル新規。

---

### フェーズA: 基盤変更（各ステップ並行可能）

**Step 1: DTO拡張** — `src/pdf_epub_reader/dto/document_dto.py`
- `ToCEntry` dataclass追加: `title: str`, `page_number: int`, `level: int`
- `DocumentInfo` に `toc: list[ToCEntry] = field(default_factory=list)` 追加
- 既存コードは`toc`デフォルト空リストのため破壊的変更なし

**Step 2: 例外クラス定義** — `src/pdf_epub_reader/utils/exceptions.py`
- `DocumentError(Exception)` — 基底例外
- `DocumentOpenError(DocumentError)` — ファイルオープン失敗（破損、未対応形式）
- `DocumentPasswordRequired(DocumentError)` — パスワード保護検出、`file_path: str` 属性付き
- `DocumentRenderError(DocumentError)` — ページレンダリング失敗、`page_number: int` 属性付き

**Step 3: 設定拡張** — `src/pdf_epub_reader/utils/config.py`
- レンダリング定数追加: `DEFAULT_RENDER_FORMAT = "png"`, `DEFAULT_JPEG_QUALITY = 85`, `PAGE_CACHE_MAX_SIZE = 50`
- `AppConfig` dataclass定義（全設定値を一元管理）
- JSON永続化関数: `load_config() -> AppConfig`, `save_config(config)`
- 設定ファイルパス: `platformdirs.user_config_dir()` 配下の `config.json`

**Step 4: 依存追加** — `pyproject.toml`
- `"Pillow>=10.0"` 追加（エラーページ画像生成、JPEG出力）
- `"platformdirs>=4.0"` 追加（設定ファイルパス解決）

---

### フェーズB: インターフェース更新（*Step 1, 2に依存*）

**Step 5: IDocumentModelプロトコル更新** — `src/pdf_epub_reader/interfaces/model_interfaces.py`
- `open_document` シグネチャ変更: `(self, file_path: str, password: str | None = None) -> DocumentInfo`
- ToCは`DocumentInfo`に含まれるため他メソッド変更不要

**Step 6: IMainViewプロトコル更新** — `src/pdf_epub_reader/interfaces/view_interfaces.py`
- `show_password_dialog(self, file_path: str) -> str | None` 追加
- 戻り値: パスワード文字列 or キャンセル時`None`

**Step 7: Mock更新** — `tests/mocks/mock_models.py`, `tests/mocks/mock_views.py`
- `MockDocumentModel.open_document` に `password` パラメータ追加
- `MockDocumentModel._should_require_password: bool` テスト制御フラグ追加
- `MockMainView.show_password_dialog` 追加（固定値返却）

---

### フェーズC: DocumentModel本実装（*Step 1-5に依存*、Phase最大の作業）

**Step 8: 基盤構造** — `src/pdf_epub_reader/models/document_model.py` 全面書き換え
- `__init__`: `ThreadPoolExecutor(max_workers=1)`, `fitz.Document | None`, `OrderedDict` LRUキャッシュ, `AppConfig` 読み込み

**Step 9: `open_document` 実装**
- `fitz.open(file_path)` をexecutorで実行
- パスワード保護: `doc.needs_pass` → `password`なしなら`DocumentPasswordRequired`送出、ありなら`doc.authenticate()` 試行
- メタデータ: `doc.metadata["title"]`
- ToC: `doc.get_toc()` → `[level, title, page]` を `list[ToCEntry]` に変換
- キャッシュクリア（新文書オープン時）

**Step 10: `render_page` 実装**
- キャッシュチェック: `(page_number, dpi)` キー
- executorレンダリング: `page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72), alpha=False)`
- フォーマット分岐: PNG → `pix.tobytes("png")` / JPEG → `pix.pil_tobytes("jpeg", quality=...)`
- エラー時: Pillowでエラーページ画像生成して返却（例外ではなく画像で返す）
- LRUキャッシュ更新（`OrderedDict` で手動実装、maxsize超過時は最古削除）

**Step 11: `render_page_range`** — 各ページを`render_page`で個別レンダ（キャッシュ活用）

**Step 12: `extract_text`** — executor内で `page.get_text("text", clip=fitz.Rect(...))`

**Step 13: `extract_all_text`** — 全ページ順次抽出、`--- Page N ---` 区切り付き

**Step 14: `close_document`** — `doc.close()`, キャッシュ全クリア, 内部状態リセット

**Step 15: エラーページヘルパー** — `_generate_error_page(width, height, message) -> bytes`、Pillow使用（薄赤背景＋エラーテキスト描画）

---

### フェーズD: Presenter更新（*Step 5, 6と並行可能*）

**Step 16: パスワードフロー** — `src/pdf_epub_reader/presenters/main_presenter.py`
- `open_file` に `try/except DocumentPasswordRequired` 追加
- フロー: 例外捕捉 → `view.show_password_dialog(file_path)` → `None`ならキャンセル → 再度`open_document(file_path, password)`
- `DocumentOpenError` の `except` も追加 → `view.show_error_dialog()`

---

### フェーズE: テスト（*Step 8-16に依存*）

**Step 17: テストフィクスチャ**
- `tests/fixtures/` ディレクトリ新規作成
- `tests/generate_fixtures.py` — PyMuPDFでテスト用ファイルを生成するスクリプト:
  - `sample.pdf`: 3ページ、既知テキスト入り
  - `sample.epub`: 簡易EPUB
  - `protected.pdf`: パスワード`"test123"`付きPDF
- `conftest.py` にフィクスチャパスを返す`@pytest.fixture`追加

**Step 18: DocumentModel統合テスト** — `tests/test_models/test_document_model.py`

| テストカテゴリ | ケース |
|---|---|
| **open_document** | PDF正常オープン、EPUB正常オープン、存在しないファイル→`DocumentOpenError`、パスワードPDF(password=None)→`DocumentPasswordRequired`、正しいパスワード→成功、間違いパスワード→`DocumentOpenError` |
| **render_page** | 正常レンダリング(PNG/JPEG)、画像ヘッダ検証、DPIによるサイズ変化、キャッシュヒット、範囲外ページ→エラー画像 |
| **extract_text** | 既知テキスト領域の抽出一致、テキストなし領域→空文字列 |
| **extract_all_text** | ページ区切りフォーマット検証、全ページテキスト含有 |
| **close_document** | クローズ後`get_document_info`→`None`、クローズ後操作→例外 |
| **LRUキャッシュ** | 上限超過エビクション、DPI別キャッシュ独立性 |

**Step 19: Presenterテスト更新** — `tests/test_presenters/test_main_presenter.py`
- パスワード正常入力→オープン成功
- キャンセル→オープン中止
- `DocumentOpenError`→エラーダイアログ表示

---

### フェーズF: 検証

**Step 20:** `uv run pytest tests/ -v` で全テスト合格確認

**Step 21:** 手動スモークテスト — 実PDF/EPUBのD&D、スクロール遅延読み込み、ズーム、テキスト選択

---

### 変更ファイル一覧
| ファイル | 変更内容 |
|---|---|
| `src/pdf_epub_reader/dto/document_dto.py` | `ToCEntry`追加、`DocumentInfo`拡張 |
| `src/pdf_epub_reader/utils/exceptions.py` | 例外クラス4種定義 |
| `src/pdf_epub_reader/utils/config.py` | レンダリング設定、`AppConfig`、JSON永続化 |
| `src/pdf_epub_reader/interfaces/model_interfaces.py` | `open_document`にpassword引数 |
| `src/pdf_epub_reader/interfaces/view_interfaces.py` | `show_password_dialog`追加 |
| `src/pdf_epub_reader/models/document_model.py` | **全面書き換え** — PyMuPDF本実装 |
| `src/pdf_epub_reader/presenters/main_presenter.py` | パスワードフロー、エラーハンドリング |
| `src/pdf_epub_reader/app.py` | DocumentModel初期化にconfig渡し |
| `tests/mocks/mock_models.py` | password対応、フラグ追加 |
| `tests/mocks/mock_views.py` | `show_password_dialog`追加 |
| `tests/conftest.py` | フィクスチャパス追加 |
| `pyproject.toml` | Pillow, platformdirs追加 |

### 新規ファイル
- `tests/fixtures/sample.pdf`, `sample.epub`, `protected.pdf`
- `tests/generate_fixtures.py`

---

### 設計判断メモ
- PyMuPDFの`Document`は非スレッドセーフ → 全fitz操作は`ThreadPoolExecutor(max_workers=1)`で直列実行
- LRUキャッシュは`collections.OrderedDict`で手動実装（`functools.lru_cache`はasync非対応）
- `show_password_dialog`はPassive Viewの例外的同期メソッド（モーダルダイアログなので許容）
- JPEG出力に`pix.pil_tobytes()`を使用するためPillow依存が必要
- **Phase 3.5を企画書に追記**: 包括的設定ダイアログ（画像フォーマット、JPEG品質、キャッシュサイズ、デフォルトDPI）のUI実装
