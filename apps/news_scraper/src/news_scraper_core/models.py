from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime


@dataclass(frozen=True)
class ParsedContent:
    content_type: str
    title: str
    url: str
    source_site: str
    category: str | None
    published_at: str | None
    author: str | None
    summary: str | None
    content: str
    word_count: int
    char_count: int
    scraped_at: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    def to_markdown(self) -> str:
        lines = [f"# {self.title}", ""]

        metadata: list[tuple[str, str | None]] = [
            ("URL", self.url),
            ("Source Site", self.source_site),
            ("Content Type", self.content_type),
            ("Category", self.category),
            ("Published At", self.published_at),
            ("Author", self.author),
            ("Word Count", str(self.word_count)),
            ("Character Count", str(self.char_count)),
            ("Scraped At", self.scraped_at),
        ]
        for label, value in metadata:
            if value:
                lines.append(f"- **{label}**: {value}")

        if self.summary:
            lines.extend(["", "## Summary", "", self.summary])

        lines.extend(["", "## Content", "", self.content.strip()])
        lines.append("")
        return "\n".join(lines)


def now_iso() -> str:
    """Return the current UTC time in ISO 8601 format."""

    return datetime.now(UTC).isoformat()
