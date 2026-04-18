from __future__ import annotations

from django.contrib import admin

from .models import ScrapeJob


@admin.register(ScrapeJob)
class ScrapeJobAdmin(admin.ModelAdmin):
    list_display = (
        "job_type",
        "domain",
        "status",
        "created_at",
        "started_at",
        "finished_at",
    )
    list_filter = ("job_type", "status", "domain")
    search_fields = ("domain", "error_message")
    readonly_fields = ("created_at", "started_at", "finished_at")
