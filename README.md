# FixFlow

FixFlow is a planned smart maintenance and repair management platform for small and medium-sized organizations. It is intended to replace fragmented spreadsheet, phone, and messaging workflows with a single place to manage equipment, repair requests, technician assignments, progress, maintenance history, and operational reporting.

## Planned features

- Secure login and logout with role-based access control.
- Administrator, Manager, and Technician workflows.
- Equipment registration, listing, editing, searching, filtering, and deactivation.
- Work-order creation, prioritization, assignment, reassignment, and validated status transitions.
- Timestamped status history, repair notes, and completed maintenance records.
- Dashboard metrics calculated from real database records.
- Automated tests, migration-based database changes, and reproducible local setup.

## Planned technology stack

- Frontend: React, Vite, JavaScript, React Router, HTML, and CSS.
- Backend: Python 3.12, FastAPI, Pydantic, and SQLAlchemy 2.x.
- Database: PostgreSQL with Alembic migrations.
- Testing: Pytest and FastAPI TestClient; Vitest and React Testing Library if time permits.
- Delivery: Git-based checkpoints, local-first verification, then optional Docker/AWS work.

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
│   └── DECISIONS.md
├── backend/
└── frontend/
```

## Documentation

- [Project specification](docs/PROJECT_SPEC.md) — scope, requirements, planned data model, workflows, and acceptance criteria.
- [Project status](docs/PROJECT_STATUS.md) — verified current state, commands, tests, blockers, and next action.
- [Development roadmap](docs/DEVELOPMENT_ROADMAP.md) — ordered implementation lifecycle.
- [Decision log](docs/DECISIONS.md) — approved technical choices and provisional decisions.
- [Agent instructions](AGENTS.md) — persistent rules for future development work.

## Current implementation status

Phase 1 establishes project documentation and repository structure only. The application has not been implemented, no live database has been created, and no application functionality should be considered working yet.

## Future setup documentation

Environment setup, dependency installation, PostgreSQL provisioning, migrations, backend/frontend run commands, test commands, and configuration examples will be added during Phase 2. Do not infer working setup commands from this README before that phase is complete.

## Scope note

The initial release is a single-organization MVP. Machine learning, microservices, Kubernetes, advanced analytics, notifications, and deployment automation are outside the current MVP unless explicitly approved later.
