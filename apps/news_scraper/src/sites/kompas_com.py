from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlencode, urlparse

import justhtml

from ..models import ParsedContent
from ..config import Settings

from .base import BaseSite


ARTICLE_PATH_PATTERNS = (
    re.compile(r"^/[^/]+/read/\d{4}/\d{2}/\d{2}/\d+/[^/]+$"),
)
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

    def _clean_text(self, value: str) -> str:
        return WHITESPACE_PATTERN.sub(" ", value).strip()

    def _node_text(self, node: object | None) -> str:
        if node is None:
            return ""
        to_text = getattr(node, "to_text", None)
        if callable(to_text):
            text = to_text(separator=" ", separator_blocks_only=True)
            return self._clean_text(text)
        return ""

    def normalize_article_url(self, url: str) -> str:
        normalized = self.normalize_url(url)
        parsed = urlparse(normalized)
        query = urlencode([("page", "all")], doseq=True)
        return parsed._replace(query=query).geturl()

    def _parse_document(self, html: str) -> justhtml.Document:
        return justhtml.JustHTML(html).root

    def _extract_title(self, root: justhtml.Document, url: str) -> str:
        title = self._node_text(root.query_one("h1.read__title"))
        if title:
            return title
        return self.article_slug(url).replace("-", " ")

    def _extract_category(self, root: justhtml.Document) -> str | None:
        breadcrumbs = [self._node_text(node) for node in root.query("div.breadcrumb li a.breadcrumb__link")]
        breadcrumbs = [item for item in breadcrumbs if item]
        if len(breadcrumbs) >= 2:
            return breadcrumbs[-1]
        return None

    def _extract_published_at(self, root: justhtml.Document) -> str | None:
        rendered = self._node_text(root.query_one("div.read__time"))
        if not rendered:
            return None
        if "," in rendered:
            _, published_at = rendered.split(",", 1)
            return published_at.strip()
        return rendered or None

    def _extract_author(self, root: justhtml.Document) -> str | None:
        role = self._node_text(root.query_one(".credit-title p")).lower()
        if role == "penulis":
            name = self._node_text(root.query_one(".credit-title-nameEditor"))
            if name:
                return name
        return None

    def _should_skip_item(self, text: str) -> bool:
        if not text:
            return True
        if text.startswith("Baca juga:"):
            return True
        if "Gabung KOMPAS.com Plus sekarang" in text:
            return True
        if text == "Tim Redaksi":
            return True
        if text.startswith("Copyright "):
            return True
        return False

    def _normalize_content_items(self, items: list[str]) -> list[str]:
        if not items:
            return items
        first = items[0]
        if first.startswith("KOMPAS.com - "):
            items[0] = first.removeprefix("KOMPAS.com - ").strip()
        return items

    def _extract_content_items(self, root: justhtml.Document) -> list[str]:
        content_root = root.query_one("div.read__content")
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
            if node_name not in {"p", "h2", "h3"}:
                continue

            text = self._node_text(node)
            if self._should_skip_item(text):
                continue
            items.append(text)

        return self._normalize_content_items(items)

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
