from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SiteConfig:
    domain: str
    url: str


def load_sites(path: Path) -> list[SiteConfig]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    sites: list[SiteConfig] = []
    for item in raw:
        sites.append(
            SiteConfig(
                domain=item["domain"],
                url=item["url"],
            )
        )
    return sites
