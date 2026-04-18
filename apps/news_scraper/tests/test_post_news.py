from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import news_scraper_core.post_news as post_news
from news_scraper_core.config import Settings
from news_scraper_core.models import ParsedContent


class DummyResponse:
    def __init__(self, status: int, body: str) -> None:
        self.status = status
        self._body = body.encode("utf-8")

    def __enter__(self) -> "DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._body


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        store_database_url=f"sqlite:///{tmp_path / 'news_scraper.db'}",
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


def test_build_request_body_omits_read_only_fields() -> None:
    article = ParsedContent(
        content_type="news_article",
        title="Example Title",
        url="https://example.com/article",
        source_site="example.com",
        category="News",
        published_at="2026-04-10T10:00:00+07:00",
        author="Writer",
        summary="Summary",
        content="Body text",
        word_count=2,
        char_count=9,
        scraped_at="2026-04-10T10:01:00+07:00",
    )

    body = post_news.build_request_body(article)

    assert body == {
        "title": "Example Title",
        "content": "Body text",
        "published_at": "2026-04-10T10:00:00+07:00",
    }


def test_normalize_published_at_handles_kompas_format() -> None:
    assert post_news.normalize_published_at("11 April 2026, 13:12 WIB") == (
        "2026-04-11T13:12:00+07:00"
    )


def test_normalize_published_at_handles_beritasatu_format() -> None:
    assert post_news.normalize_published_at("Kamis, 16 April 2026 | 17:47 WIB") == (
        "2026-04-16T17:47:00+07:00"
    )


def test_normalize_published_at_handles_kompas_slash_date_format() -> None:
    assert post_news.normalize_published_at("18/04/2026, 10:03 WIB") == (
        "2026-04-18T10:03:00+07:00"
    )


def test_post_article_uses_token_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(api_request, timeout: int) -> DummyResponse:
        captured["request"] = api_request
        captured["timeout"] = timeout
        return DummyResponse(201, '{"id": 1}')

    monkeypatch.setattr(post_news.request, "urlopen", fake_urlopen)

    article = ParsedContent(
        content_type="news_article",
        title="Example Title",
        url="https://example.com/article",
        source_site="example.com",
        category=None,
        published_at=None,
        author=None,
        summary=None,
        content="Body text",
        word_count=2,
        char_count=9,
        scraped_at="2026-04-10T10:01:00+07:00",
    )

    status, body = post_news.post_article(
        base_url="http://example.test",
        token="secret-token",
        article=article,
    )

    api_request = captured["request"]
    assert status == 201
    assert body == '{"id": 1}'
    assert captured["timeout"] == 30
    assert api_request.full_url == "http://example.test/api/news/"
    assert api_request.headers["Authorization"] == "Token secret-token"
    assert json.loads(api_request.data.decode("utf-8")) == {
        "title": "Example Title",
        "content": "Body text",
    }


def test_main_posts_articles_and_writes_marker(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content_dir = settings.content_dir / "news_article" / "kompas.com"
    content_dir.mkdir(parents=True, exist_ok=True)
    article_path = content_dir / "deep-dive.json"
    article_path.write_text(
        json.dumps(
            {
                "content_type": "news_article",
                "title": "Example Title",
                "url": "https://example.com/article",
                "source_site": "kompas.com",
                "category": None,
                "published_at": None,
                "author": None,
                "summary": None,
                "content": "Body text",
                "word_count": 2,
                "char_count": 9,
                "scraped_at": "2026-04-10T10:01:00+07:00",
            }
        ),
        encoding="utf-8",
    )

    def fake_get_settings() -> Settings:
        return settings

    def fake_urlopen(api_request, timeout: int) -> DummyResponse:
        return DummyResponse(201, '{"id": 1}')

    monkeypatch.setattr(post_news, "get_settings", fake_get_settings)
    monkeypatch.setattr(post_news.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(post_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        post_news,
        "get_logger",
        lambda name: SimpleNamespace(
            info=lambda *args, **kwargs: None, exception=lambda *args, **kwargs: None
        ),
    )
    monkeypatch.setattr(
        post_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                domain="kompas.com", limit=0, dry_run=False
            )
        ),
    )

    post_news.main()

    marker_path = content_dir / "deep-dive.posted.json"
    assert marker_path.exists()
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    assert marker["url"] == "https://example.com/article"
    assert marker["response_status"] == 201


def test_main_dry_run_skips_posting_and_marker_creation(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content_dir = settings.content_dir / "news_article" / "kompas.com"
    content_dir.mkdir(parents=True, exist_ok=True)
    article_path = content_dir / "deep-dive.json"
    article_path.write_text(
        json.dumps(
            {
                "content_type": "news_article",
                "title": "Example Title",
                "url": "https://example.com/article",
                "source_site": "kompas.com",
                "category": None,
                "published_at": None,
                "author": None,
                "summary": None,
                "content": "Body text",
                "word_count": 2,
                "char_count": 9,
                "scraped_at": "2026-04-10T10:01:00+07:00",
            }
        ),
        encoding="utf-8",
    )

    captured: list[dict[str, object]] = []

    def fake_get_settings() -> Settings:
        return settings

    def fake_urlopen(api_request, timeout: int):
        raise AssertionError("network should not be used in dry-run")

    def fake_info(*args, **kwargs) -> None:
        captured.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr(post_news, "get_settings", fake_get_settings)
    monkeypatch.setattr(post_news.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(post_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        post_news,
        "get_logger",
        lambda name: SimpleNamespace(
            info=fake_info, exception=lambda *args, **kwargs: None
        ),
    )
    monkeypatch.setattr(
        post_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                domain="kompas.com", limit=0, dry_run=True
            )
        ),
    )

    post_news.main()

    marker_path = content_dir / "deep-dive.posted.json"
    error_path = settings.content_dir / "errors" / "kompas.com" / "post-news.jsonl"
    assert not marker_path.exists()
    assert not error_path.exists()
    assert any("post_news_dry_run" in entry["args"][0] for entry in captured)


def test_main_logs_failed_posts(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content_dir = settings.content_dir / "news_article" / "kompas.com"
    content_dir.mkdir(parents=True, exist_ok=True)
    article_path = content_dir / "deep-dive.json"
    article_path.write_text(
        json.dumps(
            {
                "content_type": "news_article",
                "title": "Example Title",
                "url": "https://example.com/article",
                "source_site": "kompas.com",
                "category": None,
                "published_at": None,
                "author": None,
                "summary": None,
                "content": "Body text",
                "word_count": 2,
                "char_count": 9,
                "scraped_at": "2026-04-10T10:01:00+07:00",
            }
        ),
        encoding="utf-8",
    )

    def fake_get_settings() -> Settings:
        return settings

    def fake_urlopen(api_request, timeout: int):
        raise OSError("network down")

    monkeypatch.setattr(post_news, "get_settings", fake_get_settings)
    monkeypatch.setattr(post_news.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(post_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        post_news,
        "get_logger",
        lambda name: SimpleNamespace(
            info=lambda *args, **kwargs: None, exception=lambda *args, **kwargs: None
        ),
    )
    monkeypatch.setattr(
        post_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                domain="kompas.com", limit=0, dry_run=False
            )
        ),
    )

    post_news.main()

    error_path = settings.content_dir / "errors" / "kompas.com" / "post-news.jsonl"
    records = error_path.read_text(encoding="utf-8").splitlines()
    assert len(records) == 1
    assert json.loads(records[0])["error_type"] == "OSError"
