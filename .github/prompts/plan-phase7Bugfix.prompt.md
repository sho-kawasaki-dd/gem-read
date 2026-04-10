## Plan: Phase 7 Bugfix — キャッシュ作成モデル不一致 / メニュー欠落 / 起動時モデル検証

Phase 7 実装後に発見された 2 つのバグと、それに付随するモデル管理の改善を行う。

---

### Phase I: キャッシュ作成モデル修正

**1. `PanelPresenter` に `get_current_model()` getter 追加** _(parallel with 2)_

- [panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py) — `def get_current_model(self) -> str | None`

**2. `MainPresenter._do_cache_create()` で選択中モデルを使用** _(depends on 1)_

- [main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py#L335) — `model_name=self._config.gemini_model_name` → `model_name=self._panel_presenter.get_current_model()`

### Phase II: キャッシュ非対応モデルのエラー改善

**3. `AIModel.create_cache()` 内でエラーメッセージ変換**

- [ai_model.py](src/pdf_epub_reader/models/ai_model.py) — `"not supported for createCachedContent"` を検出 → `AICacheError("このモデルはコンテキストキャッシュをサポートしていません: {model}")` に変換

### Phase III: デフォルト値変更 + 起動時バックグラウンド Fetch

**4. Config デフォルト値を空に**

- [config.py](src/pdf_epub_reader/utils/config.py) — `DEFAULT_GEMINI_MODEL = ""`, `selected_models` デフォルト `[]`

**5. `ISidePanelView` Protocol に `set_model_combo_enabled(bool)` 追加**

- [view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py)

**6. `SidePanelView` にモデル未設定表示を実装**

- [side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py) — 空リスト時「モデル未設定」プレースホルダー + disabled

**7. `PanelPresenter` でモデル未設定ガード**

- [panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py) — `_do_translate()` / `_do_custom_prompt()` / `_fire_cache_create()` の先頭で `_current_model` が空/None なら `"⚠️ モデルが未設定です。Preferences (Ctrl+,) → AI Models タブで Fetch Models を実行してください。"` を表示して return

**8. `MainPresenter` にバックグラウンドモデル検証を追加** _(depends on 4-7)_

- [main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py) — `__init__` 末尾で `asyncio.ensure_future(self._validate_models_on_startup())`
- **成功時**: `gemini_model_name` が空 or Fetch リストに無い → config クリア + `save_config()` 永続化 + ステータス案内 + プルダウン disabled
- **`AIKeyMissingError`**: ステータス「API キーを設定してください」
- **ネットワークエラー等**: ステータス警告 + 既存設定で続行（オフライン利用を妨げない）

### Phase IV: メニュー追加

**9. `MainWindow._build_menu_bar()` に「キャッシュ(&C)」メニュー追加**

- [main_window.py](src/pdf_epub_reader/views/main_window.py#L145) — Edit の右に「キャッシュ(&C)」→「キャッシュ管理(&M)...」(Ctrl+Alt+G)
- `_handle_cache_management_requested()` で `self._on_cache_management_requested` を発火

### Phase V: テスト

**10. Mock 更新** _(parallel with 11-13)_

- [mock_views.py](tests/mocks/mock_views.py): `MockSidePanelView.set_model_combo_enabled` 追加

**11. PanelPresenter テスト** — モデル未設定ガード（translate / cache create）

**12. MainPresenter テスト** — `_validate_models_on_startup` 4パターン (valid / invalid model / fetch failure / no API key)

**13. AIModel テスト** — キャッシュ非対応エラーメッセージ変換

---

### Relevant Files

| 種別       | ファイル                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 修正       | [config.py](src/pdf_epub_reader/utils/config.py), [view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py), [panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py), [main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py), [ai_model.py](src/pdf_epub_reader/models/ai_model.py), [main_window.py](src/pdf_epub_reader/views/main_window.py), [side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py) |
| テスト修正 | [mock_views.py](tests/mocks/mock_views.py), [test_panel_presenter.py](tests/test_presenters/test_panel_presenter.py), [test_main_presenter.py](tests/test_presenters/test_main_presenter.py), [test_ai_model.py](tests/test_models/test_ai_model.py)                                                                                                                                                                                                             |

### Verification

1. `pytest tests/ -v` — 全テスト通過
2. 手動: 初回起動 → モデル未設定表示 + ステータス案内
3. 手動: valid model config → 起動直後にプルダウン有効
4. 手動: 廃止モデルが config 残存 → モデルクリア + 案内 + config.json 更新
5. 手動: オフライン起動 → 既存設定で続行 + 警告
6. 手動: サイドパネルで選択したモデルでキャッシュ作成される
7. 手動: キャッシュ非対応モデル → 専用エラーメッセージ
8. 手動: 「キャッシュ(&C)」メニュー or Ctrl+Alt+G → ダイアログ表示

### Decisions

- `gemini_model_name` のみリセット。`selected_models` は維持（ユーザー選択尊重）
- Fetch 失敗時 → 既存設定で続行 + 警告（オフライン利用を妨げない）
- 無効モデル検出時は config.json に即時永続化
- メニュー表記「キャッシュ(&C)」（ファイルメニューと統一）
