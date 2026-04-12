## Plan: MVP Alignment Refactor

1-5 は一連の改修として進めるのが妥当です。依存順は、まず MVP 境界を戻し、その後にキャッシュ境界とモデル状態を直し、最後に async 契約と細部の仕様差を揃える流れです。

**決定事項**
1. 項目4は設計書どおり、Presenter から見える Model 公開 API を async に統一します。
2. 項目1は MainWindow と SidePanel だけでなく、Dialog 群と Bookmark も含めて View から TranslationService を全面撤去します。
3. 項目5の cache display_name は API が返す値を正とします。

**フェーズ**
1. 翻訳責務の移動。
[src/pdf_epub_reader/views/main_window.py](src/pdf_epub_reader/views/main_window.py), [src/pdf_epub_reader/views/side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py), [src/pdf_epub_reader/views/settings_dialog.py](src/pdf_epub_reader/views/settings_dialog.py), [src/pdf_epub_reader/views/cache_dialog.py](src/pdf_epub_reader/views/cache_dialog.py), [src/pdf_epub_reader/views/language_dialog.py](src/pdf_epub_reader/views/language_dialog.py), [src/pdf_epub_reader/views/bookmark_panel.py](src/pdf_epub_reader/views/bookmark_panel.py) から TranslationService 依存を除去します。Presenter 側で解決済み文字列の束を作り、View はそれを適用するだけにします。契約変更の中心は [src/pdf_epub_reader/interfaces/view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py) です。

2. Presenter 境界の復元。
[src/pdf_epub_reader/presenters/main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py) から [src/pdf_epub_reader/presenters/panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py) の private view 直アクセスを除去し、PanelPresenter に公開メソッドを追加します。あわせて [src/pdf_epub_reader/interfaces/model_interfaces.py](src/pdf_epub_reader/interfaces/model_interfaces.py) と [src/pdf_epub_reader/models/ai_model.py](src/pdf_epub_reader/models/ai_model.py) に selected cache を名前指定で削除する公開 API を追加し、AIModel の内部状態書き換えをやめます。

3. キャッシュ DTO と UI 表示の修正。
[src/pdf_epub_reader/dto/ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py) の CacheStatus に display_name を追加し、[src/pdf_epub_reader/models/ai_model.py](src/pdf_epub_reader/models/ai_model.py) の create_cache, get_cache_status, list_caches で API 値を保持します。[src/pdf_epub_reader/views/cache_dialog.py](src/pdf_epub_reader/views/cache_dialog.py) と [src/pdf_epub_reader/presenters/cache_presenter.py](src/pdf_epub_reader/presenters/cache_presenter.py) はそれをそのまま表示する形に揃えます。

4. モデル未設定状態の一貫化。
[src/pdf_epub_reader/presenters/panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py), [src/pdf_epub_reader/presenters/main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py), [src/pdf_epub_reader/views/side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py), [src/pdf_epub_reader/utils/config.py](src/pdf_epub_reader/utils/config.py) を対象に、未設定値は空文字で統一しつつ、UI 表示は disabled とプレースホルダーに固定します。モデル変更確認をキャンセルしたときは、ComboBox の表示と PanelPresenter の内部状態を両方リバートします。

5. Model 公開 API の async 統一。
[src/pdf_epub_reader/interfaces/model_interfaces.py](src/pdf_epub_reader/interfaces/model_interfaces.py), [src/pdf_epub_reader/models/document_model.py](src/pdf_epub_reader/models/document_model.py), [src/pdf_epub_reader/models/ai_model.py](src/pdf_epub_reader/models/ai_model.py) のうち同期公開のまま残っている presenter-facing API を async 化し、[src/pdf_epub_reader/presenters/main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py), [src/pdf_epub_reader/presenters/settings_presenter.py](src/pdf_epub_reader/presenters/settings_presenter.py), テストとモック全体に await を伝播させます。

6. 細部仕様の整合。
[src/pdf_epub_reader/resources/i18n.py](src/pdf_epub_reader/resources/i18n.py) で日本語 UI からアクセラレータを除去し、英語のみ保持します。TTL, Expire Time, Not set, ON/OFF などの用語は、翻訳責務移動後の文字列束で統一します。

**主な対象**
- [src/pdf_epub_reader/interfaces/view_interfaces.py](src/pdf_epub_reader/interfaces/view_interfaces.py)
- [src/pdf_epub_reader/interfaces/model_interfaces.py](src/pdf_epub_reader/interfaces/model_interfaces.py)
- [src/pdf_epub_reader/presenters/main_presenter.py](src/pdf_epub_reader/presenters/main_presenter.py)
- [src/pdf_epub_reader/presenters/panel_presenter.py](src/pdf_epub_reader/presenters/panel_presenter.py)
- [src/pdf_epub_reader/presenters/settings_presenter.py](src/pdf_epub_reader/presenters/settings_presenter.py)
- [src/pdf_epub_reader/presenters/language_presenter.py](src/pdf_epub_reader/presenters/language_presenter.py)
- [src/pdf_epub_reader/presenters/cache_presenter.py](src/pdf_epub_reader/presenters/cache_presenter.py)
- [src/pdf_epub_reader/models/ai_model.py](src/pdf_epub_reader/models/ai_model.py)
- [src/pdf_epub_reader/models/document_model.py](src/pdf_epub_reader/models/document_model.py)
- [src/pdf_epub_reader/dto/ai_dto.py](src/pdf_epub_reader/dto/ai_dto.py)
- [src/pdf_epub_reader/views/main_window.py](src/pdf_epub_reader/views/main_window.py)
- [src/pdf_epub_reader/views/side_panel_view.py](src/pdf_epub_reader/views/side_panel_view.py)
- [src/pdf_epub_reader/views/settings_dialog.py](src/pdf_epub_reader/views/settings_dialog.py)
- [src/pdf_epub_reader/views/cache_dialog.py](src/pdf_epub_reader/views/cache_dialog.py)
- [src/pdf_epub_reader/views/language_dialog.py](src/pdf_epub_reader/views/language_dialog.py)
- [src/pdf_epub_reader/views/bookmark_panel.py](src/pdf_epub_reader/views/bookmark_panel.py)
- [src/pdf_epub_reader/resources/i18n.py](src/pdf_epub_reader/resources/i18n.py)
- [tests/mocks/mock_views.py](tests/mocks/mock_views.py)
- [tests/mocks/mock_models.py](tests/mocks/mock_models.py)
- [tests/test_presenters/test_main_presenter.py](tests/test_presenters/test_main_presenter.py)
- [tests/test_presenters/test_panel_presenter.py](tests/test_presenters/test_panel_presenter.py)
- [tests/test_presenters/test_settings_presenter.py](tests/test_presenters/test_settings_presenter.py)
- [tests/test_presenters/test_cache_presenter.py](tests/test_presenters/test_cache_presenter.py)
- [tests/test_presenters/test_language_presenter.py](tests/test_presenters/test_language_presenter.py)

**検証**
1. Presenter テストで、View が翻訳を行わず、解決済み文字列の適用だけを受けることを確認します。
2. Cache フローで private 属性アクセスが消え、selected cache の削除が public API 経由で動くことを確認します。
3. display_name が API 値で一覧表示されることを確認します。
4. モデル未設定時に ComboBox が disabled で、翻訳・キャッシュ作成が拒否されることを確認します。
5. async 化した Model 公開 API に対して、Presenter とテストがすべて await していることを確認します。
6. 日本語 UI でアクセラレータが消え、英語 UI のみ残ることを確認します。

この計画は session plan に保存済みです。必要なら次に、これをさらに「PR 1 / PR 2 / PR 3」単位まで分割します。
