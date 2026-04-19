from __future__ import annotations

from django.urls import path

from . import api_views

app_name = "jobs_api"

urlpatterns = [
    path("domains/", api_views.enabled_domains, name="enabled-domains"),
    path(
        "domains/details/",
        api_views.enabled_domain_summaries,
        name="enabled-domain-summaries",
    ),
    path("domains/action/", api_views.domain_action, name="domain-action"),
    path("jobs/seed/", api_views.create_seed_job, name="seed-job-create"),
    path("jobs/<int:job_id>/", api_views.seed_job_status, name="seed-job-status"),
]
