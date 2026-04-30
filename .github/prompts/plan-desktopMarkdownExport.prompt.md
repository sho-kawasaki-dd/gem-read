## Plan: Desktop Markdown Export

pdf_epub_reader 側には、AIサイドパネルのアクティブ結果を手動で Markdown 保存する機能を追加します。保存先は設定ダイアログで指定する既定フォルダで、保存時にフォルダが無ければ自動作成します。browser-extension の Markdown 組み立てとファイル名ルールを流用しつつ、desktop では文書タイトル・ファイル basename・選択一覧を使う形に寄せます。見出し言語は UI 言語追従、Save As は今回は入れず、自動保存のみ、失敗時は結果表示を壊さずメインウィンドウのステータスバーで通知します。

**Steps**
1. Phase 1: 設定面を先に固めます。 [src/pdf_epub_reader/utils/config.py](src/pdf_epub_reader/utils/config.py) に export folder と各 export toggle をフラットな AppConfig フィールドとして追加します。
次を保持します: explanation, selection list, raw response, document metadata, usage metrics, YAML frontmatter。
この形にすると既存の JSON 永続化、SettingsPresenter の populate/read、MockView の流儀を崩さず進められます。
このステップが後続の UI・Presenter・テストの前提になります。

2. Phase 1: 文言 DTO と翻訳配線を追加します。 [src/pdf_epub_reader/dto/ui_text_dto.py](src/pdf_epub_reader/dto/ui_text_dto.py)、[src/pdf_epub_reader/resources/i18n.py](src/pdf_epub_reader/resources/i18n.py)、[src/pdf_epub_reader/services/translation_service.py](src/pdf_epub_reader/services/translation_service.py) に Export タブ用の文言、保存先ラベル、Browse ボタン、toggle 文言、保存成功/失敗メッセージを足します。
UI 言語追従という決定に合わせて、export される Markdown 内ラベルもここから引ける設計にします。
あわせて `SettingsDialogTexts`（ui_text_dto.py）に `export_tab_text` フィールドを追加し、`build_settings_dialog_texts` でも補完します。`SidePanelTexts` には `export_button_text` を追加します（Step 5 の View 実装より先にここで定義します）。

3. Phase 2: 設定ダイアログに Export タブを新設します。 [src/pdf_epub_reader/views/settings_dialog.py](src/pdf_epub_reader/views/settings_dialog.py)、[src/pdf_epub_reader/interfaces/view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py)、[src/pdf_epub_reader/presenters/settings_presenter.py](src/pdf_epub_reader/presenters/settings_presenter.py)、[tests/mocks/mock_views.py](tests/mocks/mock_views.py) を拡張します。
Export タブには、保存先フォルダ欄、フォルダ選択ボタン、6 個の export toggle を置きます。
フォルダ選択は純粋な UI なので、設定ダイアログ View 内でディレクトリピッカーを開く方針にします。
このステップは 1 と 2 に依存します。

4. Phase 2: 純粋な Markdown export service を追加します。新規に services 配下へ markdown_export_service.py 相当のモジュールを追加し、[browser-extension/src/background/services/markdownExportService.ts](browser-extension/src/background/services/markdownExportService.ts) と [browser-extension/src/background/gateways/downloadGateway.ts](browser-extension/src/background/gateways/downloadGateway.ts) をテンプレートにします。
ここで実装する責務は、Markdown 本文組み立て、セクション出し分け、YAML frontmatter、タイトル sanitize、timestamp 付きファイル名生成です。
browser-extension 依存の URL や article metadata はそのまま持ち込まず、desktop では DocumentInfo の title と file basename を使うように差し替えます。タイトル解決は service 内のヘルパー関数 1 か所に閉じ込め、`DocumentInfo.title` が `None` または空文字のときは `Path(file_path).stem` をフォールバックとして使います。このフォールバック値はファイル名・H1 見出し・YAML frontmatter の `title` フィールドのすべてに統一して使用します。
`AnalysisMode` の Markdown 上での表記は `AnalysisMode.TRANSLATION` → `"translation"`、`AnalysisMode.CUSTOM_PROMPT` → `"custom_prompt"` とし、`- Action:` 行と YAML frontmatter の `action:` フィールドに使います。i18n キーは `export.action.translation` / `export.action.custom_prompt` で定義します。
この service は可能な限り pure function に寄せ、必要なら書き込み helper だけ薄く分けます。
このステップは 1 の後なら 3 と並行できます。

5. Phase 3: AI サイドパネルに共有 export ボタンを追加します。 [src/pdf_epub_reader/views/side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py) と [src/pdf_epub_reader/interfaces/view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py) を拡張し、翻訳タブとカスタムタブのアクティブ結果に対して 1 つの export ボタンが働く構成にします。
ボタンは成功結果が存在するまで disabled、失敗文やプレースホルダでは export 不可にします。
View はあくまでボタン表示と callback 発火だけを持ち、ファイル書き込みは持ちません。
`ISidePanelView` に `set_on_export_requested(cb: Callable[[], None]) -> None` を追加します。引数なしで発火し、状態は PanelPresenter 側が保持します。
このステップは 2 と 4 に依存します。

6. Phase 3: PanelPresenter に export-ready state を持たせます。 [src/pdf_epub_reader/presenters/panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py) で、最新の成功結果として AnalysisResult、action mode、explanation の有無、選択モデル、選択 snapshot を保持します。
export-ready state の選択 snapshot は `_export_snapshot` として既存の `_selection_snapshot`（現在の選択状態）とは別フィールドに保持します。AI 成功時に `_selection_snapshot` をコピーして更新し、無効化時は `None` にリセットします。
AI 成功時に更新し、文書変更、選択クリア、AI 失敗時には適切に無効化します。
さらに cache handler と同じ流儀で export request handler を上位へ forwarding する callback を追加します。
MainPresenter は callback 発火後、PanelPresenter の `export_state` プロパティ（`AnalysisResult`・`AnalysisMode`・`_export_snapshot`・`_current_model` をまとめた read-only プロパティ）を参照する pull 型とします。callback 引数でデータを渡しません。
これにより PanelPresenter は AI 結果の管理だけを担当し、通知先や保存先の責務は MainPresenter に渡せます。
このステップは 4 と 5 に依存します。

7. Phase 4: 実際の保存オーケストレーションを MainPresenter に寄せます。 [src/pdf_epub_reader/presenters/main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py) で PanelPresenter から export request を受け、現在の DocumentInfo と AppConfig を使って保存先パスを確定し、必要ならフォルダを自動作成し、Markdown export service を呼んで保存します。
保存後の成功・失敗通知は既存の main window status bar を使います。
今回の決定では Save As を入れないので、MainView に新しい保存ダイアログ契約は追加しません。
このステップは 1、4、5、6 に依存します。

8. Phase 4: テストを追加します。 pure service のテストは [tests/test_services/test_markdown_export_service.py](tests/test_services/test_markdown_export_service.py) に新規作成し、browser-extension の [browser-extension/__tests__/unit/background/markdownExport.test.ts](browser-extension/__tests__/unit/background/markdownExport.test.ts) と同じ観点を Python 側で再現します。
対象は、デフォルト sections、optional sections、YAML frontmatter、UI 言語追従ラベル、ファイル名 sanitize、successful result guard です。
Presenter 側は [tests/test_presenters/test_panel_presenter.py](tests/test_presenters/test_panel_presenter.py)、[tests/test_presenters/test_main_presenter.py](tests/test_presenters/test_main_presenter.py)、[tests/test_presenters/test_settings_presenter.py](tests/test_presenters/test_settings_presenter.py)、[tests/mocks/mock_views.py](tests/mocks/mock_views.py) を拡張します。
このステップは 3 から 7 に依存します。

9. Phase 5: ドキュメントを更新します。 [docs/user/operations.md](docs/user/operations.md)、[docs/user/settings-and-cache.md](docs/user/settings-and-cache.md)、[README.md](README.md) に desktop 側 Markdown export の手順、保存先設定、active tab semantics、既定ファイル名規則を反映します。
このステップは実装とテスト確定後に行います。

**Relevant files**
- [src/pdf_epub_reader/presenters/panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py)
- [src/pdf_epub_reader/presenters/main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py)
- [src/pdf_epub_reader/views/side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py)
- [src/pdf_epub_reader/views/settings_dialog.py](src/pdf_epub_reader/views/settings_dialog.py)
- [src/pdf_epub_reader/interfaces/view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py)
- [src/pdf_epub_reader/utils/config.py](src/pdf_epub_reader/utils/config.py)
- [src/pdf_epub_reader/dto/ui_text_dto.py](src/pdf_epub_reader/dto/ui_text_dto.py)
- [src/pdf_epub_reader/resources/i18n.py](src/pdf_epub_reader/resources/i18n.py)
- [src/pdf_epub_reader/services/translation_service.py](src/pdf_epub_reader/services/translation_service.py)
- [src/pdf_epub_reader/dto/ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py)
- [src/pdf_epub_reader/dto/document_dto.py](src/pdf_epub_reader/dto/document_dto.py)
- [browser-extension/src/background/services/markdownExportService.ts](browser-extension/src/background/services/markdownExportService.ts)
- [browser-extension/src/background/gateways/downloadGateway.ts](browser-extension/src/background/gateways/downloadGateway.ts)
- [browser-extension/__tests__/unit/background/markdownExport.test.ts](browser-extension/__tests__/unit/background/markdownExport.test.ts)
- [tests/test_presenters/test_panel_presenter.py](tests/test_presenters/test_panel_presenter.py)
- [tests/test_presenters/test_main_presenter.py](tests/test_presenters/test_main_presenter.py)
- [tests/test_presenters/test_settings_presenter.py](tests/test_presenters/test_settings_presenter.py)
- [tests/test_services/test_markdown_export_service.py](tests/test_services/test_markdown_export_service.py)
- [tests/mocks/mock_views.py](tests/mocks/mock_views.py)
- [docs/user/operations.md](docs/user/operations.md)
- [docs/user/settings-and-cache.md](docs/user/settings-and-cache.md)
- [README.md](README.md)

**Verification**
1. まず pure な Markdown export service のテストを追加し、default sections、optional sections、YAML frontmatter、sanitize、localized labels、successful-result-only を個別に確認します。
2. 次に presenter の focused test を回します。対象は [tests/test_presenters/test_panel_presenter.py](tests/test_presenters/test_panel_presenter.py)、[tests/test_presenters/test_main_presenter.py](tests/test_presenters/test_main_presenter.py)、[tests/test_presenters/test_settings_presenter.py](tests/test_presenters/test_settings_presenter.py) です。
3. その後に uv run pytest tests/ -q で広げます。
4. 最後に uv run python -m pdf_epub_reader で手動確認します。文書を開く、翻訳結果を出す、custom prompt 結果を出す、Export を押す、フォルダ自動作成、UI 言語切替後の見出し、title-timestamp ファイル名を確認します。
5. 負ケースとして、成功結果が無い状態で export できないこと、書き込み失敗時に AI 結果表示を壊さず status bar に失敗が出ることを確認します。

**Decisions fixed**
- browser-extension 相当の export scope を desktop 向けに移植する
- 設定 UI は今回入れる
- 保存は user-configurable folder への auto-save のみ
- Save As は今回入れない
- export button は active tab に対する shared button 1 個
- metadata は document title と file basename と selection list を含める
- absolute local path は含めない
- raw response、usage metrics、YAML frontmatter も toggle として実装する
- Markdown の見出し言語は app UI language に追従
- ファイル名は document title + timestamp
- export 対象は successful AI results のみ
- 保存先フォルダは存在しなければ自動作成
- trigger は manual only
- 成功・失敗通知は main window status bar
- 設定画面には dedicated な Export tab を新設する
- `AnalysisResult` の成功判定: `translated_text` または `raw_response` のいずれかが空でない文字列であること。両方空の場合は export 不可とする
- `export_folder` が空文字またはデフォルト値の場合、export 実行時に status bar へ「エクスポートフォルダが設定されていません」と通知してスキップする。ファイルダイアログは開かない
- ファイル名形式: `{sanitized_title}_{YYYYMMDDTHHMMSS}.md`（秒精度の UTC タイムスタンプ）。manual trigger かつ秒精度のため同名衝突は想定せず、連番サフィックスは今回入れない