import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from audit.models import AuditAction as A, AuditEvent

from .models import DocumentPermission
from .tests import PDF, TMP, client_for, mkdoc, mkuser

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


@override_settings(PRIVATE_STORAGE_ROOT=TMP)
class ContentReplacementTests(TestCase):
    def setUp(self):
        self.owner = mkuser("ce_owner", Role.OWNER)
        self.editor = mkuser("ce_editor", Role.VIEWER)
        self.reader = mkuser("ce_reader", Role.VIEWER)
        self.stranger = mkuser("ce_stranger", Role.OWNER)
        self.doc = mkdoc(self.owner, "Doc")
        DocumentPermission.objects.create(document=self.doc, user=self.editor, can_edit=True)
        DocumentPermission.objects.create(document=self.doc, user=self.reader, can_edit=False)
        self.url = reverse("document_edit", args=[self.doc.pk])

    def payload(self, name="new.png", data=PNG):
        return {"name": "Doc", "category": "Legal", "new_file": SimpleUploadedFile(name, data)}

    def test_edit_permission_can_replace_content(self):
        old_path = self.doc.file.path
        with self.captureOnCommitCallbacks(execute=True):
            r = client_for(self.editor).post(self.url, self.payload())
        self.assertEqual(r.status_code, 302)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.content_type, "image/png")
        self.assertRegex(self.doc.file.name, r"^[0-9a-f]{32}\.png$")
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(AuditEvent.objects.filter(action=A.EDIT, document_id=self.doc.pk,
                                                  detail__contains="content replaced").exists())

    def test_invalid_replacement_rejected_and_document_unchanged(self):
        r = client_for(self.editor).post(self.url, self.payload("evil.exe", b"MZ\x90"))
        self.assertEqual(r.status_code, 200)
        r = client_for(self.editor).post(self.url, self.payload("fake.png", b"not a png"))
        self.assertEqual(r.status_code, 200)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.content_type, "application/pdf")

    def test_read_only_and_stranger_cannot_replace(self):
        self.assertEqual(client_for(self.reader).post(self.url, self.payload()).status_code, 403)
        self.assertEqual(client_for(self.stranger).post(self.url, self.payload()).status_code, 404)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.content_type, "application/pdf")
