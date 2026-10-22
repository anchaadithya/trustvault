# TrustVault Threat Model

## Assets
Confidential files in `PRIVATE_STORAGE_ROOT`; the database (users, permissions, audit); session cookies; `DJANGO_SECRET_KEY`; DB credentials.

## Trust boundaries
Browser ↔ HTTPS ↔ Django ↔ (database, private file store). Everything from the browser (IDs, filenames, form fields, MIME types) is untrusted.

## Authorization design
`documents/permissions.py::authorize()` is the single check used by every document view. It loads the document, then queries `DocumentPermission` fresh from the DB on every request (no cache). No access → 404 (identical to a nonexistent ID); insufficient level → 403; both are audited as DENIED. Admin role never gets content access.

## Threats
| Threat | Impact | Mitigation | Test evidence |
|---|---|---|---|
| IDOR (change `/docs/<id>/…`) | Read others' files | `authorize()` on every view; 404 for no-access | `test_regression_user_a_cannot_access_user_b_document_even_knowing_id`, `test_changing_document_id_…` |
| Viewer self-escalation | Gain Edit/ownership | Only doc owner (role OWNER) may manage grants; role changes admin-only, not self | `test_viewer_cannot_grant_self_permission`, accounts role tests |
| Stale access after revocation | Continued reading | Permission read from DB per request; download re-checks before opening file | `test_revoked_access_fails_on_next_download` |
| Public file URL / guessable path | Direct file fetch | Files outside static/media, random UUID names, no URL route; `storage.url()` raises | `test_storage_has_no_public_url`, upload naming tests |
| Path traversal in filename | Write/read outside store | Filename never used for storage path; display name sanitised | `test_path_traversal_filename_is_neutralised` |
| Malicious upload | Stored malware / XSS | Extension allow-list + magic-byte check, size cap, always served as `attachment` + `nosniff` | `UploadTests` |
| Mass assignment | Change owner/size | ModelForm with explicit `fields` | `test_edit_cannot_mass_assign_owner` |
| CSRF / XSS / SQLi | Session abuse | CSRF middleware, template auto-escaping, ORM only | (framework defaults; no dedicated test) |
| Audit tampering by app users | Hide actions | No update/delete via model or queryset; no FKs so deletes don't cascade | `AuditIntegrityTests` |
| Brute-force login | Account takeover | Failures audited; lockout after 5 failures/username or 20/IP per 15 min | `LoginThrottleTests` |
| Privilege probing (non-admin hits admin URLs) | Recon / escalation | `role_required` returns 403 and writes ACCESS_DENIED | `test_non_admin_cannot_create_or_toggle_users_and_is_audited` |
| Deactivated user keeps session | Continued access | Django re-loads user each request; inactive users are logged out | `test_deactivated_user_loses_existing_session_immediately` |

## Secure download flow
Authenticate → load doc → check current permission → audit → open file → stream as attachment with `Cache-Control: private, no-store`. No signed/expiring links are used, so old links can't outlive a revocation.

## Revocation limits
Revocation blocks the next request. A user who already downloaded the file keeps it; it can't be recalled. A request that passed the check milliseconds before revocation may still finish streaming (small race window; SQLite has no row locking, and a grant/revoke runs in a transaction).

## Audit trail: what it proves and doesn't
Proves the application served a file to an authenticated account at a server time. Does **not** prove a person read it, that the account holder was the real person, or that the DB wasn't altered by someone with direct database access. Application-level append-only ≠ tamper-resistant: for that, ship events to an external write-once log (syslog/SIEM, S3 object lock) or add hash-chaining. IP is `REMOTE_ADDR` (behind a proxy it is the proxy's address unless configured). Failed-login events store the typed username, which could be a mistyped password — a known limitation.

## Database, backup, recovery
Compromise of the DB exposes metadata and permits audit tampering. Use a least-privilege DB role (no DELETE/UPDATE on `audit_auditevent` is possible via a separate role), TLS to the DB, and encrypted daily backups of **both** the DB and `PRIVATE_STORAGE_ROOT`, 30-day retention, restore tested quarterly into a scratch environment. *None of this has been performed or verified yet.*

## Secrets & deployment
Secrets only from environment variables; app refuses to start without `DJANGO_SECRET_KEY` when `DEBUG` is off. Production enables HTTPS redirect, HSTS, secure cookies. `SECURE_PROXY_SSL_HEADER` is safe only behind a proxy you control. Run `check --deploy` before release.

## Residual risks
Throttling can lock out a targeted username (DoS), no malware scanning, Bootstrap loaded from CDN without SRI, DB-level audit tampering, files unencrypted at rest (rely on disk encryption).
