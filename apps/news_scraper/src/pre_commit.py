from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_TEXT_FILE_NAMES = {
    ".editorconfig",
    ".env.example",
    ".gitignore",
    "Dockerfile",
    "LICENSE",
    "Makefile",
    "Procfile",
    "README.md",
}
_TEXT_FILE_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".markdown",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
_SKIP_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_step(label: str, command: list[str]) -> None:
    print(f"[quality] {label}: {' '.join(command)}")
    subprocess.run(command, cwd=_repo_root(), check=True)


def _should_normalize(path: Path) -> bool:
    if any(part in _SKIP_DIR_NAMES or part.startswith(".") for part in path.parts[:-1]):
        return False
    return path.name in _TEXT_FILE_NAMES or path.suffix.lower() in _TEXT_FILE_SUFFIXES


def _normalize_text_file(path: Path) -> bool:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    if not raw_text:
        return False

    normalized = "\n".join(line.rstrip() for line in raw_text.splitlines()) + "\n"
    if normalized == raw_text:
        return False

    path.write_text(normalized, encoding="utf-8")
    try:
        display_path = path.relative_to(_repo_root())
    except ValueError:
        display_path = path
    print(f"[quality] normalized {display_path}")
    return True


def _normalize_text_files() -> None:
    root = _repo_root()
    for path in sorted(root.rglob("*")):
        if path.is_file() and _should_normalize(path):
            _normalize_text_file(path)


def main() -> None:
    _normalize_text_files()
    _run_step("ruff", [sys.executable, "-m", "ruff", "check", "--fix", "."])
    _run_step("ruff format", [sys.executable, "-m", "ruff", "format", "."])
    _run_step("pytest", [sys.executable, "-m", "pytest"])
