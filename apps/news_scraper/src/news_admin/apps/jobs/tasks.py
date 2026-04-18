from __future__ import annotations

from datetime import datetime, UTC

from celery import shared_task
from django.db import transaction

from news_scraper_core import extract_news, post_news, scrape, seed

from news_admin.apps.articles.models import Article
from news_admin.apps.articles.services import import_articles_for_domain
from news_admin.apps.articles.services import refresh_article_from_source
from news_admin.apps.sources.models import SourceSite
from .models import ScrapeJob


def _mark_job_running(job: ScrapeJob) -> None:
    job.status = ScrapeJob.Status.RUNNING
    job.started_at = datetime.now(UTC)
    job.save(update_fields=["status", "started_at"])


def _mark_job_done(job: ScrapeJob, *, result_summary: dict[str, object]) -> None:
    job.status = ScrapeJob.Status.SUCCEEDED
    job.result_summary = result_summary
    job.finished_at = datetime.now(UTC)
    job.save(update_fields=["status", "result_summary", "finished_at"])


def _mark_job_failed(job: ScrapeJob, exc: Exception) -> None:
    job.status = ScrapeJob.Status.FAILED
    job.error_message = f"{type(exc).__name__}: {exc}"
    job.finished_at = datetime.now(UTC)
    job.save(update_fields=["status", "error_message", "finished_at"])


def _enqueue_job(job_type: str, domain: str, *, params: dict[str, object] | None = None) -> ScrapeJob:
    job = ScrapeJob.objects.create(
        job_type=job_type,
        domain=domain,
        params=params or {},
    )
    transaction.on_commit(lambda job_id=job.id: run_scrape_job.delay(job_id))
    return job


@shared_task
def seed_domain(domain: str) -> dict[str, object]:
    job = _enqueue_job(ScrapeJob.JobType.SEED, domain)
    return {"job_id": job.id, "domain": domain, "job_type": job.job_type}


@shared_task
def seed_enabled_sources() -> dict[str, object]:
    jobs: list[dict[str, object]] = []
    for site in SourceSite.objects.filter(enabled=True).order_by("domain"):
        job = _enqueue_job(ScrapeJob.JobType.SEED, site.domain)
        jobs.append({"job_id": job.id, "domain": site.domain, "job_type": job.job_type})
    return {"enqueued": len(jobs), "jobs": jobs}


@shared_task
def extract_domain(domain: str) -> dict[str, object]:
    job = _enqueue_job(ScrapeJob.JobType.EXTRACT, domain)
    return {"job_id": job.id, "domain": domain, "job_type": job.job_type}


@shared_task
def extract_enabled_sources() -> dict[str, object]:
    jobs: list[dict[str, object]] = []
    for site in SourceSite.objects.filter(enabled=True).order_by("domain"):
        job = _enqueue_job(ScrapeJob.JobType.EXTRACT, site.domain)
        jobs.append({"job_id": job.id, "domain": site.domain, "job_type": job.job_type})
    return {"enqueued": len(jobs), "jobs": jobs}


@shared_task
def import_articles_domain(domain: str) -> dict[str, object]:
    job = _enqueue_job(ScrapeJob.JobType.IMPORT_ARTICLES, domain)
    return {"job_id": job.id, "domain": domain, "job_type": job.job_type}


@shared_task
def import_articles_enabled_sources() -> dict[str, object]:
    jobs: list[dict[str, object]] = []
    for site in SourceSite.objects.filter(enabled=True).order_by("domain"):
        job = _enqueue_job(ScrapeJob.JobType.IMPORT_ARTICLES, site.domain)
        jobs.append({"job_id": job.id, "domain": site.domain, "job_type": job.job_type})
    return {"enqueued": len(jobs), "jobs": jobs}


@shared_task
def run_scrape_job(job_id: int) -> dict[str, object]:
    job = ScrapeJob.objects.get(pk=job_id)
    _mark_job_running(job)
    import_summary: dict[str, object] | None = None
    try:
        if job.job_type == ScrapeJob.JobType.SEED:
            seed.main(["seed", job.domain])
        elif job.job_type == ScrapeJob.JobType.EXTRACT:
            extract_news.main(["extract-news", job.domain])
        elif job.job_type == ScrapeJob.JobType.POST:
            post_news.main(["post-news", job.domain])
        elif job.job_type == ScrapeJob.JobType.SCRAPE:
            url = str(job.params["url"])
            scrape.main(["scrape", job.domain, "--url", url])
        elif job.job_type == ScrapeJob.JobType.REFRESH:
            article_id = int(job.params["article_id"])
            article = Article.objects.get(pk=article_id)
            import_summary = refresh_article_from_source(article)
        elif job.job_type == ScrapeJob.JobType.IMPORT_ARTICLES:
            import_summary = import_articles_for_domain(job.domain)
        else:
            raise ValueError(f"Unsupported job type: {job.job_type}")
    except Exception as exc:
        _mark_job_failed(job, exc)
        raise

    result = {"job_id": job.id, "job_type": job.job_type, "domain": job.domain}
    if import_summary is not None:
        result.update(import_summary)
    _mark_job_done(job, result_summary=result)
    return result


@shared_task
def noop() -> str:
    return "ok"
