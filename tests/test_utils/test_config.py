from __future__ import annotations

import json

from pdf_epub_reader.utils.config import AppConfig, load_config, save_config


class TestUiLanguageConfig:
    def test_missing_config_uses_os_locale_default(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        config_path = tmp_path / "config.json"
        monkeypatch.setattr(
            "pdf_epub_reader.utils.config.locale.getlocale",
            lambda: ("ja_JP", "UTF-8"),
        )

        config = load_config(config_path)

        assert config.ui_language == "ja"

    def test_existing_config_without_ui_language_uses_os_locale_default(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps({"window_width": 1600}, ensure_ascii=False),
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "pdf_epub_reader.utils.config.locale.getlocale",
            lambda: ("ja-JP", "UTF-8"),
        )

        config = load_config(config_path)

        assert config.window_width == 1600
        assert config.ui_language == "ja"

    def test_load_config_normalizes_legacy_ui_language(self, tmp_path) -> None:
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps({"ui_language": "en-US"}, ensure_ascii=False),
            encoding="utf-8",
        )

        config = load_config(config_path)

        assert config.ui_language == "en"

    def test_invalid_ui_language_falls_back_to_english(self) -> None:
        config = AppConfig(ui_language="fr-FR")

        assert config.ui_language == "en"

    def test_save_config_writes_normalized_ui_language(self, tmp_path) -> None:
        config_path = tmp_path / "config.json"
        config = AppConfig(ui_language="en")
        config.ui_language = "ja-JP"

        save_config(config, config_path)

        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert saved["ui_language"] == "ja"


class TestAiModelConfig:
    def test_ai_model_fields_are_normalized(self) -> None:
        config = AppConfig(
            gemini_model_name="  ",
            selected_models=["models/a", "", "  ", "models/a", "models/b  "],
        )

        assert config.gemini_model_name == ""
        assert config.selected_models == ["models/a", "models/b"]