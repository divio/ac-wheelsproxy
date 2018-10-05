import os

from coolfig import Settings, Value, Dictionary, computed_value, types
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
    MAX_CACHE_BUSTING_RETRIES = Value(int, default=3)

    RAVEN_CONFIG = Dictionary({
        'dsn': Value(str, key='SENTRY_DSN', default=None),
        'release': computed_value(get_version),
    })

    BUILDS_STORAGE_DSN = Value(str)
    BUILDS_DOCKER_DSN = Value(str)

    SERVE_BUILDS = Value(boolean, default=False)

    PROXIED = Value(types.boolean, default=False)
    SECURE = Value(types.boolean, default=True)

    @computed_value
    def USE_X_FORWARDED_HOST(self):
        return self.PROXIED

    @computed_value
    def USE_X_FORWARDED_PORT(self):
        return self.PROXIED

    @computed_value
    def SECURE_PROXY_SSL_HEADER(self):
        return ("HTTP_X_FORWARDED_PROTO", "https") if self.PROXIED else None

    @computed_value
    def CSRF_USE_SESSIONS(self):
        return self.SECURE

    @computed_value
    def SESSION_COOKIE_HTTPONLY(self):
        return self.SECURE

    @computed_value
    def SESSION_COOKIE_SECURE(self):
        return self.SECURE

    @computed_value
    def SESSION_COOKIE_SAMESITE(self):
        return "Strict"

    @computed_value
    def SECURE_BROWSER_XSS_FILTER(self):
        return self.SECURE

    @computed_value
    def SECURE_CONTENT_TYPE_NOSNIFF(self):
        return self.SECURE

    @computed_value
    def SECURE_SSL_REDIRECT(self):
        return self.SECURE

    @computed_value
    def SECURE_HSTS_SECONDS(self):
        return 60 * 60 * 24 * 365 if self.SECURE else 0
