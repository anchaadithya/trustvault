import secrets

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Role, User


class Command(BaseCommand):
    help = "DEVELOPMENT ONLY: create demo users (demo_admin, demo_alice, demo_bob). Refuses to run when DEBUG is off."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DJANGO_DEBUG=1 (never use demo accounts in production).")
        password = secrets.token_urlsafe(12)
        created_any = False
        for name, role in (("demo_admin", Role.ADMIN), ("demo_alice", Role.OWNER), ("demo_bob", Role.VIEWER)):
            user, created = User.objects.get_or_create(username=name, defaults={"role": role})
            if created:
                user.set_password(password)
                user.save()
                created_any = True
                self.stdout.write(f"created {name} ({role})")
        if created_any:
            self.stdout.write(f"Password for newly created demo users (shown once): {password}")
        else:
            self.stdout.write("Demo users already exist; nothing changed.")
