"""Shared policy and exceptions for the Plotly sandbox runtime."""

from __future__ import annotations

from pathlib import Path

ALLOWED_THIRDPARTY_PACKAGES: tuple[str, ...] = (
    "plotly",
    "kaleido",
    "numpy",
    "pandas",
    "scipy",
    "sympy",
)

ALLOWED_STDLIB_MODULES: frozenset[str] = frozenset(
    {"math", "statistics", "datetime", "json"}
)

DISALLOWED_BUILTIN_CALLS: frozenset[str] = frozenset(
    {"eval", "exec", "compile", "__import__", "open", "input", "breakpoint"}
)

DISALLOWED_DUNDER_ATTRS: frozenset[str] = frozenset(
    {
        "__class__",
        "__bases__",
        "__subclasses__",
        "__mro__",
        "__globals__",
        "__builtins__",
        "__import__",
        "__loader__",
        "__code__",
    }
)

SANDBOX_MANIFEST_NAME = "gem-read-sandbox.json"
SANDBOX_MANIFEST_SCHEMA_VERSION = 1


class SandboxProvisioningError(Exception):
    """Raised when the dedicated sandbox venv cannot be prepared."""


class SandboxTimeoutError(Exception):
    """Raised when sandbox execution exceeds the configured timeout."""


class SandboxCancelledError(Exception):
    """Raised when sandbox execution is cancelled by the caller."""


class SandboxStaticCheckError(Exception):
    """Raised when runner AST validation rejects the submitted code."""

    def __init__(self, disallowed: list[str], stderr_log_path: Path) -> None:
        self.disallowed = disallowed
        self.stderr_log_path = stderr_log_path
        details = ", ".join(disallowed) if disallowed else "unknown policy violation"
        super().__init__(f"Sandbox static check failed: {details}")


class SandboxRuntimeError(Exception):
    """Raised when the runner exits with a non-static-check failure."""

    def __init__(self, stderr_summary: str, stderr_log_path: Path) -> None:
        self.stderr_summary = stderr_summary
        self.stderr_log_path = stderr_log_path
        super().__init__(stderr_summary)


class SandboxOutputError(Exception):
    """Raised when runner stdout does not contain a valid JSON payload."""


__all__ = [
    "ALLOWED_THIRDPARTY_PACKAGES",
    "ALLOWED_STDLIB_MODULES",
    "DISALLOWED_BUILTIN_CALLS",
    "DISALLOWED_DUNDER_ATTRS",
    "SANDBOX_MANIFEST_NAME",
    "SANDBOX_MANIFEST_SCHEMA_VERSION",
    "SandboxProvisioningError",
    "SandboxTimeoutError",
    "SandboxCancelledError",
    "SandboxStaticCheckError",
    "SandboxRuntimeError",
    "SandboxOutputError",
]