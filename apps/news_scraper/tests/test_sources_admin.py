from __future__ import annotations

import os
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "news_admin.config.settings")
os.environ.setdefault(
    "DATA_DIR", "/home/ubuntu/projects/sinarsolusi/apps/news_scraper/.data"
)
django.setup()

import news_admin.apps.sources.admin as source_admin  # noqa: E402


class FakeQuerySet:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def update(self, **kwargs):
        self.calls.append(kwargs)
        return 1


def test_source_site_host_admin_enable_and_disable_actions() -> None:
    request = SimpleNamespace()
    queryset = FakeQuerySet()

    source_admin.SourceSiteHostAdmin.enable_hosts(
        source_admin.SourceSiteHostAdmin, request, queryset
    )
    source_admin.SourceSiteHostAdmin.disable_hosts(
        source_admin.SourceSiteHostAdmin, request, queryset
    )

    assert queryset.calls == [{"enabled": True}, {"enabled": False}]
