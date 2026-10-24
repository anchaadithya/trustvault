
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


if getattr(settings, "USE_S3_STORAGE", False):
    from storages.backends.s3 import S3Storage

    class PrivateStorage(S3Storage):
        """Private S3-compatible storage for TrustVault documents."""

        def __init__(self, **kwargs):
            super().__init__(
                bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                region_name="auto",
                access_key=settings.AWS_ACCESS_KEY_ID,
                secret_key=settings.AWS_SECRET_ACCESS_KEY,
                default_acl=None,
                querystring_auth=True,
                file_overwrite=False,
                custom_domain=None,
                addressing_style="path",
                **kwargs,
            )

else:
    class PrivateStorage(FileSystemStorage):
        """Private local storage for development."""

        def __init__(self):
            super().__init__(
                file_permissions_mode=0o600,
                directory_permissions_mode=0o700,
            )

        @property
        def base_location(self):
            return settings.PRIVATE_STORAGE_ROOT

        @property
        def location(self):
            return os.path.abspath(self.base_location)

        @property
        def base_url(self):
            return None
