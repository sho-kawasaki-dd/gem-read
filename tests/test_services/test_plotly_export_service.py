from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest
from plotly.graph_objects import Figure

import pdf_epub_reader.services.plotly_export_service as export_service
from pdf_epub_reader.dto import PlotlySpec
from pdf_epub_reader.services.plotly_export_service import (
    PlotlyExportError,
    export_figure,
    export_spec,
    is_kaleido_available,
)
from pdf_epub_reader.services.plotly_render_service import parse_spec


def _figure() -> Figure:
    return parse_spec(
        PlotlySpec(
            index=0,
            language="json",
            source_text=(
                '{"data": [{"type": "bar", "x": ["A"], "y": [5]}], '
                '"layout": {"title": {"text": "Bars"}}}'
            ),
            title="Example Plot",
        )
    )


def _spec_json() -> PlotlySpec:
    return PlotlySpec(
        index=0,
        language="json",
        source_text=(
            '{"data": [{"type": "scatter", "x": [1, 2], "y": [3, 4]}], '
            '"layout": {"title": {"text": "Source JSON"}}}'
        ),
        title="Source JSON",
    )


def _spec_python() -> PlotlySpec:
    return PlotlySpec(
        index=0,
        language="python",
        source_text="print(fig.to_json())",
        title="Python Plot",
    )


class TestPlotlyExportService:
    def test_is_kaleido_available_caches_the_import_attempt(self, monkeypatch) -> None:
        calls: list[str] = []
        monkeypatch.setattr(export_service, "_KALEIDO_AVAILABLE", None)

        def fake_import(name: str):
            calls.append(name)
            return object()

        monkeypatch.setattr(export_service.importlib, "import_module", fake_import)

        assert is_kaleido_available() is True
        assert is_kaleido_available() is True
        assert calls == ["kaleido"]

    def test_export_figure_writes_html(self, tmp_path: Path) -> None:
        figure = _figure()
        target = tmp_path / "plot.html"

        export_figure(figure, format="html", path=target)

        html = target.read_text(encoding="utf-8")
        assert html.lstrip().startswith("<html>")
        assert "Plotly.newPlot" in html

    def test_export_figure_writes_json(self, tmp_path: Path) -> None:
        figure = _figure()
        target = tmp_path / "plot.json"

        export_figure(figure, format="json", path=target)

        payload = target.read_text(encoding="utf-8")
        assert payload.startswith("{")
        assert '"layout"' in payload

    def test_export_spec_uses_source_text_for_json_specs(self, monkeypatch, tmp_path: Path) -> None:
        spec = _spec_json()
        figure = _figure()
        target = tmp_path / "plot.json"

        def fail_to_json() -> str:
            raise AssertionError("export_spec should use spec.source_text for JSON specs")

        monkeypatch.setattr(type(figure), "to_json", fail_to_json)

        export_spec(spec, figure, format="json", path=target)

        assert target.read_text(encoding="utf-8") == spec.source_text

    def test_export_spec_uses_figure_json_for_python_specs(self, monkeypatch, tmp_path: Path) -> None:
        spec = _spec_python()
        figure = _figure()
        target = tmp_path / "plot.json"

        def fake_to_json(self) -> str:
            return '{"data": [], "layout": {"title": "Python Plot"}}'

        expected_json = '{"data": [], "layout": {"title": "Python Plot"}}'

        monkeypatch.setattr(type(figure), "to_json", fake_to_json)

        export_spec(spec, figure, format="json", path=target)

        assert target.read_text(encoding="utf-8") == expected_json

    @pytest.mark.parametrize("format_name", ["png", "svg"])
    def test_export_figure_raises_when_kaleido_is_unavailable(
        self,
        monkeypatch,
        tmp_path: Path,
        format_name: Literal["png", "svg"],
    ) -> None:
        figure = _figure()
        target = tmp_path / f"plot.{format_name}"

        monkeypatch.setattr(export_service, "is_kaleido_available", lambda: False)

        with pytest.raises(PlotlyExportError) as exc_info:
            export_figure(figure, format=format_name, path=target)

        assert exc_info.value.code == "kaleido_unavailable"
        assert "kaleido" in exc_info.value.details

    @pytest.mark.parametrize(
        ("format_name", "suffix"),
        [("png", b"png-bytes"), ("svg", b"svg-bytes")],
    )
    def test_export_figure_uses_kaleido_image_export(
        self,
        monkeypatch,
        tmp_path: Path,
        format_name: Literal["png", "svg"],
        suffix: bytes,
    ) -> None:
        figure = _figure()
        target = tmp_path / f"plot.{format_name}"
        calls: list[str] = []

        monkeypatch.setattr(export_service, "is_kaleido_available", lambda: True)

        def fake_to_image(fig, *, format: str):
            calls.append(format)
            return suffix

        monkeypatch.setattr(export_service.pio, "to_image", fake_to_image)

        export_figure(figure, format=format_name, path=target)

        assert target.read_bytes() == suffix
        assert calls == [format_name]