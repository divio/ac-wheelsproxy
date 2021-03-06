import six

import furl

from django.conf import settings
from django.utils.functional import LazyObject
from django.core.files.storage import (
    Storage,
    FileSystemStorage as DjangoFileSystemStorage,
    get_storage_class,
)

from boto.s3.connection import (
    SubdomainCallingFormat,
    OrdinaryCallingFormat,
)

from storages.backends import s3boto


SCHEMES = {
    's3': 'wheelsproxy.storage.OverwritingS3Storage',
    'file': 'wheelsproxy.storage.OverwritingFileSystemStorage',
}


class FileSystemStorage(DjangoFileSystemStorage):
    def __init__(self, dsn):
        base_url = dsn.args.get('url')
        super(FileSystemStorage, self).__init__(
            location=six.text_type(dsn.path),
            base_url=base_url,
        )
        if base_url is None:
            self.base_url = None


class S3Storage(s3boto.S3BotoStorage):
    calling_formats = {
        'subdomain': SubdomainCallingFormat,
        'ordinary': OrdinaryCallingFormat,
    }

    def __init__(self, dsn):
        bucket_name, host = dsn.host.split('.', 1)
        calling_format = dsn.args.get('calling_format')
        if calling_format:
            calling_format = self.calling_formats[calling_format]
        else:
            calling_format = SubdomainCallingFormat
        super(S3Storage, self).__init__(
            access_key=dsn.username,
            secret_key=dsn.password,
            bucket_name=bucket_name,
            host=host,
            calling_format=calling_format(),
            location=six.text_type(dsn.path).lstrip('/'),
            custom_domain=furl.furl(dsn.args.get('url')).netloc,
            default_acl=dsn.args.get('acl', 'private'),
            querystring_auth=False,
        )


class OverwritingStorageMixin(object):
    def get_available_name(self, name, max_length=None):
        self.delete(name)
        return name


class OverwritingS3Storage(OverwritingStorageMixin, S3Storage):
    pass


class OverwritingFileSystemStorage(OverwritingStorageMixin, FileSystemStorage):
    pass


class NotImplementedStorage(Storage):
    def open(self, name, mode='rb'):
        raise NotImplementedError

    def save(self, name, content, max_length=None):
        raise NotImplementedError

    def get_valid_name(self, name):
        raise NotImplementedError

    def get_available_name(self, name, max_length=None):
        raise NotImplementedError


class _DSNConfiguredStorage(LazyObject):
    def _setup(self):
        dsn = getattr(settings, self._setting_name, None)
        if not dsn:
            self._wrapped = NotImplementedStorage()
        else:
            url = furl.furl(dsn)
            storage_class = get_storage_class(SCHEMES[url.scheme])
            # Django >= 1.9 now knows about LazyObject and sets them up before
            # serializing them. To work around this behavior, the storage class
            # itself needs to be deconstructible.
            storage_class = type(storage_class.__name__, (storage_class,), {
                'deconstruct': self._deconstructor,
            })
            self._wrapped = storage_class(url)


def dsn_configured_storage(setting_name):
    path = '{}.{}'.format(
        dsn_configured_storage.__module__,
        dsn_configured_storage.__name__,
    )
    return type('DSNConfiguredStorage', (_DSNConfiguredStorage,), {
        '_setting_name': setting_name,
        '_deconstructor': lambda self: (path, [setting_name], {}),
    })()
