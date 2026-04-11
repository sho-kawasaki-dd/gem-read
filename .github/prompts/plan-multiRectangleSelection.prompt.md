---
name: 'Multi-Selection Implementation'
description: '複数矩形選択の実装計画に基づきコードを生成します'
agent: 'agent'
---

以下の実装計画と設計方針（Steps, Decisions）に厳密に従って、コードの実装および修正を順次進めてください。不明点や計画の矛盾が見つかった場合は実装前に質問してください。

## Plan: Multi-Rectangle Selection

複数矩形選択は、1件の選択結果を上書きする現行設計を、選択スロットの集合を扱う設計に引き上げて実装する。通常ドラッグは全置換、Ctrl+ドラッグは末尾追加、Escで全消去とし、MainPresenter が選択順・非同期抽出・破棄判定を一元管理する。View は複数ハイライトと番号バッジを描画し、SidePanel は番号付き一覧と連結プレビューを表示する。AI 解析には選択順で結合したテキストと全画像を1回で送る。

**Steps**

1. Phase 1: 契約と状態モデルを定義する。まず src/pdf_epub_reader/dto/document_dto.py に、単一の SelectionContent は維持したまま、複数選択を表す新DTOを追加する。想定は、内部安定ID・表示番号・ページ番号・矩形・読取状態・抽出済みテキスト・サムネイル有無を持つ選択スロットDTOと、選択一覧のスナップショットDTOである。これに合わせて src/pdf_epub_reader/interfaces/view_interfaces.py の IMainView と ISidePanelView を拡張し、通常選択か追加選択かを View から通知できるようにし、複数ハイライト描画、番号付き一覧表示、個別削除（コールバック経由での伝達）、全消去の契約を明示する。
2. Phase 2: 文書ビューの入力とオーバーレイを拡張する。depends on 1。src/pdf_epub_reader/views/main_window.py の \_DocumentGraphicsView で Ctrl 修飾付きドラッグを検出し、コールバックに追加モードを渡す。Esc ショートカットを MainWindow 側に追加し、Presenter へ全消去要求を渡す。ハイライトは単一の \_highlight_item をやめ、複数の矩形アイテムと番号バッジを保持する辞書構造に置き換える。表示番号は毎回 1,2,3... に詰め直し、内部IDは不変とする。番号は矩形中央ではなく左上寄りの小型バッジで描画し、内容物を隠しすぎないようにする。また、ズームやリサイズ時には、保持している全ての矩形アイテムと番号バッジに対して一括で再計算・再配置を行うループを処理に組み込む。
3. Phase 3: MainPresenter に複数選択のオーケストレーションを実装する。depends on 1 and 2。src/pdf_epub_reader/presenters/main_presenter.py で、選択スロットを順序付きで保持する OrderedDict 相当の状態、表示番号再計算、ファイル切替時の全消去、通常選択時の全置換、Ctrl 選択時の末尾追加を実装する。各ドラッグ受理時には即座に空スロットを確保して View と SidePanel に 先に 反映し、その後に extract_content を非同期開始する。結果の完了順が前後しても表示順を保てるよう、スロット作成時点で順番を固定し、結果は該当スロットだけ埋める。通常選択で既存選択を捨てた後や文書切替後に遅延結果が戻るケースを防ぐため、選択世代トークンを持たせ、古い世代の完了結果は破棄する。
4. Phase 4: SidePanel の複数選択UIを実装する。depends on 1 and parallel with 3 after contracts are ready。src/pdf_epub_reader/views/side_panel_view.py に、現在の単一プレビュー領域を、番号付き一覧と連結プレビューの2層に再編成する。一覧には各選択の番号、ページ情報、短い本文プレビュー、読取中表示、個別削除ボタンを置く。既存のサムネイル表示は、選択ごとの小型サムネイルに移し、連結プレビューは AI に送る最終テキストをそのまま見せる読み取り専用領域とする。全消去ボタンもこのセクションに置く。Phase 6.5 で入っている CollapsibleSection パターンはそのまま再利用し、選択一覧セクション全体を折りたためるようにする。さらに、縦スペースの圧迫を防ぐため、AI回答表示領域にも CollapsibleSection を適用して折りたためるようにする。UIの柔軟性を高めるため、これらのセクション間には QSplitter を導入し、ユーザーがドラッグで自由に表示領域のサイズを調整できるようにする。また、利便性向上のためのキーバインドとして、選択一覧ボックスの折りたたみを "Ctrl+Shift+T"、AI回答欄の折りたたみを "Ctrl+Shift+I" でトグルできるようにショートカットを設定する。
5. Phase 5: PanelPresenter で AI 入力を複数選択対応にする。depends on 3 and 4。src/pdf_epub_reader/presenters/panel_presenter.py で \_selected_text と \_selected_content の単数状態をやめ、選択一覧のスナップショットを受け取る形に変更する。翻訳とカスタムプロンプトの両方で、選択順に連結した本文を AnalysisRequest.text に入れ、各選択の cropped_image を順番通りに AnalysisRequest.images に入れる。連結フォーマットは、境界が読めるように Selection 1 / Page N の見出しと空行を含む明示的区切りにする。これにより、長い証明の断片を結合しても LLM がセグメント境界を見失いにくくする。モデル未設定時や API 例外処理の既存分岐はそのまま維持する。
6. Phase 6: 個別削除と全消去の配線を仕上げる。depends on 3 and 4。SidePanel の削除イベント（on_selection_delete_requested等）を MainPresenter で購読する配線を繋ぎ、selection_id 単位の削除処理と全消去処理を追加し、View のオーバーレイと SidePanel の一覧を常に同じスナップショットから再描画する。削除後は表示番号を詰め直し、連結プレビューと AI 入力元も再計算する。通常ドラッグでの全置換、Esc 全消去、open_file の先頭での全消去、読み取り失敗スロットの扱いをここで統一する。読み取り失敗時はスロット自体は残し、本文に失敗表示を出すか、即削除するかの実装は、既定では失敗表示を短く残してユーザーが削除できるようにする。
7. Phase 7: テストとモックを更新する。depends on 1 through 6。tests/mocks/mock_views.py の MockMainView と MockSidePanelView に複数選択用APIと simulate helpers を追加する。tests/test_presenters/test_main_presenter.py では、通常選択の全置換、Ctrl 追加、スロット先行表示、世代トークンによる古い結果破棄、削除、全消去、open_file 時クリア、10件超の注意表示を検証する。tests/test_presenters/test_panel_presenter.py では、複数選択の連結テキスト生成、画像配列の順序、削除後の再計算、モデル未設定時の抑止を検証する。必要に応じて tests/test_models は変更せず、DocumentModel が単一矩形抽出責務のまま保たれていることを確認する。
8. Phase 8: 手動検証を行う。depends on 7。PDF と EPUB の両方で、通常ドラッグ、Ctrl+ドラッグ、Esc、個別削除、全消去、ズーム変更後のオーバーレイ維持、ページ跨ぎ選択順、10件超の注意表示、AI 送信結果の順序、数式や画像を含む選択のサムネイル表示を確認する。

**Relevant files**

- [src/pdf_epub_reader/dto/document_dto.py](src/pdf_epub_reader/dto/document_dto.py) — SelectionContent を維持しつつ、複数選択スロットと一覧スナップショットのDTOを追加する。
- [src/pdf_epub_reader/interfaces/view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py) — IMainView と ISidePanelView に追加選択通知、複数オーバーレイ描画、一覧更新、個別削除、全消去の契約を追加する。
- [src/pdf_epub_reader/presenters/main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py) — 選択世代管理、追加と置換の分岐、非同期完了の差し込み、削除と全消去、文書切替時のクリアを実装する。
- [src/pdf_epub_reader/presenters/panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py) — 複数選択から連結本文と画像配列を構築し、SidePanel の一覧と連結プレビューを更新する。
- [src/pdf_epub_reader/views/main_window.py](src/pdf_epub_reader/views/main_window.py) — Ctrl 修飾検出、Esc ショートカット、複数ハイライト、番号バッジ、再描画用メソッドを実装する。
- [src/pdf_epub_reader/views/side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py) — 番号付き一覧、個別削除、全消去、連結プレビュー、読取中表示を実装する。
- [tests/mocks/mock_views.py](tests/mocks/mock_views.py) — 新しい View 契約に対応するモックと simulate helpers を追加する。
- [tests/test_presenters/test_main_presenter.py](tests/test_presenters/test_main_presenter.py) — 選択状態遷移と非同期順序のテストを追加する。
- [tests/test_presenters/test_panel_presenter.py](tests/test_presenters/test_panel_presenter.py) — 連結本文、画像順序、削除後再計算のテストを追加する。

**Verification**

1. pytest tests/test_presenters/test_main_presenter.py tests/test_presenters/test_panel_presenter.py
2. pytest tests/test_models/test_document_model.py
3. 手動で PDF を開き、通常ドラッグで単独選択、Ctrl+ドラッグで追加、Esc で全消去できることを確認する。
4. 3件以上追加して番号が 1,2,3 と表示され、途中を削除すると見た目の番号だけが詰め直されることを確認する。
5. 追加順と AI に送られる連結順が一致することを、サイドパネルの連結プレビューと実際の解析結果で確認する。
6. 1件目の抽出中に 2件目と 3件目を追加しても、一覧順が崩れず、置換や文書切替後に古い結果が混入しないことを確認する。
7. 数式や画像を含む選択で、各選択の画像が AnalysisRequest.images に順番通り入ることを presenter テストで確認する。

**Decisions**

- AI 解析対象は、全選択をユーザーが選んだ順に結合して1回で送る。AIへ送信後も手動でリセット(Esc等)や置換ドラッグをするまで選択状態は保持する。
- 通常ドラッグは全置換、Ctrl+ドラッグは追加、Esc で全消去する。
- オーバーレイの見た目番号は削除後に 1,2,3... と詰め直すが、内部IDは不変にする。
- SidePanel は 番号付き一覧 + 連結プレビュー を持ち、個別削除と全消去を提供する。選択一覧とAI回答欄はそれぞれ CollapsibleSection とし、間に QSplitter を配置して柔軟にサイズ調整可能にする。トグルのためのキーバインド（Ctrl+Shift+T で選択一覧、Ctrl+Shift+I でAI回答欄）も設定する。
- 選択数は上限なしとし、10件超で「APIトークン制限や処理速度低下の恐れがあります」といった旨の注意表示だけ出す。
- 抽出は番号枠を先に確保し、読み取り中表示を出した上で、完了したスロットから中身だけ埋める。

**Further Decisions**

1. 連結フォーマットは、日本語の 選択 1 / ページ N にする。
2. 読み取り失敗スロットは短いエラー表示付きで残す。自動削除にすると、ユーザーが 何が失敗したか を追えなくなるため。
3. 番号バッジのサイズと透明度は、数式領域を隠しすぎないことを優先し、初期値は控えめに設定して手動確認で微調整する.
