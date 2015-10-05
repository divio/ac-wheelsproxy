from coolfig import Settings, Value, Dictionary
from coolfig.types import boolean


class AppSettings(Settings):
    ALWAYS_REDIRECT_DOWNLOADS = Value(boolean, default=False)
    DOCKER_BUILDER_ENDPOINT = Value(str)
    DOCKER_BUILDER_CERTS = Value(str)
    TEMP_BUILD_ROOT = Value(str, default='/tmp')

    SECURE_SSL_REDIRECT = Value(boolean, default=False)
    SESSION_COOKIE_SECURE = Value(boolean, default=False)
    CSRF_COOKIE_SECURE = Value(boolean, default=False)
    SECURE_HSTS_SECONDS = Value(int, default=0)

    RAVEN_CONFIG = Dictionary({
        'DSN': Value(str, key='SENTRY_DSN', default=None),
    })

    # TODO: Move to coolfig as a single DictValue
    # (similar to django_database_url and django_cache_url)
    BUILDS_STORAGE_ACCESS_KEY = Value(str)
    BUILDS_STORAGE_SECRET_KEY = Value(str)
    BUILDS_STORAGE_BUCKET_NAME = Value(str)
