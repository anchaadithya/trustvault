import codecs
import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

category_validator = RegexValidator(r"^[\w \-]{1,50}$", "Category may contain letters, numbers, spaces, - and _ only.")


def _is_text(head):
    if b"\x00" in head:
        return False
    try:
        codecs.getincrementaldecoder("utf-8")().decode(head, final=False)
    except UnicodeDecodeError:
        return False
    return True


# extension -> (MIME type we store/serve, check of the real leading bytes)
ALLOWED = {
    ".pdf": ("application/pdf", lambda h: h.startswith(b"%PDF-")),
    ".png": ("image/png", lambda h: h.startswith(b"\x89PNG\r\n\x1a\n")),
    ".jpg": ("image/jpeg", lambda h: h.startswith(b"\xff\xd8\xff")),
    ".jpeg": ("image/jpeg", lambda h: h.startswith(b"\xff\xd8\xff")),
    ".txt": ("text/plain", _is_text),
}


def clean_filename(name):
    """Display-only name. It is NEVER used to build a storage path."""
    name = os.path.basename((name or "").replace("\\", "/"))
    name = "".join(c for c in name if c.isprintable()).strip()[:100]
    if name in ("", ".", ".."):
        raise ValidationError("Invalid file name.")
    return name


def validate_upload(upload):
    """Return (display_name, extension, content_type) or raise ValidationError."""
    display = clean_filename(upload.name)
    if upload.size == 0:
        raise ValidationError("The file is empty.")
    if upload.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError(f"File too large (limit {settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB).")
    ext = os.path.splitext(display)[1].lower()
    if ext not in ALLOWED:
        raise ValidationError("File type not allowed. Allowed: PDF, PNG, JPG, TXT.")
    content_type, looks_right = ALLOWED[ext]
    upload.seek(0)
    head = upload.read(8192)
    upload.seek(0)
    if not looks_right(head):  # extension alone is not trusted
        raise ValidationError("File contents do not match its extension.")
    return display, ext, content_type
