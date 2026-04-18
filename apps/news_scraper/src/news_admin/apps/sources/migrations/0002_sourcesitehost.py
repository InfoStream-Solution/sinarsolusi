from __future__ import annotations

from django.db import migrations
from django.db import models
from django.db.models import deletion


class Migration(migrations.Migration):
    dependencies = [
        ("sources", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SourceSiteHost",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("host", models.CharField(max_length=255)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "source_site",
                    models.ForeignKey(
                        on_delete=deletion.CASCADE,
                        related_name="hosts",
                        to="sources.sourcesite",
                    ),
                ),
            ],
            options={
                "ordering": ["host"],
            },
        ),
        migrations.AddConstraint(
            model_name="sourcesitehost",
            constraint=models.UniqueConstraint(
                fields=("source_site", "host"),
                name="uniq_source_site_host",
            ),
        ),
    ]
