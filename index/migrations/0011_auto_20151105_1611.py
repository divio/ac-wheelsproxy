# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import index.storage
import index.models


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0010_auto_20151005_1618'),
    ]

    operations = [
        migrations.AlterField(
            model_name='build',
            name='build',
            field=models.FileField(storage=index.storage.OverwritingS3Storage(), max_length=255, null=True, upload_to=index.models.upload_build_to, blank=True),
        ),
    ]
