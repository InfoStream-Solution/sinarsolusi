from __future__ import annotations

from pathlib import Path

import pytest

import src.config as config


def test_get_settings_loads_app_env_when_cwd_env_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(Path("/tmp"))
    monkeypatch.delenv("DATA_DIR", raising=False)

    settings = config.get_settings()

    assert settings.scraped_dir == Path(
        "/home/ubuntu/projects/sinarsolusi/apps/news_scraper/.data/scraped"
    )
