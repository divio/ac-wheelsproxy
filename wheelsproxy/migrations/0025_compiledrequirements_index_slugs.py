# -*- coding: utf-8 -*-
# Generated by Django 1.10.1 on 2016-09-13 12:49
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wheelsproxy', '0024_auto_20160908_2206'),
    ]

    operations = [
        migrations.AddField(
            model_name='compiledrequirements',
            name='index_slugs',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.SlugField(), default=[], size=None),
            preserve_default=False,
        ),
    ]
