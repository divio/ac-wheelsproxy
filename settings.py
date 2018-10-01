"""
Application definition for wheel-proxy.

This file contains only static values (app definition) and no configuration
directives. Those are read from environment variables.
"""

import sys
from datetime import timedelta

from coolfig import EnvConfig, EnvDirConfig, load_django_settings

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'raven.contrib.django',
    'django_object_actions',
    'celery_app',
    'wheelsproxy',
    'divio_sso',
    'social_django',
    'django.contrib.admin',
)

MIDDLEWARE_CLASSES = (
    'raven.contrib.django.middleware.SentryResponseErrorIdMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'

MEDIA_URL = '/media/'

STATIC_ROOT = '/static'
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    'static',
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',  # NOQA
        },
    },
    'root': {
        'handlers': ['sentry', 'console'],
        'level': 'INFO',
    },
}

CELERYBEAT_SCHEDULE = {
    'sync-all-indexes': {
        'task': 'wheelsproxy.tasks.sync_indexes',
        'schedule': timedelta(seconds=60),
    },
}

CELERY_TIMEZONE = 'UTC'

CELERY_ACKS_LATE = True

CELERYD_PREFETCH_MULTIPLIER = 1

LOGIN_REDIRECT_URL = "/admin/"

load_django_settings(
    [EnvDirConfig("/run/secrets/divio.com"), EnvConfig()], locals()
)


import celery_app.app  # NOQA
