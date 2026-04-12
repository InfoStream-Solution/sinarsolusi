from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.group_news as group_news
from src.config import Settings
from src.models import ParsedContent


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
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


def write_article(path: Path, article: ParsedContent) -> None:
    path.write_text(article.to_json(), encoding="utf-8")


def make_article(
    *,
    title: str,
    url: str,
    source_site: str,
    summary: str,
    content: str,
) -> ParsedContent:
    return ParsedContent(
        content_type="news_article",
        title=title,
        url=url,
        source_site=source_site,
        category=None,
        published_at=None,
        author=None,
        summary=summary,
        content=content,
        word_count=len(content.split()),
        char_count=len(content),
        scraped_at="2026-04-11T00:00:00+07:00",
    )


def test_group_news_clusters_similar_cross_site_articles(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kompas_dir = settings.content_dir / "news_article" / "kompas.com"
    detik_dir = settings.content_dir / "news_article" / "detik.com"
    beritasatu_dir = settings.content_dir / "news_article" / "beritasatu.com"
    kompas_dir.mkdir(parents=True, exist_ok=True)
    detik_dir.mkdir(parents=True, exist_ok=True)
    beritasatu_dir.mkdir(parents=True, exist_ok=True)

    write_article(
        kompas_dir / "kompas.json",
        make_article(
            title="Prabowo Hadiri Munas XVI PB IPSI 2026 di JCC",
            url="https://kompas.com/a",
            source_site="kompas.com",
            summary="Presiden hadir di Munas IPSI.",
            content="Prabowo hadir dalam Munas IPSI 2026 di JCC.",
        ),
    )

    def fake_get_settings() -> Settings:
        return settings

    monkeypatch.setattr(group_news, "get_settings", fake_get_settings)
    monkeypatch.setattr(group_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(group_news, "get_logger", lambda name: SimpleNamespace(info=lambda *args, **kwargs: None))
    monkeypatch.setattr(
        group_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="kompas.com", rebuild=True, incremental=False)
        ),
    )

    group_news.main()

    write_article(
        detik_dir / "detik.json",
        make_article(
            title="Prabowo Hadiri Munas XVI PB IPSI 2026 di JCC, DetikNews",
            url="https://detik.com/b",
            source_site="detik.com",
            summary="Munas IPSI digelar di JCC.",
            content="Prabowo menghadiri Munas IPSI 2026 di JCC.",
        ),
    )
    write_article(
        beritasatu_dir / "beritasatu.json",
        make_article(
            title="Dihadiri Prabowo, Munas IPSI 2026 Jadi Momentum Nasional",
            url="https://beritasatu.com/c",
            source_site="beritasatu.com",
            summary="Munas IPSI menjadi momentum nasional.",
            content="Prabowo menghadiri Munas IPSI 2026 bersama para peserta.",
        ),
    )

    monkeypatch.setattr(
        group_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="detik.com", rebuild=False, incremental=True)
        ),
    )
    group_news.main()

    monkeypatch.setattr(
        group_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="beritasatu.com", rebuild=False, incremental=True)
        ),
    )
    group_news.main()

    db_path = settings.content_dir / "news_group" / "news_group.sqlite3"
    assert db_path.exists()

    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT title, source_site, group_id FROM topic_group_articles ORDER BY title"
        ).fetchall()
    finally:
        connection.close()

    group_to_titles: dict[str, set[str]] = {}
    for title, _source_site, group_id in rows:
        group_to_titles.setdefault(group_id, set()).add(title)

    assert len(group_to_titles) == 1
    munas_group = next(iter(group_to_titles.values()))
    assert munas_group == {
        "Prabowo Hadiri Munas XVI PB IPSI 2026 di JCC",
        "Prabowo Hadiri Munas XVI PB IPSI 2026 di JCC, DetikNews",
        "Dihadiri Prabowo, Munas IPSI 2026 Jadi Momentum Nasional",
    }


def test_group_news_is_incremental_and_idempotent(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles_dir = settings.content_dir / "news_article" / "kompas.com"
    articles_dir.mkdir(parents=True, exist_ok=True)
    write_article(
        articles_dir / "one.json",
        make_article(
            title="Prabowo Hadiri Munas IPSI",
            url="https://kompas.com/a",
            source_site="kompas.com",
            summary="Prabowo hadir.",
            content="Munas IPSI digelar di JCC.",
        ),
    )
    monkeypatch.setattr(group_news, "get_settings", lambda: settings)
    monkeypatch.setattr(group_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        group_news,
        "get_logger",
        lambda name: SimpleNamespace(info=lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        group_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="kompas.com", rebuild=True, incremental=False)
        ),
    )

    group_news.main()
    group_news.main()

    db_path = settings.content_dir / "news_group" / "news_group.sqlite3"
    connection = sqlite3.connect(db_path)
    try:
        group_rows = connection.execute(
            "SELECT group_id, article_count FROM topic_groups"
        ).fetchall()
        article_rows = connection.execute(
            "SELECT article_path, group_id FROM topic_group_articles"
        ).fetchall()
        event_rows = connection.execute(
            "SELECT group_id, article_path FROM topic_group_events"
        ).fetchall()
    finally:
        connection.close()

    assert len(group_rows) == 1
    assert group_rows[0][1] == 1
    assert len(article_rows) == 1
    assert len(event_rows) == 1


def test_group_news_ignores_extra_article_fields(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles_dir = settings.content_dir / "news_article" / "kompas.com"
    articles_dir.mkdir(parents=True, exist_ok=True)
    payload = make_article(
        title="Prabowo Hadiri Munas IPSI",
        url="https://kompas.com/a",
        source_site="kompas.com",
        summary="Prabowo hadir.",
        content="Munas IPSI digelar di JCC.",
    )
    data = json.loads(payload.to_json())
    data["posted_at"] = "2026-04-11T14:00:00+07:00"
    (articles_dir / "one.json").write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr(group_news, "get_settings", lambda: settings)
    monkeypatch.setattr(group_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        group_news,
        "get_logger",
        lambda name: SimpleNamespace(info=lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        group_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="kompas.com", rebuild=True, incremental=False)
        ),
    )

    group_news.main()

    db_path = settings.content_dir / "news_group" / "news_group.sqlite3"
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT title FROM topic_group_articles"
        ).fetchall()
    finally:
        connection.close()

    assert rows == [("Prabowo Hadiri Munas IPSI",)]


def test_group_news_skips_posted_marker_files(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles_dir = settings.content_dir / "news_article" / "kompas.com"
    articles_dir.mkdir(parents=True, exist_ok=True)
    write_article(
        articles_dir / "one.json",
        make_article(
            title="Prabowo Hadiri Munas IPSI",
            url="https://kompas.com/a",
            source_site="kompas.com",
            summary="Prabowo hadir.",
            content="Munas IPSI digelar di JCC.",
        ),
    )
    (articles_dir / "one.posted.json").write_text(
        json.dumps({"posted_at": "2026-04-11T14:00:00+07:00"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(group_news, "get_settings", lambda: settings)
    monkeypatch.setattr(group_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        group_news,
        "get_logger",
        lambda name: SimpleNamespace(info=lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        group_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="kompas.com", rebuild=True, incremental=False)
        ),
    )

    group_news.main()

    db_path = settings.content_dir / "news_group" / "news_group.sqlite3"
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT article_path FROM topic_group_articles"
        ).fetchall()
    finally:
        connection.close()

    assert rows == [(str(articles_dir / "one.json"),)]


def test_group_news_rebuild_deletes_existing_database(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles_dir = settings.content_dir / "news_article" / "kompas.com"
    articles_dir.mkdir(parents=True, exist_ok=True)
    write_article(
        articles_dir / "one.json",
        make_article(
            title="Prabowo Hadiri Munas IPSI",
            url="https://kompas.com/a",
            source_site="kompas.com",
            summary="Prabowo hadir.",
            content="Munas IPSI digelar di JCC.",
        ),
    )

    db_path = settings.content_dir / "news_group" / "news_group.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text("old-db", encoding="utf-8")

    monkeypatch.setattr(group_news, "get_settings", lambda: settings)
    monkeypatch.setattr(group_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        group_news,
        "get_logger",
        lambda name: SimpleNamespace(info=lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        group_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="kompas.com", rebuild=True)
        ),
    )

    group_news.main()

    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute(
            "SELECT article_path FROM topic_group_articles"
        ).fetchall()
    finally:
        connection.close()

    assert rows == [(str(articles_dir / "one.json"),)]


def test_group_news_incremental_preserves_existing_database(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    articles_dir = settings.content_dir / "news_article" / "kompas.com"
    articles_dir.mkdir(parents=True, exist_ok=True)
    write_article(
        articles_dir / "one.json",
        make_article(
            title="Prabowo Hadiri Munas IPSI",
            url="https://kompas.com/a",
            source_site="kompas.com",
            summary="Prabowo hadir.",
            content="Munas IPSI digelar di JCC.",
        ),
    )

    monkeypatch.setattr(group_news, "get_settings", lambda: settings)
    monkeypatch.setattr(group_news, "configure_logging", lambda debug: None)
    monkeypatch.setattr(
        group_news,
        "get_logger",
        lambda name: SimpleNamespace(info=lambda *args, **kwargs: None),
    )
    monkeypatch.setattr(
        group_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="kompas.com", rebuild=True, incremental=False)
        ),
    )

    group_news.main()

    write_article(
        articles_dir / "two.json",
        make_article(
            title="Prabowo Hadiri Munas IPSI 2026",
            url="https://kompas.com/b",
            source_site="kompas.com",
            summary="Prabowo hadir lagi.",
            content="Munas IPSI berlangsung di JCC.",
        ),
    )
    monkeypatch.setattr(
        group_news,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(domain="kompas.com", rebuild=False, incremental=True)
        ),
    )

    group_news.main()

    db_path = settings.content_dir / "news_group" / "news_group.sqlite3"
    connection = sqlite3.connect(db_path)
    try:
        article_rows = connection.execute(
            "SELECT article_path FROM topic_group_articles ORDER BY article_path"
        ).fetchall()
        group_rows = connection.execute(
            "SELECT group_id, article_count FROM topic_groups"
        ).fetchall()
    finally:
        connection.close()

    assert article_rows == [
        (str(articles_dir / "one.json"),),
        (str(articles_dir / "two.json"),),
    ]
    assert len(group_rows) == 1
    assert group_rows[0][1] == 2
