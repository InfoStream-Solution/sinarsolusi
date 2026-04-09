from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse


LINK_PATTERN = re.compile(r"""href=["']([^"'#]+)["']""", re.IGNORECASE)


@dataclass(frozen=True)
class LinkRecord:
    url: str
    scraped: bool


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
        discovered.setdefault(normalized, LinkRecord(url=normalized, scraped=False))

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
    normalizer: callable,
) -> list[LinkRecord]:
    discovered: dict[str, LinkRecord] = {}
    for link in links:
        normalized_url = normalizer(link.url)
        existing = discovered.get(normalized_url)
        scraped = link.scraped if existing is None else (existing.scraped or link.scraped)
        discovered[normalized_url] = LinkRecord(url=normalized_url, scraped=scraped)
    return sorted(discovered.values(), key=lambda item: item.url)


def read_links(path: Path) -> list[LinkRecord]:
    links: list[LinkRecord] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        item = json.loads(line)
        links.append(LinkRecord(url=item["url"], scraped=bool(item["scraped"])))
    return links


def mark_link_scraped(path: Path, target_url: str) -> None:
    links = read_links(path)
    updated = [
        LinkRecord(url=link.url, scraped=True if link.url == target_url else link.scraped)
        for link in links
    ]
    write_links(path, updated)


def page_output_name(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"{digest}.html"
