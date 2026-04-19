from __future__ import annotations

import json
import os
from datetime import UTC
from datetime import datetime
from types import SimpleNamespace

import django
from django.http import Http404
from django.test import RequestFactory
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "news_admin.config.settings")
os.environ.setdefault(
    "DATA_DIR", "/home/ubuntu/projects/sinarsolusi/apps/news_scraper/.data"
)
django.setup()

from news_admin.apps.jobs import api_views  # noqa: E402
from news_admin.apps.jobs.models import ScrapeJob  # noqa: E402


def test_enabled_domains_returns_json(monkeypatch) -> None:
    request = RequestFactory().get("/api/dashboard/domains/")
    monkeypatch.setattr(api_views, "get_enabled_domains", lambda: ["kompas.com"])

    response = api_views.enabled_domains(request)

    assert response.status_code == 200
    assert json.loads(response.content) == {"domains": ["kompas.com"]}


def test_enabled_domain_summaries_returns_json(monkeypatch) -> None:
    request = RequestFactory().get("/api/dashboard/domains/details/")
    monkeypatch.setattr(
        api_views,
        "get_domain_summaries",
        lambda: [
            {
                "domain": "kompas.com",
                "enabled": True,
                "article_count": 12,
                "host_count": 2,
                "last_seed": "2026-04-19T10:30:00+00:00",
                "last_seed_status": "succeeded",
                "last_extract": "2026-04-19T11:00:00+00:00",
                "last_extract_status": "running",
                "last_import": "2026-04-19T11:15:00+00:00",
                "last_import_status": "queued",
                "hosts": ["www.kompas.com", "kompas.id"],
            }
        ],
    )

    response = api_views.enabled_domain_summaries(request)

    assert response.status_code == 200
    assert json.loads(response.content) == {
        "domains": [
            {
                "domain": "kompas.com",
                "enabled": True,
                "article_count": 12,
                "host_count": 2,
                "last_seed": "2026-04-19T10:30:00+00:00",
                "last_seed_status": "succeeded",
                "last_extract": "2026-04-19T11:00:00+00:00",
                "last_extract_status": "running",
                "last_import": "2026-04-19T11:15:00+00:00",
                "last_import_status": "queued",
                "hosts": ["www.kompas.com", "kompas.id"],
            }
        ]
    }


def test_domain_action_queues_pipeline(monkeypatch) -> None:
    request = RequestFactory().post(
        "/api/dashboard/domains/action/",
        data=json.dumps({"domain": "kompas.com", "action": "pipeline"}),
        content_type="application/json",
    )
    monkeypatch.setattr(api_views, "get_enabled_domains", lambda: ["kompas.com"])
    monkeypatch.setattr(
        api_views,
        "queue_domain_action",
        lambda domain, action: {"queued": True, "domain": domain, "action": action},
    )

    response = api_views.domain_action(request)

    assert response.status_code == 201
    payload = json.loads(response.content)
    assert payload == {"queued": True, "domain": "kompas.com", "action": "pipeline"}


def test_create_seed_job_rejects_empty_domain() -> None:
    request = RequestFactory().post(
        "/api/dashboard/jobs/seed/",
        data=json.dumps({"domain": ""}),
        content_type="application/json",
    )

    response = api_views.create_seed_job(request)

    assert response.status_code == 400


def test_create_seed_job_queues_background_job(monkeypatch) -> None:
    request = RequestFactory().post(
        "/api/dashboard/jobs/seed/",
        data=json.dumps({"domain": "kompas.com"}),
        content_type="application/json",
    )
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
    monkeypatch.setattr(api_views, "get_enabled_domains", lambda: ["kompas.com"])
    monkeypatch.setattr(
        api_views, "queue_seed_job", lambda domain: (created_job, True)
    )

    response = api_views.create_seed_job(request)

    assert response.status_code == 201
    payload = json.loads(response.content)
    assert payload["job_id"] == 7
    assert payload["created"] is True


def test_seed_job_status_returns_404_for_non_seed_job(monkeypatch) -> None:
    request = RequestFactory().get("/api/dashboard/jobs/9/")
    job = SimpleNamespace(
        id=9,
        job_type=ScrapeJob.JobType.POST,
        domain="kompas.com",
        status=ScrapeJob.Status.SUCCEEDED,
        params={},
        result_summary={},
        error_message="",
        created_at=datetime(2026, 4, 19, 10, 30, tzinfo=UTC),
        started_at=None,
        finished_at=None,
    )
    monkeypatch.setattr(api_views.ScrapeJob.objects, "get", lambda pk: job)

    with pytest.raises(Http404):
        api_views.seed_job_status(request, job_id=9)
