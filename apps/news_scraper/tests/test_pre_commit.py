from __future__ import annotations

import subprocess

from src import pre_commit


def test_normalize_text_file_strips_trailing_whitespace(tmp_path) -> None:
    path = tmp_path / "example.md"
    path.write_text("line one  \nline two\t\n", encoding="utf-8")

    changed = pre_commit._normalize_text_file(path)

    assert changed is True
    assert path.read_text(encoding="utf-8") == "line one\nline two\n"


def test_should_normalize_skips_hidden_directories(tmp_path) -> None:
    path = tmp_path / ".data" / "scraped" / "article.html"

    assert pre_commit._should_normalize(path) is False


def test_pre_commit_runs_cleanup_ruff_then_pytest(monkeypatch) -> None:
    calls: list[tuple[list[str], str]] = []

    def fake_run(command, cwd=None, check=None):
        calls.append((list(command), str(cwd)))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        pre_commit, "_normalize_text_files", lambda: calls.append((["normalize"], ""))
    )
    monkeypatch.setattr(pre_commit.subprocess, "run", fake_run)

    pre_commit.main()

    assert calls[0][0] == ["normalize"]
    assert calls[1][0][1:6] == ["-m", "ruff", "check", "--fix", "."]
    assert calls[2][0][1:4] == ["-m", "ruff", "format"]
    assert calls[3][0][1:3] == ["-m", "pytest"]
    assert calls[1][1] == calls[2][1] == calls[3][1]
