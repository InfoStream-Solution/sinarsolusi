from __future__ import annotations

import os
from functools import lru_cache

from news_scraper_core.links import normalize_host


def _ensure_django_ready() -> bool:
    try:
        from django.apps import apps
        from django.conf import settings as django_settings
    except ImportError:
        return False

    if apps.ready:
        return True

    if not django_settings.configured:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "news_admin.config.settings")

    try:
        import django
    except ImportError:
        return False

    try:
        django.setup()
    except Exception:
        return False

    return apps.ready


@lru_cache(maxsize=None)
def get_additional_allowed_hosts(domain: str) -> frozenset[str]:
    if not _ensure_django_ready():
        return frozenset()

    from .models import SourceSite
    from .models import SourceSiteHost

    source_site = SourceSite.objects.filter(domain=domain, enabled=True).first()
    if source_site is None:
        return frozenset()

    hosts = {
        normalize_host(host)
        for host in SourceSiteHost.objects.filter(
            source_site=source_site,
            enabled=True,
        ).values_list("host", flat=True)
    }
    return frozenset(hosts)


def register_discovered_hosts(domain: str, hosts: set[str]) -> dict[str, int]:
    if not hosts:
        return {"created": 0, "skipped": 0}
    if not _ensure_django_ready():
        return {"created": 0, "skipped": len(hosts)}

    from .models import SourceSite
    from .models import SourceSiteHost

    source_site, _ = SourceSite.objects.get_or_create(
        domain=domain,
        defaults={"name": domain, "enabled": False},
    )

    created = 0
    skipped = 0
    for host in sorted({normalize_host(host) for host in hosts if host}):
        _, was_created = SourceSiteHost.objects.get_or_create(
            source_site=source_site,
            host=host,
            defaults={"enabled": False},
        )
        if was_created:
            created += 1
        else:
            skipped += 1

    clear_allowed_hosts_cache()
    return {"created": created, "skipped": skipped}


def clear_allowed_hosts_cache() -> None:
    get_additional_allowed_hosts.cache_clear()
