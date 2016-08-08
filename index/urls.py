from django.conf.urls import include, url

from . import views


urlpatterns = [
    url(r'^d/(?P<index_slug>[a-z0-9-]+)/(?P<platform_slug>[a-z0-9-]+)/', include([  # NOQA
        # Simple PyPI API
        url(
            '^(?P<package_name>[a-zA-Z0-9_\.-]+)/$',
            views.PackageLinks.as_view(),
            name='package_links',
        ),

        # Download redirects
        url(
            '^(?P<package_name>[^/]+)/(?P<version>[^/]+)/download/(?P<build_id>\d+)/(?P<filename>[^/]+)$',  # NOQA
            views.BuildView.as_view(),
            name='download_build',
        ),
    ])),
]
