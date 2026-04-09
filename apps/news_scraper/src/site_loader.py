from __future__ import annotations

from importlib import import_module

from .config import Settings
from .sites.base import BaseSite


def _domain_to_module_name(domain: str) -> str:
    return domain.replace(".", "_").replace("-", "_")


def _domain_to_class_name(domain: str) -> str:
    parts = _domain_to_module_name(domain).split("_")
    return "".join(part.capitalize() for part in parts) + "Site"


def load_site(domain: str, settings: Settings) -> BaseSite:
    module_name = _domain_to_module_name(domain)
    class_name = _domain_to_class_name(domain)
    module = import_module(f"{__package__}.sites.{module_name}")
    site_class = getattr(module, class_name)
    return site_class(settings=settings)
