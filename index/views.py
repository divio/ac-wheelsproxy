import json

import six

from django.http import HttpResponse
from django.core.cache import cache
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


class PackageInfo(DevelopmentIndexMixin, JSONView):
    def process_package_info(self, payload):
        for version, releases in six.iteritems(payload['releases']):
            if releases:
                release = self.package.get_release(
                    version, self.package.get_best_release(releases))
                build = release.get_build(self.platform)
                payload['releases'][version] = [build.to_pypi_dict()]
        # Process the `urls` section later so that we already got the
        # correct build created
        version = payload['info']['version']
        payload['urls'] = payload['releases'][version]
        return payload

    def get_data(self, request, *args, **kwargs):
        return self.process_package_info(
            self.index.get_package_details(self.package_name, self.version))


class PackageLinks(DevelopmentIndexMixin, TemplateView):
    template_name = 'index/simple.html'

    def get(self, request, *args, **kwargs):
        cache_key = models.Package.get_cache_key(
            'links',
            slugify(self.kwargs['index_slug']),
            slugify(self.kwargs['platform_slug']),
            models.normalize_package_name(self.kwargs['package_name']),
        )
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
