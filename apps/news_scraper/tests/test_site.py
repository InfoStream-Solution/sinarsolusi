from __future__ import annotations

import re
from pathlib import Path

import pytest

import src.sites.base as base_module
from src.config import Settings
from src.sites.base import BaseSite
from src.sites.kompas_com import KompasComSite


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        seed_dir=tmp_path / "seed",
        links_dir=tmp_path / "links",
        scraped_dir=tmp_path / "scraped",
        content_dir=tmp_path / "content",
        scraper_debug=False,
        keep_seed=False,
        keep_scraped=False,
    )


@pytest.fixture
def base_site(settings: Settings) -> BaseSite:
    return BaseSite(
        settings=settings,
        domain="example.com",
        start_url="https://example.com",
    )


@pytest.fixture
def article_site(settings: Settings) -> BaseSite:
    return BaseSite(
        settings=settings,
        domain="example.com",
        start_url="https://example.com",
        article_path_patterns=(re.compile(r"^/articles/\d+$"),),
    )


def test_base_site_uses_instance_patterns(article_site: BaseSite) -> None:
    assert article_site.is_article_url("https://example.com/articles/123")
    assert not article_site.is_article_url("https://example.com/news/123")


def test_base_site_builds_paths_and_options(base_site: BaseSite, settings: Settings) -> None:
    assert base_site.logger_name == "site.example.com"
    assert base_site.link_allowed_hosts == {"example.com"}
    assert base_site.normalize_url("https://example.com/a#frag") == "https://example.com/a"
    assert base_site.normalize_article_url("https://example.com/a#frag") == "https://example.com/a"
    assert base_site.article_slug("https://example.com/articles/deep-dive/") == "deep-dive"
    assert base_site.article_slug("https://example.com/") == "article"
    assert base_site.output_path == settings.seed_dir / "example.com.seed"
    assert base_site.scraped_article_output_path("https://example.com/articles/deep-dive") == (
        settings.scraped_dir / "example.com" / "article_html" / "deep-dive.html"
    )
    assert base_site.article_output_path("https://example.com/articles/deep-dive") == (
        settings.content_dir / "news_article" / "example.com" / "deep-dive.json"
    )
    assert base_site.article_markdown_output_path("https://example.com/articles/deep-dive") == (
        settings.content_dir / "news_article" / "example.com" / "deep-dive.md"
    )

    options = base_site.build_options()
    assert options.url == "https://example.com"
    assert str(options.output_path) == str(settings.seed_dir / "example.com.seed")
    assert options.transform == "basic"
    assert options.pretty is True
    assert options.headers == "default"


def test_base_site_default_parsed_content_and_save(settings: Settings) -> None:
    site = BaseSite(
        settings=settings,
        domain="example.com",
        start_url="https://example.com",
    )

    article = site.default_parsed_content(
        title="Example Title",
        url="https://example.com/articles/deep-dive",
        category="News",
        author="Writer",
        published_at="2026-04-10",
        summary="Summary",
        content="  First paragraph.\n\nSecond paragraph.  ",
        content_type="news_article",
    )

    assert article.source_site == "example.com"
    assert article.word_count == 4
    assert article.char_count == len("First paragraph.\n\nSecond paragraph.")
    assert article.content == "First paragraph.\n\nSecond paragraph."
    assert article.scraped_at

    output_path = site.save_parsed_article(article, article.url)
    assert output_path == settings.content_dir / "news_article" / "example.com" / "deep-dive.json"
    assert output_path.read_text(encoding="utf-8")
    assert output_path.with_suffix(".md").read_text(encoding="utf-8").startswith("# Example Title")


def test_base_site_scrape_article_uses_normalized_url_and_output_path(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    site = BaseSite(
        settings=settings,
        domain="example.com",
        start_url="https://example.com",
    )

    captured: dict[str, object] = {}

    class DummyScraper:
        def __init__(self, options) -> None:
            captured["options"] = options

        def scrape(self):
            captured["scraped"] = True
            return object()

    monkeypatch.setattr(base_module, "HttpScraper", DummyScraper)

    site.scrape_article("https://example.com/articles/deep-dive#frag")

    options = captured["options"]
    assert options.url == "https://example.com/articles/deep-dive"
    assert str(options.output_path) == str(
        settings.scraped_dir / "example.com" / "article_html" / "deep-dive.html"
    )
    assert captured["scraped"] is True


def test_kompas_site_matches_article_urls(settings: Settings) -> None:
    site = KompasComSite(settings)

    assert site.is_article_url("https://www.kompas.com/tekno/read/2024/01/01/123456789/example")
    assert not site.is_article_url("https://www.kompas.com/")
