import json

import six

from django.core.urlresolvers import reverse
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
        return models.BackingIndex.objects.get(pk=1)

    @cached_property
    def package(self):
        package, created = models.Package.objects.get_or_create(
            index=self.index, slug=self.package_name)
        return package

    @cached_property
    def package_name(self):
        return slugify(self.kwargs['package_name'])

    @cached_property
    def version(self):
        return self.kwargs.get('version')

    @cached_property
    def release(self):
        release, created = models.Release.objects.get_or_create(
            package=self.package, version=self.version)
        return release

    @cached_property
    def platform(self):
        return models.Platform.objects.get(pk=1)

    @cached_property
    def build(self):
        try:
            return models.Build.objects.get(
                platform=self.platform, release=self.release)
        except models.Build.DoesNotExist:
            return self.release.create_build(self.platform)


class PackageInfo(IndexMixin, JSONView):

    def replace_url(self, url):
        url['url'] = self.request.build_absolute_uri(
            reverse('index:download_release', kwargs={
                'package_name': self.package_name,
                'version': self.version,
                'filename': url['filename'],
            })
        )

    def replace_urls(self, payload):
        for url in payload['urls']:
            self.replace_url(url)
        for version, releases in six.iteritems(payload['releases']):
            for release in releases:
                self.replace_url(release)
        return payload

    def get_data(self, request, *args, **kwargs):
        return self.replace_urls(
            self.index.get_package_details(self.package_name, self.version))


class PackageLinks(IndexMixin, TemplateView):
    template_name = 'index/simple.html'

    def get_context_data(self, **kwargs):
        context = super(PackageLinks, self).get_context_data(**kwargs)
        context['details'] = self.index.get_package_details(self.package_name)
        return context


class BuildView(IndexMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        return self.build.get_build_url()
