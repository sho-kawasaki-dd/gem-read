from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from browser_api.api.dependencies import BrowserAPIServices, get_services
from browser_api.api.error_handlers import to_http_exception
from browser_api.api.schemas.cache import (
    CacheCreateRequest,
    CacheDeleteResponse,
    CacheStatusResponse,
)

router = APIRouter(prefix="/cache", tags=["cache"])
logger = logging.getLogger(__name__)


@router.get("/status", response_model=CacheStatusResponse)
async def get_cache_status(
    services: BrowserAPIServices = Depends(get_services),
) -> CacheStatusResponse:
    """Return the current active cache status for the browser extension."""

    try:
        result = await services.analyze_service.get_cache_status()
        return CacheStatusResponse.from_result(result)
    except Exception as exc:
        logger.exception("Unexpected browser API cache status error")
        raise to_http_exception(exc) from exc


@router.post("/create", response_model=CacheStatusResponse)
async def create_cache(
    request: CacheCreateRequest,
    services: BrowserAPIServices = Depends(get_services),
) -> CacheStatusResponse:
    """Create a cache from extracted article text via the application service."""

    try:
        result = await services.analyze_service.create_cache(request.to_command())
        return CacheStatusResponse.from_result(result)
    except Exception as exc:
        logger.exception("Unexpected browser API cache create error")
        raise to_http_exception(exc) from exc


@router.delete("/{cache_name:path}", response_model=CacheDeleteResponse)
async def delete_cache(
    cache_name: str,
    services: BrowserAPIServices = Depends(get_services),
) -> CacheDeleteResponse:
    """Delete a named Gemini cache resource."""

    try:
        result = await services.analyze_service.delete_cache(cache_name)
        return CacheDeleteResponse.from_result(result)
    except Exception as exc:
        logger.exception("Unexpected browser API cache delete error")
        raise to_http_exception(exc) from exc