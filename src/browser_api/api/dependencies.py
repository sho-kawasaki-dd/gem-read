from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, Request

from browser_api.adapters.ai_gateway import GemReadAIGateway
from browser_api.adapters.config_gateway import load_api_key, load_runtime_config
from browser_api.application.services.analyze_service import AnalyzeService
from pdf_epub_reader.models.ai_model import AIModel


@dataclass(slots=True)
class BrowserAPIServices:
    analyze_service: AnalyzeService


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_runtime_config()
    ai_model = AIModel(api_key=load_api_key(), config=config)
    app.state.services = BrowserAPIServices(
        analyze_service=AnalyzeService(
            ai_gateway=GemReadAIGateway(ai_model),
            config=config,
        )
    )
    yield


def get_services(request: Request) -> BrowserAPIServices:
    return request.app.state.services