import json

from django.http import HttpResponse
from django.core.cache import cache as cache_backend
from django.core.cache.backends import dummy
from django.utils.text import slugify
from django.views.generic import RedirectView, View, TemplateView
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, redirect

from . import models


class JSONView(View):
    indent = True

    def get(self, request, *args, **kwargs):
        data = self.get_data(request, *args, **kwargs)
        payload = json.dumps(data, indent=self.indent)
        return HttpResponse(payload, content_type='application/json')


class IndexMixin(object):
    @cached_property
    def index(self):
        raise NotImplementedError

    @cached_property
    def package(self):
        # TODO: Redirect if the package.name does not match self.package_name
        return get_object_or_404(
            models.Package,
            index=self.index,
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
        raise NotImplementedError

    @cached_property
    def build(self):
        return self.release.get_build(self.platform)


class DevelopmentIndexMixin(IndexMixin):
    @cached_property
    def index(self):
        return models.BackingIndex.objects.get(slug=self.kwargs['index_slug'])

    @cached_property
    def platform(self):
        return models.Platform.objects.get(slug=self.kwargs['platform_slug'])


class DirectBuildGetterMixin(object):
    @cached_property
    def build(self):
        try:
            # NOTE: If the build id is available and a build exists, avoid
            # to query the whole hierarchy and return as fast as possible.
            return models.Build.objects.get(pk=self.kwargs['build_id'])
        except (KeyError, models.Build.DoesNotExist):
            return super(DirectBuildGetterMixin, self).build


class PackageLinks(DevelopmentIndexMixin, TemplateView):
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
            response = super(PackageLinks, self).get(request, *args, **kwargs)
            if hasattr(response, 'render') and callable(response.render):
                response.render()
            cache.set(cache_key, response, timeout=None)
        return response

    def get_context_data(self, **kwargs):
        context = super(PackageLinks, self).get_context_data(**kwargs)
        context['package'] = self.package
        context['index'] = self.index
        context['platform'] = self.platform
        context['builds'] = self.package.get_builds(self.platform)
        return context


class BuildView(DirectBuildGetterMixin,
                DevelopmentIndexMixin,
                RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return self.build.get_build_url(build_if_needed=True)
