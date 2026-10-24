# TrustVault Threat Model

## 1. Overview

TrustVault is a Django-based secure document-sharing application designed to protect confidential files through role-based authorization, private file storage, owner-controlled download approvals, and audit logging.

This threat model identifies the application's important assets, trust boundaries, attack scenarios, security controls, verification evidence, and residual risks.

Security claims must be verified against the submitted source code and actual test results. A listed test name is not proof that the test passes.

## 2. Assets

The assets requiring protection include:

- Confidential files stored under `PRIVATE_STORAGE_ROOT`.
- Database records containing users, roles, documents, permissions, download requests, and audit events.
- Authentication credentials and session cookies.
- `DJANGO_SECRET_KEY` and database credentials.
- Document metadata, including owner, original filename, category, and upload time.
- Download approvals, expiry timestamps, and download-use records.
- Audit records used to investigate security-related activity.

## 3. Trust Boundaries

The application's principal trust boundaries are:

`Browser → HTTPS → Django application → Database / Private file storage`

The browser and all client-supplied information must be treated as untrusted, including:

- Document IDs and URL parameters.
- Filenames, extensions, and MIME types.
- Form fields and submitted role values.
- Access-request IDs and approval decisions.
- Cookies and session-related requests.

Authorization decisions must be made by the server using the authenticated identity and current database state.

## 4. Roles and Authorization Rules

### ADMIN

- May manage users and roles through authorized management functions.
- May view the audit dashboard and permitted document metadata.
- Must not automatically receive permission to read or download confidential document contents.
- Must not approve another owner's document request merely because of the ADMIN role.

### OWNER

- May upload and manage documents they own, according to the application's implemented authorization rules.
- May review download requests for documents they own.
- Is the authorized approver for access requests concerning their own documents.
- Must not bypass access controls for documents owned by other users.

### VIEWER

- Must not upload documents.
- Must not download protected documents without valid authorization.
- Must submit a download-access request when direct download is not permitted.
- Must not approve their own request or grant themselves permissions.

### Authorization enforcement

The existing design identifies `documents/permissions.py::authorize()` as the central document authorization check. Every protected document view must use this function or an equivalent explicit authorization check.

Current permission state should be checked on each protected request rather than relying on stale cached permission data.

Unauthorized document access may return `404` to avoid disclosing whether a document exists. Authenticated users who lack a required permission may receive `403`, depending on the endpoint's intended disclosure policy.

## 5. Threat Analysis

| Threat | Potential impact | Mitigation | Verification evidence |
|---|---|---|---|
| IDOR / document ID manipulation | Unauthorized access to another user's document | Verify ownership and current permissions on every protected endpoint | `test_regression_user_a_cannot_access_user_b_document_even_knowing_id`; `test_changing_document_id_…` |
| Viewer self-escalation | Viewer gains edit rights or ownership | Enforce role and ownership checks server-side; restrict role changes to authorized administrators | `test_viewer_cannot_grant_self_permission`; account role tests |
| Stale access after revocation | Formerly authorized user continues accessing a document | Read current permission state on every request and re-check before downloading | `test_revoked_access_fails_on_next_download` |
| Public file URL or guessable path | Direct download without authorization | Store files outside publicly served directories; use generated storage names; avoid public storage URLs | `test_storage_has_no_public_url`; upload naming tests |
| Path traversal in filename | Access to or modification of files outside the storage directory | Never use supplied filenames directly as storage paths; sanitize display names | `test_path_traversal_filename_is_neutralised` |
| Malicious file upload | Storage of unsafe content or exploitation of downstream file handlers | Validate allowed types, inspect file signatures where implemented, enforce size limits, serve as an attachment, and set `nosniff` | `UploadTests` |
| Mass assignment | Unauthorized changes to owner, size, or protected fields | Use forms with explicit allowed fields and validate ownership server-side | `test_edit_cannot_mass_assign_owner` |
| CSRF | Unauthorized actions performed through a victim's authenticated session | Use Django CSRF middleware and tokens for applicable state-changing requests | Framework configuration; dedicated test coverage must be verified |
| XSS | Script execution in another user's browser | Escape untrusted template values and avoid unsafe HTML rendering | Django template auto-escaping; dedicated test coverage must be verified |
| SQL injection | Unauthorized database queries or data exposure | Use Django ORM parameterization and avoid unsafe raw SQL | ORM usage review; dedicated test coverage must be verified |
| Audit tampering by application users | Hiding or falsifying security events | Restrict audit modification and deletion through application logic; avoid cascading deletion of historical events | `AuditIntegrityTests` |
| Brute-force login | Account takeover or denial of service | Apply login throttling and record relevant authentication failures | `LoginThrottleTests` |
| Privilege probing | Unauthorized access to administrator functions | Enforce role checks on protected management routes and record denied attempts | `test_non_admin_cannot_create_or_toggle_users_and_is_audited` |
| Deactivated account retains a session | Continued access after account deactivation | Re-check account status and invalidate access for inactive accounts | `test_deactivated_user_loses_existing_session_immediately` |
| Unauthorized approval | Viewer or unrelated user obtains protected file access | Verify the document owner and permitted reviewer before accepting a decision | Add or verify owner-only approval tests |
| Approval reuse | Multiple downloads from a single-use approval | Track successful use and enforce one-time consumption on the server | Add or verify one-time approval tests |
| Expired approval reuse | Download after approval expiry | Compare the expiry timestamp with server time at the download endpoint | Add or verify expiry tests |
| Concurrent downloads | One-time approval consumed more than once | Use an atomic transaction or appropriate database locking | Add or verify concurrent-use tests |
| Secret exposure | Account compromise or unauthorized configuration changes | Keep secrets in environment variables and out of source control | Review environment configuration and repository contents |
| Database compromise | Disclosure of metadata and possible audit alteration | Use least-privilege database access, secure connections, backups, and restricted administration | Deployment configuration and operational verification |
| Storage loss after redeployment | Permanent loss of uploaded documents | Configure persistent storage and test recovery procedures | Deployment and recovery tests |

**Verification note:** Existing test names must be checked against the actual test suite. New approval-related tests must not be described as passing until they have been implemented and executed successfully.

## 6. Secure Download Flow

The intended protected download flow is:

1. Authenticate the requester.
2. Resolve the requested document.
3. Check the current user's role, ownership, and applicable permissions.
4. If access requires approval, locate a valid approval for the specific requester and document.
5. Verify that the approval has not expired or already been used.
6. Record the appropriate audit event.
7. Open the file only after authorization succeeds.
8. Stream the file as an attachment using appropriate response headers.
9. Atomically mark the approval as used after a successful download, where one-time approval is implemented.
10. Record the download result in the audit trail.

Protected responses should use appropriate cache-control headers, such as `Cache-Control: private, no-store`, to reduce unintended caching.

No public or signed download URL should bypass the authorization check.

## 7. Download Requests, Approval, and Revocation

### Fresh request for every download

- Whenever a user wants to download a document uploaded by another owner, the user must submit a **new download-access request for each download**.
- A previous approval must not authorize a later download, even if it was issued for the same document and user.
- The document owner must review and approve each new request before the download is permitted.
- Only the owner of the requested document may approve or reject that request.
- The administrator role alone does not grant approval authority for another owner's document.

### One-time approval and one-hour expiry

- Each approved download request is valid for **one successful download only**.
- Each approval expires **one hour after approval**, unless it has already been used.
- After a successful download, the approval must be marked as used and must not authorize another download.
- To download the same document again, the user must submit a new request and receive a new approval.
- Rejected, expired, or already-used approvals must never authorize a download.
- The server must determine the requester, document, approver, expiry, and usage state from trusted application data, not from client-submitted fields.
- Concurrent requests must not allow the same one-time approval to authorize multiple downloads.

### Revocation limitations

Revocation should block subsequent requests that fail the current authorization check.

Revocation cannot erase a file already downloaded by an authorized user. A download already in progress when revocation occurs may finish, depending on the timing and implementation.

Concurrency handling must be tested with the production database configuration. SQLite behavior may differ from PostgreSQL locking behavior.

## 8. Audit Trail: What It Proves and Does Not Prove

The audit trail is intended to record security-relevant events, including document operations, access requests, approval decisions, permission changes, denied attempts, and user-management actions where implemented.

An audit event may help establish that the application recorded an action under an authenticated account at a server-recorded time.

It does not independently prove:

- That a human actually read the downloaded file.
- That the account holder, rather than another person using their credentials, performed the action.
- That the database was not modified by someone with direct privileged access.
- That every event was recorded successfully if logging fails or the application is compromised.

Application-level append-only behavior is not the same as tamper-proof storage. Stronger protection may require external write-once logging, a SIEM, protected object storage, or a carefully implemented hash chain.

If IP addresses are collected from `REMOTE_ADDR`, they may represent a reverse proxy rather than the original client unless trusted proxy configuration is correct.

Failed-login logging should not store passwords, authentication tokens, or other secrets. Recording a typed username is a privacy consideration.

## 9. Database, Backup, and Recovery

A database compromise may expose document metadata, permissions, user records, and audit history. A sufficiently privileged attacker may also alter application-level audit events.

Recommended production controls:

- Use a least-privilege database account.
- Restrict database network access and use TLS where supported.
- Restrict direct database administration to trusted operators.
- Back up both the database and private document storage.
- Encrypt backups and restrict access to backup credentials.
- Define a retention period appropriate to project requirements.
- Periodically test restoring the database and uploaded files.
- Reconcile document records and file storage during recovery.

**Verification status:** Encryption, daily backups, 30-day retention, quarterly restore testing, and database-level audit restrictions are recommendations unless they have actually been configured and tested.

## 10. Secrets and Deployment Security

- Load production secrets from environment variables or an appropriate secrets manager.
- Never commit `.env` files containing real credentials.
- Set `DJANGO_DEBUG=0` in production.
- Configure a strong, unique `DJANGO_SECRET_KEY`.
- Restrict `DJANGO_ALLOWED_HOSTS` to the intended hostnames.
- Use HTTPS and configure secure session and CSRF cookies.
- Enable HTTPS redirection and HSTS only with an appropriate verified configuration.
- Configure `SECURE_PROXY_SSL_HEADER` only behind a trusted, correctly configured proxy.
- Keep dependencies updated.
- Run `python manage.py check --deploy` before release.
- Verify that private document storage persists and is not directly exposed by the web server.

A successful Django deployment check does not prove that every application-specific security requirement is satisfied.

## 11. File Upload Security

The existing project notes specify an allow-list of file extensions, file-signature checks, size limits, attachment delivery, and `nosniff` protection. Verify these controls against the actual upload and download implementation.

Additional considerations:

- Do not trust the browser-supplied MIME type alone.
- Generate server-controlled storage names.
- Sanitize filenames used for display.
- Reject unsupported or oversized uploads.
- Store files outside publicly accessible static directories.
- Consider malware scanning for real confidential documents.
- Do not render untrusted uploaded content inline unless it is safely handled.

Malware scanning is not claimed as implemented unless independently verified.

## 12. Residual Risks

The following risks may remain even after application-level controls:

- **Previously downloaded copies:** A user can retain a file after access is revoked.
- **Audit tampering:** A privileged database operator may alter application-level audit records.
- **Denial of service:** Login throttling can temporarily block a targeted username or IP address.
- **Malware:** File validation cannot guarantee that every accepted file is safe.
- **CDN integrity:** Third-party frontend resources may create supply-chain risks if loaded without suitable integrity protections.
- **Storage encryption:** Files may not be encrypted individually at rest unless explicitly configured; underlying disk or volume encryption is a separate control.
- **Concurrent revocation and downloads:** A request that has already passed authorization may still be in progress when permissions change.
- **Credential compromise:** An attacker with valid credentials may perform actions available to that account.
- **Audit availability:** If logging fails or the database becomes unavailable, some events may not be recorded.

## 13. Security Verification Checklist

Before submission, verify the following security requirements and record the actual test results:

- Anonymous users cannot access protected document contents.
- Viewers cannot upload documents.
- Unauthorized users cannot download documents by changing IDs or URLs.
- Owners cannot manage other owners' documents without authorization.
- Only the correct document owner can approve or reject access requests.
- A new request and approval are required for every download of another owner's document.
- A previous approval cannot be reused for another download.
- Approvals expire after one hour, if this behavior is implemented.
- A successful download consumes its one-time approval.
- Rejected or expired approvals cannot authorize downloads.
- Revoked permissions prevent subsequent unauthorized requests.
- Administrators cannot read or download confidential document contents.
- Sensitive operations and denied attempts appear in the audit trail.
- Invalid file types and oversized uploads are rejected.
- Real secrets are not committed to the repository.
- Production configuration and persistent storage are verified.
- Automated tests pass in the intended environment.

## 14. Final Security Statement

TrustVault uses a defense-in-depth approach based on role-based authorization, private document storage, controlled download workflows, input validation, and audit monitoring.

Every download of another owner's document is intended to require a fresh owner-approved request. Each approval is intended to permit one download only and expire after one hour.

These guarantees depend on the actual implementation and test results. Controls that have not been implemented, configured, or verified must be identified as outstanding work rather than presented as completed security guarantees.
