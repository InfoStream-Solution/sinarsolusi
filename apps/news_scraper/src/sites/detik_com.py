from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import parse_qsl, urlencode, urlparse

import justhtml

from ..config import Settings
from ..models import ParsedContent
from .base import BaseSite


ARTICLE_PATH_PATTERNS = (
    re.compile(r"^/[^/]+/(?:berita|edu|jabar|jateng|jatim|jogja|oto|sport|travel|food|health|finance|hot|inet|wolipop)/d-\d+/.+$"),
    re.compile(r"^/(?:berita|edu|jabar|jateng|jatim|jogja|oto|sport|travel|food|health|finance|hot|inet|wolipop)/d-\d+/.+$"),
)
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass
class DetikComSite(BaseSite):
    settings: Settings

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings=settings,
            domain="detik.com",
            start_url="https://detik.com",
            allowed_hosts={
                "detik.com",
                "www.detik.com",
                "news.detik.com",
                "finance.detik.com",
                "inet.detik.com",
                "hot.detik.com",
                "sport.detik.com",
                "oto.detik.com",
                "travel.detik.com",
                "food.detik.com",
                "health.detik.com",
                "wolipop.detik.com",
                "edukasi.detik.com",
                "jabar.detik.com",
                "jateng.detik.com",
                "jatim.detik.com",
                "jogja.detik.com",
                "detik.com",
            },
            article_path_patterns=ARTICLE_PATH_PATTERNS,
        )

    def _clean_text(self, value: str) -> str:
        return WHITESPACE_PATTERN.sub(" ", value).strip()

    def _node_text(self, node: object | None) -> str:
        if node is None:
            return ""
        to_text = getattr(node, "to_text", None)
        if callable(to_text):
            return self._clean_text(to_text(separator=" ", separator_blocks_only=True))
        return ""

    def normalize_article_url(self, url: str) -> str:
        normalized = self.normalize_url(url)
        parsed = urlparse(normalized)
        query_items = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key in {"page"}
        ]
        if ("page", "all") not in query_items:
            query_items = [("page", "all")]
        query = urlencode(query_items, doseq=True)
        return parsed._replace(query=query).geturl()

    def _parse_document(self, html: str) -> justhtml.Document:
        return justhtml.JustHTML(html).root

    def _extract_title(self, root: justhtml.Document, url: str) -> str:
        title = self._node_text(root.query_one("h1.detail__title"))
        if title:
            return title
        return self.article_slug(url).replace("-", " ")

    def _extract_category(self, root: justhtml.Document) -> str | None:
        breadcrumb = self._node_text(root.query_one("a.breadcrumb__link"))
        return breadcrumb or None

    def _extract_published_at(self, root: justhtml.Document) -> str | None:
        candidates = [
            "div.detail__date",
            "div.detail__date-time",
            "div.detail__dateinfo",
            "div.detail__date__wrap",
        ]
        for selector in candidates:
            rendered = self._node_text(root.query_one(selector))
            if rendered:
                return rendered
        return None

    def _extract_author(self, root: justhtml.Document) -> str | None:
        candidates = [
            "div.detail__author",
            "div.detail__author a",
            "span.detail__author",
        ]
        for selector in candidates:
            author = self._node_text(root.query_one(selector))
            if author:
                return author
        return None

    def _extract_content_items(self, root: justhtml.Document) -> list[str]:
        content_root = root.query_one("div.detail__body-text")
        if content_root is None:
            content_root = root.query_one("div.itp_bodycontent")
        if content_root is None:
            return []

        items: list[str] = []
        stack = list(reversed(getattr(content_root, "children", []) or []))
        while stack:
            node = stack.pop()
            children = getattr(node, "children", None) or []
            if children:
                stack.extend(reversed(children))

            node_name = getattr(node, "name", None)
            if node_name not in {"p", "h2", "h3", "li"}:
                continue

            text = self._node_text(node)
            if not text:
                continue
            if text.startswith("Baca juga:"):
                continue
            if text.startswith("ADVERTISEMENT"):
                continue
            if text.startswith("SCROLL TO CONTINUE"):
                continue
            if text.startswith("Simak juga"):
                continue
            items.append(text)

        return items

    def parse_article(self, html: str, url: str) -> ParsedContent:
        root = self._parse_document(html)
        title = self._extract_title(root, url)
        category = self._extract_category(root)
        author = self._extract_author(root)
        published_at = self._extract_published_at(root)
        items = self._extract_content_items(root)
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
