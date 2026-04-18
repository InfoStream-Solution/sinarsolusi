from __future__ import annotations

import argparse
import json as jsonlib
import os
import sys
from functools import lru_cache
from pathlib import Path

from ..llm_api_client.base import MAX_ITEMS
from ..llm_api_client.base import LlmApiClient
from ..llm_api_client.base import build_prompt
from ..llm_api_client.google import GoogleClient
from ..llm_api_client.schema import SummarizationError
from ..llm_api_client.schema import SummaryResponse
from .json_summarizer import JsonSummarizer
from .text import TextSummarizer

__all__ = [
    "JsonSummarizer",
    "MODEL_NAME",
    "MAX_ITEMS",
    "SummarizationError",
    "Summarizer",
    "TextSummarizer",
    "build_parser",
    "build_prompt",
    "get_client",
    "get_summarizer",
    "load_text_from_args",
    "main",
]

MODEL_NAME = "gemini-2.5-flash"


def _debug_enabled() -> bool:
    return os.environ.get("SUMMARIZER_DEBUG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _get_api_key() -> str:
    _load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SummarizationError("GEMINI_API_KEY is required for summarization")
    return api_key


def _create_client() -> LlmApiClient:
    return GoogleClient(model_name=MODEL_NAME, api_key=_get_api_key())


@lru_cache(maxsize=1)
def get_client() -> LlmApiClient:
    """Return a cached Gemini client."""
    return _create_client()


class Summarizer:
    """High-level article summarizer."""

    def __init__(self, client: LlmApiClient) -> None:
        self.client = client

    def summarize(self, text: str, count: int = 3) -> list[str]:
        prompt = self.client.build_prompt(text, count)
        summary_text = self.client.send(prompt)
        if _debug_enabled():
            print(f"RAW GEMINI RESPONSE: {summary_text}", file=sys.stderr)

        try:
            summary = SummaryResponse.model_validate_json(summary_text)
        except Exception as exc:
            raise SummarizationError(
                "Gemini response was not valid structured JSON"
            ) from exc

        item_limit = max(1, count)
        return summary.root[:item_limit]


def get_summarizer() -> Summarizer:
    """Return a summarizer using the cached Gemini client."""
    return Summarizer(client=get_client())


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the summarizer."""
    parser = argparse.ArgumentParser(prog="summarize")
    parser.add_argument("file", nargs="?", help="Path to a text file to summarize.")
    parser.add_argument(
        "-f",
        "--format",
        choices={"json", "text"},
        default="json",
        help="Output format.",
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=3,
        help="Number of summary items to return.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print the raw Gemini response to stderr.",
    )
    parser.add_argument(
        "--text",
        nargs="+",
        help="Inline article text to summarize. Overrides the file argument.",
    )
    return parser


def load_text_from_args(argv: list[str]) -> str:
    """Load article text from a file argument, inline text, or stdin."""
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    if args.text is not None:
        return " ".join(args.text).strip()
    if args.file is not None:
        return Path(args.file).read_text(encoding="utf-8").strip()
    if sys.stdin.isatty():
        parser.print_help()
        raise SystemExit(2)

    return sys.stdin.read().strip()


def main(argv: list[str] | None = None) -> None:
    """Read text from args or stdin, summarize it, and print JSON."""
    parser = build_parser()
    args = parser.parse_args((argv or sys.argv)[1:])
    if args.text is not None:
        text = " ".join(args.text).strip()
    elif args.file is not None:
        text = Path(args.file).read_text(encoding="utf-8").strip()
    elif sys.stdin.isatty():
        parser.print_help()
        raise SystemExit(2)
    else:
        text = sys.stdin.read().strip()

    if not text:
        raise SystemExit("Provide article text via stdin, --text, or a file path.")

    if args.debug:
        os.environ["SUMMARIZER_DEBUG"] = "1"

    summarizer = get_summarizer()
    if args.format == "text":
        print(TextSummarizer(summarizer.client).summarize(text, count=args.count))
        return

    print(
        jsonlib.dumps(
            JsonSummarizer(summarizer.client).summarize(text, count=args.count),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
