from __future__ import annotations

from .base import Summarizer


class JsonSummarizer(Summarizer):
    """Summarizer that returns a JSON-compatible list of strings."""

    def summarize(self, text: str, count: int = 3) -> list[str]:
        return super().summarize(text, count=count)
