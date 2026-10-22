
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Role
from audit.models import AuditAction, Outcome
from audit.services import record

from .forms import UploadForm, EditForm, GrantForm, FilterForm
from .models import Document, DocumentPermission, DownloadAccessRequest


APPROVAL_DURATION = timedelta(hours=1)


def _is_owner(user, document):
    return (
        user.is_authenticated
        and user.role == Role.OWNER
        and document.owner_id == user.pk
    )


def _approved_download(user, document):
    now = timezone.now()
    return DownloadAccessRequest.objects.filter(
        document=document,
        requester=user,
        request_type=DownloadAccessRequest.TYPE_DOWNLOAD,
        status=DownloadAccessRequest.STATUS_APPROVED,
        downloaded_at__isnull=True,
        approval_expires_at__gt=now,
    ).exists()


def _approved_view(user, document):
    now = timezone.now()
    return DownloadAccessRequest.objects.filter(
        document=document,
        requester=user,
        request_type=DownloadAccessRequest.TYPE_READ,
        status=DownloadAccessRequest.STATUS_APPROVED,
        approval_expires_at__gt=now,
    ).exists()


@login_required
def document_list(request):
    form = FilterForm(request.GET or None)
    documents = Document.objects.select_related("owner").all()

    if form.is_valid():
        data = form.cleaned_data
        if data.get("q"):
            documents = documents.filter(name__icontains=data["q"])
        if data.get("owner"):
            documents = documents.filter(
                owner__username__icontains=data["owner"]
            )
        if data.get("category"):
            documents = documents.filter(
                category__icontains=data["category"]
            )
        if data.get("date_from"):
            documents = documents.filter(
                uploaded_at__date__gte=data["date_from"]
            )
        if data.get("date_to"):
            documents = documents.filter(
                uploaded_at__date__lte=data["date_to"]
            )

    # Listing shows document names; opening details is separately protected.
    return render(
        request,
        "documents/document_list.html",
        {"documents": documents, "form": form},
    )


@login_required
def upload(request):
    if request.user.role != Role.OWNER:
        raise PermissionDenied

    form = UploadForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        uploaded_file = form.cleaned_data["file"]
        meta = form.meta

        document = Document(
            owner=request.user,
            name=(form.cleaned_data.get("name") or meta["display"])[:120],
            category=form.cleaned_data.get("category") or "General",
            original_filename=meta["display"][:100],
            content_type=meta["content_type"][:50],
            size=uploaded_file.size,
        )
        document.file.save("upload" + meta["ext"], uploaded_file, save=True)

        record(
            request,
            AuditAction.UPLOAD,
            Outcome.SUCCESS,
            detail=f"uploaded document {document.pk}",
        )
        messages.success(request, "Document uploaded successfully.")
        return redirect("document_detail", pk=document.pk)

    return render(request, "documents/upload.html", {"form": form})


@login_required
@require_POST
def request_download_access(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if document.owner_id == request.user.pk:
        messages.info(request, "You already own this document.")
        return redirect("document_detail", pk=pk)

    if request.user.role not in (Role.VIEWER, Role.ADMIN, Role.OWNER):
        raise PermissionDenied

    with transaction.atomic():
        access_request = DownloadAccessRequest.objects.select_for_update().filter(
            document=document,
            requester=request.user,
            request_type=DownloadAccessRequest.TYPE_DOWNLOAD,
        ).first()

        now = timezone.now()

        if access_request is None:
            DownloadAccessRequest.objects.create(
                document=document,
                requester=request.user,
                request_type=DownloadAccessRequest.TYPE_DOWNLOAD,
                status=DownloadAccessRequest.STATUS_PENDING,
            )
            messages.success(request, "Download request sent to the owner.")

        elif access_request.status == DownloadAccessRequest.STATUS_PENDING:
            messages.info(request, "Your download request is already pending.")

        elif (
            access_request.status == DownloadAccessRequest.STATUS_APPROVED
            and access_request.downloaded_at is None
            and access_request.approval_expires_at
            and access_request.approval_expires_at > now
        ):
            messages.info(request, "Your download approval is still active.")

        else:
            access_request.status = DownloadAccessRequest.STATUS_PENDING
            access_request.requested_at = now
            access_request.reviewed_at = None
            access_request.reviewed_by = None
            access_request.approval_expires_at = None
            access_request.downloaded_at = None
            access_request.save(update_fields=[
                "status", "requested_at", "reviewed_at", "reviewed_by",
                "approval_expires_at", "downloaded_at",
            ])
            messages.success(request, "New download request sent to the owner.")

    return redirect("document_detail", pk=pk)


@login_required
@require_POST
def request_view_access(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if document.owner_id == request.user.pk:
        messages.info(request, "You already own this document.")
        return redirect("document_detail", pk=pk)

    with transaction.atomic():
        access_request = DownloadAccessRequest.objects.select_for_update().filter(
            document=document,
            requester=request.user,
            request_type=DownloadAccessRequest.TYPE_READ,
        ).first()

        now = timezone.now()

        if access_request is None:
            DownloadAccessRequest.objects.create(
                document=document,
                requester=request.user,
                request_type=DownloadAccessRequest.TYPE_READ,
                status=DownloadAccessRequest.STATUS_PENDING,
            )
            messages.success(request, "View access request sent to the owner.")

        elif (
            access_request.status == DownloadAccessRequest.STATUS_APPROVED
            and access_request.approval_expires_at
            and access_request.approval_expires_at > now
        ):
            messages.info(request, "Your view access is already active.")

        elif access_request.status == DownloadAccessRequest.STATUS_PENDING:
            messages.info(request, "Your view request is already pending.")

        else:
            access_request.status = DownloadAccessRequest.STATUS_PENDING
            access_request.requested_at = now
            access_request.reviewed_at = None
            access_request.reviewed_by = None
            access_request.approval_expires_at = None
            access_request.downloaded_at = None
            access_request.save(update_fields=[
                "status", "requested_at", "reviewed_at", "reviewed_by",
                "approval_expires_at", "downloaded_at",
            ])
            messages.success(request, "New view request sent to the owner.")

    return redirect("document_detail", pk=pk)


@login_required
def download_requests(request):
    if request.user.role != Role.OWNER:
        raise PermissionDenied

    requests_list = (
        DownloadAccessRequest.objects.filter(
            document__owner=request.user,
        )
        .select_related("document", "requester")
        .order_by("-requested_at")
    )

    return render(
        request,
        "documents/download_requests.html",
        {
            "requests": requests_list,
            "download_requests": requests_list,
        },
    )


@login_required
@require_POST
def review_download_request(request, request_pk, decision):
    if request.user.role != Role.OWNER:
        raise PermissionDenied

    if decision not in ("approve", "reject"):
        raise Http404

    with transaction.atomic():
        access_request = get_object_or_404(
            DownloadAccessRequest.objects.select_for_update().select_related(
                "document", "requester"
            ),
            pk=request_pk,
            document__owner=request.user,
        )

        if access_request.status != DownloadAccessRequest.STATUS_PENDING:
            messages.info(request, "This request has already been reviewed.")
            return redirect("download_requests")

        now = timezone.now()
        access_request.reviewed_at = now
        access_request.reviewed_by = request.user

        if decision == "approve":
            access_request.status = DownloadAccessRequest.STATUS_APPROVED
            access_request.approval_expires_at = now + APPROVAL_DURATION
            if access_request.request_type == DownloadAccessRequest.TYPE_DOWNLOAD:
                access_request.downloaded_at = None
        else:
            access_request.status = DownloadAccessRequest.STATUS_REJECTED
            access_request.approval_expires_at = None

        access_request.save(update_fields=[
            "status", "reviewed_at", "reviewed_by",
            "approval_expires_at", "downloaded_at",
        ])

    messages.success(request, f"{access_request.get_request_type_display()} request {decision}d.")
    return redirect("download_requests")


@login_required
def detail(request, pk):
    document = get_object_or_404(
        Document.objects.select_related("owner"),
        pk=pk,
    )

    own_document = document.owner_id == request.user.pk
    view_request = DownloadAccessRequest.objects.filter(
        document=document,
        requester=request.user,
        request_type=DownloadAccessRequest.TYPE_READ,
    ).first()

    download_request = DownloadAccessRequest.objects.filter(
        document=document,
        requester=request.user,
        request_type=DownloadAccessRequest.TYPE_DOWNLOAD,
    ).first()

    can_view = own_document or _approved_view(request.user, document)

    # Do not reveal document metadata to users without view permission.
    if not can_view:
        return render(
            request,
            "documents/detail.html",
            {
                "document": None,
                "protected_document": True,
                "protected_document_id": document.pk,
                "is_document_owner": False,
                "can_view": False,
                "can_download": False,
                "view_request": view_request,
                "download_request": download_request,
                "events": [],
            },
        )

    can_download = own_document or _approved_download(request.user, document)

    return render(
        request,
        "documents/detail.html",
        {
            "document": document,
            "protected_document": False,
            "protected_document_id": document.pk,
            "is_document_owner": own_document,
            "can_view": True,
            "can_download": can_download,
            "view_request": view_request,
            "download_request": download_request,
            "events": [],
        },
    )


@login_required
def download(request, pk):
    document = get_object_or_404(Document, pk=pk)
    own_document = document.owner_id == request.user.pk

    if not own_document:
        with transaction.atomic():
            access_request = DownloadAccessRequest.objects.select_for_update().filter(
                document=document,
                requester=request.user,
                request_type=DownloadAccessRequest.TYPE_DOWNLOAD,
                status=DownloadAccessRequest.STATUS_APPROVED,
                downloaded_at__isnull=True,
                approval_expires_at__gt=timezone.now(),
            ).first()

            if access_request is None:
                record(
                    request, AuditAction.DOWNLOAD, Outcome.FAILURE,
                    detail=f"blocked unauthorized download of document {document.pk}",
                )
                messages.error(request, "Download denied. Request owner approval.")
                return redirect("document_detail", pk=pk)

            try:
                file_handle = document.file.open("rb")
            except (FileNotFoundError, OSError, ValueError):
                raise Http404("Document file is unavailable.")

            access_request.downloaded_at = timezone.now()
            access_request.save(update_fields=["downloaded_at"])
    else:
        try:
            file_handle = document.file.open("rb")
        except (FileNotFoundError, OSError, ValueError):
            raise Http404("Document file is unavailable.")

    record(
        request, AuditAction.DOWNLOAD, Outcome.SUCCESS,
        detail=f"downloaded document {document.pk}",
    )

    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=document.original_filename,
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
def edit(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if not _is_owner(request.user, document):
        raise PermissionDenied

    form = EditForm(request.POST or None, request.FILES or None, instance=document)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            updated = form.save(commit=False)
            new_file = form.cleaned_data.get("new_file")
            if new_file:
                meta = form.meta
                updated.original_filename = meta["display"][:100]
                updated.content_type = meta["content_type"][:50]
                updated.size = new_file.size
                updated.file = new_file
            updated.save()

        messages.success(request, "Document updated successfully.")
        return redirect("document_detail", pk=pk)

    return render(request, "documents/edit.html", {"form": form, "document": document})


@login_required
@require_POST
def delete(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if not _is_owner(request.user, document):
        raise PermissionDenied

    document.delete()
    messages.success(request, "Document deleted successfully.")
    return redirect("documents")


@login_required
def permissions(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if not _is_owner(request.user, document):
        raise PermissionDenied

    form = GrantForm(document, request.POST or None)

    if request.method == "POST" and form.is_valid():
        DocumentPermission.objects.update_or_create(
            document=document,
            user=form.target,
            defaults={
                "can_edit": form.cleaned_data["level"] == "edit",
                "granted_by": request.user,
            },
        )
        messages.success(request, "Permission granted.")
        return redirect("document_permissions", pk=pk)

    return render(
        request,
        "documents/permissions.html",
        {
            "document": document,
            "form": form,
            "permissions": document.permissions.select_related("user"),
        },
    )


@login_required
@require_POST
def revoke(request, pk, perm_pk):
    document = get_object_or_404(Document, pk=pk)

    if not _is_owner(request.user, document):
        raise PermissionDenied

    permission = get_object_or_404(
        DocumentPermission,
        pk=perm_pk,
        document=document,
    )
    permission.delete()
    messages.success(request, "Permission revoked.")
    return redirect("document_permissions", pk=pk)
