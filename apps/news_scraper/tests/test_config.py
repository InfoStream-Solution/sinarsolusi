from __future__ import annotations

from pathlib import Path

import pytest

import src.config as config


def test_get_settings_requires_dotenv_in_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(Path("/tmp"))
    monkeypatch.delenv("DATA_DIR", raising=False)

    with pytest.raises(ValueError, match=r"Error \.env is not found in /tmp/\.env"):
        config.get_settings()
