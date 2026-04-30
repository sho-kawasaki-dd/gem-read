"""Plotly 可視化で使う DTO。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PlotlySpec:
    """LLM 応答から抽出した Plotly spec の生データ。"""

    index: int
    language: Literal["json"]
    source_text: str
    title: str | None = None