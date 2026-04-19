from __future__ import annotations

from datetime import datetime
from datetime import timezone

from django.db import transaction

from news_admin.apps.jobs.models import ScrapeJob
from news_admin.apps.jobs.tasks import run_scrape_job
from news_admin.apps.sources.models import SourceSite


def get_enabled_domains() -> list[str]:
    return list(
        SourceSite.objects.filter(enabled=True)
        .order_by("domain")
        .values_list("domain", flat=True)
    )


def serialize_job(job: ScrapeJob) -> dict[str, object]:
    return {
        "job_id": job.id,
        "job_type": job.job_type,
        "domain": job.domain,
        "status": job.status,
        "params": job.params,
        "result_summary": job.result_summary,
        "error_message": job.error_message,
        "created_at": _serialize_datetime(job.created_at),
        "started_at": _serialize_datetime(job.started_at),
        "finished_at": _serialize_datetime(job.finished_at),
    }


def queue_seed_job(domain: str) -> tuple[ScrapeJob, bool]:
    job = ScrapeJob.objects.create(
        job_type=ScrapeJob.JobType.SEED,
        domain=domain,
    )
    transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))
    return job, True


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.isoformat()
