# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('wheelsproxy', '0008_backingindex_last_update_serial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='package',
            options={'ordering': ('slug',)},
        ),
        migrations.AlterModelOptions(
            name='release',
            options={'ordering': ('package', 'version')},
        ),
        migrations.AddField(
            model_name='build',
            name='build_duration',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='build',
            name='build_log',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='build',
            name='build_timestamp',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='build',
            name='filesize',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='release',
            name='last_update',
            field=models.DateTimeField(default=datetime.datetime(2015, 10, 2, 6, 55, 1, 711175, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
    ]
