"""Plotly figure/spec export helpers for Markdown export and PlotWindow save actions."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Literal, cast

import plotly.io as pio
from plotly.graph_objects import Figure

from pdf_epub_reader.dto import PlotlySpec

PlotlyExportFormat = Literal["html", "png", "svg", "json"]

_KALEIDO_AVAILABLE: bool | None = None


class PlotlyExportError(Exception):
    """Plotly export failures wrapped for UI-level handling."""

    def __init__(self, code: str, details: str) -> None:
        super().__init__(details)
        self.code = code
        self.details = details


def is_kaleido_available() -> bool:
    """Return True when kaleido can be imported in the current environment."""
    global _KALEIDO_AVAILABLE

    if _KALEIDO_AVAILABLE is not None:
        return _KALEIDO_AVAILABLE

    try:
        importlib.import_module("kaleido")
    except ImportError:
        _KALEIDO_AVAILABLE = False
    else:
        _KALEIDO_AVAILABLE = True
    return _KALEIDO_AVAILABLE


def export_figure(
    fig: Figure,
    *,
    format: PlotlyExportFormat,
    path: str | Path,
) -> None:
    """Export a Plotly figure to the requested format."""
    target_path = Path(path)
    try:
        if format == "html":
            target_path.write_text(_figure_to_html(fig), encoding="utf-8")
            return
        if format == "json":
            json_text = fig.to_json()
            if not isinstance(json_text, str):
                raise PlotlyExportError(
                    "export_failed",
                    "Plotly returned non-string JSON output.",
                )
            target_path.write_text(json_text, encoding="utf-8")
            return
        if format in {"png", "svg"}:
            _ensure_kaleido_available()
            target_path.write_bytes(pio.to_image(fig, format=format))
            return
    except PlotlyExportError:
        raise
    except OSError as exc:
        raise PlotlyExportError("write_failed", str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive wrap for Plotly internals
        raise PlotlyExportError("export_failed", str(exc)) from exc

    raise PlotlyExportError(
        "unsupported_format",
        f"Unsupported Plotly export format: {format}",
    )


def export_spec(
    spec: PlotlySpec,
    fig: Figure,
    *,
    format: PlotlyExportFormat,
    path: str | Path,
) -> None:
    """Export a Plotly spec and its restored figure to disk."""
    if format == "json" and spec.language == "json":
        target_path = Path(path)
        try:
            target_path.write_text(spec.source_text, encoding="utf-8")
        except OSError as exc:
            raise PlotlyExportError("write_failed", str(exc)) from exc
        return

    export_figure(fig, format=format, path=path)


def _ensure_kaleido_available() -> None:
    if not is_kaleido_available():
        raise PlotlyExportError(
            "kaleido_unavailable",
            "kaleido is required for PNG/SVG export.",
        )


def _figure_to_html(fig: Figure) -> str:
    return pio.to_html(
        fig,
        include_plotlyjs=cast(Any, "inline"),
        full_html=True,
        default_width="100%",
        default_height="100vh",
    )