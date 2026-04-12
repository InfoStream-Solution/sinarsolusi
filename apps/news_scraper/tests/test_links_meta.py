from __future__ import annotations

from pathlib import Path

from src.links import (
    LinkMetaRecord,
    ensure_link_meta_records,
    read_link_meta,
    update_link_meta_record,
    write_link_meta,
)


def test_write_and_read_link_meta(tmp_path: Path) -> None:
    path = tmp_path / "links.meta.json"
    records = [
        LinkMetaRecord(
            url="https://example.com/a",
            discovered_at="2026-04-11T00:00:00+07:00",
            scraped=False,
            last_scraped_at=None,
            error_code=None,
            error_message=None,
        )
    ]

    write_link_meta(path, records)

    assert read_link_meta(path) == records


def test_ensure_link_meta_records_skips_existing_urls() -> None:
    existing = [
        LinkMetaRecord(
            url="https://example.com/a",
            discovered_at="2026-04-11T00:00:00+07:00",
            scraped=True,
            last_scraped_at="2026-04-11T00:10:00+07:00",
            error_code=None,
            error_message=None,
        )
    ]

    updated = ensure_link_meta_records(
        existing,
        ["https://example.com/a", "https://example.com/b"],
    )

    assert [record.url for record in updated] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert updated[0].scraped is True
    assert updated[1].scraped is False
    assert updated[1].last_scraped_at is None
    assert updated[1].error_code is None
    assert updated[1].error_message is None


def test_update_link_meta_record_sets_success_state() -> None:
    records = [
        LinkMetaRecord(
            url="https://example.com/a",
            discovered_at="2026-04-11T00:00:00+07:00",
            scraped=False,
            last_scraped_at=None,
            error_code="TimeoutError",
            error_message="timeout",
        )
    ]

    updated = update_link_meta_record(
        records,
        "https://example.com/a",
        scraped=True,
    )

    assert updated[0].scraped is True
    assert updated[0].last_scraped_at is not None
    assert updated[0].error_code is None
    assert updated[0].error_message is None


def test_update_link_meta_record_sets_failure_state() -> None:
    records = [
        LinkMetaRecord(
            url="https://example.com/a",
            discovered_at="2026-04-11T00:00:00+07:00",
            scraped=True,
            last_scraped_at="2026-04-11T00:10:00+07:00",
            error_code=None,
            error_message=None,
        )
    ]

    updated = update_link_meta_record(
        records,
        "https://example.com/a",
        scraped=False,
        error_code="HTTPError",
        error_message="500",
    )

    assert updated[0].scraped is False
    assert updated[0].last_scraped_at is not None
    assert updated[0].error_code == "HTTPError"
    assert updated[0].error_message == "500"
