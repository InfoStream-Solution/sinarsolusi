from __future__ import annotations

from pathlib import Path

from news_scraper_core.links import LinkMetaRecord
from news_scraper_core.store.db import DbStore


def test_db_store_upserts_and_reads_records(tmp_path: Path) -> None:
    store = DbStore(f"sqlite:///{tmp_path / 'news_scraper.db'}")

    store.upsert_discovered_links(
        "example.com",
        ["https://example.com/news/a"],
        discovered_at="2026-04-11T00:00:00+07:00",
    )
    store.mark_scraped(
        "example.com",
        "https://example.com/news/a",
        scraped_at="2026-04-11T00:10:00+07:00",
    )
    store.upsert_discovered_links(
        "example.com",
        ["https://example.com/news/a", "https://example.com/news/b"],
        discovered_at="2026-04-11T00:20:00+07:00",
    )

    records = store.list_meta_records("example.com")

    assert records == [
        LinkMetaRecord(
            url="https://example.com/news/a",
            discovered_at="2026-04-11T00:00:00+07:00",
            scraped=True,
            last_scraped_at="2026-04-11T00:10:00+07:00",
            error_code=None,
            error_message=None,
        ),
        LinkMetaRecord(
            url="https://example.com/news/b",
            discovered_at="2026-04-11T00:20:00+07:00",
            scraped=False,
            last_scraped_at=None,
            error_code=None,
            error_message=None,
        ),
    ]


def test_db_store_reports_pending_urls(tmp_path: Path) -> None:
    store = DbStore(f"sqlite:///{tmp_path / 'news_scraper.db'}")
    store.upsert_discovered_links(
        "example.com",
        [
            "https://example.com/news/a",
            "https://example.com/news/b",
        ],
        discovered_at="2026-04-11T00:00:00+07:00",
    )
    store.mark_scraped(
        "example.com",
        "https://example.com/news/a",
        scraped_at="2026-04-11T00:10:00+07:00",
    )

    assert store.list_pending_news_urls("example.com") == [
        "https://example.com/news/b",
    ]
