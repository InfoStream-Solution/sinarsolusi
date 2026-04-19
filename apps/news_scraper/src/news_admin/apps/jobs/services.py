from __future__ import annotations

from datetime import UTC
from datetime import datetime

from django.db import transaction

from news_admin.apps.articles.models import Article
from news_admin.apps.jobs.models import ScrapeJob
from news_admin.apps.jobs.tasks import run_pipeline_domain
from news_admin.apps.jobs.tasks import run_scrape_job
from news_admin.apps.sources.models import SourceSite
from news_admin.apps.sources.models import SourceSiteHost


def get_enabled_domains() -> list[str]:
    return list(
        SourceSite.objects.filter(enabled=True).order_by("domain").values_list(
            "domain", flat=True
        )
    )


def get_domain_summaries() -> list[dict[str, object]]:
    domains = list(SourceSite.objects.order_by("domain").values_list("domain", flat=True))
    summaries: list[dict[str, object]] = []

    for domain in domains:
        site = SourceSite.objects.filter(domain=domain).first()
        seed_job = _latest_job(domain, ScrapeJob.JobType.SEED)
        extract_job = _latest_job(domain, ScrapeJob.JobType.EXTRACT)
        import_job = _latest_job(domain, ScrapeJob.JobType.IMPORT_ARTICLES)
        summaries.append(
            {
                "domain": domain,
                "enabled": bool(site.enabled) if site is not None else False,
                "article_count": Article.objects.filter(source_site=domain).count(),
                "host_count": _host_count(domain),
                "last_seed": _job_timestamp(seed_job),
                "last_seed_status": _job_status(seed_job),
                "last_extract": _job_timestamp(extract_job),
                "last_extract_status": _job_status(extract_job),
                "last_import": _job_timestamp(import_job),
                "last_import_status": _job_status(import_job),
                "hosts": _hosts(domain),
            }
        )

    return summaries


def get_enabled_domain_summaries() -> list[dict[str, object]]:
    return [summary for summary in get_domain_summaries() if summary["enabled"]]


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
    return _queue_job(domain, ScrapeJob.JobType.SEED)


def queue_extract_job(domain: str) -> tuple[ScrapeJob, bool]:
    return _queue_job(domain, ScrapeJob.JobType.EXTRACT)


def queue_import_articles_job(domain: str) -> tuple[ScrapeJob, bool]:
    return _queue_job(domain, ScrapeJob.JobType.IMPORT_ARTICLES)


def queue_domain_action(
    domain: str, action: str
) -> dict[str, object]:
    if action == "seed":
        job, created = queue_seed_job(domain)
        payload = serialize_job(job)
        payload["created"] = created
        return {"job": payload}
    if action == "extract":
        job, created = queue_extract_job(domain)
        payload = serialize_job(job)
        payload["created"] = created
        return {"job": payload}
    if action == "import":
        job, created = queue_import_articles_job(domain)
        payload = serialize_job(job)
        payload["created"] = created
        return {"job": payload}
    if action == "pipeline":
        transaction.on_commit(lambda: run_pipeline_domain.delay(domain))
        return {"queued": True, "action": action, "domain": domain}
    raise ValueError(f"Unsupported action: {action}")


def _queue_job(
    domain: str, job_type: str, *, params: dict[str, object] | None = None
) -> tuple[ScrapeJob, bool]:
    job = ScrapeJob.objects.create(
        job_type=job_type,
        domain=domain,
        params=params or {},
    )
    transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))
    return job, True


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC).isoformat()
    return value.isoformat()


def _latest_job(domain: str, job_type: str) -> ScrapeJob | None:
    return (
        ScrapeJob.objects.filter(domain=domain, job_type=job_type)
        .order_by("-created_at")
        .first()
    )


def _hosts(domain: str) -> list[str]:
    return list(
        SourceSiteHost.objects.filter(source_site__domain=domain)
        .order_by("host")
        .values_list("host", flat=True)
    )


def _host_count(domain: str) -> int:
    return SourceSiteHost.objects.filter(source_site__domain=domain).count()


def _job_timestamp(job: ScrapeJob | None) -> str | None:
    if job is None:
        return None
    return _serialize_datetime(job.finished_at or job.started_at or job.created_at)


def _job_status(job: ScrapeJob | None) -> str | None:
    if job is None:
        return None
    return job.status
