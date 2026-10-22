from accounts.models import Role
from documents.models import DownloadAccessRequest


def owner_access_request_notifications(request):
    count = 0

    if (
        request.user.is_authenticated
        and request.user.role == Role.OWNER
    ):
        count = DownloadAccessRequest.objects.filter(
            document__owner=request.user,
            status=DownloadAccessRequest.STATUS_PENDING,
        ).count()

    return {
        "owner_pending_request_count": count,
    }