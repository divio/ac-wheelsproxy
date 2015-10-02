import os

import requests

import jsonfield

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from . import storage, tasks, builder




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

    def get_builder(self):
        # TODO: If we need to support more platform types here (e.g. VM based)
        assert self.type == self.DOCKER
        return builder.DockerBuilder(self.spec)


class BackingIndex(models.Model):
    slug = models.SlugField(unique=True)
    url = models.URLField()

    def __str__(self):
        return self.slug

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

    def get_package(self, package_name):
        package, created = Package.objects.get_or_create(
            index=self, slug=package_name)
        return package


class Package(models.Model):
    slug = models.SlugField()
    index = models.ForeignKey(BackingIndex)

    class Meta:
        unique_together = ('slug', 'index')

    def __str__(self):
        return self.slug

    def get_best_release(self, releases):
        for release in releases:
            if release['packagetype'] == 'sdist':
                return release
            elif release['packagetype'] == 'bdist_wheel':
                if release['filename'].endswith('-py2.py3-none-any.whl'):
                    return release

    def get_release(self, version, details=None):
        release, created = Release.objects.get_or_create(
            package=self, version=version)
        if created:
            if details:
                release.original_details = details
            else:
                info = self.index.get_package_details(self.slug, version)
                releases = info['releases'][version]
                release.original_details = self.get_best_release(releases)
            assert release.original_details
            release.save()
        return release


class Release(models.Model):
    package = models.ForeignKey(Package)
    version = models.CharField(max_length=32)
    original_details = jsonfield.JSONField()

    class Meta:
        unique_together = ('package', 'version')

    def __str__(self):
        return '{}-{}'.format(self.package.slug, self.version)

    def get_build(self, platform):
        build, created = Build.objects.get_or_create(
            release=self, platform=platform)
        return build


def upload_build_to(self, filename):
    return '{index}/{package}/{version}/{platform}/{filename}'.format(
        index=self.release.package.index.slug,
        package=self.release.package.slug,
        version=self.release.version,
        platform=self.platform.slug,
        filename=filename,
    )


class Build(models.Model):
    release = models.ForeignKey(Release)
    platform = models.ForeignKey(Platform)
    md5_digest = models.CharField(max_length=32, default='', blank=True)
    build = models.FileField(storage=storage.builds_storage,
                             upload_to=upload_build_to,
                             blank=True, null=True)

    # TODO: Add fields for:
    # - Downloads
    # - Build timestsamp
    # - Build time
    # - Build logs
    # - Filesize

    class Meta:
        unique_together = ('release', 'platform')

    def __str__(self):
        return self.filename

    def rebuild(self):
        builder = self.platform.get_builder()
        builder(self)

    def schedule_build(self, force=False):
        return tasks.build.delay(self.pk, force=force)

    def get_build_url(self, build_if_needed=False):
        if self.build:
            return self.build.url
        else:
            if build_if_needed:
                self.schedule_build()
            return self.original_url

    @property
    def filename(self):
        if self.build:
            path = self.build.name
        else:
            path = self.original_url
        return os.path.basename(path)

    @property
    def original_url(self):
        try:
            return self.release.original_details['url']
        except TypeError:
            return ''

    def get_absolute_url(self):
        if self.build:
            # NOTE: Return the final URL directly if the build is already
            # available, so that we can avoid one additional request to get the
            # redirect. This prevents us from collecting stats about package
            # activity, but given the problems we're trying to solve with the
            # proxy, this is an acceptable compromise.
            # TODO: Make this behaviour configurable with a settings directive.
            return self.get_build_url()
        else:
            return reverse('index:download_build', kwargs={
                'platform_slug': self.platform.slug,
                'version': self.release.version,
                'package_name': self.release.package.slug,
                'filename': self.filename,
                'build_id': self.pk,
            })

    def to_pypi_dict(self):
        details = self.release.original_details
        if self.build:
            # TODO: Provide these values
            # details['upload_time']
            # details['python_version']
            # details['downloads']
            # details['size']
            details['filename'] = self.filename
            details['packagetype'] = 'bdist_wheel'
            details['md5_digest'] = self.md5_digest
            # NOTE: Ignored fields
            # details['has_sig']
            # details['comment_text']
        details['url'] = self.get_absolute_url()
        return details
