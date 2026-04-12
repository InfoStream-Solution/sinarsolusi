from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import Settings, get_settings
from .links import LinkRecord, read_links
from .paths import links_jsonl_path


APP_DIR = Path(__file__).resolve().parents[1]
SUPPORTED_DOMAINS = ["kompas.com", "detik.com", "beritasatu.com"]


@dataclass(frozen=True)
class SeedRunResult:
    domain: str
    links_path: Path
    links: list[LinkRecord]
    raw_jsonl: str
    output: str
    returncode: int


def build_seed_command(domain: str) -> list[str]:
    return [sys.executable, "-m", "src.seed", domain]


def run_seed_command(domain: str) -> subprocess.CompletedProcess[str]:
    command = build_seed_command(domain)
    return subprocess.run(
        command,
        cwd=APP_DIR,
        check=False,
        text=True,
        capture_output=True,
    )


def run_extract_command(domain: str, limit: int) -> subprocess.CompletedProcess[str]:
    command = build_extract_command(domain, limit)
    return subprocess.run(
        command,
        cwd=APP_DIR,
        check=False,
        text=True,
        capture_output=True,
    )


def build_extract_command(domain: str, limit: int) -> list[str]:
    command = [sys.executable, "-m", "src.extract_news", domain]
    if limit > 0:
        command.extend(["--limit", str(limit)])
    return command


def build_group_command(domain: str, rebuild: bool) -> list[str]:
    command = [sys.executable, "-m", "src.group_news"]
    command.append("--rebuild" if rebuild else "--incremental")
    command.append(domain)
    return command


def run_group_command(domain: str, rebuild: bool) -> subprocess.CompletedProcess[str]:
    command = build_group_command(domain, rebuild)
    return subprocess.run(
        command,
        cwd=APP_DIR,
        check=False,
        text=True,
        capture_output=True,
    )


def links_to_rows(links: list[LinkRecord]) -> list[dict[str, object]]:
    return [
        {
            "url": link.url,
            "scraped": "yes" if link.scraped else "no",
        }
        for link in links
    ]


def _format_command_output(completed: subprocess.CompletedProcess[str]) -> str:
    parts = [completed.stdout.strip(), completed.stderr.strip()]
    return "\n".join(part for part in parts if part)


def _extract_json_payload(output: str) -> dict[str, object] | None:
    start = output.rfind("\n{")
    if start == -1:
        start = output.find("{")
    if start == -1:
        return None

    candidate = output[start + 1 :] if output[start] == "\n" else output[start:]
    candidate = candidate.strip()
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


async def _run_seed_and_load(domain: str, settings: Settings) -> SeedRunResult:
    import asyncio

    completed = await asyncio.to_thread(run_seed_command, domain)
    links_path = links_jsonl_path(settings.links_dir, domain)
    links = read_links(links_path) if links_path.exists() else []
    raw_jsonl = links_path.read_text(encoding="utf-8") if links_path.exists() else ""
    return SeedRunResult(
        domain=domain,
        links_path=links_path,
        links=links,
        raw_jsonl=raw_jsonl,
        output=_format_command_output(completed),
        returncode=completed.returncode,
    )


def _render_domain_select(ui: object, default: str) -> object:
    return ui.select(
        SUPPORTED_DOMAINS,
        value=default,
        label="Domain",
    ).classes("w-full")


def _render_shell(ui: object, title: str, subtitle: str) -> None:
    with ui.column().classes("mx-auto w-full max-w-5xl gap-6 p-6"):
        ui.label("News Scraper Admin").classes("text-2xl font-bold")
        ui.label("Manage scraper workflows from one place.").classes(
            "text-sm text-gray-600"
        )
        with ui.row().classes("items-center gap-3"):
            ui.link("Seed", "/seed")
            ui.link("Extract", "/extract")
            ui.link("Grouping", "/group")
        ui.label(title).classes("text-xl font-semibold")
        ui.label(subtitle).classes("text-sm text-gray-600")


def create_app() -> None:
    from nicegui import ui

    @ui.page("/")
    def index_page() -> None:
        ui.navigate.to("/seed")

    @ui.page("/seed")
    def seed_admin_page() -> None:
        settings = get_settings()
        ui.page_title("News Scraper Seed Admin")
        _render_shell(
            ui,
            "Seed",
            "Run seed for a domain and inspect the generated link queue.",
        )

        with ui.column().classes("mx-auto w-full max-w-5xl gap-6 p-6"):
            with ui.card().classes("w-full gap-4"):
                domain_input = _render_domain_select(ui, SUPPORTED_DOMAINS[0])
                status_label = ui.label("Idle").classes("text-sm text-gray-600")

                with ui.row().classes("items-center gap-3"):
                    run_button = ui.button("Run seed")
                    clear_button = ui.button("Clear results", color="secondary")

            with ui.card().classes("w-full gap-3"):
                ui.label("Summary").classes("text-lg font-semibold")
                summary_label = ui.label("No run yet").classes("text-sm")

            with ui.card().classes("w-full gap-3"):
                ui.label("Generated links").classes("text-lg font-semibold")
                table = ui.table(
                    columns=[
                        {
                            "name": "url",
                            "label": "URL",
                            "field": "url",
                            "align": "left",
                        },
                        {
                            "name": "scraped",
                            "label": "Scraped",
                            "field": "scraped",
                            "align": "left",
                        },
                    ],
                    rows=[],
                ).classes("w-full")

            with ui.card().classes("w-full gap-3"):
                ui.label("Raw JSONL").classes("text-lg font-semibold")
                raw_output = ui.textarea(value="").props("readonly").classes("w-full")

            def clear_results() -> None:
                summary_label.text = "No run yet"
                table.rows = []
                raw_output.value = ""
                status_label.text = "Idle"
                table.update()
                raw_output.update()
                summary_label.update()
                status_label.update()

            async def run_seed() -> None:
                domain = domain_input.value or ""
                if domain not in SUPPORTED_DOMAINS:
                    ui.notify("Select a supported domain.", type="warning")
                    return

                status_label.text = f"Running seed for {domain}..."
                run_button.disable()
                clear_button.disable()
                status_label.update()
                run_button.update()
                clear_button.update()

                try:
                    result = await _run_seed_and_load(domain, settings)
                except FileNotFoundError as exc:
                    status_label.text = f"Failed: {exc}"
                    ui.notify(str(exc), type="negative")
                    return
                finally:
                    run_button.enable()
                    clear_button.enable()
                    run_button.update()
                    clear_button.update()

                if result.returncode != 0:
                    message = result.output or f"seed exited with code {result.returncode}"
                    status_label.text = "Seed failed"
                    summary_label.text = message
                    raw_output.value = message
                    raw_output.update()
                    summary_label.update()
                    ui.notify("Seed run failed.", type="negative")
                    return

                table.rows = links_to_rows(result.links)
                table.update()
                raw_output.value = result.raw_jsonl
                raw_output.update()
                summary_label.text = (
                    f"Domain: {result.domain} | Links: {len(result.links)} | "
                    f"Path: {result.links_path}"
                )
                summary_label.update()
                status_label.text = "Seed completed"
                status_label.update()
                ui.notify(f"Seed completed for {domain}.", type="positive")

            run_button.on("click", run_seed)
            clear_button.on("click", lambda: clear_results())

    @ui.page("/extract")
    def extract_admin_page() -> None:
        ui.page_title("News Scraper Extract Admin")

        _render_shell(
            ui,
            "Extract",
            "Scrape pending article URLs from the generated seed queue.",
        )

        with ui.column().classes("mx-auto w-full max-w-5xl gap-6 p-6"):
            with ui.card().classes("w-full gap-4"):
                domain_input = _render_domain_select(ui, SUPPORTED_DOMAINS[0])
                status_label = ui.label("Idle").classes("text-sm text-gray-600")
                limit_input = ui.input(
                    label="Limit",
                    value="0",
                    placeholder="0",
                ).classes("w-full")

                with ui.row().classes("items-center gap-3"):
                    run_button = ui.button("Run extract")
                    clear_button = ui.button("Clear results", color="secondary")

            with ui.card().classes("w-full gap-3"):
                ui.label("Summary").classes("text-lg font-semibold")
                summary_label = ui.label("No run yet").classes("text-sm")

            with ui.card().classes("w-full gap-3"):
                ui.label("Extracted files").classes("text-lg font-semibold")
                extracted_files_table = ui.table(
                    columns=[
                        {
                            "name": "file",
                            "label": "File",
                            "field": "file",
                            "align": "left",
                        },
                    ],
                    rows=[],
                ).classes("w-full")

            with ui.card().classes("w-full gap-3"):
                ui.label("Command output").classes("text-lg font-semibold")
                raw_output = ui.textarea(value="").props("readonly").classes("w-full")

            def clear_results() -> None:
                summary_label.text = "No run yet"
                extracted_files_table.rows = []
                raw_output.value = ""
                status_label.text = "Idle"
                extracted_files_table.update()
                raw_output.update()
                summary_label.update()
                status_label.update()

            async def run_extract() -> None:
                domain = domain_input.value or ""
                if domain not in SUPPORTED_DOMAINS:
                    ui.notify("Select a supported domain.", type="warning")
                    return

                raw_limit = limit_input.value or "0"
                try:
                    limit = int(raw_limit)
                except ValueError:
                    ui.notify("Limit must be an integer.", type="warning")
                    return

                status_label.text = f"Running extract for {domain}..."
                run_button.disable()
                clear_button.disable()
                status_label.update()
                run_button.update()
                clear_button.update()

                try:
                    completed = await asyncio.to_thread(
                        run_extract_command,
                        domain,
                        limit,
                    )
                finally:
                    run_button.enable()
                    clear_button.enable()
                    run_button.update()
                    clear_button.update()

                output = _format_command_output(completed)
                payload = _extract_json_payload(output)
                if completed.returncode != 0:
                    status_label.text = "Extract failed"
                    summary_label.text = output or "extract command failed"
                    raw_output.value = output
                    raw_output.update()
                    summary_label.update()
                    ui.notify("Extract run failed.", type="negative")
                    return

                files = []
                if payload is not None:
                    files = [
                        str(item)
                        for item in payload.get("written_files", [])
                        if isinstance(item, str)
                    ]

                extracted_files_table.rows = [{"file": path} for path in files]
                extracted_files_table.update()
                summary_label.text = f"Domain: {domain} | Limit: {limit}"
                raw_output.value = output
                raw_output.update()
                summary_label.update()
                status_label.text = "Extract completed"
                status_label.update()
                ui.notify(f"Extract completed for {domain}.", type="positive")

            run_button.on("click", run_extract)
            clear_button.on("click", lambda: clear_results())

    @ui.page("/group")
    def group_admin_page() -> None:
        ui.page_title("News Scraper Group Admin")

        _render_shell(
            ui,
            "Grouping",
            "Cluster parsed articles into persistent topic groups.",
        )

        with ui.column().classes("mx-auto w-full max-w-5xl gap-6 p-6"):
            with ui.card().classes("w-full gap-4"):
                domain_input = _render_domain_select(ui, SUPPORTED_DOMAINS[0])
                status_label = ui.label("Idle").classes("text-sm text-gray-600")

                with ui.row().classes("items-center gap-3"):
                    rebuild_input = ui.switch("Rebuild database", value=False)
                    run_button = ui.button("Run grouping")
                    clear_button = ui.button("Clear results", color="secondary")

            with ui.card().classes("w-full gap-3"):
                ui.label("Summary").classes("text-lg font-semibold")
                summary_label = ui.label("No run yet").classes("text-sm")

            with ui.card().classes("w-full gap-3"):
                ui.label("Command output").classes("text-lg font-semibold")
                raw_output = ui.textarea(value="").props("readonly").classes("w-full")

            def clear_results() -> None:
                summary_label.text = "No run yet"
                raw_output.value = ""
                status_label.text = "Idle"
                raw_output.update()
                summary_label.update()
                status_label.update()

            async def run_grouping() -> None:
                domain = domain_input.value or ""
                if domain not in SUPPORTED_DOMAINS:
                    ui.notify("Select a supported domain.", type="warning")
                    return

                status_label.text = f"Running grouping for {domain}..."
                run_button.disable()
                clear_button.disable()
                status_label.update()
                run_button.update()
                clear_button.update()

                try:
                    completed = await asyncio.to_thread(
                        run_group_command,
                        domain,
                        bool(rebuild_input.value),
                    )
                finally:
                    run_button.enable()
                    clear_button.enable()
                    run_button.update()
                    clear_button.update()

                output = _format_command_output(completed)
                if completed.returncode != 0:
                    status_label.text = "Grouping failed"
                    summary_label.text = output or "grouping command failed"
                    raw_output.value = output
                    raw_output.update()
                    summary_label.update()
                    ui.notify("Grouping run failed.", type="negative")
                    return

                summary_label.text = (
                    f"Domain: {domain} | "
                    f"Mode: {'rebuild' if rebuild_input.value else 'incremental'}"
                )
                raw_output.value = output
                raw_output.update()
                summary_label.update()
                status_label.text = "Grouping completed"
                status_label.update()
                ui.notify(f"Grouping completed for {domain}.", type="positive")

            run_button.on("click", run_grouping)
            clear_button.on("click", lambda: clear_results())


def main() -> None:
    create_app()
    from nicegui import ui

    ui.run(title="News Scraper Seed Admin", reload=False, show=False)


if __name__ == "__main__":
    main()
