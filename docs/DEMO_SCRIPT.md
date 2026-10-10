# FixFlow local demonstration script

This runbook is for the October 19, 2026 interview demonstration. It uses the real API and database records; it does not add mock metrics or bypass authorization.

## 1. Prepare a disposable local environment

Choose either the Docker Compose path or the native path. Docker is preferred when its Linux engine is available.

### Compose path

```powershell
Copy-Item .env.example .env
# Edit .env and replace POSTGRES_PASSWORD and JWT_SECRET_KEY locally.
docker compose --env-file .env up --build
```

The migration job must complete before the API starts. Open `http://localhost:5173` only after the backend health check is healthy.

### Native path

Configure `backend/.env` with a local PostgreSQL URL and JWT secret, then run:

```powershell
Set-Location backend
python -m alembic upgrade head
python -m app.cli.create_admin
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the frontend in a second PowerShell window:

```powershell
Set-Location frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

The administrator provisioning command reads the password without printing it. Use a disposable account and a password that is not used elsewhere.

## 2. Add disposable manager and technician records

The MVP intentionally has no public registration or user-management API. For a local demonstration, create additional users from a trusted Python shell after creating the administrator. The following procedure prompts for passwords and stores only Argon2id hashes; it does not put credentials in source control.

From `backend`, run `python` and enter:

```python
from getpass import getpass
from app.core.security import hash_password, normalize_email
from app.db.session import get_session_factory
from app.models import User, UserRole

for role in (UserRole.MANAGER, UserRole.TECHNICIAN):
    full_name = input(f"{role.value.title()} full name: ").strip()
    email = normalize_email(input(f"{role.value.title()} email: "))
    password = getpass(f"{role.value.title()} password: ")
    if len(password) < 12 or password != getpass("Confirm password: "):
        raise SystemExit("Use a matching password of at least 12 characters.")
    session = get_session_factory()()
    try:
        session.add(User(full_name=full_name, email=email, password_hash=hash_password(password), role=role, is_active=True))
        session.commit()
    finally:
        session.close()
```

If a record already exists, stop and use a new disposable email rather than weakening the uniqueness rule. Keep the two accounts and their passwords local only.

## 3. Demonstrate the real workflow

Use the administrator or manager account to:

1. Sign in and confirm the dashboard loads from live database records.
2. Create an active equipment record with a unique code such as `DEMO-PUMP-01`.
3. Create a high-priority work order with a due date for that equipment.
4. Assign it to the technician and show the assignment event in history.

Use the technician account to:

1. Sign in and confirm only assigned work is visible.
2. Move the order to `in_progress`, add a repair note, and complete it with a nonblank completion summary.
3. Open the maintenance record and asset maintenance history.
4. Attempt an equipment write or access to another technician's work order and show the backend rejection.

Return to the administrator or manager account to show the completed order, maintenance report, status/priority distributions, and date filters. Sign out, then confirm the protected shell returns to the login page. For expiry behavior, use a deliberately expired or malformed token only in a disposable local browser session.

## 4. Clean up

Remove disposable application records through the supported UI/API where possible. Never delete historical rows manually. For a disposable Compose database, stop the stack with `docker compose --env-file .env down`; delete the named volume only when the entire local database is intentionally disposable and the deletion has been confirmed separately.

Do not reuse the demonstration accounts or passwords outside the local demonstration. Do not commit `.env`, browser storage, screenshots containing tokens, or database dumps.

## 5. Evidence to record

Record the date, environment path, commit hash, user roles exercised, work-order ID used, checks performed, and any blocked workflow. Distinguish browser-observed behavior from API/test coverage. The release report must not claim Docker runtime or authenticated browser verification unless those flows were actually observed.
