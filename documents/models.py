
import os
import uuid

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from .storage import PrivateStorage
from .validators import category_validator


def private_upload_path(instance, filename):
    """Generate a random storage filename while keeping the extension."""
    extension = os.path.splitext(filename)[1].lower()
    return f"{uuid.uuid4().hex}{extension}"


class Document(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    name = models.CharField(max_length=120)
    category = models.CharField(
        max_length=50,
        default="General",
        validators=[category_validator],
    )
    original_filename = models.CharField(max_length=100)
    file = models.FileField(
        storage=PrivateStorage(),
        upload_to=private_upload_path,
        max_length=100,
    )
    content_type = models.CharField(max_length=50)
    size = models.PositiveBigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.name


class DocumentPermission(models.Model):
    """A user-specific permission for a document."""

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_permissions",
    )
    can_edit = models.BooleanField(default=False)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "user"],
                name="one_permission_per_user_document",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.document}"


class DownloadAccessRequest(models.Model):
    """Request for read or download access from a document owner."""

    TYPE_READ = "read"
    TYPE_DOWNLOAD = "download"

    TYPE_CHOICES = [
        (TYPE_READ, "Read"),
        (TYPE_DOWNLOAD, "Download"),
    ]

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_EXPIRED, "Expired"),
    ]

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="download_requests",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="download_access_requests",
    )
    request_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=TYPE_DOWNLOAD,
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    # Download approval validity: one hour from approval.
    approval_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # A download approval can be successfully used only once.
    downloaded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-requested_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "requester", "request_type"],
                name="one_access_request_per_type_document_user",
            )
        ]

    @property
    def approval_is_valid(self):
        """Return whether an unused download approval is still valid."""
        if self.request_type != self.TYPE_DOWNLOAD:
            return False

        if self.status != self.STATUS_APPROVED:
            return False

        if self.downloaded_at is not None:
            return False

        if self.approval_expires_at is None:
            return False

        return timezone.now() < self.approval_expires_at

    def approve(self, reviewer):
        """Approve a request and set its one-hour expiry."""
        now = timezone.now()

        self.status = self.STATUS_APPROVED
        self.reviewed_at = now
        self.reviewed_by = reviewer

        if self.request_type == self.TYPE_DOWNLOAD:
            self.approval_expires_at = now + timedelta(hours=1)
            self.downloaded_at = None
        else:
            self.approval_expires_at = None

        self.save(
            update_fields=[
                "status",
                "reviewed_at",
                "reviewed_by",
                "approval_expires_at",
                "downloaded_at",
            ]
        )

    def __str__(self):
        return (
            f"{self.requester} - {self.document} "
            f"({self.request_type}: {self.status})"
        )
