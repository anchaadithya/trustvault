from .models import AuditEvent


def record(request, action, outcome, document=None, document_id=None, detail="", actor=None, actor_username=""):
    """Write one audit event. Identity comes from the authenticated request, never from client input.

    `detail` must never contain passwords, tokens or file contents.
    """
    user = actor
    if user is None and request is not None:
        u = getattr(request, "user", None)
        if u is not None and u.is_authenticated:
            user = u
    return AuditEvent.objects.create(
        actor_id=user.pk if user else None,
        actor_username=(user.username if user else actor_username)[:150],
        action=action,
        outcome=outcome,
        document_id=document.pk if document is not None else document_id,
        document_name=(document.name if document is not None else "")[:120],
        detail=detail[:255],
        ip_address=request.META.get("REMOTE_ADDR") if request is not None else None,
    )
