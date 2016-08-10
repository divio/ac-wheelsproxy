# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wheelsproxy', '0005_auto_20150929_0747'),
    ]

    operations = [
        migrations.AlterField(
            model_name='package',
            name='slug',
            field=models.SlugField(max_length=200),
        ),
    ]
