from __future__ import annotations

from django.db import models


class SourceSite(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["domain"]

    def __str__(self) -> str:
        return self.domain


class SourceSiteHost(models.Model):
    source_site = models.ForeignKey(
        SourceSite,
        on_delete=models.CASCADE,
        related_name="hosts",
    )
    host = models.CharField(max_length=255)
    enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["host"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_site", "host"],
                name="uniq_source_site_host",
            )
        ]

    def __str__(self) -> str:
        return f"{self.host} ({self.source_site.domain})"
