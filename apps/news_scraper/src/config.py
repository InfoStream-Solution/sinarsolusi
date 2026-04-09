from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    seed_dir: Path
    links_dir: Path
    scraped_dir: Path
    content_dir: Path
    scraper_debug: bool
    keep_seed: bool
    keep_scraped: bool


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()

    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()

    return path


def _parse_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    return default


def get_settings() -> Settings:
    _load_dotenv()
    raw_seed_dir = os.environ.get("SEED_DIR", "./seed")
    raw_links_dir = os.environ.get("LINKS_DIR", "./links")
    raw_scraped_dir = os.environ.get("SCRAPED_DIR", "./scraped")
    raw_content_dir = os.environ.get("CONTENT_DIR", "./content")
    scraper_debug = _parse_bool(os.environ.get("SCRAPER_DEBUG"), default=False)
    keep_seed = _parse_bool(os.environ.get("KEEP_SEED"), default=scraper_debug)
    keep_scraped = _parse_bool(
        os.environ.get("KEEP_SCRAPED"),
        default=scraper_debug,
    )
    seed_dir = _resolve_path(raw_seed_dir)
    links_dir = _resolve_path(raw_links_dir)
    scraped_dir = _resolve_path(raw_scraped_dir)
    content_dir = _resolve_path(raw_content_dir)

    return Settings(
        seed_dir=seed_dir,
        links_dir=links_dir,
        scraped_dir=scraped_dir,
        content_dir=content_dir,
        scraper_debug=scraper_debug,
        keep_seed=keep_seed,
        keep_scraped=keep_scraped,
    )
