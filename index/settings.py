from coolfig import Settings, Value
from coolfig.types import LazyCallable
from coolfig.schema import DictValue

django_cache_url = LazyCallable('environ', 'Env.cache_url_config')


class AppSettings(Settings):
    DOCKER_BUILDER_ENDPOINT = Value(str)
    DOCKER_BUILDER_CERTS = Value(str)
    TEMP_BUILD_ROOT = Value(str, default='/tmp')
    CACHES = DictValue(django_cache_url, str.lower)
