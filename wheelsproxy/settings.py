import os

from coolfig import Settings, Value, Dictionary, computed_value
from coolfig.types import boolean


def get_version(settings):
    version_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'VERSION',
    )
    if os.path.exists(version_file):
        with open(version_file) as fh:
            return fh.read().strip()
    else:
        return 'develop'


class AppSettings(Settings):
    ALWAYS_REDIRECT_DOWNLOADS = Value(boolean, default=False)
    TEMP_BUILD_ROOT = Value(str, default='/tmp')
    COMPILE_CACHE_ROOT = Value(str, default='/cache')

    SECURE_SSL_REDIRECT = Value(boolean, default=False)
    SESSION_COOKIE_SECURE = Value(boolean, default=False)
    CSRF_COOKIE_SECURE = Value(boolean, default=False)
    SECURE_HSTS_SECONDS = Value(int, default=0)

    RAVEN_CONFIG = Dictionary({
        'dsn': Value(str, key='SENTRY_DSN', default=None),
        'release': computed_value(get_version),
    })

    BUILDS_STORAGE_DSN = Value(str)
    BUILDS_DOCKER_DSN = Value(str)

    SERVE_BUILDS = Value(boolean, default=False)
