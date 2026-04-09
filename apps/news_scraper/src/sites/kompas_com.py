from __future__ import annotations

from dataclasses import dataclass
import re
from html import unescape
from urllib.parse import urlencode, urlparse

from ..models import ParsedContent
from ..config import Settings

from .base import BaseSite


ARTICLE_PATH_PATTERNS = (
    re.compile(r"^/[^/]+/read/\d{4}/\d{2}/\d{2}/\d+/[^/]+$"),
)
TITLE_PATTERN = re.compile(
    r'<h1[^>]*class="[^"]*read__title[^"]*"[^>]*>(.*?)</h1>',
    re.IGNORECASE,
)
CATEGORY_PATTERN = re.compile(
    r'<li[^>]*class="[^"]*breadcrumb__item[^"]*"[^>]*>\s*<a[^>]*class="[^"]*breadcrumb__link[^"]*"[^>]*>(.*?)</a>\s*</li>',
    re.IGNORECASE | re.DOTALL,
)
READ_TIME_PATTERN = re.compile(
    r'<div[^>]*class="[^"]*read__time[^"]*"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
AUTHOR_PATTERN = re.compile(
    r'<div[^>]*class="[^"]*credit-author-name[^"]*"[^>]*>(.*?)</div>\s*'
    r'<div[^>]*class="[^"]*credit-author-position[^"]*"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)
CONTENT_BLOCK_PATTERN = re.compile(
    r'<div[^>]*class="[^"]*read__content[^"]*"[^>]*>\s*<div[^>]*class="[^"]*clearfix[^"]*"[^>]*>(.*?)<div[^>]*class="[^"]*fb-quote[^"]*"',
    re.IGNORECASE | re.DOTALL,
)
CONTENT_ITEM_PATTERN = re.compile(
    r"<(p|h2|h3)\b[^>]*>(.*?)</\1>",
    re.IGNORECASE | re.DOTALL,
)
TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass
class KompasComSite(BaseSite):
    settings: Settings

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings=settings,
            domain="kompas.com",
            start_url="https://kompas.com",
            allowed_hosts={
                "kompas.com",
                "www.kompas.com",
                "news.kompas.com",
                "tekno.kompas.com",
                "otomotif.kompas.com",
                "bola.kompas.com",
                "money.kompas.com",
                "news.kompas.com",
                "edukasi.kompas.com",
                "megapolitan.kompas.com",
                "nasional.kompas.com"
            },
            article_path_patterns=ARTICLE_PATH_PATTERNS,
        )

    def _clean_html_text(self, value: str) -> str:
        stripped = TAG_PATTERN.sub(" ", value)
        stripped = unescape(stripped)
        stripped = WHITESPACE_PATTERN.sub(" ", stripped).strip()
        return stripped

    def normalize_article_url(self, url: str) -> str:
        normalized = self.normalize_url(url)
        parsed = urlparse(normalized)
        query = urlencode([("page", "all")], doseq=True)
        return parsed._replace(query=query).geturl()

    def _extract_title(self, html: str, url: str) -> str:
        title_match = TITLE_PATTERN.search(html)
        if title_match:
            return self._clean_html_text(title_match.group(1))
        return self.article_slug(url).replace("-", " ")

    def _extract_category(self, html: str) -> str | None:
        breadcrumbs = [
            self._clean_html_text(match.group(1))
            for match in CATEGORY_PATTERN.finditer(html)
        ]
        if len(breadcrumbs) >= 2:
            return breadcrumbs[-1]
        return None

    def _extract_published_at(self, html: str) -> str | None:
        time_match = READ_TIME_PATTERN.search(html)
        if not time_match:
            return None

        rendered = self._clean_html_text(time_match.group(1))
        if "," in rendered:
            _, published_at = rendered.split(",", 1)
            return published_at.strip()
        return rendered or None

    def _extract_author(self, html: str) -> str | None:
        for match in AUTHOR_PATTERN.finditer(html):
            name = self._clean_html_text(match.group(1))
            role = self._clean_html_text(match.group(2)).lower()
            if role == "penulis" and name:
                return name
        return None

    def _extract_content_items(self, html: str) -> list[str]:
        content_match = CONTENT_BLOCK_PATTERN.search(html)
        if not content_match:
            return []

        body_html = content_match.group(1)
        items: list[str] = []
        for match in CONTENT_ITEM_PATTERN.finditer(body_html):
            tag = match.group(1).lower()
            text = self._clean_html_text(match.group(2))
            if not text:
                continue
            if text.startswith("Baca juga:"):
                continue
            if "Gabung KOMPAS.com Plus sekarang" in text:
                continue
            if text == "Tim Redaksi":
                continue
            if text.startswith("Copyright "):
                continue

            if tag in {"h2", "h3"}:
                items.append(text)
            else:
                items.append(text)

        return items

    def parse_article(self, html: str, url: str) -> ParsedContent:
        title = self._extract_title(html, url)
        category = self._extract_category(html)
        author = self._extract_author(html)
        published_at = self._extract_published_at(html)
        items = self._extract_content_items(html)
        content = "\n\n".join(items)
        summary = items[0] if items else None

        return self.default_parsed_content(
            title=title,
            url=url,
            category=category,
            author=author,
            published_at=published_at,
            summary=summary,
            content=content,
        )
