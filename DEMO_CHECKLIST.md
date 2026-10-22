# Demo Checklist
Setup: `export DJANGO_DEBUG=1`, `python manage.py migrate`, `python manage.py seed_demo` (note the printed password).
- [ ] Log in as `demo_admin`; open **Users**; show roles; create a user; deactivate and re-activate it.
- [ ] Log in as `demo_alice` (Owner): upload a PDF; show random stored name is not exposed anywhere.
- [ ] Try uploading `.exe` and a renamed fake `.pdf` → rejected.
- [ ] Log in as `demo_bob` (Viewer): documents list is empty; paste Alice's document URL → 404.
- [ ] As Alice: grant Bob **Read** → Bob sees and downloads it.
- [ ] As Alice: change Bob to **Read + Edit** → Bob can rename / replace file; cannot delete or share.
- [ ] As Alice: **Revoke** → in Bob's already-open tab, reload/download → 404 immediately.
- [ ] Show the "Activity on this document" table on Alice's page.
- [ ] As `demo_admin`: audit dashboard → upload, grant, download, revoke, **denied** rows; filter by outcome=DENIED.
- [ ] As Bob open `/audit/` → 403 (and that denial appears in the admin audit log).
- [ ] Enter 5 wrong passwords for a user → locked out message.
- [ ] State limits: downloaded copies can't be erased; audit log is app-level append-only.
