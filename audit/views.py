
from datetime import timedelta

from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import Role, User
from documents.models import Document

from .models import AuditAction, AuditEvent, Outcome
from .services import record


@role_required(Role.ADMIN)
def dashboard(request):
    # Statistics cover the last 7 days only.
    # Audit history itself is NOT restricted by date.
    since = timezone.now() - timedelta(days=7)
    recent = AuditEvent.objects.filter(timestamp__gte=since)

    stats = {
        "users": User.objects.count(),
        "documents": Document.objects.count(),
        "uploads": recent.filter(
            action=AuditAction.UPLOAD,
            outcome=Outcome.SUCCESS,
        ).count(),
        "downloads": recent.filter(
            action=AuditAction.DOWNLOAD,
            outcome=Outcome.SUCCESS,
        ).count(),
        "permission_changes": recent.filter(
            action__in=[AuditAction.GRANT, AuditAction.REVOKE],
            outcome=Outcome.SUCCESS,
        ).count(),
        "denied": recent.filter(outcome=Outcome.DENIED).count(),
        "total_audit_events": AuditEvent.objects.count(),
    }

    # Start with ALL audit records, regardless of age.
    events = AuditEvent.objects.all()

    action = request.GET.get("action", "").strip()
    outcome = request.GET.get("outcome", "").strip()
    username = request.GET.get("user", "").strip()
    doc_id = request.GET.get("document", "").strip()

    if action in AuditAction.values:
        events = events.filter(action=action)

    if outcome in Outcome.values:
        events = events.filter(outcome=outcome)

    if username:
        events = events.filter(actor_username__icontains=username)

    if doc_id.isdigit():
        events = events.filter(document_id=int(doc_id))

    # Paginate instead of limiting the entire history to the newest 100.
    paginator = Paginator(events, 50)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Record the dashboard visit. This does not change or delete older events.
    record(request, AuditAction.AUDIT_VIEW, Outcome.SUCCESS)

    return render(
        request,
        "audit/dashboard.html",
        {
            "stats": stats,
            "events": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "documents": Document.objects.select_related("owner").order_by(
                "-uploaded_at"
            )[:10],
            "actions": AuditAction.choices,
            "outcomes": Outcome.choices,
            "f": {
                "action": action,
                "outcome": outcome,
                "user": username,
                "document": doc_id,
            },
        },
    )
