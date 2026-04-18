from __future__ import annotations

import os
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "news_admin.config.settings")
os.environ.setdefault("DATA_DIR", "/home/ubuntu/projects/sinarsolusi/apps/news_scraper/.data")
django.setup()

import news_admin.apps.articles.admin as article_admin  # noqa: E402
from news_admin.apps.jobs import tasks  # noqa: E402
from news_admin.apps.jobs.models import ScrapeJob  # noqa: E402


def test_enqueue_refresh_job_queues_background_run(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeJob:
        id = 123

    def fake_create(**kwargs):
        captured["create_kwargs"] = kwargs
        return FakeJob()

    monkeypatch.setattr(ScrapeJob.objects, "create", fake_create)
    monkeypatch.setattr(
        article_admin.transaction,
        "on_commit",
        lambda callback: callback(),
    )
    monkeypatch.setattr(
        article_admin.run_scrape_job,
        "delay",
        lambda job_id: captured.setdefault("queued_job_id", job_id),
    )

    article = SimpleNamespace(
        id=415,
        source_site="kompas.com",
        url="https://nasional.kompas.com/read/2026/04/17/10304621/example?page=all",
    )

    job = article_admin._enqueue_refresh_job(article)

    assert job.id == 123
    assert captured["create_kwargs"]["job_type"] == ScrapeJob.JobType.REFRESH
    assert captured["create_kwargs"]["domain"] == "kompas.com"
    assert captured["create_kwargs"]["params"] == {"article_id": 415}
    assert captured["queued_job_id"] == 123


def test_run_scrape_job_refresh_branch_refreshes_article(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeJob:
        def __init__(self) -> None:
            self.id = 99
            self.job_type = ScrapeJob.JobType.REFRESH
            self.domain = "kompas.com"
            self.params = {"article_id": 415}
            self.status = ScrapeJob.Status.QUEUED
            self.started_at = None
            self.finished_at = None
            self.result_summary = {}
            self.error_message = ""

        def save(self, update_fields=None):
            captured.setdefault("save_calls", []).append(list(update_fields or []))

    fake_job = FakeJob()
    fake_article = SimpleNamespace(id=415, url="https://example.test/article", source_site="kompas.com")

    monkeypatch.setattr(tasks.ScrapeJob.objects, "get", lambda pk: fake_job)
    monkeypatch.setattr(tasks.Article.objects, "get", lambda pk: fake_article)
    monkeypatch.setattr(
        tasks,
        "refresh_article_from_source",
        lambda article: (
            captured.__setitem__("refreshed_article", article),
            {"article_id": article.id, "url": article.url},
        )[1],
    )

    result = tasks.run_scrape_job(99)

    assert captured["refreshed_article"] is fake_article
    assert result["article_id"] == 415
    assert result["url"] == "https://example.test/article"
    assert fake_job.status == ScrapeJob.Status.SUCCEEDED
