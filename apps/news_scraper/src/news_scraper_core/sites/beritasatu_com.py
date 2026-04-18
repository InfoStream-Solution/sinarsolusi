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

    def _node_attr(self, node: object | None, name: str) -> str:
        if node is None:
            return ""
        attrs = getattr(node, "attrs", None) or {}
        value = attrs.get(name)
        if value is None:
            return ""
        return self._clean_text(str(value))

    def _looks_like_published_at(self, value: str) -> bool:
        if not value:
            return False
        if not any(ch.isdigit() for ch in value):
            return False
        return True

    def _extract_attr_from_raw_html(
        self,
        html: str,
        *,
        tag: str,
        attr_name: str,
        attr_value: str | None = None,
        value_attr: str,
    ) -> str | None:
        pattern = re.compile(rf"<{tag}\b[^>]*>", re.IGNORECASE | re.DOTALL)
        attr_pattern = re.compile(
            rf"{attr_name}\s*=\s*([\"'])(?P<value>.*?)\1",
            re.IGNORECASE | re.DOTALL,
        )
        value_pattern = (
            re.compile(
                rf"{value_attr}\s*=\s*([\"'])(?P<value>.*?)\1",
                re.IGNORECASE | re.DOTALL,
            )
            if value_attr
            else None
        )

        for match in pattern.finditer(html):
            tag_html = match.group(0)
            attr_match = attr_pattern.search(tag_html)
            if attr_match is None:
                continue
            if attr_value is not None and attr_match.group("value") != attr_value:
                continue
            if value_pattern is None:
                return self._clean_text(attr_match.group("value"))
            value_match = value_pattern.search(tag_html)
            if value_match is not None:
                return self._clean_text(value_match.group("value"))
        return None

    def _extract_text_from_raw_html(
        self,
        html: str,
        *,
        tag: str,
        class_name: str,
    ) -> str | None:
        pattern = re.compile(
            rf"<{tag}\b[^>]*class\s*=\s*([\"'])[^\"']*\b{re.escape(class_name)}\b[^\"']*\1[^>]*>(?P<value>.*?)</{tag}>",
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(html):
            value = re.sub(r"<[^>]+>", " ", match.group("value"))
            value = self._clean_text(value)
            if self._looks_like_published_at(value):
                return value
        return None

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

    def _extract_published_at(self, html: str, root: justhtml.Document) -> str | None:
        text_selectors = [
            "body > main > div > div > div.col > div.row.mb-4 > div.col.ps-0 > small > span",
            "body > main > div > div > div.col > small",
            "small.text-muted",
            "div.article__date",
            "div.article__date-info",
            "div.article__meta",
            "time",
        ]
        for selector in text_selectors:
            for node in root.query(selector):
                rendered = self._node_text(node)
                if self._looks_like_published_at(rendered):
                    return rendered

        attr_selectors = [
            ("meta[property='article:published_time']", "content"),
            ("meta[name='article:published_time']", "content"),
            ("meta[property='datePublished']", "content"),
            ("meta[itemprop='datePublished']", "content"),
            ("time[datetime]", "datetime"),
        ]
        for selector, attr_name in attr_selectors:
            for node in root.query(selector):
                rendered = self._node_attr(node, attr_name)
                if self._looks_like_published_at(rendered):
                    return rendered

        raw_html_fallbacks = [
            ("span", "text-muted"),
            ("small", "text-muted"),
            ("meta", "property", "article:published_time", "content"),
            ("meta", "name", "article:published_time", "content"),
            ("meta", "property", "datePublished", "content"),
            ("meta", "itemprop", "datePublished", "content"),
            ("time", "datetime", None, "datetime"),
        ]
        for tag, class_name in raw_html_fallbacks[:2]:
            rendered = self._extract_text_from_raw_html(
                html,
                tag=tag,
                class_name=class_name,
            )
            if rendered:
                return rendered
        for tag, attr_name, attr_value, value_attr in raw_html_fallbacks[2:]:
            rendered = self._extract_attr_from_raw_html(
                html,
                tag=tag,
                attr_name=attr_name,
                attr_value=attr_value,
                value_attr=value_attr,
            )
            if self._looks_like_published_at(rendered or ""):
                return rendered
        return None

    def _extract_author(self, root: justhtml.Document) -> str | None:
        selectors = [
            "body > main > div > div > div.col > div.row.mb-4 > div.col.ps-0 > span",
            "div.my-auto.small",
            "div.article__author",
            "div.article__author-name",
            "span.article__author",
            "span.b1-text-navy",
            "div.article__meta",
        ]
        for selector in selectors:
            nodes = list(root.query(selector))
            if not nodes:
                node = root.query_one(selector)
                nodes = [node] if node is not None else []
            for node in nodes:
                rendered = self._node_text(node)
                if not rendered:
                    continue
                if "Penulis:" in rendered:
                    rendered = rendered.split("Penulis:", 1)[1].strip()
                    if "|" in rendered:
                        rendered = rendered.split("|", 1)[0].strip()
                    return rendered
                if " | " in rendered:
                    rendered = rendered.split(" | ", 1)[0]
                if rendered != "BACA JUGA":
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
        published_at = self._extract_published_at(html, root)
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
