from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from browser_api.api.dependencies import lifespan
from browser_api.api.routers.analyze import router as analyze_router
from browser_api.api.routers.health import router as health_router
from browser_api.api.routers.models import router as models_router

DEFAULT_API_TITLE = "Gem Read Browser API"
DEFAULT_EXTENSION_ORIGIN_REGEX = r"chrome-extension://.*"


def create_app() -> FastAPI:
    app = FastAPI(title=DEFAULT_API_TITLE, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=DEFAULT_EXTENSION_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(models_router)
    app.include_router(analyze_router)
    return app


app = create_app()