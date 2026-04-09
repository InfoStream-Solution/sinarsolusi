from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from nscraper import HttpScraper, ScrapeOptions
from urllib.parse import urlparse

from ..config import Settings
from ..models import ParsedContent, now_iso
from ..paths import parsed_articles_dir, scraped_articles_dir, seed_file_path
from ..utils import LogMixin


DEFAULT_HEADERS = {
    "Accept": "text/html",
    "User-Agent": "Mozilla/5.0 (compatible; news-scraper/0.1; +https://sinarsolusi.com)",
}


@dataclass
class BaseSite(LogMixin):
    settings: Settings
    start_url: str
    domain: str
    allowed_hosts: set[str] = field(default_factory=set)
    article_path_patterns: tuple[re.Pattern[str], ...] = ()
    default_nscrape_options: dict[str, object] = field(
        default_factory=lambda: {
            "transform": "basic",
            "pretty": True,
            "headers": "default",
        }
    )

    @property
    def output_path(self):
        return seed_file_path(self.settings.seed_dir, self.domain)

    @property
    def logger_name(self) -> str:
        return f"site.{self.domain}"

    @property
    def link_allowed_hosts(self) -> set[str]:
        return self.allowed_hosts or {self.domain}

    def build_options(self) -> ScrapeOptions:
        return ScrapeOptions(
            url=self.start_url,
            output_path=str(self.output_path),
            **self.default_nscrape_options,
        )

    def scrape(self):
        self.settings.seed_dir.mkdir(parents=True, exist_ok=True)
        options = self.build_options()
        self.log_event(
            20,
            "seed_scrape_start",
            domain=self.domain,
            start_url=self.start_url,
            output_path=str(self.output_path),
            headers=self.default_nscrape_options.get("headers"),
            transform=self.default_nscrape_options.get("transform"),
            pretty=self.default_nscrape_options.get("pretty"),
        )
        scraper = HttpScraper(options)
        result = scraper.scrape()
        network = getattr(result, "network", None)
        request = getattr(network, "request", None)
        request_headers = getattr(request, "headers", None)
        self.log_event(
            20,
            "seed_scrape_result",
            domain=self.domain,
            result_type=type(result).__name__,
            request_headers=request_headers,
        )
        self.log_event(
            20,
            "seed_scrape_done",
            domain=self.domain,
            output_path=str(self.output_path),
        )
        return result

    def is_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return any(pattern.match(parsed.path) for pattern in self.article_path_patterns)

    def normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed._replace(fragment="").geturl()

    def normalize_article_url(self, url: str) -> str:
        return self.normalize_url(url)

    def article_slug(self, url: str) -> str:
        normalized_url = self.normalize_article_url(url)
        path = urlparse(normalized_url).path.rstrip("/")
        slug = path.split("/")[-1] or "article"
        return slug

    def article_output_dir(self) -> Path:
        return parsed_articles_dir(self.settings.content_dir, self.domain)

    def scraped_article_dir(self) -> Path:
        return scraped_articles_dir(self.settings.scraped_dir, self.domain)

    def scraped_article_output_path(self, url: str) -> Path:
        return self.scraped_article_dir() / f"{self.article_slug(url)}.html"

    def article_output_path(self, url: str) -> Path:
        return self.article_output_dir() / f"{self.article_slug(url)}.json"

    def article_markdown_output_path(self, url: str) -> Path:
        return self.article_output_dir() / f"{self.article_slug(url)}.md"

    def build_article_options(self, url: str) -> ScrapeOptions:
        article_url = self.normalize_article_url(url)
        return ScrapeOptions(
            url=article_url,
            output_path=str(self.scraped_article_output_path(article_url)),
            **self.default_nscrape_options,
        )

    def scrape_article(self, url: str):
        normalized_url = self.normalize_article_url(url)
        self.scraped_article_dir().mkdir(parents=True, exist_ok=True)
        output_path = self.scraped_article_output_path(normalized_url)
        self.log_event(
            20,
            "article_scrape_start",
            domain=self.domain,
            url=normalized_url,
            output_path=str(output_path),
        )
        scraper = HttpScraper(self.build_article_options(normalized_url))
        result = scraper.scrape()
        network = getattr(result, "network", None)
        request = getattr(network, "request", None)
        request_headers = getattr(request, "headers", None)
        self.log_event(
            20,
            "article_scrape_result",
            domain=self.domain,
            url=normalized_url,
            result_type=type(result).__name__,
            request_headers=request_headers,
        )
        self.log_event(
            20,
            "article_scrape_done",
            domain=self.domain,
            url=normalized_url,
            output_path=str(output_path),
        )
        return result

    def parse_article(self, html: str, url: str) -> ParsedContent:
        raise NotImplementedError

    def save_parsed_article(self, article: ParsedContent, url: str) -> Path:
        self.article_output_dir().mkdir(parents=True, exist_ok=True)
        output_path = self.article_output_path(url)
        markdown_path = self.article_markdown_output_path(url)
        output_path.write_text(article.to_json(), encoding="utf-8")
        markdown_path.write_text(article.to_markdown(), encoding="utf-8")
        self.log_event(
            20,
            "article_write_done",
            domain=self.domain,
            url=url,
            json_path=str(output_path),
            markdown_path=str(markdown_path),
        )
        return output_path

    def default_parsed_content(
        self,
        *,
        title: str,
        url: str,
        category: str | None,
        author: str | None,
        published_at: str | None,
        summary: str | None,
        content: str,
        content_type: str = "news_article",
    ) -> ParsedContent:
        normalized_content = content.strip()
        return ParsedContent(
            content_type=content_type,
            title=title,
            url=url,
            source_site=self.domain,
            category=category,
            published_at=published_at,
            author=author,
            summary=summary,
            content=normalized_content,
            word_count=len(normalized_content.split()),
            char_count=len(normalized_content),
            scraped_at=now_iso(),
        )
