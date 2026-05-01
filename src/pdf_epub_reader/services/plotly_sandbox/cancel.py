"""Cancellation primitive for sandboxed Plotly subprocess execution."""

from __future__ import annotations

from threading import Event


class CancelToken:
    """Thread-safe cancellation flag shared with sandbox execution helpers."""

    def __init__(self) -> None:
        self._event = Event()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()

    def set(self) -> None:
        self._event.set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout)