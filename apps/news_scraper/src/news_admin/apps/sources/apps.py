from __future__ import annotations

from django.apps import AppConfig


class SourcesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "news_admin.apps.sources"

    def ready(self) -> None:
        from . import signals  # noqa: F401
