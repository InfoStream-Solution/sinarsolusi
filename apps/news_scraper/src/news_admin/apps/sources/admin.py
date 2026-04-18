from __future__ import annotations

from django.contrib import admin
from django.db import transaction

from news_admin.apps.jobs.models import ScrapeJob
from news_admin.apps.jobs.tasks import run_scrape_job

from .models import SourceSite


@admin.register(SourceSite)
class SourceSiteAdmin(admin.ModelAdmin):
    list_display = ("domain", "name", "enabled", "created_at")
    list_filter = ("enabled",)
    search_fields = ("domain", "name")

    actions = [
        "enqueue_seed_jobs",
        "enqueue_extract_jobs",
        "enqueue_post_jobs",
        "enqueue_import_jobs",
    ]

    @admin.action(description="Enqueue seed jobs")
    def enqueue_seed_jobs(self, request, queryset):
        for site in queryset:
            job = ScrapeJob.objects.create(
                job_type=ScrapeJob.JobType.SEED, domain=site.domain
            )
            transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))

    @admin.action(description="Enqueue extract jobs")
    def enqueue_extract_jobs(self, request, queryset):
        for site in queryset:
            job = ScrapeJob.objects.create(
                job_type=ScrapeJob.JobType.EXTRACT, domain=site.domain
            )
            transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))

    @admin.action(description="Enqueue post jobs")
    def enqueue_post_jobs(self, request, queryset):
        for site in queryset:
            job = ScrapeJob.objects.create(
                job_type=ScrapeJob.JobType.POST, domain=site.domain
            )
            transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))

    @admin.action(description="Import articles from content dir")
    def enqueue_import_jobs(self, request, queryset):
        for site in queryset:
            job = ScrapeJob.objects.create(
                job_type=ScrapeJob.JobType.IMPORT_ARTICLES,
                domain=site.domain,
            )
            transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))
