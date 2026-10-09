# FixFlow

FixFlow is a maintenance and repair management platform for small and medium-sized organizations. It is intended to replace fragmented spreadsheet, phone, and messaging workflows with a single place to manage equipment, repair requests, technician assignments, progress, maintenance history, and operational reporting.

## Current status

Phases 1–4 are complete and verified: the repository contains a minimal FastAPI backend, React/Vite frontend skeleton, SQLAlchemy models, an applied Alembic migration, JWT authentication, and backend role dependencies.

Equipment APIs, work-order APIs, maintenance workflows, dashboards, and the frontend login UI have not been implemented yet.

## Planned features

- Secure login and logout with role-based access control.
- Administrator, Manager, and Technician workflows.
- Equipment registration, listing, editing, searching, filtering, and deactivation.
- Work-order creation, prioritization, assignment, reassignment, and validated status transitions.
- Timestamped status history, repair notes, and completed maintenance records.
- Dashboard metrics calculated from real database records.
- Automated tests, migration-based database changes, and reproducible local setup.

## Technology stack

- Frontend: React, Vite, JavaScript, HTML, and CSS.
- Backend: Python 3.12, FastAPI, Pydantic, and Uvicorn.
- Database: PostgreSQL 18 with SQLAlchemy 2.x and Alembic; the Phase 3 schema is migrated to revision `e98ccb2cbf89` locally.
- Testing: Pytest and FastAPI TestClient.
- Delivery: Git-based checkpoints and local-first verification.

## Repository structure

```text
FixFlow/
├── AGENTS.md
├── README.md
├── .gitignore
├── docs/
│   ├── PROJECT_SPEC.md
│   ├── PROJECT_STATUS.md
│   ├── DEVELOPMENT_ROADMAP.md
│   ├── DECISIONS.md
│   └── DATABASE_DESIGN.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── tests/test_health.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── styles.css
    ├── index.html
    ├── package.json
    ├── package-lock.json
    ├── vite.config.js
    └── .env.example
```

## Local development

The backend and frontend run in separate PowerShell windows. PostgreSQL is required for the database-backed API, but the public Phase 2 health endpoint remains independent of it.

### Backend

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

- Health check: `http://127.0.0.1:8000/api/health`
- Interactive API docs: `http://127.0.0.1:8000/docs`

If PowerShell blocks script activation, use the virtual-environment interpreter directly, for example `./.venv/Scripts/python.exe -m pytest -q` from `backend`. In the original Phase 2 workspace, Python's bundled `ensurepip` required a local pip bootstrap before the normal activation commands worked; this was an environment-specific issue, not an application requirement.

### Database configuration and migrations

From `backend`, configure a local PostgreSQL connection without committing credentials:

```powershell
Copy-Item .env.example .env
# Edit .env and set DATABASE_URL to a real local PostgreSQL URL.
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

The expected URL shape is `postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/fixflow_dev`. The local database is currently migrated to revision `e98ccb2cbf89`. See [database design](docs/DATABASE_DESIGN.md) for the schema and safe migration workflow.

### Authentication

Phase 4 provides:

- `POST /api/auth/login` with a JSON email/password body.
- `GET /api/auth/me` with a Bearer access token.
- Argon2id password hashing through `pwdlib`.
- HS256 JWT access tokens with a configurable 30-minute default expiry.
- Backend role dependencies for Administrator, Manager, and Technician routes.

Configure `JWT_SECRET_KEY` in `backend/.env` with a random secret of at least 32 characters. Generate one locally without printing it using Python's `secrets.token_urlsafe(48)`, then store it only in `backend/.env`.

Create the first administrator interactively after the Phase 3 migration is applied with `python -m app.cli.create_admin`.

There is no public registration endpoint. Logout for stateless JWT authentication means discarding the token on the client; server-side revocation is not implemented in this phase.

### Frontend

In a second PowerShell window, from the repository root:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173` or `http://localhost:5173`. The frontend reads `VITE_API_BASE_URL` from `.env`; copy `.env.example` to `.env` only when a different backend URL is needed. Do not place secrets in frontend environment variables.

### Stopping the servers

When running in the foreground, press `Ctrl+C` in each server's PowerShell window. The frontend's Vite process and backend's Uvicorn process can then be restarted with the commands above.

## Documentation

- [Project specification](docs/PROJECT_SPEC.md) — scope, requirements, data model, workflows, and acceptance criteria.
- [Project status](docs/PROJECT_STATUS.md) — verified current state, environment, commands, tests, blockers, and next action.
- [Database design](docs/DATABASE_DESIGN.md) — schema, relationships, constraints, configuration, and migration workflow.
- [Development roadmap](docs/DEVELOPMENT_ROADMAP.md) — ordered implementation lifecycle.
- [Decision log](docs/DECISIONS.md) — approved technical choices and provisional decisions.
- [Agent instructions](AGENTS.md) — persistent rules for future development work.

## Scope note

The initial release is a single-organization MVP. Machine learning, microservices, Kubernetes, advanced analytics, notifications, and deployment automation are outside the current MVP unless explicitly approved later.
