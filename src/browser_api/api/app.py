from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from browser_api.api.dependencies import lifespan
from browser_api.api.routers.analyze import router as analyze_router
from browser_api.api.routers.cache import router as cache_router
from browser_api.api.routers.health import router as health_router
from browser_api.api.routers.models import router as models_router
from browser_api.api.routers.tokens import router as tokens_router

DEFAULT_API_TITLE = "Gem Read Browser API"
DEFAULT_EXTENSION_ORIGIN_REGEX = r"chrome-extension://.*"


def create_app() -> FastAPI:
    """Create the FastAPI app with browser-extension-specific CORS and router wiring."""

    app = FastAPI(title=DEFAULT_API_TITLE, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        # 拡張機能からの localhost bridge 呼び出しだけを許可し、一般的な cross-origin 利用は想定しない。
        allow_origin_regex=DEFAULT_EXTENSION_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(models_router)
    app.include_router(analyze_router)
    app.include_router(cache_router)
    app.include_router(tokens_router)
    return app


app = create_app()