from django.http import Http404
from django.core.cache import cache as cache_backend
from django.core.cache.backends import dummy
from django.utils.text import slugify
from django.views.generic import RedirectView, TemplateView
from django.views.decorators import gzip
from django.utils.functional import cached_property
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect

from . import models, utils


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
        return models.normalize_package_name(self.kwargs['package_name'])

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
            if hasattr(response, 'render') and callable(response.render):
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
        return self.kwargs.get('version')

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
