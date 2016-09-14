import os
import time
import logging
import hashlib

import six

from pkg_resources import parse_version, Requirement, safe_extra
from pkg_resources.extern.packaging.markers import Marker

import furl

from django.db import models
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.contrib.postgres.fields import JSONField, ArrayField

from extended_choices import Choices

from . import storage, tasks, builder, utils, client, depgraph


log = logging.getLogger(__name__)


INDEX_BACKENDS = Choices(
    ('PYPI', 'wheelsproxy.client.PyPIClient', _('PyPI')),
    ('DEVPI', 'wheelsproxy.client.DevPIClient', _('DevPI')),
)

COMPILATION_STATUSES = Choices(
    ('PENDING', 'pending', _('Pending')),
    ('DONE', 'done', _('Done')),
    ('FAILED', 'failed', _('Failed')),
)


def get_release(indexes, package_slug, version):
    candidates = list(Release.objects.filter(
        version=version,
        package__slug=package_slug,
        package__index__in=indexes,
    ).select_related('package'))
    candidates = {c.package.index_id: c for c in candidates}
    for index in indexes:
        try:
            return candidates[index.pk]
        except KeyError:
            pass
    else:
        raise Release.DoesNotExist('Release matching query could not be found')


class Platform(models.Model):
    DOCKER = 'docker'
    PLATFORM_CHOICES = [
        (DOCKER, _('Docker'))
    ]

    slug = models.SlugField(unique=True)
    type = models.CharField(max_length=16, choices=PLATFORM_CHOICES)
    spec = JSONField(default={})
    environment = JSONField(null=True, editable=False)

    def __str__(self):
        return self.slug

    def get_builder(self):
        # TODO: If we need to support more platform types here (e.g. use VMs
        # for platforms not supported by docker: OS X, Windows, ...)
        assert self.type == self.DOCKER
        return builder.DockerBuilder(self.spec)

    def populate_environment(self):
        self.environment = self.get_builder().get_environment()
        self.save(update_fields=['environment'])

    def get_external_build(self, url):
        build, created = ExternalBuild.objects.get_or_create(
            platform=self,
            external_url=url,
        )
        return build


class BackingIndex(models.Model):
    slug = models.SlugField(unique=True)
    url = models.URLField(verbose_name=_('URL'))
    last_update_serial = models.BigIntegerField(null=True, blank=True)
    backend = models.CharField(
        max_length=255,
        choices=INDEX_BACKENDS,
        default=INDEX_BACKENDS.PYPI,
    )

    class Meta:
        verbose_name_plural = _('backing indexes')

    def __str__(self):
        return self.slug

    def get_client(self):
        Client = import_string(self.backend)
        return Client(self.url)

    client = cached_property(get_client)

    def get_package(self, package_name, create=True):
        normalized_package_name = utils.normalize_package_name(package_name)
        if create:
            package, created = Package.objects.get_or_create(
                index=self,
                slug=normalized_package_name,
                defaults={'name': package_name},
            )
        else:
            package = self.package_set.get(slug=normalized_package_name)
        return package

    def itersync(self):
        serial = self.last_update_serial
        packages_to_update = self.client.iter_updated_packages(serial)
        for package_name, serial in packages_to_update:
            if package_name:
                if not self.import_package(package_name):
                    # Nothing imported: remove the package
                    slug = utils.normalize_package_name(package_name)
                    Package.objects.filter(index=self, slug=slug).delete()
                    cache.delete(
                        Package.get_cache_version_key(self.slug, slug),
                    )

            if serial > self.last_update_serial:
                self.last_update_serial = serial
                yield self.last_update_serial
        self.save(update_fields=['last_update_serial'])

    def sync(self):
        for i in self.itersync():
            pass

    def import_package(self, package_name):
        # log.info('importing {} from {}'.format(package_name, self.url))
        try:
            versions = self.client.get_package_releases(package_name)
        except client.PackageNotFound:
            log.debug('package {} not found on {}'
                      .format(package_name, self.url))
            return
        if not versions:
            log.debug('no versions found for package {} on {}'
                      .format(package_name, self.url))
            return
        package = self.get_package(package_name)
        release_ids = []
        for version, releases in six.iteritems(versions):
            release_details = package.get_best_release(releases)
            if not release_details:
                continue
            release = package.get_release(version, release_details)
            release_ids.append(release.pk)
        if release_ids:
            # Remove outdated releases
            package.release_set.exclude(pk__in=release_ids).delete()
            # Expire the cache
            package.expire_cache()
        return package.pk if release_ids else None

    def expire_cache(self):
        for slug in self.package_set.values_list('slug', flat=True):
            Package.expire_package_cache(self.slug, slug)


class Package(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    index = models.ForeignKey(BackingIndex)

    class Meta:
        unique_together = ('slug', 'index')
        ordering = ('slug', )

    def __str__(self):
        return self.slug

    def get_best_release(self, releases):
        for release in releases:
            if release.type == 'sdist':
                return release
        for release in releases:
            if release.type == 'bdist_wheel':
                if release.url.endswith('-py2.py3-none-any.whl'):
                    return release

    def get_release(self, version, release=None):
        version = utils.normalize_version(version)
        instance, created = Release.objects.get_or_create(
            package=self, version=version)
        if created:
            if not release:
                releases = self.index.client.get_version_releases(
                    self.slug,
                    version,
                )
                release = self.get_best_release(releases)

            instance.url = release.url
            instance.md5_digest = release.md5_digest
            assert instance.url
            # TODO: Add support for hashspec and alternative hashes
            #       (newer devpi versions support sha256)
            # assert instance.md5_digest
            instance.save(update_fields=['url', 'md5_digest'])
        elif release:
            instance.url = release.url
            instance.md5_digest = release.md5_digest
            instance.save(update_fields=['url', 'md5_digest'])
        return instance

    @classmethod
    def get_cache_key(cls, namespace, index_slugs, platform_slug,
                      package_name):
        version_keys = sorted([
            cls.get_cache_version_key(index_slug, package_name)
            for index_slug in index_slugs
        ])
        versions = cache.get_many(version_keys)
        version_hash = ','.join(
            str(versions.get(k, 0))
            for k in version_keys
        )

        return '{}/indexes:{}/platform:{}/package:{}/v:{}'.format(
            namespace,
            '+'.join(index_slugs),
            platform_slug,
            package_name,
            version_hash,
        )

    @staticmethod
    def get_cache_version_key(index_slug, package_name):
        return 'serial/index:{}/package:{}'.format(index_slug, package_name)

    @classmethod
    def expire_package_cache(cls, index_slug, package_name):
        key = cls.get_cache_version_key(index_slug, package_name)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=None)

    def expire_cache(self):
        self.expire_package_cache(self.index.slug, self.slug)

    def get_builds(self, platform, check=True):
        releases = (Release.objects
                    .filter(package=self)
                    .order_by('-version')
                    .only('pk')
                    .all())
        builds_qs = (Build.objects
                     .filter(release__in=releases, platform=platform)
                     .order_by('-release__version')
                     .all())

        if check and (len(builds_qs) != len(releases)):
            return [r.get_build(platform) for r in releases]
        else:
            return list(builds_qs)

    def get_versions(self):
        return sorted([
            (rel.parsed_version, rel)
            for rel in self.release_set.all()
        ], reverse=True)


class Release(models.Model):
    package = models.ForeignKey(Package)
    version = models.CharField(max_length=200)
    url = models.URLField(
        verbose_name=_('URL'),
        blank=True,
        max_length=255,
        default='',
    )
    md5_digest = models.CharField(
        verbose_name=_('MD5 digest'),
        max_length=32,
        default='',
        blank=True,
        editable=False,
    )
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('package', 'version')
        ordering = ('package', 'version')

    def __str__(self):
        return '{}-{}'.format(self.package.slug, self.version)

    def get_build(self, platform):
        build, created = Build.objects.get_or_create(
            release=self, platform=platform)
        return build

    @cached_property
    def parsed_version(self):
        return parse_version(self.version)

    @property
    def requirement(self):
        return Requirement('{}=={}'.format(self.package.slug, self.version))


def upload_build_to(self, filename):
    return '{index}/{platform}/{package}/{version}/{filename}'.format(
        index=self.release.package.index.slug,
        package=self.release.package.slug,
        version=self.release.version,
        platform=self.platform.slug,
        filename=filename,
    )


def upload_external_build_to(self, filename):
    return '__external__/{platform}/{url_hash}/{filename}'.format(
        url_hash=hashlib.sha256(self.external_url).hexdigest(),
        platform=self.platform.slug,
        filename=filename,
    )


class BuildsManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self, *args, **kwargs):
        return (super(BuildsManager, self)
                .get_queryset(*args, **kwargs)
                .defer('build_log')
                .select_related('release__package__index'))


class BuildBase(models.Model):
    platform = models.ForeignKey(Platform)
    md5_digest = models.CharField(
        verbose_name=_('MD5 digest'),
        max_length=32,
        default='',
        blank=True,
        editable=False,
    )
    metadata = JSONField(null=True, blank=True, editable=False)
    filesize = models.PositiveIntegerField(
        blank=True, null=True,
        editable=False,
    )
    build_timestamp = models.DateTimeField(
        blank=True, null=True,
        editable=False,
    )
    build_duration = models.PositiveIntegerField(
        blank=True, null=True,
        editable=False,
    )
    build_log = models.TextField(blank=True, editable=False)

    class Meta:
        abstract = True

    def __str__(self):
        return self.filename

    @property
    def requirements(self):
        if self.metadata:
            return list(self.iter_requirements())
        else:
            return None

    def iter_requirements(self, extras=None):
        assert self.metadata

        meta = self.metadata
        extras = extras if extras else frozenset([])
        env = self.platform.environment

        def process(requirement_sets, extras, environment):
            for requirements in requirement_sets:
                if 'extra' in requirements:
                    if safe_extra(requirements['extra']) not in extras:
                        continue

                if 'environment' in requirements:
                    marker = Marker(requirements['environment'])
                    if not marker.evaluate(environment):
                        continue

                for req in requirements['requires']:
                    req = utils.parse_requirement(req)
                    req.extras = extras
                    yield Requirement(str(req))

        yield from process(meta.get('run_requires', []), extras, env)
        yield from process(meta.get('meta_requires', []), extras, env)

    def is_built(self):
        return bool(self.build)
    is_built.boolean = True

    def get_build_url(self, build_if_needed=False, include_digest=False):
        if self.is_built():
            url = self.build.url
            if include_digest and self.md5_digest:
                url += '#md5={}'.format(self.md5_digest)
            return url
        else:
            if build_if_needed:
                self.schedule_build()
            url = self.original_url
            if include_digest and self.original_md5_digest:
                url += '#md5={}'.format(self.original_md5_digest)
            return url

    def rebuild(self):
        builder = self.platform.get_builder()
        builder.build(self)

    @property
    def filename(self):
        if self.is_built():
            path = self.build.name
        else:
            path = self.original_url
        return os.path.basename(path)

    @property
    def original_url(self):
        raise NotImplementedError

    @property
    def original_md5_digest(self):
        raise NotImplementedError

    @property
    def package_name(self):
        raise NotImplementedError

    def schedule_build(self, force=False):
        raise NotImplementedError

    def is_external(self):
        raise NotImplementedError


class Build(BuildBase):
    release = models.ForeignKey(Release)
    build = models.FileField(
        storage=storage.dsn_configured_storage('BUILDS_STORAGE_DSN'),
        upload_to=upload_build_to,
        max_length=255, blank=True, null=True,
    )

    objects = BuildsManager()

    class Meta:
        unique_together = ('release', 'platform')

    def is_external(self):
        return False

    def schedule_build(self, force=False):
        return tasks.build_internal.delay(self.pk, force=force)

    def rebuild(self):
        super(Build, self).rebuild()
        self.release.package.expire_cache()

    @property
    def package_name(self):
        return self.release.package.name

    @property
    def original_url(self):
        return self.release.url

    @property
    def original_md5_digest(self):
        return self.release.md5_digest

    def get_absolute_url(self, include_digest=False):
        if self.is_built() and not settings.ALWAYS_REDIRECT_DOWNLOADS:
            # NOTE: Return the final URL directly if the build is already
            # available and ALWAYS_REDIRECT_DOWNLOADS is set to False, so that
            # we can avoid one additional request to get the redirect.
            # This prevents us from collecting stats about package activity,
            # but given the problems we're trying to solve with the proxy,
            # this is an acceptable compromise.
            return self.get_build_url(include_digest=include_digest)
        else:
            return reverse('wheelsproxy:download_build', kwargs={
                'index_slugs': self.release.package.index.slug,
                'platform_slug': self.platform.slug,
                'version': self.release.version,
                'package_name': self.release.package.slug,
                'filename': self.filename,
                'build_id': self.pk,
            })

    def get_digest(self):
        if self.is_built():
            return self.md5_digest
        else:
            return self.release.md5_digest


class ExternalBuild(BuildBase):
    external_url = models.URLField(max_length=255)
    build = models.FileField(
        storage=storage.dsn_configured_storage('BUILDS_STORAGE_DSN'),
        upload_to=upload_external_build_to,
        max_length=255, blank=True, null=True,
    )

    class Meta:
        unique_together = ('external_url', 'platform')

    @property
    def package_name(self):
        return furl.furl(self.external_url).fragment.args['egg'].split('==')[0]

    @property
    def version(self):
        return furl.furl(self.external_url).fragment.args['egg'].split('==')[1]

    def is_external(self):
        return True

    def schedule_build(self, force=False):
        return tasks.build_external.delay(self.pk, force=force)

    @property
    def original_url(self):
        return self.external_url

    @property
    def original_md5_digest(self):
        return None


class CompiledRequirements(models.Model):
    platform = models.ForeignKey(Platform)
    requirements = models.TextField()
    index_url = models.URLField()
    index_slugs = ArrayField(models.SlugField())
    created_at = models.DateTimeField(auto_now_add=True)

    pip_compilation_status = models.CharField(
        max_length=12,
        editable=False,
        choices=COMPILATION_STATUSES,
        default=COMPILATION_STATUSES.PENDING,
    )
    pip_compiled_requirements = models.TextField(blank=True, editable=False)
    pip_compilation_timestamp = models.DateTimeField(
        blank=True, null=True,
        editable=False,
    )
    pip_compilation_duration = models.PositiveIntegerField(
        blank=True, null=True,
        editable=False,
    )
    pip_compilation_log = models.TextField(
        _('Compilation log'), blank=True, editable=False)

    internal_compilation_status = models.CharField(
        max_length=12,
        choices=COMPILATION_STATUSES,
        default=COMPILATION_STATUSES.PENDING,
    )
    internal_compiled_requirements = models.TextField(
        blank=True,
        editable=False,
    )
    internal_compilation_timestamp = models.DateTimeField(
        blank=True, null=True,
        editable=False,
    )
    internal_compilation_duration = models.PositiveIntegerField(
        blank=True, null=True,
        editable=False,
    )
    internal_compilation_log = models.TextField(
        _('Compilation log'), blank=True, editable=False)

    def _mode_attr(self, mode, attr):
        return getattr(self, '{}_{}'.format(mode, attr))

    def is_pending(self, mode='pip'):
        return self._mode_attr(mode, 'compilation_status') == COMPILATION_STATUSES.PENDING  # NOQA

    def is_failed(self, mode='pip'):
        return self._mode_attr(mode, 'compilation_status') == COMPILATION_STATUSES.FAILED  # NOQA

    def is_compiled(self, mode='pip'):
        return self._mode_attr(mode, 'compilation_status') == COMPILATION_STATUSES.DONE  # NOQA

    def pip_recompile(self):
        builder = self.platform.get_builder()
        builder.compile(self)

    def internal_recompile(self):
        start = time.time()

        indexes = BackingIndex.objects.filter(slug__in=self.index_slugs)
        indexes = sorted(indexes, key=lambda i: self.index_slugs.index(i.slug))

        graph = depgraph.DependencyGraph(indexes, self.platform)

        try:
            graph.compile(self.requirements)
        except depgraph.CompilationFailed:
            self.internal_compilation_status = COMPILATION_STATUSES.FAILED
            raise
        else:
            formatter = depgraph.GraphFormatter(header_comment=(
                '# This file is autogenerated by wheelsproxy.\n'
                '# Make changes in requirements.in, then submit it to the\n'
                '# wheelsproxy to update:\n'
                '#\n'
                '#    pip-reqs -w {} compile\n'
                '#\n'
            ).format(self.index_url))
            self.internal_compiled_requirements = formatter.format(graph)
            self.internal_compilation_status = COMPILATION_STATUSES.DONE
        finally:
            self.internal_compilation_log = graph.get_last_log()
            self.internal_compilation_timestamp = timezone.now()
            self.internal_compilation_duration = time.time() - start
            self.save(update_fields=[
                'internal_compiled_requirements',
                'internal_compilation_status',
                'internal_compilation_timestamp',
                'internal_compilation_log',
                'internal_compilation_duration',
            ])
