# Plan: Phase 6 — Gemini API 本実装

AIModel のスタブを `google-genai` SDK ベースの本実装に差し替え、設定ダイアログに AI Models タブ（API 経由モデル一覧取得+選択）、サイドパネルにモデル切替プルダウンを追加する。システムプロンプトと出力言語も AppConfig で設定可能にする。

---

### Steps

#### Phase A: Foundation（並行着手可）

**Step 1: pyproject.toml 依存変更**
- `google-generativeai>=0.8` → `google-genai>=1.0` に差替え

**Step 2: AI 例外クラス追加** — [exceptions.py](src/pdf_epub_reader/utils/exceptions.py)
- `AIError(Exception)` — AI 系基底例外
- `AIKeyMissingError(AIError)` — API キー未設定
- `AIAPIError(AIError)` — API 通信エラー（`status_code`, `message` 属性付き）
- `AIRateLimitError(AIAPIError)` — 429 レート制限

**Step 3: DTO 追加・変更** — [ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py)
- `ModelInfo(frozen dataclass)`: `model_id: str`, `display_name: str` を新設
- `AnalysisRequest` に `model_name: str | None = None` フィールド追加

**Step 4: AppConfig に AI 設定フィールド追加** — [config.py](src/pdf_epub_reader/utils/config.py)
- `gemini_model_name: str = "gemini-3.1-flash-lite-preview"`
- `selected_models: list[str] = ["gemini-3.1-flash-lite-preview"]`
- `system_prompt_translation: str = DEFAULT_TRANSLATION_PROMPT` （`{output_language}` プレースホルダー付きテンプレート）
- `output_language: str = "日本語"`
- `DEFAULT_TRANSLATION_PROMPT` 定数: 「翻訳 + LaTeX数式 + `\ce{}` 化学式 + Markdown出力」の指示文

#### Phase B: AIModel 本実装（*Step 1-4 に依存*）

**Step 5: AIModel 全面書き換え** — [ai_model.py](src/pdf_epub_reader/models/ai_model.py)
- コンストラクタ: `(api_key=None, config=None)` → `genai.Client` 生成。キー未設定時はクライアント=None（アプリ起動は許可）
- `analyze(request)`:
  - `_client` が None → `raise AIKeyMissingError`
  - モデル名: `request.model_name or config.gemini_model_name`
  - TRANSLATION: `config.system_prompt_translation.format(output_language=config.output_language)` をシステム指示に使用
  - CUSTOM_PROMPT: `"{output_language}で回答してください。Markdown形式で回答してください。"` をシステム指示に使用
  - マルチモーダル: `request.images` 非空時に `Part.from_bytes` で画像添付
  - `await client.aio.models.generate_content(...)` で API呼び出し
  - レスポンス → `AnalysisResult` に変換
- `_call_with_retry()`: 最大3回、指数バックオフ (1s→2s→4s)。429/500/502/503/504 をリトライ対象。google-genai例外 → `AIAPIError`/`AIRateLimitError` にラップ
- `list_available_models()`: `client.aio.models.list()` → `generateContent` サポートモデルのみフィルタ → `list[ModelInfo]`
- `update_config(config)`: 内部 config 更新
- `create_cache`/`get_cache_status`/`invalidate_cache`/`count_tokens`: **スタブ維持 (Phase 7)**

#### Phase C: Protocol 更新（*Step 3-4 に依存、Phase B と並行可*）

**Step 6: IAIModel Protocol 更新** — [model_interfaces.py](src/pdf_epub_reader/interfaces/model_interfaces.py)
- `list_available_models() -> list[ModelInfo]`、`update_config(config)` 追加

**Step 7: ISettingsDialogView Protocol 拡張** — [view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py)
- AI Models タブ用の getter/setter 8メソッド + `set_on_fetch_models_requested` + `set_fetch_models_loading` + `show_fetch_models_error`

**Step 8: ISidePanelView Protocol 拡張** — [view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py)
- `set_available_models`, `set_selected_model`, `set_on_model_changed`

#### Phase D: Settings Dialog 拡張（*Step 7 に依存*）

**Step 9: SettingsDialog に AI Models タブ追加** — [settings_dialog.py](src/pdf_epub_reader/views/settings_dialog.py)
- 3つ目のタブ "AI Models": Default Model (QComboBox) / Available Models (QListWidget+チェックボックス + Fetch QPushButton) / Output Language (QLineEdit) / System Prompt Translation (QTextEdit)

**Step 10: SettingsPresenter 拡張** — [settings_presenter.py](src/pdf_epub_reader/presenters/settings_presenter.py)
- `ai_model: IAIModel | None = None` を引数追加（後方互換）
- AI フィールドの `_populate_view` / `_read_config_from_view` 追加
- Fetch Models: `asyncio.ensure_future` → `await ai_model.list_available_models()` → `view.set_available_models()`

#### Phase E: Side Panel モデル選択（*Step 8 に依存*）

**Step 11: SidePanelView にモデルプルダウン追加** — [side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py)
- タブ上部にモデル選択 QComboBox

**Step 12: PanelPresenter 拡張** — [panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py)
- `_current_model` 状態管理、`AnalysisRequest(model_name=...)` に渡す
- `_do_translate` / `_do_custom_prompt` に **エラーハンドリング追加**: `AIKeyMissingError`→ "API キー未設定" / `AIAPIError`→ エラー詳細 をパネルに表示
- `set_available_models` / `set_selected_model` パブリックメソッド追加

#### Phase F: Wiring 統合（*Phase D-E に依存*）

**Step 13: app.py 更新** — `AIModel(config=config)` に変更

**Step 14: MainPresenter 更新** — [main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py)
- `ai_model` 引数追加、初期化時にモデルリストをサイドパネルへ設定
- `_on_settings_requested`: `SettingsPresenter` に `ai_model` を渡す
- `_apply_config_changes`: `ai_model.update_config()` + モデルリスト更新

#### Phase G: テスト（並行して各フェーズ完了後に順次追加）

**Step 15-17: mock 更新** — `MockAIModel`, `MockSettingsDialogView`, `MockSidePanelView` に新メソッド追加

**Step 18: test_ai_model.py** — `google.genai` を mock.patch で差替え。12+ テストケース（翻訳/マルチモーダル/カスタム/モデル指定/キー未設定/APIエラー/リトライ/リトライ上限/モデル一覧 等）

**Step 19-20: 既存テスト更新** — `test_panel_presenter.py`（エラーハンドリング・モデル選択）、`test_settings_presenter.py`（AI 設定 populate/read）

---

### Relevant files

| ファイル | 変更概要 |
|---|---|
| [pyproject.toml](pyproject.toml) | SDK 差替え |
| [exceptions.py](src/pdf_epub_reader/utils/exceptions.py) | AI 例外 4 種追加 |
| [ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py) | `ModelInfo` 新設、`AnalysisRequest` に `model_name` 追加 |
| [config.py](src/pdf_epub_reader/utils/config.py) | AppConfig に AI 設定 4 フィールド + 定数追加 |
| [ai_model.py](src/pdf_epub_reader/models/ai_model.py) | **全面書き換え** |
| [model_interfaces.py](src/pdf_epub_reader/interfaces/model_interfaces.py) | IAIModel 拡張 |
| [view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py) | ISettingsDialogView + ISidePanelView 拡張 |
| [settings_dialog.py](src/pdf_epub_reader/views/settings_dialog.py) | AI Models タブ追加 |
| [settings_presenter.py](src/pdf_epub_reader/presenters/settings_presenter.py) | AI 設定 + Fetch 非同期処理 |
| [side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py) | モデルプルダウン追加 |
| [panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py) | モデル選択 + エラーハンドリング |
| [main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py) | `ai_model` 引数 + 設定反映フロー |
| [app.py](src/pdf_epub_reader/app.py) | AIModel への config 渡し |
| テスト 6 ファイル | mock 更新 + 新規テスト 12+ 件 + 既存テスト拡張 |

---

### Verification

1. `uv sync` で `google-genai` がインストールされること
2. `pytest tests/ -v` — 全テストパス（既存回帰なし）
3. `get_errors` でコンパイルエラーなし
4. 手動: 設定ダイアログ → AI Models → Fetch Models → 一覧表示確認
5. 手動: サイドパネルでモデル切替 → テキスト選択 → 翻訳 → 結果表示
6. 手動: API キー未設定時にパネルへエラーメッセージ表示

---

### Decisions

- AIModel は API キー未設定でもインスタンス化可能（ドキュメント閲覧専用利用を妨げない）
- `model_name` は `AnalysisRequest` に持たせる（リクエスト単位のモデル指定）
- システムプロンプトは `{output_language}` プレースホルダー付きテンプレート（AIModel 内で置換）
- SettingsPresenter の `ai_model` 引数は Optional（後方互換維持）
- リトライは AIModel 内部のプライベートヘルパー（外部ライブラリ不使用）
- **Phase 7 先送り**: `create_cache` / `get_cache_status` / `invalidate_cache` / `count_tokens` はスタブ維持。`analyze()` 内の `cached_content` 参照も Phase 7
