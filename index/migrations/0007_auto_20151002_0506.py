# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0006_auto_20151002_0503'),
    ]

    operations = [
        migrations.AlterField(
            model_name='release',
            name='version',
            field=models.CharField(max_length=200),
        ),
    ]
