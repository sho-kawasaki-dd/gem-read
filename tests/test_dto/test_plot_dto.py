from __future__ import annotations

from pdf_epub_reader.dto import AnalysisMode, AnalysisRequest, PlotlySpec


class TestPlotlyDtos:
    def test_analysis_request_plotly_flag_defaults_to_false(self) -> None:
        request = AnalysisRequest(text="hello", mode=AnalysisMode.TRANSLATION)

        assert request.request_plotly_json is False

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