from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from nscraper import HttpScraper, ScrapeOptions


@dataclass(frozen=True)
class ScrapeResult:
    url: str
    scraped_at: str
    output_file: str
    content_length: int


def fetch_content(url: str, headers: dict[str, str] | None = None) -> str:
    options = ScrapeOptions(
        url=url,
        headers=headers or {"Accept": "text/html"},
    )
    return HttpScraper(options).scrape()


def run_scrape(url: str, output_path: Path, headers: dict[str, str] | None = None) -> ScrapeResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = fetch_content(url=url, headers=headers)

    payload = {
        "url": url,
        "scraped_at": datetime.now(UTC).isoformat(),
        "content": content,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = ScrapeResult(
        url=url,
        scraped_at=payload["scraped_at"],
        output_file=str(output_path),
        content_length=len(content),
    )
    return result


def format_result(result: ScrapeResult) -> str:
    rendered = asdict(result)
    return json.dumps(rendered, indent=2)
