# Plan: Plotly Dynamic Visualization (pdf_epub_reader)

Gemini API などから返ってきた数式・グラフ仕様を、手元で Plotly により動的可視化する機能を `pdf_epub_reader` に追加する。LLM 応答からの抽出 → 検証 → 描画を一系統に揃え、複数 spec にも対応する。

## 0. ゴールとスコープ

- 入力: AI サイドパネルの **成功結果** に含まれる Plotly グラフ仕様（fenced code block）。
- 出力: 別ウィンドウ（`QWebEngineView`）で hover/zoom 可能な動的グラフを表示。
- 対象: 翻訳タブ・カスタムタブいずれの active result にも適用できる shared button。
- **非ゴール（Phase 1）**: 任意 Python コードの実行、PNG/HTML 保存、Markdown export との統合、subplot 自動結合。

## 1. 設計の前提（最重要: セキュリティ）

LLM 応答の Python を直接 `exec` することは、PDF 本文経由の prompt injection を踏む現実的リスクがある。よって本企画では実行方式を以下に固定する。

- **Phase 1 では「Plotly figure JSON のみ」を受け取って `plotly.io.from_json` で復元**する。
- Python 実行が必要な要望が出てきた段階で、Phase 2 として **subprocess sandbox + 出力を Plotly JSON に正規化** する経路を後付けする。描画層は Phase 1 と共通化する。
- 設定でオプトイン制とし、デフォルト無効にする。

## 2. 推奨ロードマップ（Phase 切り）

### Phase 1: JSON-only 可視化（MVP）

1. LLM への system prompt 追補（`fig.to_json()` 出力の fenced JSON block を返させる）。
2. 抽出 service: 応答 markdown から Plotly spec の list を取り出す。
3. 描画 service: spec を `Figure` に復元、`to_html(include_plotlyjs="inline")` で HTML 化。
4. View: AI サイドパネルに「Visualize」共有ボタン。複数 spec 時は選択 UI。
5. PlotWindow: `QWebEngineView` で表示する独立ウィンドウ。
6. PanelPresenter / MainPresenter: Markdown export と同じ pull 型で結線。
7. 設定: opt-in、有効/無効と複数 spec の表示モードのみ。

### Phase 2: Sandboxed Python（オプション）

- `subprocess` 隔離 runner（`-I -S`、空 env、timeout、import allow-list）。
- runner の出力は `fig.to_json()` を stdout に書く形に固定 → Phase 1 の描画パスを再利用。
- 設定で `plotly_execution_mode = "json_only" | "sandboxed_python"` を切替。

### Phase 3: 機能拡張

- 複数 spec のタブ集約 PlotWindow（QTabWidget）。
- HTML / PNG（kaleido）保存、Markdown export への埋め込み。
- spec 一覧ペイン、再描画、コピー操作。

以下は **Phase 1 を実装可能な粒度に分解した Steps** を示す。Phase 2 / 3 は別企画書で詳細化する。

## 3. Steps（Phase 1）

1. **DTO の追加**: `src/pdf_epub_reader/dto/` に `plot_dto.py` を新設し、`PlotlySpec`（`index: int`, `language: Literal["json"]`, `source_text: str`, `title: str | None`）を定義する。後の Phase 2 で `language` に `"python"` を足せる形にしておく。

2. **i18n / DTO 文言**: `dto/ui_text_dto.py`、`resources/i18n.py`、`services/translation_service.py` に以下を追加する。
   - `SidePanelTexts.visualize_button_text`
   - 複数 spec 選択ダイアログ用の文言一式（タイトル、cancel、各 spec ラベルのフォールバック「Plot {index}」）
   - status bar 通知（成功・抽出失敗・復元失敗・JSON 不正）
   - PlotWindow タイトルテンプレート

3. **設定の追加**: `utils/config.py` に以下のフラットフィールドを追加する。既存の永続化形式と SettingsPresenter の populate/read 流儀を崩さない。
   - `enable_plotly_visualization: bool = False`
   - `plotly_multi_spec_mode: Literal["prompt", "first_only"] = "prompt"`
   - （Phase 2 用の予約は今回入れない。導入時に追加する。）

4. **設定 UI**: `views/settings_dialog.py`、`interfaces/view_interfaces.py`、`presenters/settings_presenter.py`、`tests/mocks/mock_views.py` を拡張。Markdown export と同様に **Visualization タブ** を新設し、enable toggle と複数 spec 表示モードのラジオを置く。

5. **抽出 service（pure）**: `src/pdf_epub_reader/services/plotly_extraction_service.py` を新設。
   - 入力: AI 応答 markdown 文字列。
   - 出力: `list[PlotlySpec]`。
   - ` ```json … ``` ` を最優先で抽出。言語タグなし fenced block で **先頭バイトが `{` のもの** はフォールバック対象。
   - JSON parse は **ここでは行わない**（spec の保持のみ）。validate は描画 service の責務。
   - title 推測: spec 直前の H2/H3 行、もしくは block 直前 1 行の plain text からトリム。なければ `None`。

6. **描画 service（pure）**: `src/pdf_epub_reader/services/plotly_render_service.py` を新設。
   - `parse_spec(spec: PlotlySpec) -> Figure` … `plotly.io.from_json` を呼ぶ。失敗は構造化 `PlotlyRenderError` を投げる。
   - `figure_to_html(fig: Figure) -> str` … `plotly.io.to_html(fig, include_plotlyjs="inline", full_html=True)`。**`include_plotlyjs="inline"` を強制**してオフライン動作を保証する。
   - 既存の system prompt（`models/ai_model.py` で渡す instruction 群）に「Plotly JSON 以外を含めない」追補は今回は **抽出 service 側の頑健化で吸収** し、prompt 改修は Phase 1 では行わない（任意拡張として記載のみ）。

7. **PlotWindow**: `src/pdf_epub_reader/views/plot_window.py` を新設。
   - `QWebEngineView` を内包する独立ウィンドウ（`QWidget`）。`setHtml(html, baseUrl=QUrl())` で読み込み。
   - 親ウィンドウからは `show_figure_html(html: str, title: str)` のみを公開。
   - 既存の `result_window.py`（desktop_capture）に倣ってモードレス、複数同時表示可。
   - 閉じても AI 結果表示には影響しない。

8. **SidePanelView 拡張**: `views/side_panel_view.py` と `interfaces/view_interfaces.py` を拡張。
   - active tab 用の **shared Visualize button** を 1 個追加。Markdown export ボタンと同じ並び・流儀で配置する。
   - `set_on_visualize_requested(cb: Callable[[], None]) -> None` を `ISidePanelView` に追加。
   - 複数 spec の選択 UI は **PanelPresenter から呼ばれる単純な選択ダイアログ**として `views/` に最小実装で同梱（`QInputDialog.getItem` で十分）。

9. **PanelPresenter 拡張**: `presenters/panel_presenter.py`。
   - `_plot_specs: list[PlotlySpec] | None` を Markdown export の `_export_snapshot` と同流儀で保持。
   - AI 成功時に抽出 service を呼んで更新、失敗時/クリア時/ドキュメント変更時に `None` リセット。
   - `set_on_visualize_requested` を MainPresenter へ forward。
   - read-only `visualize_state` プロパティで MainPresenter に pull させる。

10. **MainPresenter 拡張**: `presenters/main_presenter.py`。
    - PanelPresenter からの request を受け、設定で disabled なら status bar 通知のみで終了。
    - 1 spec → 即描画。複数 spec かつ `plotly_multi_spec_mode == "prompt"` → View に選択を依頼、`first_only` → index 0 を採用。
    - 描画 service を呼び、`PlotWindow` を 1 つ生成して表示。
    - 失敗時は status bar に通知し、AI 結果表示と既存ウィンドウは破壊しない。

11. **テスト**: 既存パターンに合わせて以下を追加する。
    - `tests/test_services/test_plotly_extraction_service.py`: 単一/複数 block、言語タグ揺らぎ、タイトル推測、空応答、JSON 以外の混在。
    - `tests/test_services/test_plotly_render_service.py`: 正常 JSON、壊れた JSON、必須キー欠落、`include_plotlyjs="inline"` の出力検査。
    - `tests/test_presenters/test_panel_presenter.py`: 抽出結果の保持、AI 失敗時の reset、ドキュメント切替での reset。
    - `tests/test_presenters/test_main_presenter.py`: 設定 disabled、1 spec 即描画、複数 spec 選択、描画失敗時 status bar。
    - `tests/test_presenters/test_settings_presenter.py`: enable toggle、multi spec mode の往復。
    - `tests/mocks/mock_views.py`: `set_on_visualize_requested`、選択ダイアログのモック、PlotWindow ファクトリのモック。

12. **手動検証**: `uv run python -m pdf_epub_reader` で、JSON 1 個・複数・壊れた JSON・空応答・設定 disabled・UI 言語切替後のラベルを確認する。

## 4. 設計上の決定（Phase 1 で固定）

- LLM 応答の Python は **実行しない**。Plotly JSON のみ受け付ける。
- spec が 0 個ならボタンは disabled。
- spec が複数の場合の挙動は設定で `prompt`（既定）/ `first_only` を選べる。タブ集約は Phase 3。
- PlotWindow は `QWebEngineView` + `include_plotlyjs="inline"` でオフライン動作。
- ファイル保存・Markdown export 統合は今回入れない。
- 成功・失敗通知は MainWindow status bar（Markdown export と同方針）。
- system prompt 改修は Phase 1 では行わない。抽出 service の頑健性で吸収する。
- 設定はオプトイン（`enable_plotly_visualization: bool = False`）。

## 5. Relevant files

- 既存
  - [src/pdf_epub_reader/presenters/panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py)
  - [src/pdf_epub_reader/presenters/main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py)
  - [src/pdf_epub_reader/presenters/settings_presenter.py](src/pdf_epub_reader/presenters/settings_presenter.py)
  - [src/pdf_epub_reader/views/side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py)
  - [src/pdf_epub_reader/views/settings_dialog.py](src/pdf_epub_reader/views/settings_dialog.py)
  - [src/pdf_epub_reader/interfaces/view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py)
  - [src/pdf_epub_reader/utils/config.py](src/pdf_epub_reader/utils/config.py)
  - [src/pdf_epub_reader/dto/ui_text_dto.py](src/pdf_epub_reader/dto/ui_text_dto.py)
  - [src/pdf_epub_reader/resources/i18n.py](src/pdf_epub_reader/resources/i18n.py)
  - [src/pdf_epub_reader/services/translation_service.py](src/pdf_epub_reader/services/translation_service.py)
  - [tests/mocks/mock_views.py](tests/mocks/mock_views.py)
  - [tests/test_presenters/test_panel_presenter.py](tests/test_presenters/test_panel_presenter.py)
  - [tests/test_presenters/test_main_presenter.py](tests/test_presenters/test_main_presenter.py)
  - [tests/test_presenters/test_settings_presenter.py](tests/test_presenters/test_settings_presenter.py)
- 新規
  - `src/pdf_epub_reader/dto/plot_dto.py`
  - `src/pdf_epub_reader/services/plotly_extraction_service.py`
  - `src/pdf_epub_reader/services/plotly_render_service.py`
  - `src/pdf_epub_reader/views/plot_window.py`
  - `tests/test_services/test_plotly_extraction_service.py`
  - `tests/test_services/test_plotly_render_service.py`

## 6. 依存関係（パッケージ）

- `plotly`（必須・新規依存）
- `PyQt*` の `QtWebEngineWidgets`（既存環境にあるか確認。なければ依存追加）
- 数値計算系（`numpy` 等）は **Phase 1 では不要**（JSON 復元のみ）。Phase 2 で sandbox runner 用に検討する。

## 7. Verification

1. pure service の単体テストを先に通す（抽出・描画）。
2. presenter の focused test を通す（panel・main・settings）。
3. `uv run pytest tests/ -q` で全体回帰。
4. `uv run python -m pdf_epub_reader` で手動確認:
   - JSON 1 件 → 即描画
   - JSON 複数（prompt モード） → 選択ダイアログ
   - JSON 複数（first_only モード） → index 0 が描画
   - 壊れた JSON → status bar に失敗通知、AI 結果は維持
   - 設定 disabled → ボタン不活性 or 通知のみ
   - UI 言語切替後にボタン文言・ダイアログ文言が追従
5. 負ケース: AI 応答に Plotly block が無いとき、ボタンが disabled で副作用が出ないこと。

## 8. オープンな論点（実装着手前に確定したい）

- AI への system prompt 追補は Phase 1 でやるか（**現案: やらない、抽出側で吸収**）。
- `QtWebEngine` 依存追加の可否（既存依存状況を要確認）。
- 複数 spec 時の既定モード（`prompt` / `first_only`）（**現案: prompt**）。
- ボタン表示位置（Markdown export と並べるか、別行にするか）。
- spec 0 件のときの UI（ボタン非表示 / disabled）（**現案: disabled**）。
