from __future__ import annotations

from abc import ABC, abstractmethod

MAX_ITEMS = 3


def build_prompt(text: str, count: int) -> str:
    """Build the summarization prompt."""
    item_count = max(1, count)
    return (
        "Ringkas teks berita berikut hanya berdasarkan fakta yang tertulis di teks.\n"
        f"Buat tepat {item_count} kalimat ringkas dalam JSON array.\n"
        "Jangan menambah fakta baru, opini, interpretasi, atau konteks luar teks.\n"
        "Tulis ulang isi artikel secara netral, singkat, dan faktual.\n"
        "Setiap item harus berupa satu kalimat sangat ringkas.\n"
        'Gunakan format: ["...", "..."].\n'
        "Output harus valid JSON saja, tanpa markdown, tanpa penjelasan.\n\n"
        f"TEKS:\n{text.strip()}"
    )


class LlmApiClient(ABC):
    """Base class for LLM clients."""

    def __init__(self, model_name: str, api_key: str) -> None:
        self.model_name = model_name
        self.api_key = api_key

    def build_prompt(self, text: str, count: int) -> str:
        """Build the summarization prompt."""
        return build_prompt(text, count)

    @abstractmethod
    def send(self, prompt: str) -> str:
        """Send a prompt to the LLM and return the raw text response."""
