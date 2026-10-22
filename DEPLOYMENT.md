# Deployment Guide (NOT YET PERFORMED – no live deployment exists)

Any host that offers (a) Python/Gunicorn, (b) PostgreSQL and (c) a **persistent disk** works (a VPS, Render with a disk, Railway with a volume, Fly.io volume). Hosts with ephemeral disks lose uploaded files.

1. Provision PostgreSQL and a persistent directory, e.g. `/var/lib/trustvault/private` (owner = app user, mode 700).
2. Set environment variables (see `.env.example`): `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` (fresh random), `DJANGO_ALLOWED_HOSTS=your-domain`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain`, `DB_*`, `PRIVATE_STORAGE_ROOT`.
3. `pip install -r requirements.txt`
4. `python manage.py migrate` (take a DB backup first on an existing system).
5. `python manage.py collectstatic --noinput` (harmless; the app serves no static files of its own)
6. `python manage.py createsuperuser` (becomes Admin).
7. Start: `gunicorn trustvault.wsgi` (see `Procfile`) behind a TLS-terminating proxy (Nginx/Caddy or the platform's router). Proxy must set `X-Forwarded-Proto` and limit bodies (`client_max_body_size 6m` in Nginx).
8. Verify: `python manage.py check --deploy` should report no warnings; open the site over HTTPS; log in; upload; confirm `/media/…` or the storage path is **not** reachable.

## Backups and restore
- Run `scripts/backup.sh` daily (cron): encrypted DB dump + encrypted tar of the private file store. Keep 30 days, store off-host.
- Restore into a scratch environment: `gpg -d db-*.sql.gpg | psql NEWDB`; `gpg -d files-*.tar.gpg | tar -C <new private dir> -xf -`; run `manage.py check` and download a known file. Test this at least quarterly.
- Back up the DB **and** the file store from the same time; one without the other is inconsistent.

## Rollback
Redeploy previous release; restore DB backup if a migration must be reverted.
