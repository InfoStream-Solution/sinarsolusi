from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "news_admin.config.settings")
os.environ.setdefault("DATA_DIR", "/home/ubuntu/projects/sinarsolusi/apps/news_scraper/.data")
django.setup()

import news_admin.apps.articles.admin as article_admin


class FakeQuerySet:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def filter(self, **kwargs):
        self.calls.append(kwargs)
        return self


def test_article_admin_list_filters_include_metadata_fields() -> None:
    assert article_admin.ArticleAdmin.list_filter == (
        "source_site",
        article_admin.CategoryFilter,
        article_admin.AuthorFilter,
        article_admin.PublishedAtFilter,
        article_admin.WordCountFilter,
    )


def test_content_json_path_uses_site_output_path(monkeypatch) -> None:
    article = SimpleNamespace(url="https://example.test/news/a", source_site="example.test")
    payload = {"title": "Example", "content": "Hello"}
    html_payload = "<html><body><h1>Example</h1></body></html>"

    class ExpectedPath:
        def __str__(self) -> str:
            return "/tmp/content/news_article/example.test/a.json"

        def read_text(self, encoding="utf-8") -> str:
            return __import__("json").dumps(payload)

    class ExpectedHtmlPath:
        def __str__(self) -> str:
            return "/tmp/scraped/example.test/a.html"

        def read_text(self, encoding="utf-8") -> str:
            return html_payload

        def exists(self) -> bool:
            return True

    expected = ExpectedPath()
    expected_html = ExpectedHtmlPath()

    monkeypatch.setattr(article_admin, "get_settings", lambda: SimpleNamespace(content_dir=Path("/tmp/content")))
    monkeypatch.setattr(
        article_admin,
        "load_site",
        lambda domain, settings: SimpleNamespace(
            article_output_path=lambda url: expected,
            article_html_output_path=lambda url: expected_html,
            scraped_article_output_path=lambda url: expected_html,
        ),
    )

    rendered = article_admin.ArticleAdmin.content_json_path(article_admin.ArticleAdmin, article)
    preview = article_admin.ArticleAdmin.content_json_preview(article_admin.ArticleAdmin, article)
    html_path = article_admin.ArticleAdmin.content_html_path(article_admin.ArticleAdmin, article)
    html_preview = article_admin.ArticleAdmin.content_html_preview(article_admin.ArticleAdmin, article)

    assert "code" in rendered
    assert "/tmp/content/news_article/example.test/a.json" in rendered
    assert "Example" in preview
    assert "Hello" in preview
    assert "/tmp/scraped/example.test/a.html" in html_path
    assert "Example" in html_preview


def test_word_count_filter_ranges() -> None:
    request = SimpleNamespace()

    query = FakeQuerySet()
    filt = article_admin.WordCountFilter(request, {}, article_admin.Article, article_admin.ArticleAdmin)
    filt.value = lambda: "0_500"
    assert filt.queryset(request, query) is query
    assert query.calls[-1] == {"word_count__lte": 500}

    query = FakeQuerySet()
    filt = article_admin.WordCountFilter(request, {}, article_admin.Article, article_admin.ArticleAdmin)
    filt.value = lambda: "501_1000"
    assert filt.queryset(request, query) is query
    assert query.calls[-1] == {"word_count__gt": 500, "word_count__lte": 1000}

    query = FakeQuerySet()
    filt = article_admin.WordCountFilter(request, {}, article_admin.Article, article_admin.ArticleAdmin)
    filt.value = lambda: "gt_1000"
    assert filt.queryset(request, query) is query
    assert query.calls[-1] == {"word_count__gt": 1000}


def test_category_and_author_filters_handle_presence_and_missing() -> None:
    request = SimpleNamespace()

    query = FakeQuerySet()
    filt = article_admin.CategoryFilter(request, {}, article_admin.Article, article_admin.ArticleAdmin)
    filt.value = lambda: "has_value"
    assert filt.queryset(request, query) is query
    assert query.calls[-1] == {"category__isnull": False}

    query = FakeQuerySet()
    filt = article_admin.CategoryFilter(request, {}, article_admin.Article, article_admin.ArticleAdmin)
    filt.value = lambda: "missing"
    assert filt.queryset(request, query) is query
    assert query.calls[-1] == {"category__isnull": True}

    query = FakeQuerySet()
    filt = article_admin.AuthorFilter(request, {}, article_admin.Article, article_admin.ArticleAdmin)
    filt.value = lambda: "has_value"
    assert filt.queryset(request, query) is query
    assert query.calls[-1] == {"author__isnull": False}

    query = FakeQuerySet()
    filt = article_admin.AuthorFilter(request, {}, article_admin.Article, article_admin.ArticleAdmin)
    filt.value = lambda: "missing"
    assert filt.queryset(request, query) is query
    assert query.calls[-1] == {"author__isnull": True}
