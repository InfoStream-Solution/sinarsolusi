from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import parse_qsl, urlencode, urlparse

import justhtml

from ..config import Settings
from ..models import ParsedContent
from .base import BaseSite


ARTICLE_PATH_PATTERNS = (
    re.compile(r"^/[a-z-]+/\d+/.+$"),
    re.compile(r"^/network/[a-z0-9-]+/\d+/.+$"),
)
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass
class BeritasatuComSite(BaseSite):
    settings: Settings

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            settings=settings,
            domain="beritasatu.com",
            start_url="https://www.beritasatu.com",
            allowed_hosts={
                "beritasatu.com",
                "www.beritasatu.com",
                "news.beritasatu.com",
                "sport.beritasatu.com",
                "finance.beritasatu.com",
                "bisnis.beritasatu.com",
                "megapolitan.beritasatu.com",
                "jakarta.beritasatu.com",
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
            if key == "page"
        ]
        if ("page", "all") not in query_items:
            query_items = [("page", "all")]
        query = urlencode(query_items, doseq=True)
        return parsed._replace(query=query).geturl()

    def _parse_document(self, html: str) -> justhtml.Document:
        return justhtml.JustHTML(html).root

    def _extract_title(self, root: justhtml.Document, url: str) -> str:
        selectors = [
            "h1",
            "h1.article__title",
            "h1.read__title",
            "h1.detail__title",
        ]
        for selector in selectors:
            title = self._node_text(root.query_one(selector))
            if title:
                return title
        return self.article_slug(url).replace("-", " ")

    def _extract_category(self, root: justhtml.Document) -> str | None:
        selectors = [
            "a.breadcrumb__link",
            "nav.breadcrumb a",
            "div.breadcrumb a",
        ]
        for selector in selectors:
            nodes = [self._node_text(node) for node in root.query(selector)]
            nodes = [item for item in nodes if item]
            if nodes:
                return nodes[-1]
        return None

    def _category_from_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parts and not parts[0].isdigit() and parts[0] != "network":
            return parts[0].replace("-", " ").title()
        return None

    def _extract_published_at(self, root: justhtml.Document) -> str | None:
        selectors = [
            "small.text-muted",
            "div.article__date",
            "div.article__date-info",
            "div.article__meta",
            "time",
        ]
        for selector in selectors:
            rendered = self._node_text(root.query_one(selector))
            if rendered:
                return rendered
        return None

    def _extract_author(self, root: justhtml.Document) -> str | None:
        selectors = [
            "div.my-auto.small",
            "div.article__author",
            "div.article__author-name",
            "span.article__author",
            "div.article__meta",
        ]
        for selector in selectors:
            rendered = self._node_text(root.query_one(selector))
            if not rendered:
                continue
            if "Penulis:" in rendered:
                rendered = rendered.split("Penulis:", 1)[1].strip()
                if "|" in rendered:
                    rendered = rendered.split("|", 1)[0].strip()
                return rendered
            if " | " in rendered:
                rendered = rendered.split(" | ", 1)[0]
            return rendered
        return None

    def _should_skip_item(self, text: str) -> bool:
        if not text:
            return True
        if text == "ADVERTISEMENT":
            return True
        if text == "BACA JUGA":
            return True
        if text.startswith("BACA SELENGKAPNYA"):
            return True
        if text.startswith("Bagikan"):
            return True
        if text.startswith("URL berhasil di salin"):
            return True
        if text.startswith("Image:"):
            return True
        if text.startswith("Sumber :"):
            return True
        return False

    def _should_skip_node(self, node: object) -> bool:
        current = node
        while current is not None:
            class_name = str(getattr(current, "attrs", {}).get("class", ""))
            if "b1-group" in class_name:
                return True
            current = getattr(current, "parent", None)
        return False

    def _extract_content_items(self, root: justhtml.Document) -> list[str]:
        selectors = [
            "div.b1-article.body-content",
            "div.article__body",
            "div.article__content",
            "div.read__content",
            "div.detail__body-text",
        ]
        content_root = None
        for selector in selectors:
            content_root = root.query_one(selector)
            if content_root is not None:
                break
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
            if node_name != "p":
                continue
            if self._should_skip_node(node):
                continue

            text = self._node_text(node)
            if self._should_skip_item(text):
                continue
            if text.startswith("Jakarta, Beritasatu.com –"):
                text = text.removeprefix("Jakarta, Beritasatu.com –").strip()
            items.append(text)

        return items

    def parse_article(self, html: str, url: str) -> ParsedContent:
        root = self._parse_document(html)
        title = self._extract_title(root, url)
        category = self._extract_category(root) or self._category_from_url(url)
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
