from __future__ import annotations

from pathlib import Path

from src.links import (
    LinkRecord,
    extract_internal_links,
    normalize_links,
    page_output_name,
    read_links,
    write_links,
)


def test_extract_internal_links_filters_and_deduplicates() -> None:
    html = """
    <a href="/news/a#section">A</a>
    <a href="https://www.example.com/news/a">dup</a>
    <a href="https://www.example.com/news/b">B</a>
    <a href="https://other.example.com/news/c">C</a>
    <a href="mailto:test@example.com">mail</a>
    """

    links = extract_internal_links(
        "https://www.example.com",
        html,
        allowed_hosts={"example.com", "www.example.com"},
    )

    assert [link.url for link in links] == [
        "https://www.example.com/news/a",
        "https://www.example.com/news/b",
    ]
    assert all(link.discovered_at for link in links)


def test_write_read_and_mark_links(tmp_path: Path) -> None:
    path = tmp_path / "links.jsonl"
    links = [
        LinkRecord(url="https://example.com/a", discovered_at="2026-04-11T00:00:00+07:00"),
        LinkRecord(url="https://example.com/b", discovered_at="2026-04-11T00:01:00+07:00"),
    ]

    write_links(path, links)
    assert read_links(path) == links


def test_normalize_links_merges_scraped_state() -> None:
    links = [
        LinkRecord(url="https://example.com/a#one", discovered_at="2026-04-11T00:00:00+07:00"),
        LinkRecord(url="https://example.com/a#two", discovered_at="2026-04-11T00:01:00+07:00"),
        LinkRecord(url="https://example.com/b", discovered_at="2026-04-11T00:02:00+07:00"),
    ]

    normalized = normalize_links(links, lambda url: url.split("#", 1)[0])

    assert normalized == [
        LinkRecord(url="https://example.com/a", discovered_at="2026-04-11T00:00:00+07:00"),
        LinkRecord(url="https://example.com/b", discovered_at="2026-04-11T00:02:00+07:00"),
    ]


def test_page_output_name_is_stable() -> None:
    assert page_output_name("https://example.com/a") == page_output_name(
        "https://example.com/a"
    )
