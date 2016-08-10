# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import jsonfield.fields
import wheelsproxy.storage
import wheelsproxy.models


class Migration(migrations.Migration):

    dependencies = [
        ('wheelsproxy', '0004_build_md5_digest'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='build',
            name='original_url',
        ),
        migrations.AddField(
            model_name='release',
            name='original_details',
            field=jsonfield.fields.JSONField(default='{}'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='build',
            name='build',
            field=models.FileField(storage=wheelsproxy.storage.dsn_configured_storage('BUILDS_STORAGE_DSN'), null=True, upload_to=wheelsproxy.models.upload_build_to, blank=True),
        ),
        migrations.AlterField(
            model_name='build',
            name='md5_digest',
            field=models.CharField(default=b'', max_length=32, blank=True),
        ),
    ]
