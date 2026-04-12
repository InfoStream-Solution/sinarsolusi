from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        raise ValueError(f"Error .env is not found in {env_path}")

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    store_database_url: str
    seed_dir: Path
    links_dir: Path
    scraped_dir: Path
    content_dir: Path
    kbt_api_base_url: str
    kbt_api_token: str | None
    scraper_debug: bool
    keep_seed: bool
    keep_scraped: bool

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["seed_dir"] = str(self.seed_dir)
        data["links_dir"] = str(self.links_dir)
        data["scraped_dir"] = str(self.scraped_dir)
        data["content_dir"] = str(self.content_dir)
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)



def _parse_bool(raw_value: str | None, default: bool = False) -> bool:
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    return default


def _build_store_database_url() -> str:
    override = os.environ.get("STORE_DATABASE_URL")
    if override:
        return override

    db_user = os.environ.get("DB_USER", "news_scraper")
    db_password = os.environ.get("DB_PASSWORD", "news_scraper")
    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    db_port = os.environ.get("DB_PORT", "54320")
    db_name = os.environ.get("DB_NAME", "news_scraper")
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_settings() -> Settings:
    _load_dotenv()
    store_database_url = _build_store_database_url()

    raw_data_dir = os.environ.get("DATA_DIR")
    if raw_data_dir is None:
        raise ValueError("DATA_DIR is required and must be an absolute path")

    app_data_dir = Path(raw_data_dir)
    if not app_data_dir.is_absolute():
        raise ValueError(
            f"DATA_DIR must be an absolute path, got {raw_data_dir!r}"
        )

    seed_dir = app_data_dir / "seed"
    links_dir = app_data_dir / "links"
    scraped_dir = app_data_dir / "scraped"
    content_dir = app_data_dir / "content"

    kbt_api_base_url = os.environ.get("KBT_API_BASE_URL", "http://127.0.0.1:8000")
    kbt_api_token = os.environ.get("KBT_API_TOKEN")
    scraper_debug = _parse_bool(os.environ.get("SCRAPER_DEBUG"), default=False)
    keep_seed = _parse_bool(os.environ.get("KEEP_SEED"), default=scraper_debug)
    keep_scraped = _parse_bool(
        os.environ.get("KEEP_SCRAPED"),
        default=scraper_debug,
    )

    return Settings(
        store_database_url=store_database_url,
        seed_dir=seed_dir,
        links_dir=links_dir,
        scraped_dir=scraped_dir,
        content_dir=content_dir,
        kbt_api_base_url=kbt_api_base_url.rstrip("/"),
        kbt_api_token=kbt_api_token,
        scraper_debug=scraper_debug,
        keep_seed=keep_seed,
        keep_scraped=keep_scraped,
    )
