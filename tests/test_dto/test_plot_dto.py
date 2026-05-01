from __future__ import annotations

from pdf_epub_reader.dto import AnalysisMode, AnalysisRequest, PlotlySpec


class TestPlotlyDtos:
    def test_analysis_request_plotly_mode_defaults_to_off(self) -> None:
        request = AnalysisRequest(text="hello", mode=AnalysisMode.TRANSLATION)

        assert request.request_plotly_mode == "off"

    def test_plotly_spec_preserves_extracted_block_metadata(self) -> None:
        spec = PlotlySpec(
            index=1,
            language="json",
            source_text='{"data": [], "layout": {}}',
            title="Plot 1",
        )

        assert spec.index == 1
        assert spec.language == "json"
        assert spec.source_text == '{"data": [], "layout": {}}'
        assert spec.title == "Plot 1"

    def test_plotly_spec_accepts_python_language(self) -> None:
        spec = PlotlySpec(index=2, language="python", source_text="print('ok')")

        assert spec.language == "python"