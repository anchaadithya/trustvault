# TrustVault — Secure Document Sharing with Real Audit Trail

TrustVault is a Django-based secure document-sharing portal designed to protect confidential files through role-based access control, owner-approved download requests, private file storage, and audit monitoring.

## Roles

| Role | Permissions |
|---|---|
| ADMIN | Manage users and roles, view the audit dashboard and permitted document metadata. Cannot read or download document contents. |
| OWNER | Upload and manage own documents, review download requests for documents they own, and approve or reject access requests. |
| VIEWER | Access documents according to the application's authorization rules and request download access when required. Cannot upload documents or bypass owner approval. |

## Technology Stack

- Python
- Django 5.1
- SQLite for development
- PostgreSQL for production, when configured
- Django templates, HTML, CSS and JavaScript
- Django TestCase for automated testing

## Project Features

- Authentication and role-based authorization.
- Secure document upload and management.
- Owner-controlled document access.
- Download access requests and owner approval or rejection.
- Time-limited, one-time download approval where implemented.
- Audit dashboard for monitoring sensitive activities.
- Server-side permission checks to prevent unauthorized access.
- Private storage for uploaded files.
- Validation of supported file types and upload sizes.

## Local Setup

Run the following commands from the folder containing `manage.py`.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Configure the environment variables in `.env` according to `.env.example`. Use development settings and a development secret key when running locally.

### Linux or macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

Create the administrator account using the project's supported account-creation procedure. Confirm that the account has the ADMIN role.

## Demo Login Credentials

The following five accounts are designated for project evaluation.

| Account | Username | Role | Password |
|---|---|---|---|
| 1 | `Adithya` | ADMIN | `sai.ancha.54@` |
| 2 | `Alekhya` | OWNER | `sai.ancha.54@alekhya` |
| 3 | `Sai` | OWNER | `sai.ancha.54@sai` |
| 4 | `Deekshi` | VIEWER | `sai.ancha.54@deekshi` |
| 5 | `Teja` | VIEWER | `sai.ancha.54@teja` |

These credentials are intended for demonstration and evaluation. The accounts must be created in the application and assigned the corresponding roles before they can be used to log in.

## Evaluator Testing Workflow

1. Log in as `Adithya` and open the administrator audit dashboard.
2. Log in as `Alekhya` and upload a non-confidential sample document.
3. Log in as `Deekshi` and test whether unauthorized direct downloads are blocked.
4. Submit a download-access request as the viewer.
5. Log in as `Alekhya` and approve or reject the request.
6. Log in again as `Deekshi` and verify the resulting access.
7. Repeat relevant tests using `Sai` as the owner and `Teja` as the viewer.
8. Verify that document uploads, requests, approval decisions, downloads, and denied attempts appear in the audit dashboard when those events are implemented.
9. Confirm that the administrator cannot read or download confidential document contents.

## Testing

Check the Django configuration:

```bash
python manage.py check
```

Run automated tests:

```bash
python manage.py test -v 2
```

Check production settings:

```bash
python manage.py check --deploy
```

Record the actual results of these commands before submitting the project.

## Security Requirements

- Enforce permissions on the server for every protected operation.
- Prevent unauthorized access through guessed or modified document URLs.
- Ensure only the document owner can approve or reject requests for their documents.
- Reject denied or expired download approvals.
- Prevent reuse of a completed one-time approval, where implemented.
- Keep uploaded files outside publicly accessible directories.
- Avoid recording passwords, secret tokens, or document contents in audit events.
- Restrict audit dashboard access to authorized administrators.
- Use HTTPS and secure production settings when deployed.

## Deployment

For a production deployment:

1. Push the project to GitHub.
2. Configure the hosting platform and production environment variables.
3. Set `DJANGO_DEBUG=0`.
4. Configure `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS`.
5. Configure PostgreSQL if required.
6. Configure persistent private storage for uploaded documents.
7. Run database migrations and collect static files.
8. Run `python manage.py check --deploy`.
9. Test login, document permissions, downloads, and audit logging on the live website.

**Storage warning:** Uploaded files can be lost if the hosting platform uses an ephemeral filesystem. Configure persistent storage and verify that files remain available after a restart or redeployment.

Deployment status and the live website URL should be added after the deployed application has been verified.

## Known Limitations

- Revoking access cannot erase copies downloaded previously.
- Application-level append-only audit logs alone cannot prevent a privileged database administrator from altering stored records.
- File validation does not replace malware scanning.
- Authentication throttling depends on the application's implementation.
- Supported file types, maximum upload size, and approval-expiry behavior must match the actual implementation.

## Documentation

- `THREATS.md` — Security threats, mitigations, and residual risks.
- `PROMPTS.md` — AI prompts and development notes.
- `DEPLOYMENT.md` — Deployment instructions, if included.
- `DEMO_CHECKLIST.md` — Demonstration checklist, if included.
- `REQUIREMENTS_CHECKLIST.md` — Project requirements and verification checklist, if included.

## Demo Files

If present in the `demo/` directory:

- `interactive_demo.html` — Guided simulation of authorization and audit rules; not the live Django application.
- `ui_preview.html` — Static preview of the main interface.

## Credential Handling

The demo credentials above are included for evaluator testing as requested. If the repository is public, move passwords out of the public README and share them privately with the evaluator. Use dedicated demo accounts and non-sensitive sample documents.
