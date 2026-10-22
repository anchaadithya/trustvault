from django.db import models


class AuditImmutableError(Exception):
    """Raised when code tries to modify or delete an audit record."""


class AuditAction(models.TextChoices):
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Logout"
    UPLOAD = "UPLOAD", "Upload"
    VIEW = "VIEW", "View"
    DOWNLOAD = "DOWNLOAD", "Download"
    EDIT = "EDIT", "Edit"
    DELETE = "DELETE", "Delete"
    GRANT = "GRANT", "Permission granted"
    REVOKE = "REVOKE", "Permission revoked"
    ROLE_CHANGE = "ROLE_CHANGE", "Role change"
    AUDIT_VIEW = "AUDIT_VIEW", "Audit dashboard view"
    USER_MANAGE = "USER_MANAGE", "User management"
    ACCESS_DENIED = "ACCESS_DENIED", "Access denied"


class Outcome(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    DENIED = "DENIED", "Denied"
    FAILURE = "FAILURE", "Failure"


class AuditQuerySet(models.QuerySet):
    def update(self, *args, **kwargs):
        raise AuditImmutableError("Audit records cannot be updated.")

    def delete(self):
        raise AuditImmutableError("Audit records cannot be deleted.")


class AuditEvent(models.Model):
    """Append-only security log.

    Deliberately NO foreign keys: user/document IDs and names are copied in, so
    deleting a user or document never cascades into (or erases) the evidence.
    """

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)  # server-generated
    actor_id = models.IntegerField(null=True, blank=True, db_index=True)
    actor_username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=20, choices=AuditAction.choices, db_index=True)
    outcome = models.CharField(max_length=10, choices=Outcome.choices, db_index=True)
    document_id = models.IntegerField(null=True, blank=True, db_index=True)
    document_name = models.CharField(max_length=120, blank=True)
    detail = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    objects = AuditQuerySet.as_manager()

    class Meta:
        ordering = ["-timestamp", "-id"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditImmutableError("Audit records cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditImmutableError("Audit records cannot be deleted.")

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} {self.actor_username} {self.action} {self.outcome}"
