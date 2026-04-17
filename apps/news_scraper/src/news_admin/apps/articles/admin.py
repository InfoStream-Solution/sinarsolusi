from __future__ import annotations

from django.contrib import admin
from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path
from django.db.models import QuerySet

from news_admin.apps.jobs.models import ScrapeJob
from news_admin.apps.jobs.tasks import run_scrape_job
from .models import Article, ArticleImportRun
from .services import refresh_article_from_source


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
    list_display = ("title", "source_site", "published_at", "scraped_at", "updated_at", "created_at")
    list_filter = ("source_site", PublishedAtFilter)
    search_fields = ("title", "url", "source_site", "content")
    actions = ["enqueue_scrape_jobs", "refresh_selected_articles"]
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

    @admin.action(description="Enqueue scrape jobs")
    def enqueue_scrape_jobs(self, request, queryset):
        for article in queryset:
            job = ScrapeJob.objects.create(
                job_type=ScrapeJob.JobType.SCRAPE,
                domain=article.source_site,
                params={"url": article.url},
            )
            transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))

    @admin.action(description="Refresh selected articles from source URL")
    def refresh_selected_articles(self, request, queryset):
        refreshed = 0
        for article in queryset:
            refresh_article_from_source(article)
            refreshed += 1
        self.message_user(request, f"Refreshed {refreshed} article(s).", level=messages.SUCCESS)

    def refresh_article_view(self, request: HttpRequest, object_id: str):
        article = self.get_object(request, object_id)
        if article is None:
            self.message_user(request, "Article not found.", level=messages.ERROR)
            return HttpResponseRedirect("..")
        if request.method != "POST":
            return HttpResponseRedirect("..")
        refresh_article_from_source(article)
        self.message_user(
            request,
            f"Refreshed article {article.title!r} from source URL.",
            level=messages.SUCCESS,
        )
        return HttpResponseRedirect("..")
