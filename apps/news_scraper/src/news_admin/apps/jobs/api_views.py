from __future__ import annotations

import json

from django.http import Http404
from django.http import HttpRequest
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from .models import ScrapeJob
from .services import get_domain_summaries
from .services import get_enabled_domains
from .services import queue_domain_action
from .services import queue_seed_job
from .services import serialize_job


@require_GET
def enabled_domains(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"domains": get_enabled_domains()})


@require_GET
def enabled_domain_summaries(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"domains": get_domain_summaries()})


@require_POST
@csrf_exempt
def domain_action(request: HttpRequest) -> JsonResponse:
    payload = _read_json_body(request)
    domain = str(payload.get("domain", "")).strip()
    action = str(payload.get("action", "")).strip()

    if not domain:
        return JsonResponse({"error": "Domain is required."}, status=400)
    if action not in {"seed", "extract", "import", "pipeline"}:
        return JsonResponse({"error": "Unsupported action."}, status=400)

    enabled_domains = get_enabled_domains()
    if domain not in enabled_domains:
        return JsonResponse(
            {
                "errors": {
                    "domain": ["Select a valid choice from the enabled domains."]
                }
            },
            status=400,
        )

    try:
        payload = queue_domain_action(domain, action)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(payload, status=201)


@require_POST
@csrf_exempt
def create_seed_job(request: HttpRequest) -> JsonResponse:
    payload = _read_json_body(request)
    domain = str(payload.get("domain", "")).strip()

    if not domain:
        return JsonResponse({"error": "Domain is required."}, status=400)

    enabled_domains = get_enabled_domains()
    if domain not in enabled_domains:
        return JsonResponse(
            {
                "errors": {
                    "domain": ["Select a valid choice from the enabled domains."]
                }
            },
            status=400,
        )

    job, created = queue_seed_job(domain)
    response = serialize_job(job)
    response["created"] = created
    return JsonResponse(response, status=201 if created else 200)


@require_GET
def seed_job_status(request: HttpRequest, job_id: int) -> JsonResponse:
    try:
        job = ScrapeJob.objects.get(pk=job_id)
    except ScrapeJob.DoesNotExist as exc:
        raise Http404("Seed job not found.") from exc

    if job.job_type != ScrapeJob.JobType.SEED:
        raise Http404("Seed job not found.")

    return JsonResponse(serialize_job(job))


def _read_json_body(request: HttpRequest) -> dict[str, object]:
    if not request.body:
        return {}
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(body, dict):
        return body
    return {}
