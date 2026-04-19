from __future__ import annotations

from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.seed_dashboard, name="seed-dashboard"),
    path("jobs/seed/", views.create_seed_job, name="seed-job-create"),
    path("jobs/<int:job_id>/", views.seed_job_status, name="seed-job-status"),
]
