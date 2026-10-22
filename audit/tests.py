from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Role, User

from .models import AuditAction as A, AuditEvent, AuditImmutableError, Outcome as O
from .services import record

PW = "Str0ng-pass-123"


class AuditIntegrityTests(TestCase):
    def setUp(self):
        self.event = record(None, A.VIEW, O.SUCCESS, detail="x")

    def test_cannot_modify_event(self):
        self.event.detail = "tampered"
        with self.assertRaises(AuditImmutableError):
            self.event.save()

    def test_cannot_delete_event(self):
        with self.assertRaises(AuditImmutableError):
            self.event.delete()

    def test_cannot_bulk_update_or_delete(self):
        with self.assertRaises(AuditImmutableError):
            AuditEvent.objects.all().update(outcome=O.SUCCESS)
        with self.assertRaises(AuditImmutableError):
            AuditEvent.objects.all().delete()
        self.assertEqual(AuditEvent.objects.count(), 1)


class AuditAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("adm", password=PW, role=Role.ADMIN)
        self.owner = User.objects.create_user("own", password=PW, role=Role.OWNER)
        self.viewer = User.objects.create_user("vie", password=PW, role=Role.VIEWER)

    def get(self, user):
        c = Client()
        if user:
            c.force_login(user)
        return c.get(reverse("audit_dashboard"))

    def test_dashboard_restricted_to_admin(self):
        self.assertEqual(self.get(None).status_code, 302)
        self.assertEqual(self.get(self.owner).status_code, 403)
        self.assertEqual(self.get(self.viewer).status_code, 403)
        self.assertEqual(self.get(self.admin).status_code, 200)

    def test_user_admin_actions_restricted_to_admin(self):
        c = Client()
        c.force_login(self.owner)
        self.assertEqual(c.get(reverse("user_list")).status_code, 403)

    def test_login_success_and_failure_audited_without_password(self):
        Client().post(reverse("login"), {"username": "own", "password": PW})
        Client().post(reverse("login"), {"username": "own", "password": "WRONG-secret-pw"})
        self.assertTrue(AuditEvent.objects.filter(action=A.LOGIN, outcome=O.SUCCESS, actor_id=self.owner.pk).exists())
        self.assertTrue(AuditEvent.objects.filter(action=A.LOGIN, outcome=O.FAILURE, actor_username="own").exists())
        for e in AuditEvent.objects.all():
            self.assertNotIn("WRONG-secret-pw", f"{e.detail}{e.actor_username}")
            self.assertNotIn(PW, f"{e.detail}{e.actor_username}")

    def test_role_change_audited(self):
        c = Client()
        c.force_login(self.admin)
        c.post(reverse("change_role", args=[self.viewer.pk]), {"role": Role.OWNER})
        self.assertTrue(AuditEvent.objects.filter(action=A.ROLE_CHANGE, actor_id=self.admin.pk).exists())

    def test_dashboard_filters(self):
        record(None, A.DOWNLOAD, O.DENIED, detail="d")
        c = Client()
        c.force_login(self.admin)
        r = c.get(reverse("audit_dashboard"), {"outcome": "DENIED"})
        self.assertContains(r, "DOWNLOAD")
