from __future__ import annotations

import os

import dotenv

from pdf_epub_reader.utils.config import ENV_GEMINI_API_KEY, AppConfig, load_config


def load_runtime_config() -> AppConfig:
    dotenv.load_dotenv()
    return load_config()


def load_api_key() -> str | None:
    return os.environ.get(ENV_GEMINI_API_KEY)