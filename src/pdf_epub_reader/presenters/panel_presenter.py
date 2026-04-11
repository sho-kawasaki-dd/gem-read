"""AI サイドパネルの操作を仲介する Presenter。

PanelPresenter は、ユーザーが選択したテキストに対して
「翻訳する」「カスタムプロンプトで解析する」といった AI 操作を担当する。
メイン画面側の文書操作とは責務を分離し、サイドパネル固有の流れだけに集中させる。
"""

from __future__ import annotations

import asyncio

from collections.abc import Callable
from dataclasses import replace

from pdf_epub_reader.dto import (
    AnalysisMode,
    AnalysisRequest,
    CacheStatus,
    RectCoords,
    SelectionContent,
    SelectionSlot,
    SelectionSnapshot,
)
from pdf_epub_reader.interfaces.model_interfaces import IAIModel
from pdf_epub_reader.interfaces.view_interfaces import ISidePanelView
from pdf_epub_reader.utils.exceptions import (
    AIAPIError,
    AIKeyMissingError,
    AIRateLimitError,
)


class PanelPresenter:
    """ISidePanelView と IAIModel の調停役。

    この Presenter は「どの選択スロット集合を解析対象にするか」を内部状態として保持する。
    Phase 5 では単一選択の内部状態をやめ、複数選択スナップショットから
    AI 入力テキストと画像配列を組み立てる。
    """

    def __init__(self, view: ISidePanelView, ai_model: IAIModel) -> None:
        """依存オブジェクトを受け取り、サイドパネルのイベントを購読する。"""
        self._view = view
        self._ai_model = ai_model
        self._selection_snapshot = SelectionSnapshot()
        self._force_include_image: bool = False
        # Phase 6: リクエスト単位のモデル選択
        self._current_model: str | None = None
        self._on_selection_delete_handler: (
            Callable[[str], None] | None
        ) = None
        self._on_clear_selections_handler: Callable[[], None] | None = None
        # Phase 7: キャッシュ状態と MainPresenter 向けコールバック
        self._cache_status = CacheStatus()
        self._on_cache_create_handler: Callable[[], None] | None = None
        self._on_cache_invalidate_handler: Callable[[], None] | None = None
        # Phase 7.5: 期限切れコールバック
        self._on_cache_expired_handler: Callable[[], None] | None = None

        # View は「どの関数を呼ぶか」だけを知ればよい。
        # 実際の処理内容は Presenter 側に閉じ込める。
        self._view.set_on_translate_requested(self._on_translate_requested)
        self._view.set_on_custom_prompt_submitted(self._on_custom_prompt_submitted)
        self._view.set_on_force_image_toggled(self._on_force_image_toggled)
        self._view.set_on_selection_delete_requested(
            self._fire_selection_delete_requested
        )
        self._view.set_on_clear_selections_requested(
            self._fire_clear_selections_requested
        )
        self._view.set_on_model_changed(self._on_model_changed)
        self._view.set_on_cache_create_requested(self._fire_cache_create)
        self._view.set_on_cache_invalidate_requested(
            self._fire_cache_invalidate
        )
        self._view.set_on_cache_expired(self._on_cache_expired)

    # --- Public API (called by MainPresenter) ---

    @property
    def force_include_image(self) -> bool:
        """「画像としても送信」トグルの現在値を返す。

        MainPresenter が extract_content に渡す force_include_image の
        ソースとして使う。
        """
        return self._force_include_image

    def set_selected_text(self, text: str) -> None:
        """現在の解析対象テキストを更新し、View にも反映する。

        後方互換のために残す。新規フローでは set_selection_snapshot を使用する。
        """
        self.set_selection_snapshot(
            SelectionSnapshot(
                slots=(
                    SelectionSlot(
                        selection_id="legacy-selection",
                        display_number=1,
                        page_number=0,
                        rect=RectCoords(0.0, 0.0, 0.0, 0.0),
                        read_state="ready",
                        extracted_text=text,
                    ),
                ),
            )
        )

    def set_selected_content(self, content: SelectionContent) -> None:
        """マルチモーダルコンテンツを受け取り、View にプレビューを反映する。

        後方互換のために残す。新規フローでは set_selection_snapshot を使用する。
        """
        self.set_selection_snapshot(
            SelectionSnapshot(
                slots=(
                    SelectionSlot(
                        selection_id="legacy-selection",
                        display_number=1,
                        page_number=content.page_number,
                        rect=content.rect,
                        read_state="ready",
                        extracted_text=content.extracted_text,
                        has_thumbnail=content.cropped_image is not None,
                        content=content,
                    ),
                )
            )
        )

    def set_selection_snapshot(self, snapshot: SelectionSnapshot) -> None:
        """複数選択スナップショットを View に反映する。

        Phase 3 では主に MainPresenter からの先行スロット反映に使う。
        AI 解析入力の組み立ては Phase 5 でこの状態に寄せる。
        """
        self._selection_snapshot = self._normalized_snapshot(snapshot)
        self._view.set_selection_snapshot(self._selection_snapshot)
        self._view.set_combined_selection_preview(
            self._build_analysis_text()
        )

    def set_available_models(self, model_names: list[str]) -> None:
        """モデル選択プルダウンの選択肢を設定する。"""
        self._view.set_available_models(model_names)

    def set_selected_model(self, model_name: str) -> None:
        """モデル選択プルダウンの現在値を設定する。"""
        self._current_model = model_name
        self._view.set_selected_model(model_name)

    def get_current_model(self) -> str | None:
        """サイドパネルで現在選択中のモデル名を返す。

        MainPresenter がキャッシュ作成時に使用するモデルを取得するために呼ぶ。
        モデル未選択時は None を返す。
        """
        return self._current_model

    # --- Phase 7: キャッシュ連携 ---

    def set_on_cache_create_handler(
        self, cb: Callable[[], None]
    ) -> None:
        """MainPresenter が登録するキャッシュ作成ハンドラ。"""
        self._on_cache_create_handler = cb

    def set_on_selection_delete_handler(
        self, cb: Callable[[str], None]
    ) -> None:
        """MainPresenter が登録する選択削除ハンドラ。"""
        self._on_selection_delete_handler = cb

    def set_on_clear_selections_handler(
        self, cb: Callable[[], None]
    ) -> None:
        """MainPresenter が登録する全選択クリアハンドラ。"""
        self._on_clear_selections_handler = cb

    def set_on_cache_invalidate_handler(
        self, cb: Callable[[], None]
    ) -> None:
        """MainPresenter が登録するキャッシュ削除ハンドラ。"""
        self._on_cache_invalidate_handler = cb

    def update_cache_status(self, status: CacheStatus) -> None:
        """キャッシュ状態を内部に保持し、View を更新する。

        active + expire_time が存在する場合はカウントダウンを開始し、
        inactive の場合はカウントダウンを停止する。
        """
        self._cache_status = status
        self._view.set_cache_active(status.is_active)
        if status.is_active:
            brief = f"キャッシュ: ON ({status.token_count or '?'} tokens)"
        else:
            brief = "キャッシュ: OFF"
        self._view.update_cache_status_brief(brief)

        # Phase 7.5: カウントダウン連携
        if status.is_active and status.expire_time:
            self._view.start_cache_countdown(status.expire_time)
        else:
            self._view.stop_cache_countdown()

    def set_on_cache_expired_handler(
        self, cb: Callable[[], None]
    ) -> None:
        """MainPresenter が登録する期限切れハンドラ。"""
        self._on_cache_expired_handler = cb

    def _on_cache_expired(self) -> None:
        """View のカウントダウンが 0 に到達したとき呼ばれる。

        MainPresenter に委譲して get_cache_status の再取得を行う。
        """
        if self._on_cache_expired_handler:
            self._on_cache_expired_handler()

    # --- Private callback handlers ---

    def _on_force_image_toggled(self, checked: bool) -> None:
        """「画像としても送信」チェックボックスの状態変更を記録する。"""
        self._force_include_image = checked

    def _on_model_changed(self, model_name: str) -> None:
        """モデルプルダウンの変更を内部状態に反映する。

        キャッシュが active かつモデルが異なる場合は確認ダイアログを出す。
        OK → invalidate ハンドラ発火 + モデル更新
        Cancel → プルダウンを元のモデルに戻す
        """
        if (
            self._cache_status.is_active
            and self._cache_status.model_name
            and self._cache_status.model_name != model_name
        ):
            ok = self._view.show_confirm_dialog(
                "モデル変更確認",
                "キャッシュは現在のモデル専用です。"
                "モデルを変更するとキャッシュが削除されます。\n"
                "続行しますか？",
            )
            if not ok:
                self._view.set_selected_model(
                    self._cache_status.model_name
                )
                return
            if self._on_cache_invalidate_handler:
                self._on_cache_invalidate_handler()
        self._current_model = model_name

    _MODEL_UNSET_MSG = (
        "⚠️ モデルが未設定です。"
        "Preferences (Ctrl+,) → AI Models タブで Fetch Models を実行してください。"
    )

    def _on_translate_requested(self, include_explanation: bool) -> None:
        """翻訳ボタン押下を受け取り、非同期処理を開始する。"""

        # ボタンクリック自体は同期イベントなので、その場で await せず
        # タスク化して UI スレッドをふさがないようにする。
        asyncio.ensure_future(self._do_translate(include_explanation))

    async def _do_translate(self, include_explanation: bool) -> None:
        """翻訳モードで AI 解析を実行し、結果を View に返す。"""
        analysis_text = self._build_analysis_text()
        if not analysis_text:
            return
        if not self._current_model:
            self._view.update_result_text(self._MODEL_UNSET_MSG)
            return
        self._view.show_loading(True)
        try:
            request = AnalysisRequest(
                text=analysis_text,
                mode=AnalysisMode.TRANSLATION,
                include_explanation=include_explanation,
                images=self._collect_images(),
                model_name=self._current_model,
            )
            result = await self._ai_model.analyze(request)

            display = result.translated_text or result.raw_response
            if include_explanation and result.explanation:
                display += "\n\n---\n\n" + result.explanation
            self._view.update_result_text(display)
        except AIKeyMissingError:
            self._view.update_result_text(
                "⚠️ API キーが設定されていません。"
                "設定ダイアログまたは環境変数で GEMINI_API_KEY を設定してください。"
            )
        except AIRateLimitError:
            self._view.update_result_text(
                "⚠️ API レート制限に達しました。しばらく待ってから再試行してください。"
            )
        except AIAPIError as exc:
            self._view.update_result_text(
                f"⚠️ API エラー: {exc.message}"
            )
        finally:
            self._view.show_loading(False)

    def _on_custom_prompt_submitted(self, prompt: str) -> None:
        """カスタムプロンプト送信を受け取り、非同期処理を開始する。"""
        asyncio.ensure_future(self._do_custom_prompt(prompt))

    async def _do_custom_prompt(self, prompt: str) -> None:
        """カスタムプロンプトモードで AI 解析を実行する。"""
        analysis_text = self._build_analysis_text()
        if not analysis_text:
            return
        if not self._current_model:
            self._view.update_result_text(self._MODEL_UNSET_MSG)
            return
        self._view.show_loading(True)
        try:
            request = AnalysisRequest(
                text=analysis_text,
                mode=AnalysisMode.CUSTOM_PROMPT,
                custom_prompt=prompt,
                images=self._collect_images(),
                model_name=self._current_model,
            )
            result = await self._ai_model.analyze(request)
            self._view.update_result_text(result.raw_response)
        except AIKeyMissingError:
            self._view.update_result_text(
                "⚠️ API キーが設定されていません。"
                "設定ダイアログまたは環境変数で GEMINI_API_KEY を設定してください。"
            )
        except AIRateLimitError:
            self._view.update_result_text(
                "⚠️ API レート制限に達しました。しばらく待ってから再試行してください。"
            )
        except AIAPIError as exc:
            self._view.update_result_text(
                f"⚠️ API エラー: {exc.message}"
            )
        finally:
            self._view.show_loading(False)

    def _fire_cache_create(self) -> None:
        """View のキャッシュ作成ボタンを MainPresenter のハンドラに中継する。"""
        if not self._current_model:
            self._view.update_result_text(self._MODEL_UNSET_MSG)
            return
        if self._on_cache_create_handler:
            self._on_cache_create_handler()

    def _fire_cache_invalidate(self) -> None:
        """View のキャッシュ削除ボタンを MainPresenter のハンドラに中継する。"""
        if self._on_cache_invalidate_handler:
            self._on_cache_invalidate_handler()

    def _fire_selection_delete_requested(self, selection_id: str) -> None:
        """View の個別削除要求を MainPresenter のハンドラに中継する。"""
        if self._on_selection_delete_handler:
            self._on_selection_delete_handler(selection_id)

    def _fire_clear_selections_requested(self) -> None:
        """View の全消去要求を MainPresenter のハンドラに中継する。"""
        if self._on_clear_selections_handler:
            self._on_clear_selections_handler()

    # --- Private helpers ---

    def _normalized_snapshot(
        self, snapshot: SelectionSnapshot
    ) -> SelectionSnapshot:
        """表示番号を現行順に詰め直したスナップショットを返す。"""
        return SelectionSnapshot(
            slots=tuple(
                replace(slot, display_number=index)
                for index, slot in enumerate(snapshot.slots, start=1)
            )
        )

    def _build_analysis_text(self) -> str:
        """AI に送る本文を選択順・明示的区切り付きで構築する。"""
        parts: list[str] = []
        for slot in self._selection_snapshot.slots:
            if slot.read_state != "ready":
                continue
            text = slot.extracted_text.strip()
            if not text:
                continue
            parts.append(
                f"選択 {slot.display_number} / ページ {slot.page_number + 1}\n\n{text}"
            )
        return "\n\n".join(parts)

    def _collect_images(self) -> list[bytes]:
        """現在の選択スナップショットから cropped_image を順序通り収集する。"""
        images: list[bytes] = []
        for slot in self._selection_snapshot.slots:
            if slot.read_state != "ready" or slot.content is None:
                continue
            if slot.content.cropped_image:
                images.append(slot.content.cropped_image)
        return images
