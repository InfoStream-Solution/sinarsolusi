from __future__ import annotations

from django.contrib import admin
from django.urls import include
from django.urls import path

urlpatterns = [
    path("dashboard/", include("news_admin.apps.dashboard.urls")),
    path("api/dashboard/", include("news_admin.apps.jobs.api_urls")),
    path("admin/", admin.site.urls),
]
