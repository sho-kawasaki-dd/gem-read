"""キャッシュ管理ダイアログの PySide6 実装。

ICacheDialogView Protocol を満たすモーダル QDialog。
2 タブ構成:
- タブ1「現在のキャッシュ」: ステータス表示 + 作成/削除/TTL 更新
- タブ2「キャッシュ確認」: アプリ用キャッシュ一覧テーブル + 選択行削除
"""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pdf_epub_reader.dto import CacheDialogTexts, CacheStatus
from pdf_epub_reader.utils.config import (
    CACHE_TTL_MAX,
    CACHE_TTL_MIN,
    DEFAULT_UI_LANGUAGE,
)


class CacheDialog(QDialog):
    """ICacheDialogView Protocol を満たすキャッシュ管理ダイアログ実装。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        ui_language: str = DEFAULT_UI_LANGUAGE,
    ) -> None:
        super().__init__(parent)
        self._texts: CacheDialogTexts | None = None
        self.setWindowTitle("")
        self.setMinimumWidth(520)
        self.setMinimumHeight(360)

        self._action: str | None = None

        # Phase 7.5: カウントダウン状態
        self._expire_time_utc: datetime | None = None
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._on_countdown_tick)

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        # --- タブ1: 現在のキャッシュ ---
        tab1 = QWidget()
        tab1_layout = QVBoxLayout(tab1)

        form = QFormLayout()
        self._field_name_label = QLabel("")
        self._name_label = QLabel("---")
        form.addRow(self._field_name_label, self._name_label)
        self._field_model_label = QLabel("")
        self._model_label = QLabel("---")
        form.addRow(self._field_model_label, self._model_label)
        self._field_tokens_label = QLabel("")
        self._token_label = QLabel("---")
        form.addRow(self._field_tokens_label, self._token_label)
        self._field_remaining_ttl_label = QLabel("")
        self._ttl_label = QLabel("---")
        form.addRow(
            self._field_remaining_ttl_label,
            self._ttl_label,
        )
        self._field_expire_time_label = QLabel("")
        self._expire_label = QLabel("---")
        form.addRow(
            self._field_expire_time_label,
            self._expire_label,
        )
        self._field_status_label = QLabel("")
        self._active_label = QLabel("---")
        form.addRow(self._field_status_label, self._active_label)
        tab1_layout.addLayout(form)

        # TTL 更新行
        ttl_row = QHBoxLayout()
        self._field_new_ttl_label = QLabel("")
        ttl_row.addWidget(self._field_new_ttl_label)
        self._ttl_spin = QSpinBox()
        self._ttl_spin.setRange(CACHE_TTL_MIN, CACHE_TTL_MAX)
        ttl_row.addWidget(self._ttl_spin)
        self._update_ttl_btn = QPushButton("")
        self._update_ttl_btn.clicked.connect(lambda: self._finish("update_ttl"))
        ttl_row.addWidget(self._update_ttl_btn)
        tab1_layout.addLayout(ttl_row)

        # 操作ボタン行
        btn_row = QHBoxLayout()
        self._create_btn = QPushButton("")
        self._create_btn.clicked.connect(lambda: self._finish("create"))
        btn_row.addWidget(self._create_btn)
        self._delete_btn = QPushButton("")
        self._delete_btn.clicked.connect(lambda: self._finish("delete"))
        btn_row.addWidget(self._delete_btn)
        tab1_layout.addLayout(btn_row)

        self._tabs.addTab(tab1, "")

        # --- タブ2: キャッシュ確認 ---
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["", "", "", "", ""])
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        header = self._table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab2_layout.addWidget(self._table)

        self._delete_selected_btn = QPushButton("")
        self._delete_selected_btn.clicked.connect(
            lambda: self._finish("delete_selected")
        )
        tab2_layout.addWidget(self._delete_selected_btn)

        self._tabs.addTab(tab2, "")

        # --- 閉じるボタン ---
        self._close_btn = QPushButton("")
        self._close_btn.clicked.connect(self.reject)
        layout.addWidget(
            self._close_btn,
            alignment=Qt.AlignmentFlag.AlignRight,
        )

    # --- Internal ---

    def _finish(self, action: str) -> None:
        """アクションを記録してダイアログを閉じる。"""
        self._action = action
        self.accept()

    # --- タブ1: 現在のキャッシュ setter ---

    def set_cache_name(self, name: str) -> None:
        self._name_label.setText(name)

    def set_cache_model(self, model: str) -> None:
        self._model_label.setText(model)

    def set_cache_token_count(self, count: int | None) -> None:
        fallback = self._texts.not_set_text if self._texts is not None else "---"
        self._token_label.setText(str(count) if count is not None else fallback)

    def set_cache_ttl_seconds(self, seconds: int | None) -> None:
        if seconds is not None:
            m, s = divmod(seconds, 60)
            template = (
                self._texts.ttl_minutes_seconds_template
                if self._texts is not None
                else "{minutes}:{seconds}"
            )
            self._ttl_label.setText(
                template.format(minutes=m, seconds=s)
            )
        else:
            self._ttl_label.setText(
                self._texts.not_set_text if self._texts is not None else "---"
            )

    def set_cache_expire_time(self, expire_time: str | None) -> None:
        self._expire_label.setText(
            expire_time
            or (self._texts.not_set_text if self._texts is not None else "---")
        )

    def set_cache_is_active(self, active: bool) -> None:
        self._active_label.setText(
            self._texts.status_active_text
            if active and self._texts is not None
            else (
                self._texts.status_inactive_text
                if self._texts is not None
                else ""
            )
        )
        # active 時は削除/TTL更新を有効化、作成は無効化
        self._create_btn.setEnabled(not active)
        self._delete_btn.setEnabled(active)
        self._update_ttl_btn.setEnabled(active)
        self._ttl_spin.setEnabled(active)

    def set_ttl_spin_value(self, minutes: int) -> None:
        self._ttl_spin.setValue(minutes)

    def get_new_ttl_minutes(self) -> int:
        return self._ttl_spin.value()

    # --- タブ2: キャッシュ確認 ---

    def set_cache_list(self, items: list[CacheStatus]) -> None:
        self._table.setRowCount(len(items))
        for row, item in enumerate(items):
            self._table.setItem(
                row, 0, QTableWidgetItem(item.cache_name or "")
            )
            self._table.setItem(
                row, 1, QTableWidgetItem(item.model_name or "")
            )
            self._table.setItem(
                row, 2, QTableWidgetItem(item.display_name or "")
            )
            self._table.setItem(
                row, 3,
                QTableWidgetItem(
                    str(item.token_count) if item.token_count else ""
                ),
            )
            self._table.setItem(
                row, 4, QTableWidgetItem(item.expire_time or "")
            )

    def get_selected_cache_name(self) -> str | None:
        items = self._table.selectedItems()
        if not items:
            return None
        row = items[0].row()
        name_item = self._table.item(row, 0)
        return name_item.text() if name_item else None

    # --- Phase 7.5: カウントダウン ---

    def start_countdown(self, expire_time: str) -> None:
        """タブ1 の残り TTL を 1 秒間隔で H:MM:SS 更新する。"""
        et = expire_time.replace("Z", "+00:00")
        self._expire_time_utc = datetime.fromisoformat(et).astimezone(
            timezone.utc
        )
        self._on_countdown_tick()
        self._countdown_timer.start()

    def stop_countdown(self) -> None:
        """カウントダウンを停止する。"""
        self._countdown_timer.stop()
        self._expire_time_utc = None

    def _on_countdown_tick(self) -> None:
        """1 秒ごとに _ttl_label を更新する。"""
        if self._expire_time_utc is None:
            return
        now = datetime.now(timezone.utc)
        remaining = (self._expire_time_utc - now).total_seconds()
        if remaining <= 0:
            self._countdown_timer.stop()
            self._ttl_label.setText(
                self._texts.status_expired_text if self._texts is not None else ""
            )
            self._expire_time_utc = None
            return
        total_sec = int(remaining)
        h, rem = divmod(total_sec, 3600)
        m, s = divmod(rem, 60)
        self._ttl_label.setText(f"{h}:{m:02d}:{s:02d}")

    def apply_ui_texts(self, texts: CacheDialogTexts) -> None:
        self._texts = texts
        self.setWindowTitle(texts.window_title)
        self._field_name_label.setText(texts.field_name_label)
        self._field_model_label.setText(texts.field_model_label)
        self._field_tokens_label.setText(texts.field_tokens_label)
        self._field_remaining_ttl_label.setText(texts.field_remaining_ttl_label)
        self._field_expire_time_label.setText(texts.field_expire_time_label)
        self._field_status_label.setText(texts.field_status_label)
        self._field_new_ttl_label.setText(texts.field_new_ttl_label)
        self._ttl_spin.setSuffix(texts.minutes_suffix)
        self._update_ttl_btn.setText(texts.button_update_ttl_text)
        self._create_btn.setText(texts.button_create_text)
        self._delete_btn.setText(texts.button_delete_text)
        self._tabs.setTabText(0, texts.tab_current_text)
        self._table.setHorizontalHeaderLabels(
            [
                texts.table_name_header,
                texts.table_model_header,
                texts.table_display_name_header,
                texts.table_tokens_header,
                texts.table_expire_header,
            ]
        )
        self._delete_selected_btn.setText(texts.button_delete_selected_text)
        self._tabs.setTabText(1, texts.tab_list_text)
        self._close_btn.setText(texts.button_close_text)

    # --- Lifecycle ---

    def accept(self) -> None:
        """ダイアログを承認終了する前にタイマーを停止する。"""
        self.stop_countdown()
        super().accept()

    def reject(self) -> None:
        """ダイアログをキャンセル終了する前にタイマーを停止する。"""
        self.stop_countdown()
        super().reject()

    def show(self) -> str | None:  # type: ignore[override]
        """モーダル表示しユーザーアクションを返す。"""
        self._action = None
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self._action
        return None

