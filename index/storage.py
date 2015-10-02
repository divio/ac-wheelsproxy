from django.utils.functional import LazyObject
from django.core.files.storage import FileSystemStorage


class OverwritingFileSystemStorage(FileSystemStorage):
    def get_available_name(self, name, max_length=None):
        self.delete(name)
        return name


class BuildsStorage(LazyObject):
    def _setup(self):
        self._wrapped = OverwritingFileSystemStorage()


builds_storage = BuildsStorage()
