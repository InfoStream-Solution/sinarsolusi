from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "news_admin.config.settings")
os.environ.setdefault("DATA_DIR", "/home/ubuntu/projects/sinarsolusi/apps/news_scraper/.data")
django.setup()

import news_admin.apps.articles.services as article_services


def test_to_datetime_handles_beritasatu_published_at_format() -> None:
    parsed = article_services._to_datetime("Kamis, 16 April 2026 | 17:47 WIB")

    assert parsed is not None
    assert parsed.isoformat() == "2026-04-16T17:47:00+07:00"


def test_to_datetime_handles_kompas_slash_date_format() -> None:
    parsed = article_services._to_datetime("18/04/2026, 10:03 WIB")

    assert parsed is not None
    assert parsed.isoformat() == "2026-04-18T10:03:00+07:00"


def test_import_articles_for_domain_persists_article_metadata(tmp_path: Path, monkeypatch) -> None:
    content_dir = tmp_path / "content"
    article_dir = content_dir / "news_article" / "beritasatu.com"
    article_dir.mkdir(parents=True, exist_ok=True)
    (article_dir / "sample.json").write_text(
        """
        {
          "url": "https://www.beritasatu.com/example",
          "title": "Sample",
          "source_site": "beritasatu.com",
          "category": "Multimedia",
          "author": "Melati Krisna",
          "content": "First paragraph.\\n\\nSecond paragraph.",
          "published_at": "Kamis, 16 April 2026 | 17:47 WIB",
          "scraped_at": "2026-04-18T03:14:53.976678+00:00"
        }
        """,
        encoding="utf-8",
    )

    class FakeRun:
        def __init__(self) -> None:
            self.id = 7
            self.saved_update_fields: list[str] = []

        def save(self, update_fields=None):
            self.saved_update_fields = list(update_fields or [])

    class FakeArticleQuerySet:
        def first(self):
            return None

    captured: dict[str, object] = {}

    def fake_create(**kwargs):
        captured["run_kwargs"] = kwargs
        return FakeRun()

    def fake_update_or_create(url, defaults):
        captured["article_defaults"] = {"url": url, "defaults": defaults}
        return SimpleNamespace(id=1), True

    monkeypatch.setattr("news_admin.apps.articles.models.ArticleImportRun.objects.create", fake_create)
    monkeypatch.setattr(article_services.Article.objects, "filter", lambda url: FakeArticleQuerySet())
    monkeypatch.setattr(article_services.Article.objects, "update_or_create", fake_update_or_create)
    monkeypatch.setattr(
        article_services,
        "get_settings",
        lambda: SimpleNamespace(content_dir=content_dir),
    )

    result = article_services.import_articles_for_domain("beritasatu.com")

    defaults = captured["article_defaults"]["defaults"]
    assert defaults["category"] == "Multimedia"
    assert defaults["author"] == "Melati Krisna"
    assert defaults["word_count"] == 4
    assert defaults["char_count"] == len("First paragraph.\n\nSecond paragraph.")
    assert result["created"] == 1


def test_refresh_article_from_source_persists_article_metadata(tmp_path: Path, monkeypatch) -> None:
    scraped_dir = tmp_path / "scraped"
    content_dir = tmp_path / "content"
    html_path = scraped_dir / "kompas.com" / "article_html" / "sample.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text("<html><body>article</body></html>", encoding="utf-8")

    class FakeSite:
        domain = "kompas.com"

        def normalize_article_url(self, url: str) -> str:
            return url.split("?", 1)[0]

        def is_article_url(self, url: str) -> bool:
            return True

        def scrape_article(self, url: str) -> None:
            return None

        def scraped_article_output_path(self, url: str) -> Path:
            return html_path

        def parse_article(self, html: str, url: str):
            return SimpleNamespace(
                title="Updated title",
                source_site="kompas.com",
                category="News",
                author="Reporter",
                content="First paragraph.\n\nSecond paragraph.",
                word_count=4,
                char_count=len("First paragraph.\n\nSecond paragraph."),
                published_at="17 April 2026, 10:30 WIB",
                scraped_at="2026-04-18T03:14:53.976678+00:00",
            )

        def save_parsed_article(self, article, url: str):
            return content_dir / "news_article" / "kompas.com" / "sample.json"

        def article_html_output_path(self, url: str) -> Path:
            return content_dir / "news_article" / "kompas.com" / "sample.html"

        def article_markdown_output_path(self, url: str) -> Path:
            return content_dir / "news_article" / "kompas.com" / "sample.md"

    captured: dict[str, object] = {}
    article = SimpleNamespace(
        id=415,
        url="https://example.test/article?page=all",
        title="Old title",
        source_site="kompas.com",
        category=None,
        author=None,
        content="Old content",
        word_count=2,
        char_count=11,
        published_at=None,
        scraped_at=None,
        save=lambda update_fields=None: captured.setdefault("save_calls", []).append(list(update_fields or [])),
    )

    monkeypatch.setattr(
        article_services,
        "get_settings",
        lambda: SimpleNamespace(content_dir=content_dir, scraped_dir=scraped_dir),
    )
    monkeypatch.setattr(article_services, "load_site", lambda site_domain, settings: FakeSite())

    result = article_services.refresh_article_from_source(article)

    assert article.category == "News"
    assert article.author == "Reporter"
    assert article.word_count == 4
    assert article.char_count == len("First paragraph.\n\nSecond paragraph.")
    assert result["article_id"] == 415
