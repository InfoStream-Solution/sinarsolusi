from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from ..links import LinkMetaRecord


class BaseStore(ABC):
    @abstractmethod
    def upsert_discovered_links(
        self,
        domain: str,
        urls: list[str],
        *,
        discovered_at: str,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_meta_records(self, domain: str) -> list[LinkMetaRecord]:
        raise NotImplementedError

    @abstractmethod
    def list_pending_news_urls(self, domain: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def mark_scraped(self, domain: str, url: str, *, scraped_at: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def mark_failed(
        self,
        domain: str,
        url: str,
        *,
        scraped_at: str,
        error_code: str,
        error_message: str,
    ) -> None:
        raise NotImplementedError
