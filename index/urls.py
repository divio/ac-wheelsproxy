from django.conf.urls import include, url

from . import views


index_patterns = [
    # Simple PyPI API
    url('^simple/(?P<package_name>[a-zA-Z0-9_-]+)/',
        views.PackageLinks.as_view(), name='package_links'),

    # JSON PyPI API
    url('^pypi/(?P<package_name>[^/]+)/json',
        views.PackageInfo.as_view(), name='package_info'),
    url('^pypi/(?P<package_name>[^/]+)/(?P<version>[^/]+)/json',
        views.PackageInfo.as_view(), name='package_info'),

    # Download links
    url('^(?P<package_name>[^/]+)/(?P<version>[^/]+)/download/(?P<filename>[^/]+)$',
        views.BuildView.as_view(), name='download_release'),
]

urlpatterns = [
    url(r'^', include(index_patterns)),
]
