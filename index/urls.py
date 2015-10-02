from django.conf.urls import include, url

from . import views


index_patterns = [
    # Simple PyPI API
    url('^simple/$',
        views.AllPackageLinks.as_view(), name='all_package_links'),
    url('^simple/(?P<package_name>[a-zA-Z0-9_-]+)/$',
        views.PackageLinks.as_view(), name='package_links'),

    # JSON PyPI API
    url('^pypi/(?P<package_name>[^/]+)/json$',
        views.PackageInfo.as_view(), name='package_info'),
    url('^pypi/(?P<package_name>[^/]+)/(?P<version>[^/]+)/json$',
        views.PackageInfo.as_view(), name='package_info'),

    # Download redirects
    url('^(?P<package_name>[^/]+)/(?P<version>[^/]+)/download/(?P<build_id>\d+)/(?P<filename>[^/]+)$',
        views.BuildView.as_view(), name='download_build'),
]

urlpatterns = [
    url(r'^(?P<platform_slug>[a-z0-9-]+)/', include(index_patterns)),
]
