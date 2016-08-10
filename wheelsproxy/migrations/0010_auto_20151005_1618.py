# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wheelsproxy', '0009_auto_20151002_0655'),
    ]

    operations = [
        migrations.AddField(
            model_name='package',
            name='name',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='package',
            name='slug',
            field=models.SlugField(max_length=255),
        ),
    ]
