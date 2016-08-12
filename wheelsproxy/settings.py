from coolfig import Settings, Value, Dictionary
from coolfig.types import boolean


class AppSettings(Settings):
    ALWAYS_REDIRECT_DOWNLOADS = Value(boolean, default=False)
    TEMP_BUILD_ROOT = Value(str, default='/tmp')

    SECURE_SSL_REDIRECT = Value(boolean, default=False)
    SESSION_COOKIE_SECURE = Value(boolean, default=False)
    CSRF_COOKIE_SECURE = Value(boolean, default=False)
    SECURE_HSTS_SECONDS = Value(int, default=0)

    RAVEN_CONFIG = Dictionary({
        'DSN': Value(str, key='SENTRY_DSN', default=None),
    })

    BUILDS_STORAGE_DSN = Value(str)
    BUILDS_DOCKER_DSN = Value(str)

    SERVE_BUILDS = Value(boolean, default=False)
