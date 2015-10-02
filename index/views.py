import json

import six

from django.http import HttpResponse
from django.views.generic import RedirectView, View, TemplateView
from django.utils.text import slugify
from django.utils.functional import cached_property

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
        return self.index.get_package(self.package_name)

    @cached_property
    def package_name(self):
        return slugify(self.kwargs['package_name'])

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
        # TODO: Get the index from the request context
        return models.BackingIndex.objects.get(pk=1)

    @cached_property
    def platform(self):
        return models.Platform.objects.get(slug=self.kwargs['platform_slug'])


class PackageInfoMixin(DevelopmentIndexMixin):
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


class PackageInfo(PackageInfoMixin, JSONView):
    def get_data(self, request, *args, **kwargs):
        return self.process_package_info(
            self.index.get_package_details(self.package_name, self.version))


class AllPackageLinks(PackageInfoMixin, TemplateView):
    template_name = 'index/all-simple.html'

    def get_context_data(self, **kwargs):
        context = super(AllPackageLinks, self).get_context_data(**kwargs)
        context['platform'] = self.platform
        context['index'] = self.index
        context['builds'] = (
            models.Build.objects.filter(
                platform=self.platform,
                release__package__index=self.index,
            )
            .select_related('release', 'platform', 'release__package')
        )
        return context


class PackageLinks(PackageInfoMixin, TemplateView):
    template_name = 'index/simple.html'

    def get_context_data(self, **kwargs):
        context = super(PackageLinks, self).get_context_data(**kwargs)
        context['details'] = self.process_package_info(
            self.index.get_package_details(self.package_name))
        return context


class DirectBuildGetterMixin(object):
    @cached_property
    def build(self):
        try:
            # NOTE: If the build id is available and a build exists, avoid
            # to query the whole hierarchy and return as fast as possible.
            return models.Build.objects.get(pk=self.kwargs['build_id'])
        except (KeyError, models.Build.DoesNotExist):
            return super(DirectBuildGetterMixin, self).build


class BuildView(DirectBuildGetterMixin,
                DevelopmentIndexMixin,
                RedirectView):
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return self.build.get_build_url(build_if_needed=True)
