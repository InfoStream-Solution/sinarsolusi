from __future__ import annotations

from django.db.models.signals import post_delete
from django.db.models.signals import post_save

from .models import SourceSite
from .models import SourceSiteHost
from .policy import clear_allowed_hosts_cache


def _clear_allowed_hosts_cache(*args, **kwargs) -> None:
    clear_allowed_hosts_cache()


post_save.connect(
    _clear_allowed_hosts_cache,
    sender=SourceSite,
    dispatch_uid="sources.clear_allowed_hosts_cache.source_site.save",
)
post_delete.connect(
    _clear_allowed_hosts_cache,
    sender=SourceSite,
    dispatch_uid="sources.clear_allowed_hosts_cache.source_site.delete",
)
post_save.connect(
    _clear_allowed_hosts_cache,
    sender=SourceSiteHost,
    dispatch_uid="sources.clear_allowed_hosts_cache.source_site_host.save",
)
post_delete.connect(
    _clear_allowed_hosts_cache,
    sender=SourceSiteHost,
    dispatch_uid="sources.clear_allowed_hosts_cache.source_site_host.delete",
)
