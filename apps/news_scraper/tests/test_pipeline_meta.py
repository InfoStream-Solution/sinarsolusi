from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import news_scraper_core.extract_news as extract_news
import news_scraper_core.seed as seed
from news_scraper_core.config import Settings
from news_scraper_core.links import LinkRecord
from news_scraper_core.links import read_links
from news_scraper_core.models import ParsedContent


class DummySeedSite:
    domain = "example.com"
    start_url = "https://example.com"
    link_allowed_hosts = {"example.com"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def scrape(self):
        return SimpleNamespace(
            content="""
            <a href="https://example.com/news/a">A</a>
            <a href="https://example.com/news/b">B</a>
            """,
        )

    def is_article_url(self, url: str) -> bool:
        return "/news/" in url

    def normalize_article_url(self, url: str) -> str:
        return url.split("?", 1)[0]

    def normalize_url(self, url: str) -> str:
        return url

    @property
    def output_path(self) -> Path:
        return self.settings.seed_dir / f"{self.domain}.seed"


class DummyExtractSite(DummySeedSite):
    def scrape_article(self, url: str) -> None:
        path = self.scraped_article_output_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        if "fail" in url:
            raise RuntimeError("boom")
        path.write_text("<html>article</html>", encoding="utf-8")

    def scraped_article_output_path(self, url: str) -> Path:
        slug = url.rsplit("/", 1)[-1]
        return self.settings.scraped_dir / self.domain / "article_html" / f"{slug}.html"

    def parse_article(self, html: str, url: str) -> ParsedContent:
        slug = url.rsplit("/", 1)[-1]
        return ParsedContent(
            content_type="news_article",
            title=slug,
            url=url,
            source_site=self.domain,
            category=None,
            published_at=None,
            author=None,
            summary=None,
            content="Body text",
            word_count=2,
            char_count=9,
            scraped_at="2026-04-11T00:00:00+07:00",
        )

    def save_parsed_article(self, article: ParsedContent, url: str) -> Path:
        output_path = (
            self.settings.content_dir
            / "news_article"
            / self.domain
            / (f"{url.rsplit('/', 1)[-1]}.json")
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(article.to_json(), encoding="utf-8")
        output_path.with_suffix(".md").write_text(
            article.to_markdown(), encoding="utf-8"
        )
        return output_path

    def article_output_path(self, url: str) -> Path:
        return (
            self.settings.content_dir
            / "news_article"
            / self.domain
            / (f"{url.rsplit('/', 1)[-1]}.json")
        )

    def scraped_article_dir(self) -> Path:
        return self.settings.scraped_dir / self.domain / "article_html"

    def article_markdown_output_path(self, url: str) -> Path:
        return (
            self.settings.content_dir
            / "news_article"
            / self.domain
            / (f"{url.rsplit('/', 1)[-1]}.md")
        )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        store_database_url=f"sqlite:///{tmp_path / 'news_scraper.db'}",
        seed_dir=tmp_path / "seed",
        links_dir=tmp_path / "links",
        scraped_dir=tmp_path / "scraped",
        content_dir=tmp_path / "content",
        kbt_api_base_url="http://example.test",
        kbt_api_token="token",
        scraper_debug=False,
        keep_seed=False,
        keep_scraped=False,
    )


def test_seed_populates_meta_and_preserves_existing_scraped_state(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(seed, "get_settings", lambda: settings)
    monkeypatch.setattr(seed, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        seed,
        "get_logger",
        lambda name: SimpleNamespace(info=lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        seed, "load_site", lambda domain, settings: DummySeedSite(settings)
    )
    monkeypatch.setattr(
        seed,
        "_register_discovered_hosts",
        lambda domain, hosts: {"created": 0, "skipped": len(hosts)},
    )
    monkeypatch.setattr(seed, "_load_additional_allowed_hosts", lambda domain: set())
    monkeypatch.setattr(
        seed,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="example.com", keep_seed=True)
        ),
    )

    seed.main()

    links = read_links(settings.links_dir / "example.com.jsonl")

    assert [link.url for link in links] == [
        "https://example.com/news/a",
        "https://example.com/news/b",
    ]
    assert all(link.discovered_at for link in links)


def test_seed_merges_additional_allowed_hosts(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class HostAwareSeedSite(DummySeedSite):
        link_allowed_hosts = {"example.com"}

    monkeypatch.setattr(seed, "get_settings", lambda: settings)
    monkeypatch.setattr(seed, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        seed,
        "get_logger",
        lambda name: SimpleNamespace(info=lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        seed, "load_site", lambda domain, settings: HostAwareSeedSite(settings)
    )
    monkeypatch.setattr(
        seed, "_load_additional_allowed_hosts", lambda domain: {"news.example.com"}
    )
    monkeypatch.setattr(
        seed,
        "_register_discovered_hosts",
        lambda domain, hosts: (
            captured.__setitem__("registered_hosts", set(hosts))
            or {"created": len(hosts), "skipped": 0}
        ),
    )
    monkeypatch.setattr(seed, "write_links", lambda path, links: None)
    monkeypatch.setattr(seed, "normalize_links", lambda links, normalizer: links)
    monkeypatch.setattr(
        seed,
        "extract_domain_links",
        lambda seed_url, html: [
            LinkRecord(
                url="https://example.com/news/a",
                discovered_at="2026-04-11T00:00:00+07:00",
            ),
            LinkRecord(
                url="https://news.example.com/news/b",
                discovered_at="2026-04-11T00:00:00+07:00",
            ),
        ],
    )
    monkeypatch.setattr(
        seed,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="example.com", keep_seed=True)
        ),
    )

    seed.main()

    assert captured["registered_hosts"] == {"example.com", "news.example.com"}


def test_extract_news_updates_meta_on_success_and_failure(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(extract_news, "get_settings", lambda: settings)
    monkeypatch.setattr(extract_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        extract_news,
        "get_logger",
        lambda name: SimpleNamespace(
            info=lambda *args, **kwargs: None, exception=lambda *args, **kwargs: None
        ),
    )
    monkeypatch.setattr(
        extract_news, "load_site", lambda domain, settings: DummyExtractSite(settings)
    )
    monkeypatch.setattr(
        extract_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                domain="example.com", limit=0, keep_scraped=True
            )
        ),
    )

    links_path = settings.links_dir / "example.com.jsonl"
    links_path.parent.mkdir(parents=True, exist_ok=True)
    links_path.write_text(
        "\n".join(
            [
                '{"url":"https://example.com/news/a","discovered_at":"2026-04-11T00:00:00+07:00"}',
                '{"url":"https://example.com/news/fail","discovered_at":"2026-04-11T00:00:00+07:00"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    extract_news.main()

    assert (settings.content_dir / "news_article" / "example.com" / "a.json").exists()
    assert (settings.content_dir / "news_article" / "example.com" / "a.md").exists()
    assert (
        settings.content_dir / "errors" / "example.com" / "extract-news.jsonl"
    ).exists()


def test_extract_news_skips_existing_parsed_articles(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SkipOnScrapeSite(DummyExtractSite):
        def scrape_article(self, url: str) -> None:
            raise AssertionError(
                "scrape_article should not be called for existing output"
            )

    monkeypatch.setattr(extract_news, "get_settings", lambda: settings)
    monkeypatch.setattr(extract_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        extract_news,
        "get_logger",
        lambda name: SimpleNamespace(
            info=lambda *args, **kwargs: None, exception=lambda *args, **kwargs: None
        ),
    )
    monkeypatch.setattr(
        extract_news, "load_site", lambda domain, settings: SkipOnScrapeSite(settings)
    )
    monkeypatch.setattr(
        extract_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                domain="example.com", limit=0, keep_scraped=True
            )
        ),
    )

    existing_json = settings.content_dir / "news_article" / "example.com" / "a.json"
    existing_json.parent.mkdir(parents=True, exist_ok=True)
    existing_json.write_text("{}", encoding="utf-8")
    existing_json.with_suffix(".md").write_text("# existing", encoding="utf-8")

    links_path = settings.links_dir / "example.com.jsonl"
    links_path.parent.mkdir(parents=True, exist_ok=True)
    links_path.write_text(
        "\n".join(
            [
                '{"url":"https://example.com/news/a","discovered_at":"2026-04-11T00:00:00+07:00"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    extract_news.main()

    assert existing_json.exists()
    assert existing_json.with_suffix(".md").exists()
