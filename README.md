# TrustVault — Secure Document Sharing with Real Audit Trail

Django app where Owners upload documents and share them per-document (Read / Edit) with Viewers; every sensitive action is written to an append-only audit trail that only Admins can see.

## Roles
| Role | Can |
|---|---|
| Admin | Manage users/roles, view audit dashboard and document *metadata*. **Cannot read document contents** (least privilege). |
| Owner | Upload; read/edit/delete own documents; grant/revoke Read or Edit; see activity on own documents. |
| Viewer | Open only documents explicitly shared with them (Read, or Read+Edit for metadata). |

## Stack
Python, Django 5.1, SQLite (dev) / PostgreSQL (prod), Django templates + Bootstrap (CDN), Django TestCase.

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then export the variables (or use your shell/host's env settings)
export DJANGO_DEBUG=1       # local development only
python manage.py makemigrations accounts documents audit
python manage.py migrate
python manage.py createsuperuser     # becomes an Admin
python manage.py runserver
```
Log in as the Admin and use **Users → Add user** to create accounts, change roles, or deactivate users.
For a quick demo (development only): `python manage.py seed_demo` creates `demo_admin`, `demo_alice`, `demo_bob`.

## Tests
```bash
python manage.py check
python manage.py test -v 2
```
## Deployment (summary; not yet performed)
Set `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DB_*` (PostgreSQL) and `PRIVATE_STORAGE_ROOT` (a **persistent** disk/volume outside the code tree). Serve behind HTTPS (e.g. Gunicorn + Nginx/Caddy with `client_max_body_size 6m`), run `migrate`, `collectstatic`, then `python manage.py check --deploy`. Platforms with ephemeral disks (default Heroku/Render free tiers) will lose uploads — use a persistent volume.

## Demo workflow
1. Admin creates/promotes `alice` (Owner) and `bob` (Viewer). 2. Alice uploads a PDF. 3. Bob cannot see it; try its URL → 404. 4. Alice grants Bob Read. 5. Bob downloads. 6. Alice revokes; Bob's next request → 404. 7. Admin opens the Audit dashboard: upload, grant, download, revoke, denied attempt.

## Known limitations
- Revocation stops future access; **copies already downloaded cannot be erased**.
- Audit log is application-level append-only, not tamper-proof against a database administrator (see THREATS.md).
- Login throttling is per username/IP and can be used to temporarily lock a victim out; no virus scanning; no inline preview (downloads only).
- Allowed types: PDF, PNG, JPG, TXT, max 5 MB.

See also: `DEPLOYMENT.md`, `DEMO_CHECKLIST.md`, `REQUIREMENTS_CHECKLIST.md`, `THREATS.md`.

## Demo files (in `demo/`)
- `interactive_demo.html` – open in a browser: simulates the authorization/audit rules with a guided walkthrough (not the Django app).
- `ui_preview.html` – static mockup of the main screens.
