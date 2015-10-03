# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('index', '0007_auto_20151002_0506'),
    ]

    operations = [
        migrations.AddField(
            model_name='backingindex',
            name='last_update_serial',
            field=models.BigIntegerField(null=True, blank=True),
        ),
    ]
