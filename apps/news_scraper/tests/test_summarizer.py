from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import news_scraper_core.llm_api_client.base as llm_base
import news_scraper_core.llm_api_client.google as llm_google
import news_scraper_core.summarizer as summarizer
from news_scraper_core.llm_api_client.schema import SummarizationError


class DummyModels:
    def __init__(
        self, response: object | None = None, error: Exception | None = None
    ) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def generate_content(
        self,
        *,
        model: str,
        contents: str,
        config: object | None = None,
    ) -> object:
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error is not None:
            raise self.error
        return self.response or SimpleNamespace(text='["Satu","Dua"]')


class DummyClient:
    def __init__(self, models: DummyModels) -> None:
        self.models = models

    def build_prompt(self, text: str, count: int) -> str:
        return llm_base.build_prompt(text, count)

    def send(self, prompt: str) -> str:
        return self.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=None,
        ).text


def test_build_prompt_uses_requested_count() -> None:
    prompt = llm_base.build_prompt("Teks berita.", 5)

    assert "Buat tepat 5 kalimat ringkas dalam JSON array." in prompt
    assert 'Gunakan format: ["...", "..."].' in prompt
    assert "Teks berita." in prompt


def test_google_client_builds_expected_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = DummyModels()
    monkeypatch.setattr(
        llm_google.genai, "Client", lambda api_key: SimpleNamespace(models=models)
    )
    client = llm_google.GoogleClient(model_name="gemini-2.5-flash", api_key="key")

    response = client.send("prompt")

    assert response == '["Satu","Dua"]'
    assert len(models.calls) == 1
    assert models.calls[0]["model"] == "gemini-2.5-flash"
    config = models.calls[0]["config"]
    assert getattr(config, "temperature", None) == 0
    assert getattr(config, "response_mime_type", None) == "application/json"
    assert getattr(config, "response_json_schema", None) is not None


def test_summarizer_uses_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = DummyModels()
    client = DummyClient(models)
    monkeypatch.setattr(summarizer, "get_client", lambda: client)
    summary = summarizer.get_summarizer().summarize(
        "Berita utama. Isi lengkap.", count=2
    )

    assert summary == ["Satu", "Dua"]


def test_summarizer_raises_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = DummyModels(response=SimpleNamespace(text='["Satu", {"wrong":"Dua"}]'))
    client = DummyClient(models)
    summary = summarizer.Summarizer(client)

    with pytest.raises(SummarizationError, match="structured JSON"):
        summary.summarize("Berita utama.")


def test_get_client_loads_api_key_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("GEMINI_API_KEY=from-dotenv\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    summarizer.get_client.cache_clear()
    monkeypatch.setattr(
        llm_google.genai,
        "Client",
        lambda api_key: SimpleNamespace(api_key=api_key, models=SimpleNamespace()),
    )

    client = summarizer.get_client()

    assert client.api_key == "from-dotenv"


def test_main_reads_stdin_and_prints_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        summarizer,
        "get_summarizer",
        lambda: summarizer.Summarizer(
            client=SimpleNamespace(
                build_prompt=lambda text, count: "",
                send=lambda prompt: '["Satu","Dua"]',
            )
        ),
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("Isi berita"))

    summarizer.main(["summarize.py"])

    captured = capsys.readouterr()
    assert json.loads(captured.out) == ["Satu", "Dua"]


def test_load_text_from_args_reads_file(tmp_path: Path) -> None:
    article_path = tmp_path / "article.txt"
    article_path.write_text("Isi artikel", encoding="utf-8")

    assert (
        summarizer.load_text_from_args(["summarizer.py", str(article_path)])
        == "Isi artikel"
    )


def test_load_text_from_args_reads_inline_text() -> None:
    assert (
        summarizer.load_text_from_args(["summarizer.py", "--text", "Isi", "artikel"])
        == "Isi artikel"
    )


def test_load_text_from_args_rejects_interactive_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    with pytest.raises(SystemExit) as exc_info:
        summarizer.load_text_from_args(["summarizer.py"])

    assert exc_info.value.code == 2
