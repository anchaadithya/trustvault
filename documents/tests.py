import re
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import Role, User
from audit.models import AuditAction as A, AuditEvent, Outcome as O

from .models import Document, DocumentPermission

TMP = tempfile.mkdtemp()
PDF = b"%PDF-1.4\n%secret contents\n"
PW = "Str0ng-pass-123"


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def mkuser(name, role):
    return User.objects.create_user(username=name, password=PW, role=role)


def client_for(user):
    c = Client()
    c.force_login(user)
    return c


def mkdoc(owner, name="Report", content=PDF):
    doc = Document(owner=owner, name=name, category="Legal", original_filename="report.pdf",
                   content_type="application/pdf", size=len(content))
    doc.file.save("upload.pdf", ContentFile(content), save=False)
    doc.save()
    return doc


def body(resp):
    return b"".join(resp.streaming_content)


def audited(action, outcome, user=None, doc=None):
    qs = AuditEvent.objects.filter(action=action, outcome=outcome)
    if user:
        qs = qs.filter(actor_id=user.pk)
    if doc:
        qs = qs.filter(document_id=doc.pk)
    return qs.exists()


@override_settings(PRIVATE_STORAGE_ROOT=TMP)
class DocumentSecurityTests(TestCase):
    def setUp(self):
        self.a = mkuser("owner_a", Role.OWNER)
        self.b = mkuser("owner_b", Role.OWNER)
        self.v = mkuser("viewer", Role.VIEWER)
        self.admin = mkuser("admin", Role.ADMIN)
        self.doc = mkdoc(self.b, "B private")

    # --- owner / viewer happy paths ---
    def test_owner_can_view_and_download_own_document(self):
        c = client_for(self.b)
        self.assertEqual(c.get(reverse("document_detail", args=[self.doc.pk])).status_code, 200)
        r = c.get(reverse("document_download", args=[self.doc.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(body(r), PDF)
        self.assertIn("attachment", r["Content-Disposition"])
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_authorized_viewer_can_read_and_download(self):
        DocumentPermission.objects.create(document=self.doc, user=self.v)
        c = client_for(self.v)
        self.assertEqual(c.get(reverse("document_detail", args=[self.doc.pk])).status_code, 200)
        self.assertEqual(body(c.get(reverse("document_download", args=[self.doc.pk]))), PDF)

    def test_download_success_is_audited(self):
        client_for(self.b).get(reverse("document_download", args=[self.doc.pk]))
        self.assertTrue(audited(A.DOWNLOAD, O.SUCCESS, self.b, self.doc))

    # --- SECURITY REGRESSION: user A cannot access user B's private document by ID ---
    def test_regression_user_a_cannot_access_user_b_document_even_knowing_id(self):
        c = client_for(self.a)
        pk = self.doc.pk
        for name in ("document_detail", "document_download", "document_edit", "document_permissions"):
            self.assertEqual(c.get(reverse(name, args=[pk])).status_code, 404, name)
        self.assertEqual(c.post(reverse("document_delete", args=[pk])).status_code, 404)
        self.assertTrue(Document.objects.filter(pk=pk).exists())
        self.assertTrue(audited(A.DOWNLOAD, O.DENIED, self.a, self.doc))

    def test_unauthorized_response_does_not_leak_content(self):
        r = client_for(self.a).get(reverse("document_download", args=[self.doc.pk]))
        self.assertNotIn(b"secret contents", r.content)

    def test_changing_document_id_cannot_bypass_authorization(self):
        mine = mkdoc(self.a, "A doc")
        c = client_for(self.a)
        self.assertEqual(c.get(reverse("document_download", args=[mine.pk])).status_code, 200)
        self.assertEqual(c.get(reverse("document_download", args=[self.doc.pk])).status_code, 404)
        self.assertEqual(c.get(reverse("document_download", args=[999999])).status_code, 404)

    def test_anonymous_redirected_to_login(self):
        r = Client().get(reverse("document_download", args=[self.doc.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login"), r["Location"])

    def test_admin_role_cannot_read_document_contents(self):
        r = client_for(self.admin).get(reverse("document_download", args=[self.doc.pk]))
        self.assertEqual(r.status_code, 404)

    def test_admin_with_stale_permission_row_still_denied(self):
        DocumentPermission.objects.create(document=self.doc, user=self.admin)
        self.assertEqual(client_for(self.admin).get(reverse("document_download", args=[self.doc.pk])).status_code, 404)

    # --- read vs edit ---
    def test_read_permission_cannot_edit_or_delete_or_share(self):
        DocumentPermission.objects.create(document=self.doc, user=self.v, can_edit=False)
        c = client_for(self.v)
        self.assertEqual(c.post(reverse("document_edit", args=[self.doc.pk]), {"name": "x", "category": "y"}).status_code, 403)
        self.assertEqual(c.post(reverse("document_delete", args=[self.doc.pk])).status_code, 403)
        self.assertEqual(c.post(reverse("document_permissions", args=[self.doc.pk]),
                                {"username": "viewer", "level": "edit"}).status_code, 403)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.name, "B private")
        self.assertTrue(audited(A.EDIT, O.DENIED, self.v, self.doc))

    def test_edit_permission_can_edit_metadata_but_not_delete_or_share(self):
        DocumentPermission.objects.create(document=self.doc, user=self.v, can_edit=True)
        c = client_for(self.v)
        r = c.post(reverse("document_edit", args=[self.doc.pk]), {"name": "Renamed", "category": "Misc"})
        self.assertEqual(r.status_code, 302)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.name, "Renamed")
        self.assertEqual(c.post(reverse("document_delete", args=[self.doc.pk])).status_code, 403)
        self.assertEqual(c.get(reverse("document_permissions", args=[self.doc.pk])).status_code, 403)

    def test_edit_cannot_mass_assign_owner(self):
        c = client_for(self.b)
        c.post(reverse("document_edit", args=[self.doc.pk]),
               {"name": "n", "category": "c", "owner": self.a.pk, "size": 1})
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.owner_id, self.b.pk)
        self.assertEqual(self.doc.size, len(PDF))

    def test_viewer_cannot_grant_self_permission(self):
        c = client_for(self.v)  # no access at all
        r = c.post(reverse("document_permissions", args=[self.doc.pk]), {"username": "viewer", "level": "edit"})
        self.assertEqual(r.status_code, 404)
        self.assertFalse(DocumentPermission.objects.filter(user=self.v).exists())

    def test_other_owner_cannot_grant_on_someone_elses_document(self):
        r = client_for(self.a).post(reverse("document_permissions", args=[self.doc.pk]),
                                    {"username": "owner_a", "level": "read"})
        self.assertEqual(r.status_code, 404)
        self.assertFalse(DocumentPermission.objects.filter(user=self.a).exists())

    # --- grant / revoke ---
    def test_owner_can_grant_and_audit(self):
        r = client_for(self.b).post(reverse("document_permissions", args=[self.doc.pk]),
                                    {"username": "viewer", "level": "read"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(DocumentPermission.objects.filter(document=self.doc, user=self.v, can_edit=False).exists())
        self.assertTrue(audited(A.GRANT, O.SUCCESS, self.b, self.doc))

    def test_cannot_grant_to_admin_or_unknown_user(self):
        c = client_for(self.b)
        for name in ("admin", "nobody"):
            c.post(reverse("document_permissions", args=[self.doc.pk]), {"username": name, "level": "read"})
        self.assertEqual(DocumentPermission.objects.count(), 0)

    def test_revoked_access_fails_on_next_download(self):
        perm = DocumentPermission.objects.create(document=self.doc, user=self.v)
        viewer, owner = client_for(self.v), client_for(self.b)
        url = reverse("document_download", args=[self.doc.pk])
        self.assertEqual(viewer.get(url).status_code, 200)          # allowed
        r = owner.post(reverse("document_revoke", args=[self.doc.pk, perm.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(viewer.get(url).status_code, 404)          # SAME session, next request denied
        self.assertEqual(viewer.get(reverse("document_detail", args=[self.doc.pk])).status_code, 404)
        self.assertTrue(audited(A.REVOKE, O.SUCCESS, self.b, self.doc))
        self.assertTrue(audited(A.DOWNLOAD, O.DENIED, self.v, self.doc))

    def test_cannot_revoke_permission_of_another_document(self):
        other = mkdoc(self.a, "other")
        perm = DocumentPermission.objects.create(document=other, user=self.v)
        r = client_for(self.b).post(reverse("document_revoke", args=[self.doc.pk, perm.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(DocumentPermission.objects.filter(pk=perm.pk).exists())

    # --- delete ---
    def test_owner_can_delete_and_audit_survives(self):
        pk = self.doc.pk
        with self.captureOnCommitCallbacks(execute=True):
            r = client_for(self.b).post(reverse("document_delete", args=[pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Document.objects.filter(pk=pk).exists())
        self.assertTrue(AuditEvent.objects.filter(action=A.DELETE, document_id=pk, document_name="B private").exists())

    def test_delete_requires_post(self):
        self.assertEqual(client_for(self.b).get(reverse("document_delete", args=[self.doc.pk])).status_code, 405)

    # --- list / search ---
    def test_list_shows_only_authorized_documents(self):
        mkdoc(self.a, "A visible")
        r = client_for(self.a).get(reverse("documents"))
        self.assertContains(r, "A visible")
        self.assertNotContains(r, "B private")

    def test_search_filters_by_name_and_owner(self):
        DocumentPermission.objects.create(document=self.doc, user=self.v)
        mkdoc(self.a, "Other thing")
        DocumentPermission.objects.create(document=Document.objects.get(name="Other thing"), user=self.v)
        c = client_for(self.v)
        r = c.get(reverse("documents"), {"q": "private"})
        self.assertContains(r, "B private")
        self.assertNotContains(r, "Other thing")
        r = c.get(reverse("documents"), {"owner": "owner_a"})
        self.assertContains(r, "Other thing")
        self.assertNotContains(r, "B private")


@override_settings(PRIVATE_STORAGE_ROOT=TMP)
class UploadTests(TestCase):
    def setUp(self):
        self.owner = mkuser("up_owner", Role.OWNER)
        self.c = client_for(self.owner)

    def post(self, name, content, ctype="application/octet-stream"):
        return self.c.post(reverse("document_upload"),
                           {"file": SimpleUploadedFile(name, content, ctype), "name": "", "category": "General"})

    def test_valid_pdf_accepted_with_random_stored_name(self):
        r = self.post("My Report.pdf", PDF, "application/pdf")
        self.assertEqual(r.status_code, 302)
        doc = Document.objects.get()
        self.assertRegex(doc.file.name, r"^[0-9a-f]{32}\.pdf$")
        self.assertNotIn("Report", doc.file.name)
        self.assertTrue(audited(A.UPLOAD, O.SUCCESS, self.owner, doc))

    def test_disallowed_extension_rejected(self):
        self.post("run.exe", b"MZ\x90\x00")
        self.assertEqual(Document.objects.count(), 0)
        self.assertTrue(audited(A.UPLOAD, O.FAILURE, self.owner))

    def test_extension_content_mismatch_rejected(self):
        self.post("fake.pdf", b"MZ\x90\x00 not a pdf")
        self.post("fake.png", PDF)
        self.assertEqual(Document.objects.count(), 0)

    def test_binary_masquerading_as_txt_rejected(self):
        self.post("x.txt", b"hello\x00world")
        self.assertEqual(Document.objects.count(), 0)

    def test_empty_file_rejected(self):
        self.post("e.pdf", b"")
        self.assertEqual(Document.objects.count(), 0)

    @override_settings(MAX_UPLOAD_SIZE=100)
    def test_oversized_file_rejected(self):
        self.post("big.pdf", PDF + b"A" * 500)
        self.assertEqual(Document.objects.count(), 0)

    def test_path_traversal_filename_is_neutralised(self):
        for evil in ("../../evil.pdf", "..\\..\\evil.pdf", "/etc/passwd.pdf"):
            self.post(evil, PDF, "application/pdf")
        self.assertEqual(Document.objects.count(), 3)
        for d in Document.objects.all():
            self.assertRegex(d.file.name, r"^[0-9a-f]{32}\.pdf$")
            self.assertTrue(d.file.path.startswith(TMP))
            self.assertNotIn("/", d.original_filename)
            self.assertNotIn("\\", d.original_filename)

    def test_viewer_role_cannot_upload(self):
        v = client_for(mkuser("just_viewer", Role.VIEWER))
        r = v.post(reverse("document_upload"), {"file": SimpleUploadedFile("a.pdf", PDF)})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Document.objects.count(), 0)

    def test_storage_has_no_public_url(self):
        self.post("a.pdf", PDF, "application/pdf")
        with self.assertRaises(ValueError):
            Document.objects.get().file.url
