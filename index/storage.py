from django.utils.functional import LazyObject
from django.conf import settings

from storages.backends.s3boto import S3BotoStorage


class OverwritingS3Storage(S3BotoStorage):
    def __init__(self):
        super(OverwritingS3Storage, self).__init__(
            access_key=settings.BUILDS_STORAGE_ACCESS_KEY,
            secret_key=settings.BUILDS_STORAGE_SECRET_KEY,
            bucket_name=settings.BUILDS_STORAGE_BUCKET_NAME,
        )

    def get_available_name(self, name, max_length=None):
        self.delete(name)
        return name


class BuildsStorage(LazyObject):
    def _setup(self):
        self._wrapped = OverwritingS3Storage()


builds_storage = BuildsStorage()
