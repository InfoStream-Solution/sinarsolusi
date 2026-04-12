from __future__ import annotations

from .base import Summarizer


class TextSummarizer(Summarizer):
    """Summarizer that returns a plain text summary."""

    def summarize(self, text: str, count: int = 3) -> str:
        return "\n".join(super().summarize(text, count=count))
