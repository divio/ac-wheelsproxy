import json

from django.http import HttpResponse, Http404
from django.core.cache import cache as cache_backend
from django.core.cache.backends import dummy
from django.utils.text import slugify
from django.views.generic import RedirectView, View, TemplateView
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, redirect

from . import models, utils


class JSONView(View):
    indent = True

    def get(self, request, *args, **kwargs):
        data = self.get_data(request, *args, **kwargs)
        payload = json.dumps(data, indent=self.indent)
        return HttpResponse(payload, content_type='application/json')


class SingleIndexMixin(object):
    @cached_property
    def index(self):
        return get_object_or_404(
            models.BackingIndex,
            slug=self.kwargs['index_slug'],
        )

    @cached_property
    def package(self):
        return get_object_or_404(
            self.index.package_set,
            slug=models.normalize_package_name(self.package_name),
        )

    @cached_property
    def package_name(self):
        return self.kwargs['package_name']

    @cached_property
    def version(self):
        return self.kwargs.get('version')

    @cached_property
    def release(self):
        return self.package.get_release(self.version)

    @cached_property
    def platform(self):
        return get_object_or_404(
            models.Platform,
            slug=self.kwargs['platform_slug'],
        )

    @cached_property
    def build(self):
        return self.release.get_build(self.platform)


class DirectBuildGetterMixin(object):
    @cached_property
    def build(self):
        try:
            # NOTE: If the build id is available and a build exists, avoid
            # to query the whole hierarchy and return as fast as possible.
            return models.Build.objects.get(pk=self.kwargs['build_id'])
        except (KeyError, models.Build.DoesNotExist):
            return super(DirectBuildGetterMixin, self).build


class SingleIndexPackageLinks(SingleIndexMixin, TemplateView):
    template_name = 'index/simple.html'

    def get_cache_backend(self):
        if self.request.GET.get('cache') == 'off':
            return dummy.DummyCache(host=None, params={})
        else:
            return cache_backend

    def cache_key(self):
        return models.Package.get_cache_key(
            'links',
            slugify(self.kwargs['index_slug']),
            slugify(self.kwargs['platform_slug']),
            models.normalize_package_name(self.kwargs['package_name']),
        )

    def get(self, request, *args, **kwargs):
        cache = self.get_cache_backend()
        cache_key = self.cache_key()
        response = cache.get(cache_key)
        if not response:
            if self.package.name != self.kwargs['package_name']:
                return redirect(
                    'index:package_links', permanent=True,
                    index_slug=self.kwargs['index_slug'],
                    platform_slug=self.kwargs['platform_slug'],
                    package_name=self.package.name,
                )
            response = (
                super(SingleIndexPackageLinks, self)
                .get(request, *args, **kwargs)
            )
            if hasattr(response, 'render') and callable(response.render):
                response.render()
            cache.set(cache_key, response, timeout=None)
        return response

    def get_context_data(self, **kwargs):
        context = (
            super(SingleIndexPackageLinks, self).get_context_data(**kwargs)
        )
        context['package_name'] = self.package.name
        context['platform'] = self.platform
        context['links'] = [
            (self.index, self.package, self.package.get_builds(self.platform)),
        ]
        return context


class MultiIndexPackageLinks(TemplateView):
    template_name = 'index/simple.html'

    @cached_property
    def package_name(self):
        return self.kwargs['package_name']

    @cached_property
    def platform(self):
        return get_object_or_404(
            models.Platform,
            slug=self.kwargs['platform_slug'],
        )

    @cached_property
    def indexes(self):
        index_slugs = self.kwargs['index_slugs'].split('+')
        if len(index_slugs) == 1:
            return get_object_or_404(
                models.BackingIndex,
                slug=self.kwargs['index_slugs'],
            )
        else:
            indexes = models.BackingIndex.objects.filter(slug__in=index_slugs)
            indexes = {index.slug: index for index in indexes}
            try:
                return [indexes[slug] for slug in index_slugs]
            except KeyError:
                raise Http404('BackingIndex not found')

    def get_context_data(self, **kwargs):
        context = (
            super(MultiIndexPackageLinks, self).get_context_data(**kwargs)
        )
        package_name = models.normalize_package_name(self.package_name)
        context['package_name'] = package_name
        context['platform'] = self.platform
        context['links'] = []

        unique_builds = utils.UniquesIterator(lambda b: b.release.version)

        for index in self.indexes:
            try:
                package = index.package_set.get(slug=package_name)
            except models.Package.DoesNotExist:
                package = None
                builds = []
            else:
                builds = unique_builds(package.get_builds(self.platform))
            context['links'].append((index, package, builds))
        return context


class BuildView(DirectBuildGetterMixin,
                SingleIndexMixin,
                RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return self.build.get_build_url(build_if_needed=True)
