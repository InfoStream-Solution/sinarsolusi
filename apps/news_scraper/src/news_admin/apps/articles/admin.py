from __future__ import annotations

from django.contrib import admin
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path
from django.db.models import QuerySet
from django.utils.html import format_html
import json
from urllib.parse import urlparse

from news_scraper_core.config import get_settings
from news_scraper_core.site_loader import load_site

from news_admin.apps.jobs.models import ScrapeJob
from news_admin.apps.jobs.tasks import run_scrape_job
from .models import Article, ArticleImportRun


class PublishedAtFilter(admin.SimpleListFilter):
    title = "published at"
    parameter_name = "published_at_state"

    def lookups(self, request, model_admin):
        return (
            ("has_value", "Has published_at"),
            ("missing", "Missing published_at"),
        )

    def queryset(self, request, queryset: QuerySet):
        if self.value() == "has_value":
            return queryset.filter(published_at__isnull=False)
        if self.value() == "missing":
            return queryset.filter(published_at__isnull=True)
        return queryset


class WordCountFilter(admin.SimpleListFilter):
    title = "word count"
    parameter_name = "word_count_range"

    def lookups(self, request, model_admin):
        return (
            ("0_500", "0-500 words"),
            ("501_1000", "501-1000 words"),
            ("gt_1000", "> 1000 words"),
        )

    def queryset(self, request, queryset: QuerySet):
        if self.value() == "0_500":
            return queryset.filter(word_count__lte=500)
        if self.value() == "501_1000":
            return queryset.filter(word_count__gt=500, word_count__lte=1000)
        if self.value() == "gt_1000":
            return queryset.filter(word_count__gt=1000)
        return queryset


class CategoryFilter(admin.SimpleListFilter):
    title = "category"
    parameter_name = "category_state"

    def lookups(self, request, model_admin):
        return (
            ("has_value", "Has category"),
            ("missing", "Missing category"),
        )

    def queryset(self, request, queryset: QuerySet):
        if self.value() == "has_value":
            return queryset.filter(category__isnull=False)
        if self.value() == "missing":
            return queryset.filter(category__isnull=True)
        return queryset


class AuthorFilter(admin.SimpleListFilter):
    title = "author"
    parameter_name = "author_state"

    def lookups(self, request, model_admin):
        return (
            ("has_value", "Has author"),
            ("missing", "Missing author"),
        )

    def queryset(self, request, queryset: QuerySet):
        if self.value() == "has_value":
            return queryset.filter(author__isnull=False)
        if self.value() == "missing":
            return queryset.filter(author__isnull=True)
        return queryset


def _domain_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _enqueue_refresh_job(article: Article) -> ScrapeJob:
    job = ScrapeJob.objects.create(
        job_type=ScrapeJob.JobType.REFRESH,
        domain=article.source_site or _domain_from_url(article.url),
        params={"article_id": article.id},
    )
    transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))
    return job


def _article_source_domain(article: Article) -> str:
    return article.source_site or _domain_from_url(article.url)


@admin.register(ArticleImportRun)
class ArticleImportRunAdmin(admin.ModelAdmin):
    list_display = (
        "domain",
        "status",
        "scanned_files",
        "created_count",
        "updated_count",
        "skipped_count",
        "created_at",
        "finished_at",
    )
    list_filter = ("domain", "status")
    search_fields = ("domain", "error_message")
    readonly_fields = (
        "created_at",
        "started_at",
        "finished_at",
        "scanned_files",
        "created_count",
        "updated_count",
        "skipped_count",
        "file_paths",
    )


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "source_site",
        "category",
        "author",
        "word_count",
        "char_count",
        "published_at",
        "scraped_at",
        "updated_at",
        "created_at",
    )
    list_filter = ("source_site", CategoryFilter, AuthorFilter, PublishedAtFilter, WordCountFilter)
    search_fields = ("title", "url", "source_site", "category", "author", "content")
    actions = ["enqueue_scrape_jobs", "refresh_selected_articles"]
    readonly_fields = ("content_json_path", "content_json_preview", "content_html_path", "content_html_preview")
    change_form_template = "admin/articles/article/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/refresh/",
                self.admin_site.admin_view(self.refresh_article_view),
                name="articles_article_refresh",
            ),
        ]
        return custom_urls + urls

    @admin.display(description="JSON file location")
    def content_json_path(self, obj: Article) -> str:
        try:
            settings = get_settings()
            site = load_site(_article_source_domain(obj), settings=settings)
            path = site.article_output_path(obj.url)
            return format_html("<code>{}</code>", path)
        except Exception as exc:  # pragma: no cover - defensive admin fallback
            return f"Unavailable: {exc}"

    @admin.display(description="JSON content")
    def content_json_preview(self, obj: Article) -> str:
        try:
            settings = get_settings()
            site = load_site(_article_source_domain(obj), settings=settings)
            path = site.article_output_path(obj.url)
            payload = json.loads(path.read_text(encoding="utf-8"))
            rendered = json.dumps(payload, indent=2, ensure_ascii=False)
            return format_html("<pre style='white-space: pre-wrap; margin: 0'>{}</pre>", rendered)
        except FileNotFoundError:
            return "JSON file not found."
        except Exception as exc:  # pragma: no cover - defensive admin fallback
            return f"Unavailable: {exc}"

    @admin.display(description="Scraped HTML file location")
    def content_html_path(self, obj: Article) -> str:
        try:
            settings = get_settings()
            site = load_site(_article_source_domain(obj), settings=settings)
            path = site.article_html_output_path(obj.url)
            return format_html("<code>{}</code>", path)
        except Exception as exc:  # pragma: no cover - defensive admin fallback
            return f"Unavailable: {exc}"

    @admin.display(description="Scraped HTML content")
    def content_html_preview(self, obj: Article) -> str:
        try:
            settings = get_settings()
            site = load_site(_article_source_domain(obj), settings=settings)
            path = site.article_html_output_path(obj.url)
            if not path.exists():
                path = site.scraped_article_output_path(obj.url)
            html = path.read_text(encoding="utf-8")
            return format_html("<pre style='white-space: pre-wrap; margin: 0'>{}</pre>", html)
        except FileNotFoundError:
            return "Scraped HTML file not found."
        except Exception as exc:  # pragma: no cover - defensive admin fallback
            return f"Unavailable: {exc}"

    @admin.action(description="Enqueue scrape jobs")
    def enqueue_scrape_jobs(self, request, queryset):
        for article in queryset:
            job = ScrapeJob.objects.create(
                job_type=ScrapeJob.JobType.SCRAPE,
                domain=_article_source_domain(article),
                params={"url": article.url},
            )
            transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))

    @admin.action(description="Queue refresh selected articles from source URL")
    def refresh_selected_articles(self, request, queryset):
        queued = 0
        for article in queryset:
            _enqueue_refresh_job(article)
            queued += 1
        self.message_user(request, f"Queued refresh for {queued} article(s).", level=messages.SUCCESS)

    def refresh_article_view(self, request: HttpRequest, object_id: str):
        article = self.get_object(request, object_id)
        if article is None:
            self.message_user(request, "Article not found.", level=messages.ERROR)
            return HttpResponseRedirect("..")
        if request.method != "POST":
            return HttpResponseRedirect("..")
        _enqueue_refresh_job(article)
        self.message_user(
            request,
            f"Queued refresh for article {article.title!r} from source URL.",
            level=messages.SUCCESS,
        )
        return HttpResponseRedirect("..")
