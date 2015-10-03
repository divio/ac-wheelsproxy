from coolfig import Settings, Value
from coolfig.types import LazyCallable, boolean
from coolfig.schema import DictValue

django_cache_url = LazyCallable('environ', 'Env.cache_url_config')


class AppSettings(Settings):
    ALWAYS_REDIRECT_DOWNLOADS = Value(boolean, default=False)
    DOCKER_BUILDER_ENDPOINT = Value(str)
    DOCKER_BUILDER_CERTS = Value(str)
    TEMP_BUILD_ROOT = Value(str, default='/tmp')
    CACHES = DictValue(django_cache_url, str.lower)
    BUILDS_STORAGE_ACCESS_KEY = Value(str)
    BUILDS_STORAGE_SECRET_KEY = Value(str)
    BUILDS_STORAGE_BUCKET_NAME = Value(str)
