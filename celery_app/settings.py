from coolfig import Settings, Value, types


class AppSettings(Settings):
    CELERY_IGNORE_RESULT = Value(types.boolean, default=False)
    CELERY_STORE_ERRORS_EVEN_IF_IGNORED = Value(types.boolean, default=True)
    BROKER_URL = Value(str, default=None)
    CELERY_RESULT_BACKEND = Value(str, key='BROKER_URL', default=None)
    CELERY_TIMEZONE = Value(str, default='UTC')
    CELERY_ACCEPT_CONTENT = Value(types.list(str), default=['json'])
    CELERY_TASK_SERIALIZER = Value(str, default='json')
    CELERY_RESULT_SERIALIZER = Value(str, default='json')
