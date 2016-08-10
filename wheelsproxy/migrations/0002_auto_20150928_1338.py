# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.files.storage
import wheelsproxy.models


class Migration(migrations.Migration):

    dependencies = [
        ('wheelsproxy', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='build',
            name='original_url',
            field=models.URLField(default=''),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='build',
            name='build',
            field=models.FileField(storage=django.core.files.storage.FileSystemStorage(), null=True, upload_to=wheelsproxy.models.upload_build_to, blank=True),
        ),
    ]
