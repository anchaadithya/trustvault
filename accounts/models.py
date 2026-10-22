
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    OWNER = "OWNER", "Owner"
    VIEWER = "VIEWER", "Viewer"


class TrustVaultUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(
            username=username,
            email=email,
            password=password,
            **extra_fields,
        )


class User(AbstractUser):
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    objects = TrustVaultUserManager()

    @property
    def is_admin_role(self):
        return self.role == Role.ADMIN

    @property
    def is_owner_role(self):
        return self.role == Role.OWNER

    def __str__(self):
        return f"{self.username} ({self.role})"
