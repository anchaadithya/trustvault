# Requirements vs. Repository
Legend: **IMPL** = implemented in code, tests written. **NOT VERIFIED** = nothing has been executed yet (no Django in the AI sandbox). Run `python manage.py test -v 2` and update this table with real results.

| Requirement | Where | Status |
|---|---|---|
| Django/SQLite/PostgreSQL/Bootstrap stack | `settings.py`, templates | IMPL / NOT VERIFIED |
| Secure login/logout, hashed passwords | `accounts`, Django auth | IMPL / NOT VERIFIED |
| Login throttling | `accounts.views.ThrottledLoginView` | IMPL / NOT VERIFIED |
| Admin/Owner/Viewer, backend enforcement | `accounts.decorators`, `documents.permissions` | IMPL / NOT VERIFIED |
| Admin manages users (create, role, deactivate) | `accounts.views` | IMPL / NOT VERIFIED |
| Upload, list, delete, metadata, search (name/owner/category/date) | `documents.views` | IMPL / NOT VERIFIED |
| Edit metadata **and content** | `documents.views.edit` | IMPL / NOT VERIFIED |
| Per-document Read/Edit, grant, revoke | `DocumentPermission`, `views.permissions/revoke` | IMPL / NOT VERIFIED |
| Deny by default, per-request DB check, IDOR-safe | `permissions.authorize` | IMPL / NOT VERIFIED |
| Immediate revocation | no caching; `test_revoked_access_fails_on_next_download` | IMPL / NOT VERIFIED |
| Secure download endpoint, audited | `views.download` | IMPL / NOT VERIFIED |
| Upload validation: size, type, magic bytes, random names, private storage | `validators.py`, `storage.py` | IMPL / NOT VERIFIED |
| In-browser inline preview of documents | – | NOT IMPLEMENTED (deliberate: downloads are attachment-only to avoid XSS) |
| Audit: uploads, reads, downloads, edits, deletes, grants/revokes, denials, logins, admin actions | `audit/`, signals, views | IMPL / NOT VERIFIED |
| Audit immutability (app level), survives document deletion | `audit.models` | IMPL / NOT VERIFIED (tamper-proof storage: NOT IMPLEMENTED) |
| Admin dashboard, restricted | `audit.views` | IMPL / NOT VERIFIED |
| Required automated tests | `*/tests.py`, `test_*.py` (67 tests) | WRITTEN / NOT RUN |
| README, THREATS, PROMPTS, requirements, .env.example, .gitignore | repo root | DONE (PROMPTS needs your real results) |
| Deployment guide, demo checklist, backup script | `DEPLOYMENT.md`, `DEMO_CHECKLIST.md`, `scripts/backup.sh`, `Procfile` | DONE (actual deployment: NOT DONE) |
| `check`, `migrate`, `check --deploy`, encrypted backup/restore test | – | NOT VERIFIED |
| Malware scanning, virus checks, external tamper-resistant log | – | NOT IMPLEMENTED (documented as residual risk) |
