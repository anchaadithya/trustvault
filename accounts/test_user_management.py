from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from audit.models import AuditAction as A, AuditEvent, Outcome as O

from .models import Role, User

PW = "Str0ng-pass-123"


def mk(name, role):
    return User.objects.create_user(name, password=PW, role=role)


def login_client(user):
    c = Client()
    c.force_login(user)
    return c


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = mk("adm", Role.ADMIN)
        self.owner = mk("own", Role.OWNER)

    def test_admin_creates_user_with_hashed_password_and_audit(self):
        r = login_client(self.admin).post(reverse("user_create"),
                                          {"username": "newbie", "role": "VIEWER", "password": "An0ther-Str0ng-pw"})
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(username="newbie")
        self.assertEqual(u.role, Role.VIEWER)
        self.assertNotEqual(u.password, "An0ther-Str0ng-pw")
        self.assertTrue(u.check_password("An0ther-Str0ng-pw"))
        self.assertTrue(AuditEvent.objects.filter(action=A.USER_MANAGE, outcome=O.SUCCESS, actor_id=self.admin.pk).exists())

    def test_weak_password_and_duplicate_username_rejected(self):
        c = login_client(self.admin)
        c.post(reverse("user_create"), {"username": "weak", "role": "VIEWER", "password": "123"})
        c.post(reverse("user_create"), {"username": "OWN", "role": "VIEWER", "password": "An0ther-Str0ng-pw"})
        self.assertFalse(User.objects.filter(username="weak").exists())
        self.assertEqual(User.objects.filter(username__iexact="own").count(), 1)

    def test_non_admin_cannot_create_or_toggle_users_and_is_audited(self):
        c = login_client(self.owner)
        self.assertEqual(c.post(reverse("user_create"), {"username": "x", "role": "ADMIN", "password": "An0ther-Str0ng-pw"}).status_code, 403)
        self.assertEqual(c.post(reverse("toggle_active", args=[self.admin.pk])).status_code, 403)
        self.assertFalse(User.objects.filter(username="x").exists())
        self.assertTrue(AuditEvent.objects.filter(action=A.ACCESS_DENIED, outcome=O.DENIED, actor_id=self.owner.pk).exists())

    def test_deactivated_user_loses_existing_session_immediately(self):
        c = login_client(self.owner)
        self.assertEqual(c.get(reverse("home")).status_code, 200)
        login_client(self.admin).post(reverse("toggle_active", args=[self.owner.pk]))
        r = c.get(reverse("home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login"), r["Location"])

    def test_admin_cannot_deactivate_self_or_change_own_role_and_it_is_audited(self):
        c = login_client(self.admin)
        self.assertEqual(c.post(reverse("toggle_active", args=[self.admin.pk])).status_code, 403)
        self.assertEqual(c.post(reverse("change_role", args=[self.admin.pk]), {"role": "VIEWER"}).status_code, 403)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, Role.ADMIN)
        self.assertEqual(AuditEvent.objects.filter(outcome=O.DENIED, actor_id=self.admin.pk).count(), 2)


class LoginThrottleTests(TestCase):
    def setUp(self):
        mk("victim", Role.VIEWER)
        mk("other", Role.VIEWER)

    def test_lockout_after_repeated_failures_even_with_correct_password(self):
        c = Client()
        for _ in range(5):
            c.post(reverse("login"), {"username": "victim", "password": "wrong"})
        r = c.post(reverse("login"), {"username": "victim", "password": PW})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", c.session)
        self.assertTrue(AuditEvent.objects.filter(action=A.LOGIN, outcome=O.DENIED, actor_username="victim").exists())

    def test_other_users_not_locked_by_someone_elses_failures(self):
        c = Client()
        for _ in range(5):
            c.post(reverse("login"), {"username": "victim", "password": "wrong"})
        r = Client().post(reverse("login"), {"username": "other", "password": PW})
        self.assertEqual(r.status_code, 302)


class SeedDemoTests(TestCase):
    @override_settings(DEBUG=False)
    def test_refuses_when_debug_off(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())
        self.assertEqual(User.objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_creates_demo_users_in_debug(self):
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(set(User.objects.values_list("role", flat=True)), {Role.ADMIN, Role.OWNER, Role.VIEWER})
