from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

from .models import now_iso


LINK_PATTERN = re.compile(r"""href=["']([^"'#]+)["']""", re.IGNORECASE)


@dataclass(frozen=True)
class LinkRecord:
    url: str
    discovered_at: str


@dataclass(frozen=True)
class LinkMetaRecord:
    url: str
    discovered_at: str
    scraped: bool
    last_scraped_at: str | None
    error_code: str | None
    error_message: str | None
def _normalized_host(host: str) -> str:
    lowered = host.lower().strip()
    if lowered.startswith("www."):
        return lowered[4:]
    return lowered


def extract_internal_links(
    seed_url: str,
    html: str,
    allowed_hosts: set[str] | None = None,
) -> list[LinkRecord]:
    seed_host = _normalized_host(urlparse(seed_url).netloc)
    normalized_allowed_hosts = {
        _normalized_host(host) for host in (allowed_hosts or {seed_host})
    }
    discovered: dict[str, LinkRecord] = {}

    for match in LINK_PATTERN.finditer(html):
        raw_href = match.group(1).strip()
        absolute = urljoin(seed_url, raw_href)
        parsed = urlparse(absolute)

        if parsed.scheme not in {"http", "https"}:
            continue
        if _normalized_host(parsed.netloc) not in normalized_allowed_hosts:
            continue

        normalized = parsed._replace(fragment="").geturl()
        discovered.setdefault(normalized, LinkRecord(url=normalized, discovered_at=now_iso()))

    return sorted(discovered.values(), key=lambda item: item.url)


def write_links(path: Path, links: list[LinkRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(asdict(link), ensure_ascii=True) for link in links]
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def normalize_links(
    links: list[LinkRecord],
    normalizer: Callable[[str], str],
) -> list[LinkRecord]:
    discovered: dict[str, LinkRecord] = {}
    for link in links:
        normalized_url = normalizer(link.url)
        existing = discovered.get(normalized_url)
        discovered_at = link.discovered_at if existing is None else min(
            existing.discovered_at,
            link.discovered_at,
        )
        discovered[normalized_url] = LinkRecord(
            url=normalized_url,
            discovered_at=discovered_at,
        )
    return sorted(discovered.values(), key=lambda item: item.url)


def read_links(path: Path) -> list[LinkRecord]:
    links: list[LinkRecord] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        item = json.loads(line)
        links.append(
            LinkRecord(
                url=item["url"],
                discovered_at=str(item["discovered_at"]),
            )
        )
    return links


def mark_link_scraped(path: Path, target_url: str) -> None:
    return None


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []

    records: list[dict[str, object]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def read_link_meta(path: Path) -> list[LinkMetaRecord]:
    records: list[LinkMetaRecord] = []
    for item in _read_jsonl(path):
        records.append(
            LinkMetaRecord(
                url=str(item["url"]),
                discovered_at=str(item["discovered_at"]),
                scraped=bool(item["scraped"]),
                last_scraped_at=(
                    None
                    if item.get("last_scraped_at") is None
                    else str(item["last_scraped_at"])
                ),
                error_code=None
                if item.get("error_code") is None
                else str(item["error_code"]),
                error_message=(
                    None
                    if item.get("error_message") is None
                    else str(item["error_message"])
                ),
            )
        )
    return records


def write_link_meta(path: Path, records: list[LinkMetaRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(asdict(record), ensure_ascii=True) for record in records]
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def _index_link_meta(records: list[LinkMetaRecord]) -> dict[str, LinkMetaRecord]:
    return {record.url: record for record in records}


def ensure_link_meta_records(
    existing_records: list[LinkMetaRecord],
    discovered_urls: list[str],
) -> list[LinkMetaRecord]:
    existing_by_url = _index_link_meta(existing_records)
    updated = list(existing_records)
    for url in discovered_urls:
        if url in existing_by_url:
            continue
        updated.append(
            LinkMetaRecord(
                url=url,
                discovered_at=now_iso(),
                scraped=False,
                last_scraped_at=None,
                error_code=None,
                error_message=None,
            )
        )
    return sorted(updated, key=lambda item: item.url)


def update_link_meta_record(
    records: list[LinkMetaRecord],
    target_url: str,
    *,
    scraped: bool,
    error_code: str | None = None,
    error_message: str | None = None,
) -> list[LinkMetaRecord]:
    updated: list[LinkMetaRecord] = []
    attempt_time = now_iso()
    for record in records:
        if record.url != target_url:
            updated.append(record)
            continue
        updated.append(
            LinkMetaRecord(
                url=record.url,
                discovered_at=record.discovered_at,
                scraped=scraped,
                last_scraped_at=attempt_time,
                error_code=error_code if not scraped else None,
                error_message=error_message if not scraped else None,
            )
        )
    return sorted(updated, key=lambda item: item.url)


def link_meta_map(records: list[LinkMetaRecord]) -> dict[str, LinkMetaRecord]:
    return _index_link_meta(records)


def page_output_name(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"{digest}.html"
