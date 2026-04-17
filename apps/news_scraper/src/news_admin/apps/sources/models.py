from __future__ import annotations

from django.db import models


class SourceSite(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["domain"]

    def __str__(self) -> str:
        return self.domain

