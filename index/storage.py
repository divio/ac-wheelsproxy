from django.utils.functional import LazyObject
from django.core.files.storage import get_storage_class


class BuildsStorage(LazyObject):
    def _setup(self):
        self._wrapped = get_storage_class()()


builds_storage = BuildsStorage()
