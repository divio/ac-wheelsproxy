"""
Wheel proxy URL Configuration
"""
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.views import static


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('wheelsproxy.urls', namespace='wheelsproxy')),
    url(r'^static/(?P<path>.*)$', static.serve, {
        'document_root': settings.STATIC_ROOT,
    }),
]
