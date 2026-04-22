from __future__ import annotations

from browser_api.adapters.config_gateway import load_runtime_config
from browser_api.application.config import BrowserApiConfig
from pdf_epub_reader.utils.config import AppConfig


def test_load_runtime_config_maps_app_config(monkeypatch) -> None:
    app_config = AppConfig(
        gemini_model_name="gemini-2.5-flash",
        selected_models=["gemini-2.5-pro", "gemini-2.5-flash"],
        output_language="English",
        system_prompt_translation="Translate carefully.",
        cache_ttl_minutes=90,
    )

    monkeypatch.setattr(
        "browser_api.adapters.config_gateway.load_config",
        lambda: app_config,
    )

    assert load_runtime_config() == BrowserApiConfig(
        default_model="gemini-2.5-flash",
        selected_models=["gemini-2.5-pro", "gemini-2.5-flash"],
        output_language="English",
        default_translation_system_prompt="Translate carefully.",
        cache_ttl_minutes=90,
    )