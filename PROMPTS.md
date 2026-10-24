# AI Prompt Log — TrustVault

This document records the AI-assisted development of TrustVault, the purpose of the prompts, the implementation decisions, and the verification status.

The AI-generated output, actual repository implementation, and executed test results are different things. A feature must not be described as fully implemented or verified unless the source code and test results support that claim.

## 1. Master Prompt — Secure Document-Sharing MVP (Phased Development)

**Purpose**

Build TrustVault in phases using Django, including project setup, authentication, role-based access control, document management, security controls, audit logging, automated tests, and documentation.

**Output used**

- Initial Django project structure and configuration.
- Custom user model with role support.
- Login and logout functionality.
- Role-management functionality.
- Initial automated tests.
- Initial project documentation and setup guidance.

**Verification status**

The original AI development record states that syntax compilation was performed, but the AI environment did not have Django or network access. The Django tests were not executed by the AI.

**Student verification required**

Record the actual result of running `python manage.py test` in the development environment. Include failures and subsequent fixes rather than reporting an unverified success.

## 2. Master Prompt — Complete the Project by Inspecting the Existing Repository

**Purpose**

Inspect the existing TrustVault repository and implement the document-management workflow, authorization rules, secure downloads, audit trail, administrator dashboard, automated tests, and supporting documentation.

**Output used**

- `documents/` and `audit/` Django applications.
- Document upload, listing, detail, editing, and deletion workflows.
- Role-based document authorization.
- File validation and private-storage configuration.
- Download-access request and review workflows.
- Audit-event recording and dashboard functionality.
- Application templates and error pages.
- Automated tests and documentation updates.

**Security decisions recorded during development**

- ADMIN is responsible for authorized system management and audit monitoring, not automatic access to confidential document contents.
- OWNER manages their own documents and reviews requests for those documents.
- VIEWER cannot upload documents or directly download protected documents without authorization.
- Access to another owner's document must follow the applicable owner-approved request workflow.
- Unauthorized document access may return `404`, while `403` may be used for authenticated users who lack a required permission, depending on the endpoint.
- Audit records are intended to preserve security-relevant activity.
- The project uses a custom role-checked management interface rather than relying on the standard Django admin site.

**Verification status**

The original record reports syntax compilation only. Django checks, migrations, automated tests, and deployment checks were not executed in the AI environment at that stage.

## 3. Prompt — Compare the Repository Against Every Requirement and Implement Missing Features

**Purpose**

Compare the existing repository with the project requirements, identify missing functionality, and implement or document gaps without unnecessarily replacing working features.

**Output recorded during development**

The development record identifies the following additions or improvements:

- Administrator user creation and deactivation.
- Login throttling.
- Audit logging for role-check denials.
- Document file-content replacement.
- Custom `404` and `500` error pages.
- Logging and CSRF-origin settings.
- Demo-data seeding command.
- Deployment process configuration.
- Backup script.
- `DEPLOYMENT.md`.
- `DEMO_CHECKLIST.md`.
- `REQUIREMENTS_CHECKLIST.md`.
- Additional automated tests.

**Verification status**

The original record reports syntax compilation only. The listed additions must be checked against the current repository before they are claimed as implemented. Their tests and operational behavior must also be verified.

## 4. Prompt — Implement Secure Document Management

**Purpose**

Create a secure document lifecycle for uploading, viewing permitted metadata, editing, replacing, downloading, and deleting documents according to ownership and role restrictions.

**Requirements**

- Validate uploads against the application's supported file types and size limits.
- Generate safe server-controlled storage names.
- Keep private documents outside publicly accessible file directories.
- Check ownership and authorization on every protected document operation.
- Prevent users from changing document IDs or submitted fields to bypass authorization.
- Prevent unauthorized edits, replacements, and deletions.
- Serve protected downloads only after server-side authorization.
- Record relevant document operations in the audit trail.

**Verification status**

Inspect the current document views, forms, storage configuration, validators, URL routes, and tests. Record the actual test results before marking the requirements as complete.

## 5. Prompt — Enforce Role-Based Access Control

**Purpose**

Ensure that ADMIN, OWNER, and VIEWER accounts receive only their intended capabilities.

**Expected behavior**

### ADMIN

- Manage users and roles through authorized management views.
- Access audit monitoring and permitted management information.
- Not automatically read or download confidential document contents.
- Not automatically approve access requests belonging to document owners.

### OWNER

- Upload and manage their own documents according to implemented permissions.
- Review requests for documents they own.
- Approve or reject access requests for their own documents.
- Not bypass authorization for documents uploaded by other owners.

### VIEWER

- Not upload documents.
- Not directly download protected documents without authorization.
- Submit an access request when approval is required.
- Not grant themselves access or approve their own requests.

**Verification status**

Verify the role decorators or equivalent authorization logic, URL configuration, templates, and direct HTTP access tests. Hiding a button in a template is not sufficient authorization.

## 6. Prompt — Implement Fresh Download Requests and One-Time Approvals

**Purpose**

Ensure that every download of another owner's document follows an owner-approved request process.

**Expected behavior**

- A requester submits a new download-access request for each new download.
- The document owner receives or can see the request.
- Only that document's owner can approve or reject the request.
- Each approval authorizes one successful download only.
- An unused approval expires one hour after approval.
- A successful download consumes the approval.
- Rejected, expired, and used approvals cannot authorize another download.
- A subsequent download requires a new request and a new approval.
- The requester, document, approver, expiry, and usage state are validated on the server.
- Concurrent requests cannot reuse the same approval for multiple downloads.
- Requests, decisions, successful downloads, and denied attempts are recorded in the audit trail.

**Verification status**

Confirm that the current `DownloadAccessRequest` model and download views enforce all of these rules. Verify the existence and behavior of fields such as `approval_expires_at` and `downloaded_at` before claiming they are present.

Run tests covering owner-only approval, expiry, one-time use, repeat requests, rejection, unauthorized users, and concurrent access where supported.

## 7. Prompt — Build the Audit Trail and Administrator Monitoring Dashboard

**Purpose**

Provide a record of security-relevant events and a management interface for reviewing activity.

**Expected behavior**

- Record relevant login and logout activity where implemented.
- Record uploads, downloads, edits, replacements, and deletions.
- Record download-access requests and approval decisions.
- Record permission grants and revocations where implemented.
- Record denied access attempts and role-check failures.
- Record user-management and role changes.
- Display useful event details, timestamps, actors, outcomes, and document references where available.
- Provide appropriate filters and summary statistics if implemented.
- Restrict dashboard access to authorized administrators.
- Prevent ordinary application users from modifying or deleting audit records.

**Limitations**

Application-level restrictions do not automatically make audit data tamper-proof against a person with direct database access. External immutable logging may be needed for stronger guarantees.

**Verification status**

Inspect audit-recording call sites, the audit model, dashboard views, filters, and integrity tests. Verify that failures and denied actions are actually recorded, rather than assuming that the presence of an audit dashboard proves complete coverage.

## 8. Prompt — Improve Authentication and Application Security

**Purpose**

Reduce the risk of unauthorized access and unsafe requests.

**Expected controls**

- Django authentication and session management.
- Server-side role and ownership checks.
- CSRF protection for applicable state-changing requests.
- Safe template output and avoidance of unsafe HTML rendering.
- Validation of uploaded files and submitted form fields.
- Appropriate handling of invalid IDs and inaccessible resources.
- Secure cookie and HTTPS settings for production.
- Login throttling if implemented.
- Appropriate application error handling and logging.
- No exposure of passwords, tokens, or file contents in audit details or error messages.

**Verification status**

Inspect the relevant settings, middleware, views, forms, templates, and tests. Security settings must be evaluated in the actual deployment environment.

## 9. Prompt — Create the Documentation and Evaluation Materials

**Purpose**

Document how to install, configure, test, demonstrate, deploy, and assess TrustVault.

**Documentation files**

- `README.md` — project overview, setup, features, roles, and usage.
- `THREATS.md` — assets, trust boundaries, threats, mitigations, residual risks, and verification status.
- `PROMPTS.md` — AI-assisted development record and verification history.
- `DEPLOYMENT.md` — deployment instructions and production configuration.
- `DEMO_CHECKLIST.md` — steps for demonstrating the application's workflows.
- `REQUIREMENTS_CHECKLIST.md` — mapping of project requirements to implementation and test evidence.

**Verification status**

Check that each documentation file exists and matches the actual repository. Remove claims about features, tests, deployment settings, or backups that have not been verified.

## 10. Prompt — Prepare Demo Accounts and Seed Data

**Purpose**

Make the application easier to demonstrate and evaluate using predictable demo data.

**Expected behavior**

- Create demo users with the intended roles.
- Provide sample documents and access-request scenarios where implemented.
- Avoid duplicate records when the seeding command is run repeatedly.
- Avoid exposing production credentials or real confidential documents.
- Document how demo accounts are created and how their passwords are configured.

**Security considerations**

Demo passwords must be treated as development-only credentials. Do not publish real passwords or reuse demo credentials in production. If the repository is public, use environment-based credentials or clearly documented local-only setup instructions.

**Verification status**

Confirm the actual seeding command name, required arguments, generated accounts, and repeat-run behavior from the source code. Do not assume that a `seed_demo` command works merely because it is mentioned in documentation.

## 11. Prompt — Prepare for Deployment

**Purpose**

Prepare TrustVault for deployment and ensure that its configuration is appropriate for a production environment.

**Expected behavior**

- Configure environment variables for secrets and deployment settings.
- Disable Django debug mode in production.
- Set allowed hostnames correctly.
- Configure HTTPS and secure cookies.
- Use an appropriate production database.
- Ensure uploaded documents are stored persistently and privately.
- Configure static files and application startup.
- Provide appropriate logging and error handling.
- Document database migrations and recovery procedures.
- Avoid committing `.env` files or other secrets.

**Verification status**

Deployment configuration must be checked against the actual hosting provider. A successful local run does not prove that document downloads, persistent storage, migrations, or secure settings work in production.

## 12. Deferred or Rejected Design Choices

The development record identifies these decisions:

- **Signed expiring URLs:** Deferred because a separate URL-based download mechanism could bypass revocation or the intended authorization workflow if not designed carefully.
- **Standard Django admin site:** Not used in the intended design; the project uses custom role-checked management views.
- **In-app user creation:** The initial record lists this as deferred, but later work reportedly added administrator user creation. The current repository determines the actual status.
- **Login rate limiting:** Initially deferred, but later work reportedly added login throttling. Verify the current implementation and tests.
- **Direct access to another owner's documents:** Not allowed without the required authorization.
- **Approval reuse:** Not allowed. A new owner-approved request is required for each subsequent download.

These decisions should be updated if the current implementation differs from the recorded development history.

## 13. Verification and Test Results

The original AI development record states that syntax compilation was performed but that Django tests and other application checks were not executed in the AI environment.

The following results must be recorded from the actual development environment.

| Verification command | Purpose | Actual result |
|---|---|---|
| `python -m compileall .` | Check Python syntax | Record actual output |
| `python manage.py check` | Check Django configuration | Record actual output |
| `python manage.py makemigrations --check --dry-run` | Check for model changes requiring migrations | Record actual output |
| `python manage.py migrate` | Apply database migrations | Record actual output |
| `python manage.py test` | Execute automated tests | Record passed, failed, and skipped tests |
| `python manage.py check --deploy` | Check production-oriented Django settings | Record warnings and fixes |
| Manual role and permission tests | Verify ADMIN, OWNER, and VIEWER restrictions | Record observed results |
| Download approval tests | Verify fresh requests, one-time use, and one-hour expiry | Record observed results |
| Audit verification | Confirm important actions and denied attempts are recorded | Record observed results |
| Deployment smoke tests | Verify login, private storage, uploads, and downloads after deployment | Record observed results |

Do not invent passing results. If a command fails, record the error and the fix applied. Run commands from the directory containing `manage.py`.

## 14. Final Statement

AI assistance was used to help design, implement, review, and document TrustVault. AI-generated code and documentation were treated as development outputs requiring verification.

The actual implementation status is determined by the current repository, configuration, successful execution of relevant tests, and deployment behavior—not by the prompt log alone.

The student is responsible for recording the actual test results, identifying incomplete controls, and ensuring that the final project documentation accurately reflects the submitted application.