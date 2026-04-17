from __future__ import annotations

from pathlib import Path

from ..config import Settings
from .base import BaseStore
from .db import DbStore


def build_store(settings: Settings) -> BaseStore:
    return DbStore(settings.store_database_url)


def build_store_from_path(db_path: Path) -> BaseStore:
    return DbStore(db_path)
