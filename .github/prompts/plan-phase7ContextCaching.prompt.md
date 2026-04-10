## Plan: Phase 7 — Context Caching 実装

AIModel の 4 つのスタブ（`create_cache` / `get_cache_status` / `invalidate_cache` / `count_tokens`）を google-genai SDK の Explicit Caching API で本実装し、`analyze()` にキャッシュ自動付与＋フォールバックロジックを追加する。サイドパネルにキャッシュ作成/削除トグルボタンを追加し、詳細管理は専用ダイアログで行う。

---

### Phase A: Foundation（DTO・Config・例外）— _並行作業可_

**A1. CacheStatus DTO 拡張** ([ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py))

- `model_name: str | None = None` — キャッシュ紐付きモデル名
- `expire_time: str | None = None` — ISO 形式の有効期限

**A2. AICacheError 例外追加** ([exceptions.py](src/pdf_epub_reader/utils/exceptions.py))

- `class AICacheError(AIError)` — キャッシュ作成失敗・トークン不足等用

**A3. AppConfig にキャッシュ TTL 追加** ([config.py](src/pdf_epub_reader/utils/config.py))

- `DEFAULT_CACHE_TTL_MINUTES = 60` 定数 + `cache_ttl_minutes: int` フィールド
- バリデーション定数: `CACHE_TTL_MIN = 1`, `CACHE_TTL_MAX = 1440`

**A4. 設定ダイアログに TTL スピナー追加**

- `ISettingsDialogView` に `get_cache_ttl_minutes` / `set_cache_ttl_minutes` 追加
- [settings_dialog.py](src/pdf_epub_reader/views/settings_dialog.py) の AI Models タブに QSpinBox
- [settings_presenter.py](src/pdf_epub_reader/presenters/settings_presenter.py) に TTL 読み書き

---

### Phase B: AIModel コア実装 — _Phase A に依存_

**B1. `IAIModel` Protocol 更新** ([model_interfaces.py](src/pdf_epub_reader/interfaces/model_interfaces.py))

- `create_cache(full_text, *, model_name=None, display_name=None)` / `count_tokens(text, *, model_name=None)` にモデル名パラメータ追加
- `async def update_cache_ttl(self, ttl_minutes: int) -> CacheStatus` 新規追加
- `async def list_caches(self) -> list[CacheStatus]` 新規追加

**B2. `count_tokens` 本実装** ([ai_model.py](src/pdf_epub_reader/models/ai_model.py))

- `await self._client.aio.models.count_tokens(model=model_name, contents=text)`
- SDK エラー → `AIAPIError` ラップ

**B3. `create_cache` 本実装**

- 内部状態: `self._cache_name: str | None`, `self._cache_model: str | None`
- SDK: `await self._client.aio.caches.create(model=..., config=CreateCachedContentConfig(contents=[full_text], display_name=display_name, ttl=...))`
- `display_name` にはプレフィックス `"pdf-reader: {filename}"` を設定（`list_caches` でのフィルタリング用）
- Presenter がドキュメントのファイル名を `display_name` 引数として渡す
- **system_instruction はキャッシュに含めない**（翻訳/カスタムでシステム指示が異なるため）
- SDK エラー → `AICacheError` 送出（自動フォールバック用）

**B4. `get_cache_status` 本実装**

- `_cache_name` 存在時: `await self._client.aio.caches.get()` で最新状態取得
- expire 済み → 内部状態クリア → `is_active=False` 返却

**B5. `invalidate_cache` 本実装**

- `await self._client.aio.caches.delete(name=...)` + 内部状態クリア
- 既に削除済みの場合はログのみ（例外なし）

**B6. `analyze()` にキャッシュ統合**

- キャッシュ active かつモデル一致時: `GenerateContentConfig(cached_content=self._cache_name, system_instruction=...)` を付与
- **失敗時フォールバック**: キャッシュ付きリクエストが非レートリミットエラーの場合、キャッシュを内部クリア、キャッシュなしで 1 回リトライ
- **`usage_metadata` ログ出力**: レスポンスの `usage_metadata` から `prompt_token_count`, `cached_content_token_count`, `candidates_token_count` を `logger.info` で出力し、キャッシュヒットを実行時に確認可能にする

**B7. `update_cache_ttl` 新設**

- `await self._client.aio.caches.update(name=..., config=UpdateCachedContentConfig(ttl=...))`

**B8. `list_caches` 新設**

- `async def list_caches(self) -> list[CacheStatus]`
- `client.aio.caches.list()` で全キャッシュ取得 → `display_name.startswith("pdf-reader:")` でアプリ用キャッシュのみフィルタ
- 各エントリを `CacheStatus` DTO に変換して返却
- SDK エラー → `AIAPIError` ラップ

---

### Phase C: View インターフェース・サイドパネル — _Phase A に依存_

**C1. `ISidePanelView` 拡張** ([view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py))

- `set_on_cache_create_requested(cb)` / `set_on_cache_invalidate_requested(cb)` コールバック登録
- `set_cache_active(active: bool)` — ボタンテキスト切替（"作成" / "削除"）
- `set_cache_button_enabled(enabled: bool)` — 操作中の無効化
- `show_confirm_dialog(title: str, message: str) -> bool` — モデル切替確認

**C2. `ICacheDialogView` Protocol 新設** (同ファイル)

- **タブ1「現在のキャッシュ」**: ステータス表示セッター群 + `get_new_ttl_minutes()` — 作成/削除/TTL更新操作
- **タブ2「キャッシュ確認」**: `set_cache_list(items: list[CacheStatus])` — アプリ用キャッシュ一覧のテーブル表示 + `get_selected_cache_name() -> str | None` — 選択行の名前取得
- `show() -> str | None` — 返値: `"delete"` / `"update_ttl"` / `"create"` / `"delete_selected"` / `None`(閉じる)

**C3. SidePanelView にキャッシュ UI 追加** ([side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py))

- 既存 `_cache_label` の右にトグル QPushButton 追加
- `show_confirm_dialog` → `QMessageBox.question()` で実装

---

### Phase D: Presenter 更新 — _Phase B, C に依存_

**D1. PanelPresenter** ([panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py))

- 内部状態: `_cache_status: CacheStatus`
- `set_on_cache_create_handler(cb)` / `set_on_cache_invalidate_handler(cb)` — MainPresenter が登録するコールバック
- `update_cache_status(status: CacheStatus)` — 公開メソッド（MainPresenter から呼出）→ View を更新
- `_on_model_changed` 改修: キャッシュ active + モデル不一致 → `show_confirm_dialog` → OK: invalidate ハンドラ発火 + モデル更新 / Cancel: `view.set_selected_model` でリバート

**D2. MainPresenter** ([main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py))

- `__init__`: `panel_presenter.set_on_cache_create_handler(...)` 等を登録
- `async _on_cache_create()`: `extract_all_text()` → `create_cache(full_text, model_name=...)` → `panel_presenter.update_cache_status()`。`AICacheError` catch → ステータスメッセージ通知
- `async _on_cache_create()` 内で `display_name=f"pdf-reader: {filename}"` を `create_cache` に渡す（ファイル名は `document_model.get_document_info()` から取得）
- `async _on_cache_invalidate()`: `invalidate_cache()` → ステータス更新
- `open_file()` 先頭: 既存キャッシュがあれば `invalidate_cache()` を呼ぶ
- `_on_cache_management_requested()`: スタブ → **async 本実装**。`await ai_model.list_caches()` + `await ai_model.get_cache_status()` でデータ取得後、`CachePresenter` にデータを渡してダイアログ表示。ユーザーアクション（`"delete"` / `"update_ttl"` / `"create"` / `"delete_selected"`）に応じて非同期処理を実行
- ツールバーにキャッシュ管理ボタン追加。キーバインド: **Ctrl+Alt+G**

---

### Phase E: キャッシュ管理ダイアログ — _Phase C2 に依存_

**E1. CachePresenter 新設** (`src/pdf_epub_reader/presenters/cache_presenter.py`)

- `__init__(view: ICacheDialogView, cache_status: CacheStatus, cache_list: list[CacheStatus], config: AppConfig)`
- `show() -> tuple[str | None, int, str | None]`: ダイアログ表示＋ユーザーアクション＋新TTL値＋選択キャッシュ名を返却
- View に現在のキャッシュ情報とキャッシュ一覧を設定して表示

**E2. CacheDialog View 新設** (`src/pdf_epub_reader/views/cache_dialog.py`)

- QDialog モーダル、2タブ構成:
  - **タブ1「現在のキャッシュ」**: キャッシュ名、モデル名、トークン数、残り TTL、有効期限を表示。操作ボタン: 作成(非active時) / 削除(active時) / TTL更新(active時) + QSpinBox
  - **タブ2「キャッシュ確認」**: `list_caches()` 結果をテーブル表示（name, model, display_name, token_count, expire_time）。選択行の削除ボタン付き
- 「閉じる」ボタンで終了

---

### Phase F: テスト — _全 Phase に依存_

**F1. Mock 更新**

- [mock_models.py](tests/mocks/mock_models.py): `create_cache`/`count_tokens` にパラメータ追加、`update_cache_ttl` / `list_caches` 追加、失敗制御フラグ
- [mock_views.py](tests/mocks/mock_views.py): キャッシュ関連メソッド追加 + `MockCacheDialogView` 新設

**F2. AIModel テスト** ([test_ai_model.py](tests/test_models/test_ai_model.py)) ~10 件

- `count_tokens` 正常系 + error ラップ
- `create_cache` 正常系 + `AICacheError` 変換
- `get_cache_status` active / inactive / expire済み
- `invalidate_cache` 正常系 + 既削除（エラー無視）
- `analyze` with cache（`cached_content` 付与確認）+ フォールバック
- `update_cache_ttl` 正常系
- `list_caches` 正常系（`"pdf-reader:"` フィルタリング確認）+ 空リスト

**F3. PanelPresenter テスト** ([test_panel_presenter.py](tests/test_presenters/test_panel_presenter.py)) ~6 件

- 作成/削除ハンドラ呼出確認、`update_cache_status` → View 更新、モデル切替確認ダイアログ

**F4. MainPresenter テスト** ([test_main_presenter.py](tests/test_presenters/test_main_presenter.py)) ~5 件

- キャッシュ作成オーケストレーション、作成エラーハンドリング、ドキュメント切替時 invalidate、ダイアログフロー

**F5. CachePresenter テスト** (`tests/test_presenters/test_cache_presenter.py`) ~3 件

---

### Relevant Files (summary)

| 種別       | ファイル                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 修正       | [ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py), [exceptions.py](src/pdf_epub_reader/utils/exceptions.py), [config.py](src/pdf_epub_reader/utils/config.py), [model_interfaces.py](src/pdf_epub_reader/interfaces/model_interfaces.py), [view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py), [ai_model.py](src/pdf_epub_reader/models/ai_model.py), [panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py), [main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py), [side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py), [main_window.py](src/pdf_epub_reader/views/main_window.py), [settings_dialog.py](src/pdf_epub_reader/views/settings_dialog.py), [settings_presenter.py](src/pdf_epub_reader/presenters/settings_presenter.py) |
| 新規       | `presenters/cache_presenter.py`, `views/cache_dialog.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| テスト修正 | [mock_models.py](tests/mocks/mock_models.py), [mock_views.py](tests/mocks/mock_views.py), [test_ai_model.py](tests/test_models/test_ai_model.py), [test_panel_presenter.py](tests/test_presenters/test_panel_presenter.py), [test_main_presenter.py](tests/test_presenters/test_main_presenter.py)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| テスト新規 | `test_presenters/test_cache_presenter.py`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

---

### Verification

1. `pytest tests/test_models/test_ai_model.py -v` — AIModel の全キャッシュメソッドテスト通過
2. `pytest tests/test_presenters/ -v` — 全 Presenter テスト通過（既存+新規）
3. `pytest tests/ -v` — 全テスト通過（リグレッション確認）
4. 手動: PDF 開く → "全文キャッシュを作成" → ステータス確認 → 翻訳実行 → ログで `cached_content_token_count > 0` を確認 → モデル切替確認ダイアログ → Ctrl+Alt+G でキャッシュ管理ダイアログ → TTL 更新/削除
5. 手動: キャッシュ管理ダイアログの「キャッシュ確認」タブで `pdf-reader:` プレフィックス付きキャッシュのみテーブル表示されること
6. 手動: 短いドキュメントでキャッシュ作成失敗 → フォールバック通知
7. 手動: ドキュメント切替で前キャッシュが自動削除されること

---

### Decisions

- **system_instruction はキャッシュに含めない** — 翻訳/カスタムプロンプトでシステム指示が異なるため
- **キャッシュ対象はドキュメント全文テキストのみ** — 画像はキャッシュしない
- **PanelPresenter → MainPresenter 連携** — コールバックパターンで結合度を抑える
- **`display_name` プレフィックス `"pdf-reader: "`** — `create_cache` で設定し `list_caches` でフィルタリングに使用
- **`usage_metadata` ログ出力** — `analyze()` のレスポンスから `cached_content_token_count` 等を `logger.info` で出力
- **キャッシュ管理ダイアログ呼出** — ツールバーボタン＋ **Ctrl+Alt+G** キーバインドから起動。表示前に `await list_caches()` + `await get_cache_status()` でデータ取得
- **スコープ外** — 複数ドキュメント同時キャッシュ、暗黙キャッシュ (Implicit Caching) の活用
