# AI Prompt Log (truthful record)

## 1. Master prompt — secure document-sharing MVP (phased)
- **Purpose:** Build TrustVault in phases (Django, roles, documents, audit, tests, docs).
- **Output used:** Phase 1 (project setup, custom user with roles, login/logout, role-change view, 16 tests).
- **Verification:** Syntax-compiled only. The AI environment had no Django/network, so tests were **not executed by the AI**. *Student: record your own `manage.py test` result here.*

## 2. Master prompt — complete project, inspect existing repo and finish
- **Purpose:** Implement documents, permissions, secure download, audit trail, admin dashboard, tests, docs.
- **Output used:** `documents/` and `audit/` apps, permission policy, validators, templates, 39 new tests, README/THREATS.
- **Decisions:** Admin cannot read contents; 404 for no-access/403 for insufficient; audit table has no foreign keys; no Django admin site.
- **Verification:** Syntax compile only. **Tests, `check`, migrations and `check --deploy` have NOT been run.** *Student: paste real results and any fixes here.*
- **Rejected/deferred:** signed expiring URLs (would bypass revocation); in-app user creation; login rate-limiting.

## 3. “Compare the repository against every requirement and implement what is missing”
- **Purpose:** Gap analysis of both master prompts against the actual files.
- **Gaps found and implemented:** admin user create/deactivate, login throttling, audit of role-check denials, file-content replacement, 404/500 pages, logging/CSRF-origin settings, `seed_demo`, Procfile, backup script, DEPLOYMENT.md, DEMO_CHECKLIST.md, REQUIREMENTS_CHECKLIST.md, ~13 new tests.
- **Verification:** Syntax compile only. **Nothing has been executed.** *Student: paste real `manage.py test` output and fixes here.*
