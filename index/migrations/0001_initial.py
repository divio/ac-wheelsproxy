# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.files.storage
import index.models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BackingIndex',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(unique=True)),
                ('url', models.URLField()),
            ],
        ),
        migrations.CreateModel(
            name='Build',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('build', models.FileField(storage=django.core.files.storage.FileSystemStorage(), upload_to=index.models.upload_build_to)),
            ],
        ),
        migrations.CreateModel(
            name='Package',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField()),
                ('index', models.ForeignKey(to='index.BackingIndex')),
            ],
        ),
        migrations.CreateModel(
            name='Platform',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(unique=True)),
                ('type', models.CharField(max_length=16, choices=[(b'docker', 'Docker')])),
                ('spec', jsonfield.fields.JSONField()),
            ],
        ),
        migrations.CreateModel(
            name='Release',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version', models.CharField(max_length=32)),
                ('package', models.ForeignKey(to='index.Package')),
            ],
        ),
        migrations.AddField(
            model_name='build',
            name='platform',
            field=models.ForeignKey(to='index.Platform'),
        ),
        migrations.AddField(
            model_name='build',
            name='release',
            field=models.ForeignKey(to='index.Release'),
        ),
        migrations.AlterUniqueTogether(
            name='release',
            unique_together=set([('package', 'version')]),
        ),
        migrations.AlterUniqueTogether(
            name='package',
            unique_together=set([('slug', 'index')]),
        ),
    ]
