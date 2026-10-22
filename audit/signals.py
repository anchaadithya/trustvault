from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import AuditAction, Outcome
from .services import record


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    record(request, AuditAction.LOGIN, Outcome.SUCCESS, actor=user)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    # Only the submitted username is kept (untrusted text). The password is never read.
    record(request, AuditAction.LOGIN, Outcome.FAILURE, detail="invalid credentials",
           actor_username=str(credentials.get("username", "")))


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user is not None:
        record(request, AuditAction.LOGOUT, Outcome.SUCCESS, actor=user)
