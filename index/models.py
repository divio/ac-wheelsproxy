import sys
import os

import requests

import jsonfield

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from . import storage


class BackingIndex(models.Model):
    slug = models.SlugField(unique=True)
    url = models.URLField()

    def get_package_details_url(self, package_name, version=None):
        url = '{}/{}'.format(self.url.rstrip('/'), package_name)
        if version:
            url = '{}/{}'.format(url, version)
        url = '{}/{}'.format(url, 'json')
        return url

    def get_package_details(self, package_name, version=None):
        url = self.get_package_details_url(package_name, version)
        response = requests.get(url)
        assert response.status_code < 300
        return response.json()


class Package(models.Model):
    slug = models.SlugField()
    index = models.ForeignKey(BackingIndex)

    class Meta:
        unique_together = ('slug', 'index')

    def __str__(self):
        return self.slug


class Release(models.Model):
    package = models.ForeignKey(Package)
    version = models.CharField(max_length=32)

    class Meta:
        unique_together = ('package', 'version')

    def __str__(self):
        return '{}-{}'.format(self.package.slug, self.version)

    def get_original_release_url(self):
        def sorting_key(release):
            # Prefer wheels, but only if they are py 2/3 compatible
            # without arch:
            if release['packagetype'] == 'bdist_wheel':
                if release['python_version'] == 'py2.py3':
                    spec = release['filename'].split('-')
                    if spec[-2] != 'none':
                        return sys.maxsize
                    elif spec[-1] != 'any.whl':
                        return sys.maxsize
                    else:
                        return 0  # Best match
                else:
                    return sys.maxsize  # Worst match
            elif release['packagetype'] == 'sdist':
                return 1  # We would still prefer wheels
            else:
                return sys.maxsize

        details = self.package.index.get_package_details(
            self.package.slug, self.version)
        try:
            releases = details['releases'][self.version]
        except KeyError:
            return None
        for release in sorted(releases, key=sorting_key):
            return release['url']
        else:
            return None

    def create_build(self, platform):
        original_url = self.get_original_release_url()
        if not original_url:
            raise RuntimeError('Could not find a package URL')
        return Build.objects.create(
            platform=platform,
            release=self,
            original_url=original_url,
        )


class Platform(models.Model):
    DOCKER = 'docker'
    PLATFORM_CHOICES = [
        (DOCKER, _('Docker'))
    ]

    slug = models.SlugField(unique=True)
    type = models.CharField(max_length=16, choices=PLATFORM_CHOICES)
    spec = jsonfield.JSONField()

    def __str__(self):
        return self.slug


def upload_build_to(self, filename):
    return '{index}/{package}/{version}/{platform}.whl'.format(
        index=self.release.package.index.slug,
        package=self.release.package.slug,
        version=self.release.version,
        platform=self.platform.slug,
    )


class Build(models.Model):
    release = models.ForeignKey(Release)
    platform = models.ForeignKey(Platform)
    original_url = models.URLField()
    build = models.FileField(storage=storage.builds_storage,
                             upload_to=upload_build_to,
                             blank=True, null=True)

    class Meta:
        unique_together = ('release', 'platform')

    def get_build_url(self):
        if self.build:
            return self.build.url
        else:
            return self.original_url

    def get_filename(self):
        if self.build:
            path = self.build.name
        else:
            path = self.original_url
        return os.path.basename(path)

    def get_absolute_url(self):
        return reverse('index:download_release', kwargs={
            'version': self.release.version,
            'package_name': self.release.package.slug,
            'filename': self.get_filename(),
        })
