from django.test import TestCase
from django.urls import reverse

from .models import Role, User


def make_user(username, role=Role.VIEWER, password="Str0ng-pass-123"):
    return User.objects.create_user(username=username, password=password, role=role)


class RoleModelTests(TestCase):
    def test_default_role_is_viewer(self):
        u = User.objects.create_user(username="x", password="Str0ng-pass-123")
        self.assertEqual(u.role, Role.VIEWER)

    def test_superuser_is_admin_role(self):
        u = User.objects.create_superuser(username="root", password="Str0ng-pass-123")
        self.assertEqual(u.role, Role.ADMIN)


class AuthTests(TestCase):
    def test_login_and_home(self):
        make_user("alice", Role.OWNER)
        ok = self.client.post(reverse("login"), {"username": "alice", "password": "Str0ng-pass-123"})
        self.assertRedirects(ok, reverse("home"))
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_bad_password_rejected(self):
        make_user("alice")
        r = self.client.post(reverse("login"), {"username": "alice", "password": "wrong"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login"), r["Location"])

    def test_logout_requires_post(self):
        make_user("alice")
        self.client.login(username="alice", password="Str0ng-pass-123")
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)


class RoleEnforcementTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin1", Role.ADMIN)
        self.owner = make_user("owner1", Role.OWNER)
        self.viewer = make_user("viewer1", Role.VIEWER)

    def login(self, user):
        self.client.login(username=user.username, password="Str0ng-pass-123")

    def test_anonymous_cannot_list_users(self):
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 302)

    def test_non_admins_get_403_on_user_list(self):
        for u in (self.owner, self.viewer):
            self.client.logout()
            self.login(u)
            self.assertEqual(self.client.get(reverse("user_list")).status_code, 403)

    def test_admin_can_list_users(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 200)

    def test_viewer_cannot_promote_self(self):
        self.login(self.viewer)
        r = self.client.post(reverse("change_role", args=[self.viewer.pk]), {"role": Role.ADMIN})
        self.assertEqual(r.status_code, 403)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.role, Role.VIEWER)

    def test_owner_cannot_change_other_roles(self):
        self.login(self.owner)
        r = self.client.post(reverse("change_role", args=[self.viewer.pk]), {"role": Role.OWNER})
        self.assertEqual(r.status_code, 403)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.role, Role.VIEWER)

    def test_admin_can_change_another_users_role(self):
        self.login(self.admin)
        self.client.post(reverse("change_role", args=[self.viewer.pk]), {"role": Role.OWNER})
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.role, Role.OWNER)

    def test_admin_cannot_change_own_role(self):
        self.login(self.admin)
        r = self.client.post(reverse("change_role", args=[self.admin.pk]), {"role": Role.VIEWER})
        self.assertEqual(r.status_code, 403)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, Role.ADMIN)

    def test_invalid_role_rejected(self):
        self.login(self.admin)
        self.client.post(reverse("change_role", args=[self.viewer.pk]), {"role": "SUPERHERO"})
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.role, Role.VIEWER)

    def test_role_change_is_post_only(self):
        self.login(self.admin)
        r = self.client.get(reverse("change_role", args=[self.viewer.pk]))
        self.assertEqual(r.status_code, 405)

    def test_demoted_admin_loses_access_on_next_request(self):
        self.login(self.admin)
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 200)
        User.objects.filter(pk=self.admin.pk).update(role=Role.VIEWER)  # changed by someone else
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 403)
