# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import wheelsproxy.storage
import wheelsproxy.models


class Migration(migrations.Migration):

    dependencies = [
        ('wheelsproxy', '0010_auto_20151005_1618'),
    ]

    operations = [
        migrations.AlterField(
            model_name='build',
            name='build',
            field=models.FileField(storage=wheelsproxy.storage.dsn_configured_storage('BUILDS_STORAGE_DSN'), max_length=255, null=True, upload_to=wheelsproxy.models.upload_build_to, blank=True),
        ),
    ]
