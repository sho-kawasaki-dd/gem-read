"""しおり（目次）パネルの PySide6 実装。

BookmarkPanelView は ToCEntry のフラットリストを受け取り、
QTreeWidget 上に階層構造として表示する。
このクラス自身はページ移動ロジックを持たず、項目クリックを
コールバックで Presenter に通知するだけに徹する。
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from pdf_epub_reader.dto import ToCEntry
from pdf_epub_reader.services.translation_service import TranslationService
from pdf_epub_reader.utils.config import DEFAULT_UI_LANGUAGE, normalize_ui_language


class BookmarkPanelView(QWidget):
    """目次をツリー表示する受動的なビュー。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        ui_language: str = DEFAULT_UI_LANGUAGE,
    ) -> None:
        super().__init__(parent)
        self._on_entry_selected: Callable[[int], None] | None = None
        self._ui_language = normalize_ui_language(ui_language, fallback="en")
        self._translation_service = TranslationService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabel(self._translate("bookmark.header"))
        self._tree.itemClicked.connect(self._handle_item_clicked)
        layout.addWidget(self._tree)

    def apply_ui_language(self, language: str) -> None:
        self._ui_language = normalize_ui_language(language, fallback="en")
        self._tree.setHeaderLabel(self._translate("bookmark.header"))

    def set_toc(self, entries: list[ToCEntry]) -> None:
        """ToCEntry のリストからツリーを再構築する。"""
        self._tree.clear()
        if not entries:
            return

        parents: list[tuple[int, QTreeWidgetItem]] = []
        for entry in entries:
            level = max(1, entry.level)
            item = QTreeWidgetItem([entry.title])
            item.setData(0, Qt.ItemDataRole.UserRole, entry.page_number)

            while parents and parents[-1][0] >= level:
                parents.pop()

            if parents:
                parents[-1][1].addChild(item)
            else:
                self._tree.addTopLevelItem(item)

            parents.append((level, item))

        self._tree.collapseAll()
        for index in range(self._tree.topLevelItemCount()):
            self._tree.topLevelItem(index).setExpanded(True)

    def set_on_entry_selected(self, cb: Callable[[int], None]) -> None:
        """目次項目クリック時に呼ぶコールバックを登録する。"""
        self._on_entry_selected = cb

    def _handle_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        """クリックされた項目のページ番号を通知する。"""
        if self._on_entry_selected is None:
            return

        page_number = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(page_number, int):
            self._on_entry_selected(page_number)

    def _translate(self, key: str, **kwargs: object) -> str:
        return self._translation_service.translate(
            key,
            self._ui_language,
            **kwargs,
        )