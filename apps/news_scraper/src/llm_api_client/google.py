from __future__ import annotations

from google import genai
from google.genai import types

from .base import LlmApiClient
from .schema import SummaryResponse, SummarizationError


class GoogleClient(LlmApiClient):
    """Gemini implementation of the LLM client."""

    def __init__(self, model_name: str, api_key: str) -> None:
        super().__init__(model_name=model_name, api_key=api_key)
        self._client = genai.Client(api_key=api_key)

    def send(self, prompt: str) -> str:
        config = types.GenerateContentConfig(
            temperature=0,
            top_p=1,
            top_k=1,
            response_mime_type="application/json",
            response_json_schema=SummaryResponse.model_json_schema(),
            max_output_tokens=2048,
        )
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        summary = getattr(response, "text", None)
        if not isinstance(summary, str) or not summary.strip():
            raise SummarizationError("Gemini response did not include text")
        return summary.strip()
