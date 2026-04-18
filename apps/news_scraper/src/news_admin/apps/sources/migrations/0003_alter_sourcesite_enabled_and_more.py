from __future__ import annotations

from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("sources", "0002_sourcesitehost"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sourcesite",
            name="enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="sourcesitehost",
            name="enabled",
            field=models.BooleanField(default=False),
        ),
    ]
