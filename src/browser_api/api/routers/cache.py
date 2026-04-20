from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from browser_api.api.dependencies import BrowserAPIServices, get_services
from browser_api.api.error_handlers import to_http_exception
from browser_api.api.schemas.cache import (
    CacheCreateRequest,
    CacheDeleteResponse,
    CacheListResponse,
    CacheStatusResponse,
)

router = APIRouter(prefix="/cache", tags=["cache"])
logger = logging.getLogger(__name__)


@router.get("/list", response_model=CacheListResponse)
async def list_caches(
    services: BrowserAPIServices = Depends(get_services),
) -> CacheListResponse:
    """List all browser-extension-owned caches for the popup debug section."""

    try:
        result = await services.analyze_service.list_browser_extension_caches()
        return CacheListResponse.from_result(result)
    except Exception as exc:
        logger.exception("Unexpected browser API cache list error")
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