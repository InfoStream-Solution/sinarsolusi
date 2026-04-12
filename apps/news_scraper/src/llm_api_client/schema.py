from __future__ import annotations

from pydantic import RootModel, model_validator


class SummaryResponse(RootModel[list[str]]):
    """Structured summary response from Gemini."""

    @model_validator(mode="after")
    def _validate_items(self) -> SummaryResponse:
        self.root = [item.strip() for item in self.root if item.strip()]
        if not self.root:
            raise ValueError("items must not be empty")
        return self


class SummarizationError(RuntimeError):
    """Raised when Gemini summarization cannot be completed."""
