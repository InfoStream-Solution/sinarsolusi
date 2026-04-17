from __future__ import annotations

from pathlib import Path

import pytest

import news_scraper_core.config as config


def test_get_settings_requires_data_dir_even_without_dotenv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(Path("/tmp"))
    monkeypatch.delenv("DATA_DIR", raising=False)
    monkeypatch.setattr(config, "_load_dotenv", lambda: None)

    with pytest.raises(ValueError, match=r"DATA_DIR is required"):
        config.get_settings()
