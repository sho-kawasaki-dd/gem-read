from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from browser_api.application.dto import (
    CacheCreateCommand,
    CacheDeleteResult,
    CacheStatusResult,
)


class CacheCreateRequest(BaseModel):
    """HTTP schema for creating a single active context cache."""

    full_text: str = Field(min_length=1)
    model_name: str | None = None
    display_name: str | None = None

    @model_validator(mode="after")
    def validate_full_text(self) -> "CacheCreateRequest":
        if not self.full_text.strip():
            raise ValueError("full_text is required")
        return self

    def to_command(self) -> CacheCreateCommand:
        return CacheCreateCommand(
            full_text=self.full_text.strip(),
            model_name=self.model_name.strip() if self.model_name else None,
            display_name=self.display_name.strip() if self.display_name else None,
        )


class CacheStatusResponse(BaseModel):
    """Normalized cache state returned to the browser extension."""

    ok: bool = True
    is_active: bool = False
    ttl_seconds: int | None = None
    token_count: int | None = None
    cache_name: str | None = None
    display_name: str | None = None
    model_name: str | None = None
    expire_time: str | None = None

    @classmethod
    def from_result(cls, result: CacheStatusResult) -> "CacheStatusResponse":
        return cls(
            is_active=result.is_active,
            ttl_seconds=result.ttl_seconds,
            token_count=result.token_count,
            cache_name=result.cache_name,
            display_name=result.display_name,
            model_name=result.model_name,
            expire_time=result.expire_time,
        )


class CacheDeleteResponse(BaseModel):
    """Delete acknowledgement for a named cache resource."""

    ok: bool = True
    cache_name: str

    @classmethod
    def from_result(cls, result: CacheDeleteResult) -> "CacheDeleteResponse":
        return cls(cache_name=result.cache_name)