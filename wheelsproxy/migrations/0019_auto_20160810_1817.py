# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-10 18:17
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wheelsproxy', '0018_remove_release_original_details'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompiledRequirements',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requirements', models.TextField()),
                ('pip_compilation_status', models.CharField(choices=[(b'pending', 'Pending'), (b'done', 'Done'), (b'failed', 'Failed')], default=b'pending', max_length=12)),
                ('pip_compiled_requirements', models.TextField(blank=True)),
                ('pip_compilation_timestamp', models.DateTimeField(blank=True, editable=False, null=True)),
                ('pip_compilation_duration', models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ('pip_compilation_log', models.TextField(blank=True, editable=False)),
                ('internal_compilation_status', models.CharField(choices=[(b'pending', 'Pending'), (b'done', 'Done'), (b'failed', 'Failed')], default=b'pending', max_length=12)),
                ('internal_compiled_requirements', models.TextField(blank=True)),
                ('internal_compilation_timestamp', models.DateTimeField(blank=True, editable=False, null=True)),
                ('internal_compilation_duration', models.PositiveIntegerField(blank=True, editable=False, null=True)),
                ('internal_compilation_log', models.TextField(blank=True, editable=False)),
                ('platform', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='wheelsproxy.Platform')),
            ],
        ),
        migrations.AlterField(
            model_name='release',
            name='url',
            field=models.URLField(blank=True, default=b'', max_length=255, verbose_name='URL'),
        ),
    ]
