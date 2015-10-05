# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0003_auto_20150928_1427'),
    ]

    operations = [
        migrations.AddField(
            model_name='build',
            name='md5_digest',
            field=models.CharField(default='', max_length=32),
            preserve_default=False,
        ),
    ]
