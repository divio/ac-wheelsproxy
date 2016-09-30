import six

from django.db import transaction
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseBadRequest,
    UnreadablePostError,
)
from django.core.cache import cache as cache_backend
from django.core.cache.backends import dummy
from django.core.urlresolvers import reverse
from django.utils.text import slugify
from django.views.generic import RedirectView, TemplateView, View
from django.views.decorators import gzip
from django.views.decorators.csrf import csrf_exempt
from django.utils.functional import cached_property
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect

from pkg_resources import Requirement, RequirementParseError

from . import models, utils, tasks


class PackageViewMixin(object):
    @cached_property
    def indexes(self):
        index_slugs = self.kwargs['index_slugs'].split('+')
        indexes = models.BackingIndex.objects.filter(slug__in=index_slugs)
        indexes = {index.slug: index for index in indexes}
        try:
            return [indexes[slug] for slug in index_slugs]
        except KeyError:
            raise Http404('BackingIndex not found')

    @cached_property
    def package_name(self):
        return utils.normalize_package_name(self.kwargs['package_name'])

    @cached_property
    def platform(self):
        return get_object_or_404(
            models.Platform,
            slug=self.kwargs['platform_slug'],
        )


class PackageLinks(PackageViewMixin, TemplateView):
    template_name = 'wheelsproxy/simple.html'

    def get_cache_backend(self):
        cache = True

        if self.package_name != self.kwargs['package_name']:
            cache = False

        if self.request.GET.get('cache') == 'off':
            cache = False

        if cache:
            return cache_backend
        else:
            return dummy.DummyCache(host=None, params={})

    def cache_key(self):
        index_slugs = self.kwargs['index_slugs'].split('+')
        return models.Package.get_cache_key(
            'links',
            [slugify(slug) for slug in index_slugs],
            slugify(self.kwargs['platform_slug']),
            self.package_name,
        )

    @method_decorator(gzip.gzip_page)
    def get(self, request, *args, **kwargs):
        cache = self.get_cache_backend()
        cache_key = self.cache_key()
        response = cache.get(cache_key)
        if not response:
            # Ensure at least one package exists in the index set
            for index in self.indexes:
                if index.package_set.filter(slug=self.package_name).exists():
                    break
            else:
                raise Http404('Package not found')

            # Ensure package names are canonicalized
            if self.package_name != self.kwargs['package_name']:
                return redirect(
                    'wheelsproxy:package_links', permanent=True,
                    index_slugs=self.kwargs['index_slugs'],
                    platform_slug=self.kwargs['platform_slug'],
                    package_name=self.package_name,
                )

            # Render the normal response
            response = super(PackageLinks, self).get(request, *args, **kwargs)
            if hasattr(response, 'render') and six.callable(response.render):
                response.render()
            cache.set(cache_key, response, timeout=None)
        return response

    def get_context_data(self, **kwargs):
        context = super(PackageLinks, self).get_context_data(**kwargs)
        context['package_name'] = self.package_name
        context['platform'] = self.platform
        context['links'] = self.get_links()
        return context

    def get_links(self):
        unique_builds = utils.UniquesIterator(lambda b: b.release.version)

        links = []

        for index in self.indexes:
            try:
                package = index.package_set.get(slug=self.package_name)
            except models.Package.DoesNotExist:
                package = None
                builds = []
            else:
                builds = package.get_builds(self.platform)
                builds = unique_builds(builds)
            links.append((index, package, builds))

        return links


class BuildTrigger(PackageViewMixin, RedirectView):
    permanent = False

    @cached_property
    def version(self):
        return utils.normalize_version(self.kwargs.get('version'))

    @cached_property
    def build(self):
        try:
            # NOTE: If the build id is available and a build exists, avoid
            # to query the whole hierarchy and return as fast as possible.
            return models.Build.objects.get(pk=self.kwargs['build_id'])
        except (KeyError, models.Build.DoesNotExist):
            assert len(self.indexes) == 1
            package = get_object_or_404(
                self.indexes[0].package_set,
                slug=self.package_name,
            )
            release = package.get_release(self.version)
            return release.get_build(self.platform)

    def get_redirect_url(self, *args, **kwargs):
        return self.build.get_build_url(build_if_needed=True)


class RequirementsProcessingMixin(object):
    @method_decorator(csrf_exempt)
    @method_decorator(transaction.non_atomic_requests)
    def dispatch(self, request, *args, **kwargs):
        return (super(RequirementsProcessingMixin, self)
                .dispatch(request, *args, **kwargs))

    def post(self, request, *args, **kwargs):
        try:
            return self.process_body(request.body)
        except UnreadablePostError:
            raise HttpResponseBadRequest(
                'Malformed request payload received',
                content_type='text/plain',
            )


class RequirementsCompilationView(RequirementsProcessingMixin,
                                  PackageViewMixin,
                                  View):
    def process_body(self, body):
        index_url = self.request.build_absolute_uri(
            reverse('wheelsproxy:index_root', kwargs={
                'index_slugs': self.kwargs['index_slugs'],
                'platform_slug': self.kwargs['platform_slug'],
            }),
        )
        reqs = models.CompiledRequirements.objects.create(
            platform=self.platform,
            requirements=body,
            index_url=index_url,
            index_slugs=[i.slug for i in self.indexes],
        )
        tasks.internal_compile.delay(reqs.pk)
        tasks.pip_compile.delay(reqs.pk).get(propagate=False)
        reqs = models.CompiledRequirements.objects.get(pk=reqs.pk)
        if reqs.is_compiled():
            return HttpResponse(
                reqs.pip_compiled_requirements,
                content_type='text/plain',
            )
        else:
            return HttpResponseBadRequest(
                reqs.pip_compilation_log,
                content_type='text/plain',
            )


class RequirementsResolution(RequirementsProcessingMixin,
                             PackageViewMixin,
                             View):
    def _resolve_url(self, url):
        build, created = models.ExternalBuild.objects.get_or_create(
            external_url=url,
            platform=self.platform,
        )
        return self.request.build_absolute_uri(
            build.get_build_url(build_if_needed=True, include_digest=True),
        )

    def _resolve_package(self, req):
        assert len(req.specs) == 1
        assert req.specs[0][0] == '=='

        release = models.get_release(
            self.indexes,
            utils.normalize_package_name(req.key),
            utils.normalize_version(req.specs[0][1]),
        )
        build = release.get_build(self.platform)
        return self.request.build_absolute_uri(
            build.get_absolute_url(include_digest=True)
        )

    def process_body(self, body):
        urls = []
        reqs = body.decode('utf-8').splitlines()

        for req in utils.split_requirements(reqs):
            try:
                req = Requirement(req)
            except RequirementParseError:
                if req.startswith('https://') or req.startswith('http://'):
                    urls.append(self._resolve_url(req))
                else:
                    urls.append(req)
            else:
                urls.append(self._resolve_package(req))

        return HttpResponse(
            u'\n'.join(urls) + u'\n',
            content_type='text/plain'
        )
