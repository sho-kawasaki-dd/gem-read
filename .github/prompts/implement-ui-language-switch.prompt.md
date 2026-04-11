---
name: 'Implement UI Language Switch'
description: 'Use when implementing the Japanese/English UI language switch for this PySide6 MVP app based on the agreed decision sheet'
argument-hint: 'Optional: target phase(s), constraints, or leave blank to implement all phases'
agent: 'agent'
model: 'GPT-5 (copilot)'
---

# Implement UI Language Switch

このプロンプトは、このワークスペースの PySide6 + MVP アプリに対して、View 表示言語の日本語 / English 切替機能を実装するための実行用プロンプトです。

必ず合意済みの決定事項を優先してください:

- [UI language decisions](../../ui-language-decisions.md)

## Goal

以下の仕様に従って、UI 表示言語の切替機能を段階的に実装してください。

- UI 表示言語と AI 出力言語は分離する
- 設定名は `ui_language`
- `ui_language` は `AppConfig` に永続化する
- 初回起動時は OS ロケールで自動判定し、`ja` / `en` に正規化する
- 翻訳方式は「独自辞書 + translation service」
- 文言キーは階層キーで管理する
- Presenter 生成文言も切替対象に含める
- Presenter 側で翻訳済み文字列を解決し、View には完成済み文字列を渡す
- 言語変更は即時反映する
- `MainWindow` と `SidePanel` は即時更新、`SettingsDialog` / `CacheDialog` は次回生成時に新言語を適用する
- メニューバーの「キャッシュ」の右に「言語 / Language」メニューを追加し、そこから言語設定ウィンドウを開けるようにする
- 言語設定ウィンドウではドロップダウンで言語を選択する
- 英語メニューのみアクセラレータを付与する
- ショートカットは既存のまま維持する
- `TTL` はラベル上も `TTL` を維持し、日時は `有効期限` / `Expire Time` として分離する
- 空状態は `未設定` / `Not set` に統一し、`---` は内部表示用途のみに限定する
- ログと UI は分離し、例外の生文字列は UI 表示向けに適切に扱う
- `show_error_dialog` / `show_confirm_dialog` の title / message は呼び出し側で翻訳済み文字列として組み立てる
- 未翻訳キーは英語にフォールバックする
- 内部ロケール値は `ja` / `en` とし、`ja-JP` / `en-US` は読み込み時に正規化する
- 将来の多言語追加に耐えられる辞書構造にする

## Working Rules

- 既存の MVP / Passive View 構成を崩さない
- Qt 依存を不要に Presenter へ漏らさない
- 既存の public API を壊さず、必要最小限の拡張に留める
- 既存のテストスタイルに合わせる
- まず既存コードを確認してから編集する
- 編集は最小差分で行う
- 各フェーズ完了後に、関連テストを実行して結果を確認する
- 既存のユーザー変更や unrelated な差分は巻き戻さない

## Phase Plan

### Phase 1: Config と翻訳基盤

目的:

- `ui_language` の保存・復元・正規化を成立させる
- 翻訳辞書と translation service の導入基盤を作る

実装内容:

- `AppConfig` に `ui_language` を追加する
- `config.py` に UI 言語のデフォルト値と正規化ロジックを追加する
- 旧 config に `ui_language` が無い場合は OS ロケールから既定値を決める
- 保存値は `ja` / `en` に正規化する
- `pdf_epub_reader` 配下に translation service と辞書モジュールを追加する
- 未翻訳キー時は英語フォールバックにする

期待成果:

- 言語設定が永続化され、次回起動時に再利用できる
- 翻訳取得 API が Presenter から呼べる

### Phase 2: Protocol と言語設定ダイアログ

目的:

- 言語設定画面と即時反映のための契約を追加する

実装内容:

- `view_interfaces.py` に必要な Protocol を追加・拡張する
- 言語設定ダイアログ用の View Protocol を追加する
- `MainWindow` のメニューバーに「言語 / Language」メニューを追加する
- 言語設定ダイアログを新規作成する
- ダイアログはドロップダウンで `日本語` / `English` を選択できるようにする
- 英語モード時のみアクセラレータを付ける方針を守る

期待成果:

- UI 上から表示言語を変更できる導線ができる

### Phase 3: Presenter 統合と即時反映

目的:

- 言語設定変更をアプリ状態へ反映し、開いている主要 View を即時更新する

実装内容:

- 言語設定ダイアログ用 Presenter を追加する
- `MainPresenter` に言語設定ダイアログ起動フローを統合する
- `MainWindow` と `SidePanel` に再翻訳適用の仕組みを追加する
- `SettingsDialog` / `CacheDialog` は次回生成時に新言語が反映されるようにする
- 呼び出し側で翻訳済み title / message を組み立てて `show_error_dialog` / `show_confirm_dialog` を呼ぶようにする

期待成果:

- 言語変更後、アプリ再起動なしで主要画面が切り替わる

### Phase 4: View の静的文言置換

目的:

- 現在ハードコードされている View 側文字列を翻訳キー参照へ移行する

実装対象の中心:

- `views/main_window.py`
- `views/side_panel_view.py`
- `views/settings_dialog.py`
- `views/cache_dialog.py`
- 必要なら `views/bookmark_panel.py`

対象文字列:

- メニュー名、アクション名、ボタン、ラベル、タブ名、プレースホルダー、空状態、初期 HTML 文言
- `TTL`、`Expire Time`、`Not set` など、決定表で定めた用語統一

期待成果:

- View の静的文言が言語切替に追従する

### Phase 5: Presenter 文言の翻訳対応

目的:

- 統一切替対象に含まれる Presenter 発メッセージを翻訳対応する

実装対象の中心:

- `presenters/main_presenter.py`
- `presenters/panel_presenter.py`
- `presenters/settings_presenter.py`
- 必要なら `presenters/cache_presenter.py`

対象文字列:

- status message
- confirm dialog title / body
- error dialog title
- View に渡すユーザー向け通知文言

期待成果:

- Presenter 発の UI 文言も言語切替に追従する

### Phase 6: テストと検証

目的:

- 合意済みの完了条件をテストで担保する

実装内容:

- config / locale 正規化のテスト追加
- translation service のテスト追加
- Presenter の翻訳済み文言生成のテスト追加
- `MainWindow` / `SidePanel` の即時反映に関するテスト追加
- 既存 mock が足りなければ拡張する

最低限の完了条件:

- View の静的文言
- Presenter 発メッセージ
- `MainWindow` / `SidePanel` の即時反映

## File Guidance

重点的に確認・編集する候補:

- `src/pdf_epub_reader/utils/config.py`
- `src/pdf_epub_reader/interfaces/view_interfaces.py`
- `src/pdf_epub_reader/presenters/main_presenter.py`
- `src/pdf_epub_reader/presenters/panel_presenter.py`
- `src/pdf_epub_reader/presenters/settings_presenter.py`
- `src/pdf_epub_reader/views/main_window.py`
- `src/pdf_epub_reader/views/side_panel_view.py`
- `src/pdf_epub_reader/views/settings_dialog.py`
- `src/pdf_epub_reader/views/cache_dialog.py`
- `src/pdf_epub_reader/app.py`
- `tests/mocks/mock_views.py`
- `tests/test_presenters/test_main_presenter.py`
- `tests/test_presenters/test_panel_presenter.py`

新規作成候補:

- `src/pdf_epub_reader/services/translation_service.py`
- `src/pdf_epub_reader/resources/i18n.py`
- `src/pdf_epub_reader/views/language_dialog.py`
- `src/pdf_epub_reader/presenters/language_presenter.py`
- 必要なテストファイル

## Execution Instructions

以下の流れで作業してください。

1. まず既存コードと [UI language decisions](../../ui-language-decisions.md) を読み、実装に必要な差分を把握する。
2. いきなり広範囲を編集せず、Phase 1 から順に進める。
3. 各 Phase の開始時に、その Phase で何を変えるかを短く宣言する。
4. 各 Phase の完了後に、関連テストを実行する。
5. 問題があれば同じ Phase 内で解決する。
6. 最後に全体テストまたは関連テストを実行し、変更点と残リスクを報告する。

## Verification

最低限、以下を確認すること。

1. `ui_language` が保存・復元されること
2. 旧設定ファイルでも起動できること
3. 日本語 / English の両方で `MainWindow` と `SidePanel` が即時更新されること
4. `SettingsDialog` / `CacheDialog` は次回生成時に新言語になること
5. View の静的文言が切り替わること
6. Presenter 発メッセージが切り替わること
7. 未翻訳キーが英語にフォールバックすること
8. 既存の主要 Presenter テストが壊れていないこと

## Output Format

作業時は以下の形式で進めること。

- 最初に実装対象 Phase を明示する
- 変更は Phase 単位でまとめる
- 各 Phase で編集した主要ファイルを示す
- テスト結果を Phase ごと、最後に全体で報告する
- 未対応項目や妥協点があれば最後に明記する

引数が無い場合は Phase 1 から Phase 6 まで順に実装してください。
引数で対象 Phase が指定された場合は、その Phase のみを実装してください。
