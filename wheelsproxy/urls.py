from django.conf.urls import include, url
from django.conf import settings
from django.views import static, generic

from . import views, storage


urlpatterns = [
    # Simple index view (per-package only), for backwards compatibility
    url(
        r'^d/(?P<index_slugs>[a-z0-9\+-]+)/(?P<platform_slug>[a-z0-9-]+)/(?P<package_name>[a-zA-Z0-9_\.-]+)/$',  # NOQA
        views.PackageLinks.as_view(),
    ),
    url(r'^v1/(?P<index_slugs>[a-z0-9\+-]+)/(?P<platform_slug>[a-z0-9-]+)/', include([  # NOQA
        url(
            r'^\+simple/$',
            generic.TemplateView.as_view(template_name='root.html'),
            name='index_root',
        ),

        # Simple index view (per-package only)
        url(
            r'^\+simple/(?P<package_name>[a-zA-Z0-9_\.-]+)/$',
            views.PackageLinks.as_view(),
            name='package_links',
        ),

        # Download redirects
        url(
            r'^\+simple/(?P<package_name>[^/]+)/(?P<version>[^/]+)/download/(?P<build_id>\d+)/(?P<filename>[^/]+)$',  # NOQA
            views.BuildTrigger.as_view(),
            name='download_build',
        ),

        # Dependencies compilation
        url(
            r'^\+compile/$',
            views.RequirementsCompilationView.as_view(),
            name='compile_requirements',
        ),

        # URLs resolution
        url(
            r'^\+resolve/$',
            views.RequirementsResolution.as_view(),
            name='resolve_requirements',
        ),
    ])),
]

if settings.SERVE_BUILDS:
    builds_storage = storage.dsn_configured_storage('BUILDS_STORAGE_DSN')
    urlpatterns.append(
        url(
            r'^{}(?P<path>.*)$'.format(builds_storage.base_url.lstrip('/')),
            static.serve,
            {'document_root': builds_storage.location},
        ),
    )
