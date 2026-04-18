from __future__ import annotations

from django.db import models


class ArticleImportRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    domain = models.CharField(max_length=255)
    content_dir = models.CharField(max_length=500)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.QUEUED
    )
    scanned_files = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    file_paths = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.domain}:{self.status}:{self.created_at:%Y-%m-%d %H:%M:%S}"


class Article(models.Model):
    url = models.URLField(unique=True)
    title = models.CharField(max_length=500)
    source_site = models.CharField(max_length=255)
    category = models.CharField(max_length=255, null=True, blank=True)
    author = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField(blank=True)
    word_count = models.PositiveIntegerField(default=0)
    char_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    scraped_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
