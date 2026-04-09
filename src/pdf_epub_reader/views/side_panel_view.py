"""AI サイドパネルの PySide6 実装。

ISidePanelView Protocol を満たし、翻訳・カスタムプロンプトの操作と
AI 解析結果の表示を担当する。このクラス自身はロジックを持たず、
ボタン押下やタブ切り替えの通知をコールバック経由で Presenter に渡すだけ。
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# タブインデックスと AnalysisMode.value の対応。
# Presenter は文字列でモードを受け取るため、ここで変換する。
_TAB_NAMES = {0: "translation", 1: "custom_prompt"}


class SidePanelView(QWidget):
    """ISidePanelView Protocol を満たすサイドパネル実装。

    上から順に「選択テキスト」「ローディングバー」「タブ（翻訳 / カスタム）」
    「キャッシュステータス」を縦積みし、ボタンイベントはコールバックで外部に通知する。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # --- コールバック保持用 ---
        self._on_translate_requested: Callable[[bool], None] | None = None
        self._on_custom_prompt_submitted: Callable[[str], None] | None = None
        self._on_tab_changed: Callable[[str], None] | None = None

        # --- ウィジェット構築 ---
        layout = QVBoxLayout(self)

        # 選択テキスト表示
        layout.addWidget(QLabel("選択テキスト:"))
        self._selected_text_edit = QTextEdit()
        self._selected_text_edit.setReadOnly(True)
        self._selected_text_edit.setMaximumHeight(120)
        self._selected_text_edit.setPlaceholderText(
            "ドキュメント上でテキストを選択してください"
        )
        layout.addWidget(self._selected_text_edit)

        # ローディングバー（通常は非表示）
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate モード
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        # タブウィジェット
        self._tab_widget = QTabWidget()
        self._tab_widget.currentChanged.connect(self._handle_tab_changed)
        layout.addWidget(self._tab_widget)

        # --- 翻訳タブ ---
        translation_tab = QWidget()
        translation_layout = QVBoxLayout(translation_tab)

        # 翻訳ボタン群（横並び）
        btn_layout = QHBoxLayout()
        self._translate_btn = QPushButton("翻訳")
        self._translate_btn.clicked.connect(lambda: self._fire_translate(False))
        btn_layout.addWidget(self._translate_btn)

        self._explain_btn = QPushButton("解説付き翻訳")
        self._explain_btn.clicked.connect(lambda: self._fire_translate(True))
        btn_layout.addWidget(self._explain_btn)
        translation_layout.addLayout(btn_layout)

        # 翻訳結果表示エリア
        self._translation_result = QTextEdit()
        self._translation_result.setReadOnly(True)
        self._translation_result.setPlaceholderText("翻訳結果がここに表示されます")
        translation_layout.addWidget(self._translation_result)

        self._tab_widget.addTab(translation_tab, "翻訳")

        # --- カスタムプロンプトタブ ---
        custom_tab = QWidget()
        custom_layout = QVBoxLayout(custom_tab)

        # プロンプト入力欄
        self._prompt_edit = QTextEdit()
        self._prompt_edit.setMaximumHeight(100)
        self._prompt_edit.setPlaceholderText("カスタムプロンプトを入力...")
        custom_layout.addWidget(self._prompt_edit)

        # 送信ボタン
        self._submit_btn = QPushButton("送信")
        self._submit_btn.clicked.connect(self._fire_custom_prompt)
        custom_layout.addWidget(self._submit_btn)

        # カスタム結果表示エリア
        self._custom_result = QTextEdit()
        self._custom_result.setReadOnly(True)
        self._custom_result.setPlaceholderText("結果がここに表示されます")
        custom_layout.addWidget(self._custom_result)

        self._tab_widget.addTab(custom_tab, "カスタムプロンプト")

        # キャッシュステータス
        self._cache_label = QLabel("キャッシュステータス: ---")
        layout.addWidget(self._cache_label)

        # ローディング中に無効化する全ボタンのリスト
        self._all_buttons = [
            self._translate_btn,
            self._explain_btn,
            self._submit_btn,
        ]

    # --- ISidePanelView Display commands ---

    def set_selected_text(self, text: str) -> None:
        """選択テキスト欄の内容を差し替える。"""
        self._selected_text_edit.setPlainText(text)

    def update_result_text(self, text: str) -> None:
        """現在アクティブなタブの結果表示エリアに結果を反映する。"""
        current_tab = self._tab_widget.currentIndex()
        if current_tab == 0:
            self._translation_result.setPlainText(text)
        else:
            self._custom_result.setPlainText(text)

    def show_loading(self, loading: bool) -> None:
        """ローディングバーの表示切り替えとボタンの有効/無効を制御する。"""
        self._progress_bar.setVisible(loading)
        for btn in self._all_buttons:
            btn.setEnabled(not loading)

    def update_cache_status_brief(self, text: str) -> None:
        """キャッシュステータスラベルのテキストを差し替える。"""
        self._cache_label.setText(text)

    def set_active_tab(self, mode: str) -> None:
        """モード文字列に対応するタブをアクティブにする。"""
        # _TAB_NAMES の逆引きでインデックスを特定する。
        for idx, name in _TAB_NAMES.items():
            if name == mode:
                self._tab_widget.setCurrentIndex(idx)
                return

    # --- ISidePanelView Callback registration ---

    def set_on_translate_requested(
        self, cb: Callable[[bool], None]
    ) -> None:
        """翻訳ボタン押下時に呼ばれるコールバックを登録する。"""
        self._on_translate_requested = cb

    def set_on_custom_prompt_submitted(
        self, cb: Callable[[str], None]
    ) -> None:
        """カスタムプロンプト送信時に呼ばれるコールバックを登録する。"""
        self._on_custom_prompt_submitted = cb

    def set_on_tab_changed(self, cb: Callable[[str], None]) -> None:
        """タブ切り替え時に呼ばれるコールバックを登録する。"""
        self._on_tab_changed = cb

    # --- Internal event handlers ---

    def _fire_translate(self, include_explanation: bool) -> None:
        """翻訳ボタンのクリックをコールバックに変換する。"""
        if self._on_translate_requested:
            self._on_translate_requested(include_explanation)

    def _fire_custom_prompt(self) -> None:
        """送信ボタンのクリックをコールバックに変換する。"""
        if self._on_custom_prompt_submitted:
            self._on_custom_prompt_submitted(
                self._prompt_edit.toPlainText()
            )

    def _handle_tab_changed(self, index: int) -> None:
        """QTabWidget のタブ切り替えシグナルをコールバックに変換する。"""
        if self._on_tab_changed and index in _TAB_NAMES:
            self._on_tab_changed(_TAB_NAMES[index])
