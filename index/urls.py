from django.conf.urls import include, url

from . import views


index_patterns = [
    # Simple PyPI API
    url('^(?P<package_name>[a-zA-Z0-9_-]+)/$',
        views.PackageLinks.as_view(), name='package_links'),

    # Download redirects
    url('^(?P<package_name>[^/]+)/(?P<version>[^/]+)/download/(?P<build_id>\d+)/(?P<filename>[^/]+)$',
        views.BuildView.as_view(), name='download_build'),

    # JSON PyPI API
    # url('^pypi/(?P<package_name>[^/]+)/json$',
    #     views.PackageInfo.as_view(), name='package_info'),
    # url('^pypi/(?P<package_name>[^/]+)/(?P<version>[^/]+)/json$',
    #     views.PackageInfo.as_view(), name='package_info'),
]

urlpatterns = [
    url(r'^d/(?P<index_slug>[a-z0-9-]+)/(?P<platform_slug>[a-z0-9-]+)/',
        include(index_patterns)),
]
