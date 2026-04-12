from __future__ import annotations

import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

from .base import BaseStore
from ..links import LinkMetaRecord


class DbStore(BaseStore):
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.backend = self._detect_backend(database_url)
        self._initialize()

    def _detect_backend(self, database_url: str) -> str:
        if database_url.startswith("sqlite:///") or database_url.endswith(".db"):
            return "sqlite"
        parsed = urlparse(database_url)
        if parsed.scheme in {"postgres", "postgresql"}:
            return "postgres"
        raise ValueError(f"Unsupported database URL: {database_url}")

    def _schema_path(self) -> Path:
        filename = "schema.postgres.sql" if self.backend == "postgres" else "schema.sqlite.sql"
        return Path(__file__).with_name(filename)

    def _connect_sqlite(self) -> sqlite3.Connection:
        path = self.database_url.replace("sqlite:///", "", 1)
        connection = sqlite3.connect(path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _connect_postgres(self) -> psycopg.Connection:
        connection = psycopg.connect(self.database_url, row_factory=dict_row)
        connection.autocommit = False
        return connection

    def _connect(self):
        if self.backend == "postgres":
            return self._connect_postgres()
        return self._connect_sqlite()

    def _initialize(self) -> None:
        schema_path = self._schema_path()
        schema = schema_path.read_text(encoding="utf-8")
        statements = [statement.strip() for statement in schema.split(";") if statement.strip()]
        with self._connect() as connection:
            if self.backend == "postgres":
                connection.execute("SET lock_timeout = '5s'")
                connection.execute("SET statement_timeout = '30s'")
            for statement in statements:
                connection.execute(statement)

    def upsert_discovered_links(
        self,
        domain: str,
        urls: list[str],
        *,
        discovered_at: str,
    ) -> None:
        if not urls:
            return

        if self.backend == "postgres":
            self._upsert_discovered_links_postgres(domain, urls, discovered_at=discovered_at)
        else:
            self._upsert_discovered_links_sqlite(domain, urls, discovered_at=discovered_at)

    def _upsert_discovered_links_sqlite(
        self,
        domain: str,
        urls: list[str],
        *,
        discovered_at: str,
    ) -> None:
        rows = [
            (
                domain,
                url,
                discovered_at,
                discovered_at,
            )
            for url in urls
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO link_meta (
                    domain,
                    url,
                    discovered_at,
                    scraped,
                    last_scraped_at,
                    error_code,
                    error_message,
                    updated_at
                )
                VALUES (?, ?, ?, 0, NULL, NULL, NULL, ?)
                ON CONFLICT(domain, url) DO NOTHING
                """,
                rows,
            )

    def _upsert_discovered_links_postgres(
        self,
        domain: str,
        urls: list[str],
        *,
        discovered_at: str,
    ) -> None:
        rows = [
            (
                domain,
                url,
                discovered_at,
                discovered_at,
            )
            for url in urls
        ]
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO link_meta (
                        domain,
                        url,
                        discovered_at,
                        scraped,
                        last_scraped_at,
                        error_code,
                        error_message,
                        updated_at
                    )
                    VALUES (%s, %s, %s, FALSE, NULL, NULL, NULL, %s)
                    ON CONFLICT (domain, url) DO NOTHING
                    """,
                    rows,
                )

    def list_meta_records(self, domain: str) -> list[LinkMetaRecord]:
        if self.backend == "postgres":
            return self._list_meta_records_postgres(domain)
        return self._list_meta_records_sqlite(domain)

    def _list_meta_records_sqlite(self, domain: str) -> list[LinkMetaRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT url, discovered_at, scraped, last_scraped_at, error_code, error_message
                FROM link_meta
                WHERE domain = ?
                ORDER BY url
                """,
                (domain,),
            ).fetchall()
        return [
            LinkMetaRecord(
                url=row["url"],
                discovered_at=row["discovered_at"],
                scraped=bool(row["scraped"]),
                last_scraped_at=row["last_scraped_at"],
                error_code=row["error_code"],
                error_message=row["error_message"],
            )
            for row in rows
        ]

    def _list_meta_records_postgres(self, domain: str) -> list[LinkMetaRecord]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT url, discovered_at, scraped, last_scraped_at, error_code, error_message
                    FROM link_meta
                    WHERE domain = %s
                    ORDER BY url
                    """,
                    (domain,),
                )
                rows = cursor.fetchall()
        return [
            LinkMetaRecord(
                url=row["url"],
                discovered_at=row["discovered_at"],
                scraped=bool(row["scraped"]),
                last_scraped_at=row["last_scraped_at"],
                error_code=row["error_code"],
                error_message=row["error_message"],
            )
            for row in rows
        ]

    def list_pending_news_urls(self, domain: str) -> list[str]:
        if self.backend == "postgres":
            return self._list_pending_news_urls_postgres(domain)
        return self._list_pending_news_urls_sqlite(domain)

    def _list_pending_news_urls_sqlite(self, domain: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT url
                FROM link_meta
                WHERE domain = ? AND scraped = 0
                ORDER BY url
                """,
                (domain,),
            ).fetchall()
        return [row["url"] for row in rows]

    def _list_pending_news_urls_postgres(self, domain: str) -> list[str]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT url
                    FROM link_meta
                    WHERE domain = %s AND scraped = FALSE
                    ORDER BY url
                    """,
                    (domain,),
                )
                rows = cursor.fetchall()
        return [row["url"] for row in rows]

    def mark_scraped(self, domain: str, url: str, *, scraped_at: str) -> None:
        if self.backend == "postgres":
            self._mark_scraped_postgres(domain, url, scraped_at=scraped_at)
        else:
            self._mark_scraped_sqlite(domain, url, scraped_at=scraped_at)

    def _mark_scraped_sqlite(self, domain: str, url: str, *, scraped_at: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE link_meta
                SET scraped = 1,
                    last_scraped_at = ?,
                    error_code = NULL,
                    error_message = NULL,
                    updated_at = ?
                WHERE domain = ? AND url = ?
                """,
                (scraped_at, scraped_at, domain, url),
            )

    def _mark_scraped_postgres(self, domain: str, url: str, *, scraped_at: str) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE link_meta
                    SET scraped = TRUE,
                        last_scraped_at = %s,
                        error_code = NULL,
                        error_message = NULL,
                        updated_at = %s
                    WHERE domain = %s AND url = %s
                    """,
                    (scraped_at, scraped_at, domain, url),
                )

    def mark_failed(
        self,
        domain: str,
        url: str,
        *,
        scraped_at: str,
        error_code: str,
        error_message: str,
    ) -> None:
        if self.backend == "postgres":
            self._mark_failed_postgres(
                domain,
                url,
                scraped_at=scraped_at,
                error_code=error_code,
                error_message=error_message,
            )
        else:
            self._mark_failed_sqlite(
                domain,
                url,
                scraped_at=scraped_at,
                error_code=error_code,
                error_message=error_message,
            )

    def _mark_failed_sqlite(
        self,
        domain: str,
        url: str,
        *,
        scraped_at: str,
        error_code: str,
        error_message: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE link_meta
                SET scraped = 0,
                    last_scraped_at = ?,
                    error_code = ?,
                    error_message = ?,
                    updated_at = ?
                WHERE domain = ? AND url = ?
                """,
                (scraped_at, error_code, error_message, scraped_at, domain, url),
            )

    def _mark_failed_postgres(
        self,
        domain: str,
        url: str,
        *,
        scraped_at: str,
        error_code: str,
        error_message: str,
    ) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE link_meta
                    SET scraped = FALSE,
                        last_scraped_at = %s,
                        error_code = %s,
                        error_message = %s,
                        updated_at = %s
                    WHERE domain = %s AND url = %s
                    """,
                    (scraped_at, error_code, error_message, scraped_at, domain, url),
                )
