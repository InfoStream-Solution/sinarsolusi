from __future__ import annotations

from django.db import models


class ScrapeJob(models.Model):
    class JobType(models.TextChoices):
        SEED = "seed", "Seed"
        EXTRACT = "extract", "Extract"
        SCRAPE = "scrape", "Scrape"
        REFRESH = "refresh", "Refresh"
        POST = "post", "Post"
        IMPORT_ARTICLES = "import_articles", "Import Articles"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    job_type = models.CharField(max_length=16, choices=JobType.choices)
    domain = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.QUEUED
    )
    params = models.JSONField(default=dict, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.job_type}:{self.domain}:{self.status}"
