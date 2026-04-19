from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from news_admin.apps.jobs.models import ScrapeJob

from .forms import SeedJobForm
from .services import get_enabled_domains
from .services import queue_seed_job
from .services import serialize_job


@staff_member_required
@require_GET
def seed_dashboard(request: HttpRequest) -> HttpResponse:
    domains = get_enabled_domains()
    form = SeedJobForm(
        domains=domains, initial={"domain": domains[0] if domains else ""}
    )
    return render(
        request,
        "dashboard/seed_dashboard.html",
        {
            "form": form,
            "domains": domains,
            "has_domains": bool(domains),
        },
    )


@staff_member_required
@require_POST
def create_seed_job(request: HttpRequest) -> JsonResponse:
    domains = get_enabled_domains()
    form = SeedJobForm(request.POST, domains=domains)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    job, created = queue_seed_job(form.cleaned_data["domain"])
    payload = serialize_job(job)
    payload["created"] = created
    return JsonResponse(payload, status=201 if created else 200)


@staff_member_required
@require_GET
def seed_job_status(request: HttpRequest, job_id: int) -> JsonResponse:
    try:
        job = ScrapeJob.objects.get(pk=job_id)
    except ScrapeJob.DoesNotExist as exc:
        raise Http404("Seed job not found.") from exc

    if job.job_type != ScrapeJob.JobType.SEED:
        raise Http404("Seed job not found.")

    return JsonResponse(serialize_job(job))
