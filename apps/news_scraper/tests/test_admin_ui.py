from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

import src.admin_ui as admin_ui
from src.config import Settings
from src.links import LinkRecord, write_links


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        store_database_url=f"sqlite:///{tmp_path / 'news_scraper.db'}",
        seed_dir=tmp_path / "seed",
        links_dir=tmp_path / "links",
        scraped_dir=tmp_path / "scraped",
        content_dir=tmp_path / "content",
        kbt_api_base_url="http://example.test",
        kbt_api_token="secret-token",
        scraper_debug=False,
        keep_seed=False,
        keep_scraped=False,
    )


def test_build_seed_command_uses_current_python() -> None:
    assert admin_ui.build_seed_command("kompas.com") == [
        admin_ui.sys.executable,
        "-m",
        "src.seed",
        "kompas.com",
    ]


def test_build_extract_command_includes_limit() -> None:
    assert admin_ui.build_extract_command("kompas.com", 5) == [
        admin_ui.sys.executable,
        "-m",
        "src.extract_news",
        "kompas.com",
        "--limit",
        "5",
    ]


def test_build_group_command_switches_mode() -> None:
    assert admin_ui.build_group_command("kompas.com", rebuild=True) == [
        admin_ui.sys.executable,
        "-m",
        "src.group_news",
        "--rebuild",
        "kompas.com",
    ]
    assert admin_ui.build_group_command("kompas.com", rebuild=False) == [
        admin_ui.sys.executable,
        "-m",
        "src.group_news",
        "--incremental",
        "kompas.com",
    ]


def test_links_to_rows_maps_scraped_state() -> None:
    rows = admin_ui.links_to_rows(
        [
            LinkRecord(url="https://example.com/a", scraped=False),
            LinkRecord(url="https://example.com/b", scraped=True),
        ]
    )

    assert rows == [
        {"url": "https://example.com/a", "scraped": "no"},
        {"url": "https://example.com/b", "scraped": "yes"},
    ]


def test_run_seed_command_invokes_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = args
        captured.update(kwargs)
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="seed ok",
            stderr="",
        )

    monkeypatch.setattr(admin_ui.subprocess, "run", fake_run)
    monkeypatch.setattr(admin_ui, "APP_DIR", Path("/tmp/news_scraper"))
    monkeypatch.setattr(admin_ui.sys, "executable", "/opt/python/bin/python")

    result = admin_ui.run_seed_command("kompas.com")

    assert result.returncode == 0
    assert captured["args"][0] == [
        "/opt/python/bin/python",
        "-m",
        "src.seed",
        "kompas.com",
    ]
    assert captured["cwd"] == Path("/tmp/news_scraper")
    assert captured["check"] is False
    assert captured["text"] is True
    assert captured["capture_output"] is True


def test_extract_json_payload_reads_trailing_json() -> None:
    output = """
    2026-04-11 INFO extract-news start
    {
      "domain": "kompas.com",
      "written_files": [
        "/tmp/content/news_article/kompas.com/a.json"
      ],
      "written_markdown_files": [
        "/tmp/content/news_article/kompas.com/a.md"
      ]
    }
    """

    payload = admin_ui._extract_json_payload(output)

    assert payload == {
        "domain": "kompas.com",
        "written_files": ["/tmp/content/news_article/kompas.com/a.json"],
        "written_markdown_files": ["/tmp/content/news_article/kompas.com/a.md"],
    }


def test_extract_json_payload_returns_none_for_non_json_output() -> None:
    assert admin_ui._extract_json_payload("no json here") is None


def test_seed_module_imports_as_script() -> None:
    import importlib.util
    from pathlib import Path

    seed_path = Path(admin_ui.__file__).resolve().parent / "seed.py"
    spec = importlib.util.spec_from_file_location("seed_script", seed_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert hasattr(module, "main")


def test_run_seed_and_load_reads_generated_links(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    links_path = settings.links_dir / "kompas.com.jsonl"
    write_links(
        links_path,
        [
            LinkRecord(url="https://example.com/a", scraped=False),
            LinkRecord(url="https://example.com/b", scraped=True),
        ],
    )

    monkeypatch.setattr(
        admin_ui,
        "run_seed_command",
        lambda domain: subprocess.CompletedProcess(
            args=["python", "-m", "src.seed", domain],
            returncode=0,
            stdout="seed ok",
            stderr="",
        ),
    )

    result = asyncio.run(admin_ui._run_seed_and_load("kompas.com", settings))

    assert result.domain == "kompas.com"
    assert result.links_path == links_path
    assert result.raw_jsonl.strip().splitlines() == [
        '{"url": "https://example.com/a", "scraped": false}',
        '{"url": "https://example.com/b", "scraped": true}',
    ]
    assert result.links == [
        LinkRecord(url="https://example.com/a", scraped=False),
        LinkRecord(url="https://example.com/b", scraped=True),
    ]
    assert result.output == "seed ok"
    assert result.returncode == 0
