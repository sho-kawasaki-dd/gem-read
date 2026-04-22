from __future__ import annotations

from dataclasses import dataclass

from pdf_epub_reader.utils.config import AppConfig


@dataclass(frozen=True, slots=True)
class BrowserApiConfig:
    """Runtime settings that browser_api is allowed to read directly."""

    default_model: str
    selected_models: list[str]
    output_language: str
    default_translation_system_prompt: str
    cache_ttl_minutes: int


def map_app_config_to_browser_api_config(config: AppConfig) -> BrowserApiConfig:
    """Project the desktop AppConfig into the smaller browser_api configuration surface."""

    return BrowserApiConfig(
        default_model=config.gemini_model_name,
        selected_models=list(config.selected_models),
        output_language=config.output_language,
        default_translation_system_prompt=config.system_prompt_translation,
        cache_ttl_minutes=config.cache_ttl_minutes,
    )