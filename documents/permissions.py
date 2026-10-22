
"""Central document authorization policy."""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.db import models

from accounts.models import Role
from audit.models import Outcome
from audit.services import record

from .models import Document, DocumentPermission, DownloadAccessRequest

READ, EDIT, OWNER = 1, 2, 3


def access_level(user, document):
    """Return the user's access level for a document."""

    if (
        not user.is_authenticated
        or not user.is_active
        or document is None
    ):
        return None

    # Only the actual uploader has ownership access.
    if document.owner_id == user.pk:
        return OWNER if user.role == Role.OWNER else None

    # Admins require an approved READ request to read.
    if user.role == Role.ADMIN:
        approved_read = DownloadAccessRequest.objects.filter(
            document=document,
            requester=user,
            request_type=DownloadAccessRequest.TYPE_READ,
            status=DownloadAccessRequest.STATUS_APPROVED,
        ).exists()

        return READ if approved_read else None

    # Other owners can access documents explicitly shared with them.
    permission = DocumentPermission.objects.filter(
        document=document,
        user=user,
    ).first()

    if permission is None:
        return None

    return EDIT if permission.can_edit else READ


def accessible_documents(user):
    """Return documents visible to the user."""

    if not user.is_authenticated or not user.is_active:
        return Document.objects.none()

    # Admins can see metadata listings only.
    if user.role == Role.ADMIN:
        return Document.objects.all()

    # Owners see their own documents and documents shared with them.
    if user.role == Role.OWNER:
        return Document.objects.filter(
            models.Q(owner=user)
            | models.Q(permissions__user=user)
        ).distinct()

    # Viewers see documents explicitly shared with them.
    return Document.objects.filter(
        permissions__user=user
    ).distinct()


def authorize(request, pk, needed, action):
    """Check authorization before performing a document action."""

    document = Document.objects.filter(pk=pk).first()

    level = (
        access_level(request.user, document)
        if document is not None
        else None
    )

    if level is None or level < needed:
        record(
            request,
            action,
            Outcome.DENIED,
            document=document,
            document_id=pk,
            detail=(
                "insufficient permission"
                if level is not None
                else "no access or not found"
            ),
        )

        if level is None:
            raise Http404

        raise PermissionDenied

    # Only the uploader can perform owner-level actions.
    if needed >= OWNER and document.owner_id != request.user.pk:
        record(
            request,
            action,
            Outcome.DENIED,
            document=document,
            document_id=pk,
            detail="only the document uploader may manage this document",
        )
        raise PermissionDenied

    return document, level
