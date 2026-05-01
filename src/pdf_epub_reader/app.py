"""MVP コンポーネントのワイヤリングとアプリケーション起動。

Model, View, Presenter を組み立て、qasync 統合ループで起動する。
各コンポーネントの依存関係はここで解決し、循環参照を防ぐ。
"""

from __future__ import annotations

import os

import dotenv

from pdf_epub_reader.infrastructure.event_loop import run_app
from pdf_epub_reader.models.ai_model import AIModel
from pdf_epub_reader.models.document_model import DocumentModel
from pdf_epub_reader.presenters.main_presenter import MainPresenter
from pdf_epub_reader.presenters.panel_presenter import PanelPresenter
from pdf_epub_reader.utils.config import ENV_GEMINI_API_KEY, load_config
from pdf_epub_reader.views.bookmark_panel import BookmarkPanelView
from pdf_epub_reader.views.cache_dialog import CacheDialog
from pdf_epub_reader.views.language_dialog import LanguageDialog
from pdf_epub_reader.views.main_window import MainWindow
from pdf_epub_reader.views.settings_dialog import SettingsDialog
from pdf_epub_reader.views.side_panel_view import SidePanelView


# Phase 7.5: シャットダウン時にキャッシュを自動破棄するための参照
_ai_model_ref: AIModel | None = None


def main() -> None:
    """Model, View, Presenter を組み立ててアプリケーションを起動する。"""
    dotenv.load_dotenv()
    run_app(_app_main, on_shutdown=_shutdown)


async def _shutdown() -> None:
    """アプリ終了時にキャッシュを自動破棄する。確認ダイアログなし。

    ここでの invalidate はアプリの後始末であり、ユーザーが実行中 request を
    cancel したときの挙動とは別物として扱う。
    """
    if _ai_model_ref is not None:
        try:
            await _ai_model_ref.invalidate_cache()
        except Exception:  # noqa: BLE001
            pass  # 終了時エラーは握りつぶす


async def _app_main() -> None:
    """非同期コンテキスト内で MVP コンポーネントを生成・結合する。"""
    global _ai_model_ref  # noqa: PLW0603

    # --- Config ---
    config = load_config()

    # --- Models ---
    document_model = DocumentModel(config=config)
    api_key = os.environ.get(ENV_GEMINI_API_KEY)
    ai_model = AIModel(api_key=api_key, config=config)
    _ai_model_ref = ai_model  # シャットダウンフック用に参照を保持

    # --- Views ---
    bookmark_panel_view = BookmarkPanelView(ui_language=config.ui_language)
    side_panel_view = SidePanelView(ui_language=config.ui_language)
    main_window = MainWindow(
        side_panel=side_panel_view,
        bookmark_panel=bookmark_panel_view,
        ui_language=config.ui_language,
    )

    # --- Presenters ---
    panel_presenter = PanelPresenter(
        view=side_panel_view,
        ai_model=ai_model,
        ui_language=config.ui_language,
    )
    _main_presenter = MainPresenter(  # noqa: F841
        view=main_window,
        document_model=document_model,
        panel_presenter=panel_presenter,
        config=config,
        settings_view_factory=lambda ui_language: SettingsDialog(
            main_window,
            ui_language=ui_language,
        ),
        language_view_factory=lambda ui_language: LanguageDialog(
            main_window,
            ui_language=ui_language,
        ),
        ai_model=ai_model,
        cache_dialog_view_factory=lambda ui_language: CacheDialog(
            main_window,
            ui_language=ui_language,
        ),
    )

    main_window.show()
