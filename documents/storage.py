import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateStorage(FileSystemStorage):
    """Files live outside static/media. base_url is None, so .url() always raises:
    there is no way to build a public link to a stored document."""

    def __init__(self):
        super().__init__(file_permissions_mode=0o600, directory_permissions_mode=0o700)

    @property
    def base_location(self):
        return settings.PRIVATE_STORAGE_ROOT  # read at use-time so tests can override it

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return None
