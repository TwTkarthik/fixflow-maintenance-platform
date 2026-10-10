# FixFlow release-readiness checklist

This checklist is the final verification record for the single-organization MVP. A check is only marked complete when the command or workflow has actually been observed in the current environment.

## Before release

- [ ] Confirm `git status --short --branch` is clean and the intended commit is on `master`.
- [ ] Confirm no `.env`, password, token, private key, database dump, or generated build output is tracked.
- [ ] Copy `.env.example` to a local `.env` and replace every secret placeholder. Do not use the example secret values for a shared or production deployment.
- [ ] Confirm PostgreSQL is running and accepting connections on the configured host and port.
- [ ] Apply migrations with `python -m alembic upgrade head`.
- [ ] Confirm `python -m alembic current` reports the expected head and `python -m alembic check` reports no drift.

## Automated checks

Run from the repository root unless noted otherwise:

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\alembic.exe check
Set-Location ..\frontend
npm test
npm run build
npm ls --depth=0
npm audit --audit-level=high
Set-Location ..
docker compose --env-file .env config
```

Record the actual output. A registry outage makes `npm audit` unavailable; it is not a passing audit result. A missing PostgreSQL service blocks the backend suite and Alembic checks; it is not a passing integration result.

`pip check` verifies installed dependency consistency. `pip-audit` is an additional advisory scan, but it is not installed in this workspace; do not report a backend advisory scan until that tool is deliberately installed and run.

## Local runtime checks

With PostgreSQL configured and Docker Desktop's Linux engine running:

```powershell
docker compose --env-file .env up --build
```

Observe all of the following before stopping the stack:

1. PostgreSQL becomes healthy.
2. The one-shot `migrate` service completes successfully.
3. The backend health check becomes healthy and `http://localhost:8000/api/health` returns `{"status":"ok","service":"fixflow-api"}`.
4. The frontend is delivered at `http://localhost:5173` and can load the sign-in shell.
5. The frontend can reach the backend from the browser origin; CORS errors are absent.

Stop with `docker compose --env-file .env down`. Do not use `down -v` unless deleting the disposable local volume is intentional.

## Authenticated acceptance pass

Use disposable local accounts and records from [the demo script](DEMO_SCRIPT.md). Record each role separately:

- Administrator: sign in, restore the session, create/edit/deactivate equipment, create/assign/reassign/progress/complete a work order, inspect history and maintenance, view reports, and sign out.
- Manager: verify the same operational management flows permitted by the API, plus rejection of administrator-only actions if any are added later.
- Technician: verify visibility of assigned work only, permitted status/note/completion flows, technician-scoped dashboard/reports/history, and rejection of equipment writes, assignment, and out-of-scope work orders.
- Expired or invalid token: confirm the UI clears the session and returns to sign-in after a protected request receives HTTP 401.
- Empty/error states: verify an empty list/report and a failed API request render a useful state with a retry path where applicable.

Do not call the authenticated workflow complete based only on unit or API tests. Record whether it was observed in a real browser, exercised through an API client, or left unverified.

## Release decision

The release is ready for the local interview demonstration only when the documented setup, migration, automated checks, runtime checks, and authenticated acceptance pass are either complete or have an explicitly approved limitation. Docker configuration validation alone does not establish container readiness, and a frontend build alone does not establish frontend-to-backend connectivity.

## Current Phase 12 record

As of October 10, 2026, this verification started from the clean Phase 11 commit `15203e7` and passed the frontend tests/build, Python compilation, `pip check`, Compose configuration validation, the public API health check, and `npm audit --audit-level=high` with 0 vulnerabilities. PostgreSQL is not listening in the current environment and Docker Desktop's Linux engine is unavailable. The backend integration suite, live Alembic drift check, Docker build/runtime, and authenticated browser workflows therefore remain pending.
