from __future__ import annotations

from pydantic import BaseModel, model_validator

from browser_api.application.dto import TokenCountCommand, TokenCountResult


class TokenCountRequest(BaseModel):
    """HTTP schema for token preflight estimation requests."""

    text: str
    model_name: str | None = None

    @model_validator(mode="after")
    def validate_text(self) -> "TokenCountRequest":
        if not self.text.strip():
            raise ValueError("text is required")
        return self

    def to_command(self) -> TokenCountCommand:
        return TokenCountCommand(
            text=self.text.strip(),
            model_name=self.model_name.strip() if self.model_name else None,
        )


class TokenCountResponse(BaseModel):
    """Normalized token count result returned to the browser extension."""

    ok: bool = True
    token_count: int
    model_name: str

    @classmethod
    def from_result(cls, result: TokenCountResult) -> "TokenCountResponse":
        return cls(token_count=result.token_count, model_name=result.model_name)