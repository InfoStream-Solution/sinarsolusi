from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import src.scrape as scrape
from src.config import Settings
from src.models import ParsedContent


class DummySite:
    domain = "kompas.com"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def is_article_url(self, url: str) -> bool:
        return url.startswith("https://www.kompas.com/")

    def normalize_article_url(self, url: str) -> str:
        return url.split("#", 1)[0]

    def scraped_article_output_path(self, url: str) -> Path:
        return self.settings.scraped_dir / self.domain / "article_html" / "example.html"

    def scrape_article(self, url: str):
        path = self.scraped_article_output_path(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<html>article</html>", encoding="utf-8")

    def parse_article(self, html: str, url: str) -> ParsedContent:
        return ParsedContent(
            content_type="news_article",
            title="Example Title",
            url=url,
            source_site=self.domain,
            category=None,
            published_at=None,
            author=None,
            summary="Summary",
            content="Body text",
            word_count=2,
            char_count=9,
            scraped_at="2026-04-11T00:00:00+07:00",
        )

    def save_parsed_article(self, article: ParsedContent, url: str) -> Path:
        output_path = self.settings.content_dir / "news_article" / self.domain / "example.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(article.to_json(), encoding="utf-8")
        output_path.with_suffix(".md").write_text(article.to_markdown(), encoding="utf-8")
        return output_path

    def article_markdown_output_path(self, url: str) -> Path:
        return self.settings.content_dir / "news_article" / self.domain / "example.md"

    def scraped_article_dir(self) -> Path:
        return self.settings.scraped_dir / self.domain / "article_html"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        seed_dir=tmp_path / "seed",
        links_dir=tmp_path / "links",
        scraped_dir=tmp_path / "scraped",
        content_dir=tmp_path / "content",
        kbt_api_base_url="http://example.test",
        kbt_api_token="secret-token",
        scraper_debug=False,
        keep_seed=False,
        keep_scraped=False,
    )


def test_build_parser_requires_url() -> None:
    parser = scrape.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["kompas.com"])


def test_main_writes_same_output_location_as_extract_news(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(scrape, "get_settings", lambda: settings)
    monkeypatch.setattr(scrape, "configure_logging", lambda debug: None)
    monkeypatch.setattr(scrape, "get_logger", lambda name: SimpleNamespace(info=lambda *args, **kwargs: None, exception=lambda *args, **kwargs: None))
    monkeypatch.setattr(scrape, "load_site", lambda domain, settings: DummySite(settings))
    monkeypatch.setattr(
        scrape,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                domain="kompas.com",
                url="https://www.kompas.com/2026/04/11/123456/example#frag",
                keep_scraped=None,
            )
        ),
    )

    scrape.main()

    json_path = settings.content_dir / "news_article" / "kompas.com" / "example.json"
    markdown_path = settings.content_dir / "news_article" / "kompas.com" / "example.md"
    scraped_path = settings.scraped_dir / "kompas.com" / "article_html" / "example.html"
    assert json_path.exists()
    assert markdown_path.exists()
    assert not scraped_path.exists()


def test_main_keeps_scraped_when_requested(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(scrape, "get_settings", lambda: settings)
    monkeypatch.setattr(scrape, "configure_logging", lambda debug: None)
    monkeypatch.setattr(scrape, "get_logger", lambda name: SimpleNamespace(info=lambda *args, **kwargs: None, exception=lambda *args, **kwargs: None))
    monkeypatch.setattr(scrape, "load_site", lambda domain, settings: DummySite(settings))
    monkeypatch.setattr(
        scrape,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                domain="kompas.com",
                url="https://www.kompas.com/2026/04/11/123456/example",
                keep_scraped=True,
            )
        ),
    )

    scrape.main()

    scraped_path = settings.scraped_dir / "kompas.com" / "article_html" / "example.html"
    assert scraped_path.exists()


def test_main_rejects_non_article_url(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(scrape, "get_settings", lambda: settings)
    monkeypatch.setattr(scrape, "configure_logging", lambda debug: None)
    monkeypatch.setattr(scrape, "get_logger", lambda name: SimpleNamespace(info=lambda *args, **kwargs: None, exception=lambda *args, **kwargs: None))
    monkeypatch.setattr(scrape, "load_site", lambda domain, settings: DummySite(settings))
    monkeypatch.setattr(
        scrape,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                domain="kompas.com",
                url="https://other.com/article",
                keep_scraped=None,
            )
        ),
    )

    with pytest.raises(SystemExit):
        scrape.main()
