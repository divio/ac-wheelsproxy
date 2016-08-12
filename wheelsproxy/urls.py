from django.conf.urls import include, url
from django.conf import settings
from django.views import static

from . import views, storage


urlpatterns = [
    url(r'^d/(?P<index_slugs>[a-z0-9\+-]+)/(?P<platform_slug>[a-z0-9-]+)/', include([  # NOQA
        # Simple index view (per-package only)
        url(
            r'^(?P<package_name>[a-zA-Z0-9_\.-]+)/$',
            views.PackageLinks.as_view(),
            name='package_links',
        ),

        # Download redirects
        url(
            r'^(?P<package_name>[^/]+)/(?P<version>[^/]+)/download/(?P<build_id>\d+)/(?P<filename>[^/]+)$',  # NOQA
            views.BuildTrigger.as_view(),
            name='download_build',
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
