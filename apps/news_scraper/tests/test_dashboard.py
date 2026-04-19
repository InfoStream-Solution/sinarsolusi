from __future__ import annotations

import json
import os
from datetime import UTC
from datetime import datetime
from types import SimpleNamespace

import django
from django.test import RequestFactory

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "news_admin.config.settings")
os.environ.setdefault(
    "DATA_DIR", "/home/ubuntu/projects/sinarsolusi/apps/news_scraper/.data"
)
django.setup()

import news_admin.apps.dashboard.services as dashboard_services  # noqa: E402
import news_admin.apps.dashboard.views as dashboard_views  # noqa: E402
from news_admin.apps.jobs.models import ScrapeJob  # noqa: E402


def _staff_user() -> SimpleNamespace:
    return SimpleNamespace(is_active=True, is_staff=True)


def test_seed_dashboard_renders_enabled_domains(monkeypatch) -> None:
    request = RequestFactory().get("/dashboard/")
    request.user = _staff_user()
    monkeypatch.setattr(
        dashboard_services, "get_enabled_domains", lambda: ["kompas.com"]
    )
    monkeypatch.setattr(dashboard_views, "get_enabled_domains", lambda: ["kompas.com"])

    response = dashboard_views.seed_dashboard(request)

    assert response.status_code == 200
    assert b"kompas.com" in response.content
    assert b"Run Seed" in response.content


def test_create_seed_job_queues_job_and_serializes_payload(monkeypatch) -> None:
    request = RequestFactory().post(
        "/dashboard/jobs/seed/", data={"domain": "kompas.com"}
    )
    request.user = _staff_user()
    monkeypatch.setattr(
        dashboard_services, "get_enabled_domains", lambda: ["kompas.com"]
    )
    monkeypatch.setattr(dashboard_views, "get_enabled_domains", lambda: ["kompas.com"])

    created_job = SimpleNamespace(
        id=7,
        job_type=ScrapeJob.JobType.SEED,
        domain="kompas.com",
        status=ScrapeJob.Status.QUEUED,
        params={},
        result_summary={},
        error_message="",
        created_at=datetime(2026, 4, 19, 10, 30, tzinfo=UTC),
        started_at=None,
        finished_at=None,
    )
    captured: dict[str, object] = {}

    def fake_queue_seed_job(domain: str):
        captured["domain"] = domain
        return created_job, True

    monkeypatch.setattr(dashboard_views, "queue_seed_job", fake_queue_seed_job)

    response = dashboard_views.create_seed_job(request)

    assert response.status_code == 201
    assert captured["domain"] == "kompas.com"
    payload = json.loads(response.content)
    assert payload["job_id"] == 7
    assert payload["created"] is True
    assert payload["status"] == ScrapeJob.Status.QUEUED


def test_create_seed_job_always_enqueues_a_fresh_job(monkeypatch) -> None:
    request = RequestFactory().post(
        "/dashboard/jobs/seed/", data={"domain": "kompas.com"}
    )
    request.user = _staff_user()
    monkeypatch.setattr(
        dashboard_services, "get_enabled_domains", lambda: ["kompas.com"]
    )
    monkeypatch.setattr(dashboard_views, "get_enabled_domains", lambda: ["kompas.com"])

    fresh_job = SimpleNamespace(
        id=8,
        job_type=ScrapeJob.JobType.SEED,
        domain="kompas.com",
        status=ScrapeJob.Status.QUEUED,
        params={},
        result_summary={},
        error_message="",
        created_at=datetime(2026, 4, 19, 10, 31, tzinfo=UTC),
        started_at=None,
        finished_at=None,
    )

    monkeypatch.setattr(
        dashboard_views, "queue_seed_job", lambda domain: (fresh_job, True)
    )

    response = dashboard_views.create_seed_job(request)

    assert response.status_code == 201
    payload = json.loads(response.content)
    assert payload["job_id"] == 8
    assert payload["created"] is True
    assert payload["status"] == ScrapeJob.Status.QUEUED


def test_seed_job_status_serializes_payload(monkeypatch) -> None:
    request = RequestFactory().get("/dashboard/jobs/7/")
    request.user = _staff_user()
    job = SimpleNamespace(
        id=7,
        job_type=ScrapeJob.JobType.SEED,
        domain="kompas.com",
        status=ScrapeJob.Status.SUCCEEDED,
        params={"keep_seed": True},
        result_summary={"link_count": 9},
        error_message="",
        created_at=datetime(2026, 4, 19, 10, 30, tzinfo=UTC),
        started_at=datetime(2026, 4, 19, 10, 31, tzinfo=UTC),
        finished_at=datetime(2026, 4, 19, 10, 32, tzinfo=UTC),
    )
    monkeypatch.setattr(dashboard_views.ScrapeJob.objects, "get", lambda pk: job)

    response = dashboard_views.seed_job_status(request, job_id=7)

    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload["job_id"] == 7
    assert payload["status"] == ScrapeJob.Status.SUCCEEDED
    assert payload["result_summary"] == {"link_count": 9}


def test_queue_seed_job_creates_a_new_job(monkeypatch) -> None:
    created_job = SimpleNamespace(
        id=22,
        job_type=ScrapeJob.JobType.SEED,
        domain="kompas.com",
        status=ScrapeJob.Status.QUEUED,
        params={},
        result_summary={},
        error_message="",
        created_at=datetime(2026, 4, 19, 10, 31, tzinfo=UTC),
        started_at=None,
        finished_at=None,
    )
    captured: dict[str, object] = {}

    def fake_create(**kwargs):
        captured["create_kwargs"] = kwargs
        return created_job

    monkeypatch.setattr(
        dashboard_services.ScrapeJob.objects,
        "create",
        fake_create,
    )
    monkeypatch.setattr(
        dashboard_services.transaction,
        "on_commit",
        lambda callback: callback(),
    )
    monkeypatch.setattr(
        dashboard_services.run_scrape_job,
        "delay",
        lambda job_id: captured.setdefault("queued_job_id", job_id),
    )

    job, was_created = dashboard_services.queue_seed_job("kompas.com")

    assert job is created_job
    assert was_created is True
    assert captured["create_kwargs"]["job_type"] == ScrapeJob.JobType.SEED
    assert captured["create_kwargs"]["domain"] == "kompas.com"
    assert captured["queued_job_id"] == 22
