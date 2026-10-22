from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from audit.models import AuditAction, Outcome
from audit.services import record


def role_required(*roles):
    """Backend role check. Anonymous -> login page; wrong role -> 403.

    The role is read from request.user, which Django loads from the database on
    every request, so a role change takes effect on the user's very next request.
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                record(request, AuditAction.ACCESS_DENIED, Outcome.DENIED,
                       detail=f"{request.method} {request.path}")
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
