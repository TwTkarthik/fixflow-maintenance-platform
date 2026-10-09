# FixFlow Database Design

## Purpose and scope

This document describes the Phase 3 PostgreSQL schema foundation. It covers five SQLAlchemy 2.x ORM models and the initial Alembic migration. Authentication behavior, equipment APIs, work-order APIs, and maintenance workflows are intentionally not implemented yet.

The database is designed for the initial single-organization MVP. Integer auto-incrementing primary keys were selected for readability and straightforward relational joins. All stored timestamps use timezone-aware PostgreSQL timestamps and are generated in UTC by the database/application environment.

## Configuration

The backend reads `DATABASE_URL` from the environment. The expected driver is psycopg 3:

```text
postgresql+psycopg://USER:PASSWORD@HOST:5432/fixflow_dev
```

Copy `backend/.env.example` to `backend/.env`, replace the placeholder with a locally configured credential, and never commit `backend/.env`. The current repository does not contain a credential. PostgreSQL 18 is installed, the local service is listening on port 5432, and the Phase 3 schema has been migrated and verified locally.

The API health endpoint remains independent of this configuration. Database sessions are created only by future database-backed routes or migration commands.

## ORM and session layer

- `app.db.base.Base` is the shared SQLAlchemy `DeclarativeBase`.
- `app.db.base.Base.metadata` contains all five tables after importing `app.models`.
- `app.db.session.get_engine()` creates a PostgreSQL engine from `DATABASE_URL` with `pool_pre_ping=True`.
- `app.db.session.get_session_factory()` creates non-autoflush sessions.
- `app.db.session.get_db()` yields a session and closes it in a `finally` block for future FastAPI dependencies.
- The engine is created lazily, so importing the health API does not require a database connection.

## Tables and important columns

### `users`

Stores future administrator, manager, and technician accounts.

- `id`: integer primary key.
- `full_name`, `email`: required identity fields; email is unique.
- `password_hash`: required password hash only; plaintext passwords are not stored.
- `role`: constrained to `administrator`, `manager`, or `technician`.
- `is_active`: boolean with a server default of `true`.
- `created_at`, `updated_at`: timezone-aware audit timestamps.

Indexes support unique email lookup and role/active filtering. Blank names and emails are rejected by database check constraints.

### `assets`

Stores equipment records and preserves historical references after deactivation.

- `id`: integer primary key.
- `asset_code`: required unique business identifier.
- `name`, `category`, `location`: required descriptive fields.
- `serial_number`, `manufacturer`, `model`: optional equipment-identification fields.
- `description`: optional text.
- `status`: `active` or `deactivated`; deactivation is preferred over deletion.
- `created_by_id`: required foreign key to `users.id`.
- `created_at`, `updated_at`: timezone-aware audit timestamps.

Indexes support status/category, location, and unique asset-code lookup. Historical foreign keys use restrictive deletion behavior.

### `work_orders`

Stores repair or maintenance requests.

- `id`: integer primary key.
- `asset_id`: required foreign key to `assets.id`.
- `title`, `description`: required request details.
- `priority`: `low`, `medium`, `high`, or `critical`.
- `status`: `open`, `assigned`, `in_progress`, `on_hold`, `completed`, or `cancelled`.
- `created_by_id`: required foreign key to `users.id`.
- `assigned_to_id`: nullable technician foreign key to `users.id`; unassigned work is supported.
- `due_at`: optional timezone-aware target timestamp.
- `created_at`, `updated_at`, `completed_at`: lifecycle timestamps.

Indexes support status/priority, assignee/status, and asset/status filtering. Status-transition logic belongs to the future work-order API phase.

### `work_order_updates`

Stores append-only work-order activity and status history.

- `id`: integer primary key.
- `work_order_id`: required foreign key to `work_orders.id`.
- `author_id`: required foreign key to `users.id`.
- `update_type`: `status_change`, `note`, or `assignment`.
- `from_status`, `to_status`: nullable constrained lifecycle values.
- `note`: optional repair or transition comment.
- `created_at`: immutable timezone-aware event timestamp.

The `(work_order_id, created_at)` index supports chronological history retrieval. No activity-writing API exists yet.

### `maintenance_records`

Stores completed service history.

- `id`: integer primary key.
- `asset_id`: required foreign key to `assets.id`.
- `work_order_id`: required unique foreign key to `work_orders.id`.
- `performed_by_id`: required foreign key to `users.id`.
- `outcome`, `work_performed`: required completion documentation.
- `completed_at`: required timezone-aware service timestamp.
- `created_at`: record creation timestamp.

The unique `work_order_id` constraint represents the Phase 3 decision that one completed work order has at most one maintenance record. Completion logic will be implemented and validated in a later phase.

## Relationships and deletion behavior

- One user can create many assets and work orders, author many updates, and perform many maintenance records.
- One asset can have many work orders and maintenance records.
- One work order belongs to one asset, one creator, optionally one assigned technician, many updates, and at most one maintenance record.
- Historical parent records use `RESTRICT` foreign keys so accidental deletion cannot destroy maintenance history.
- An assigned technician reference uses `SET NULL` if that user is ever removed at the database layer; user deactivation is preferred.
- No cascading delete is configured for historical work-order, update, or maintenance relationships.

## Constraints and indexes

- Primary keys are named through the shared metadata convention.
- Foreign keys are explicitly named and use restrictive or nulling delete actions as documented.
- Role, asset status, work-order priority/status, and update types use non-native SQLAlchemy enums with database `CHECK` constraints, keeping the initial migration readable and PostgreSQL-compatible.
- Required strings have non-blank checks where a blank value would be invalid.
- Email, asset code, and maintenance work-order reference are unique.
- Composite indexes support the expected future list and history queries.
- Dashboard totals are not stored in these tables; future reporting queries will calculate them.

## Alembic migration

The initial migration prepared from the shared SQLAlchemy model design is:

```text
backend/alembic/versions/e98ccb2cbf89_initial_database_schema.py
```

It creates `users`, `assets`, `work_orders`, `work_order_updates`, and `maintenance_records` in dependency order, followed by the foreign keys and indexes. Its downgrade removes those objects in reverse dependency order.

The migration was reviewed, rendered with PostgreSQL offline SQL generation, and applied to the local development database. Final live verification reported revision `e98ccb2cbf89` as head, `alembic check` reported no new upgrade operations, and read-only inspection confirmed all five application tables plus the matching `alembic_version` row.

## Migration commands

From `backend`, with the virtual environment active and `DATABASE_URL` configured:

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

For a future schema change, inspect the model change first, then generate one migration:

```powershell
python -m alembic revision --autogenerate -m "describe the schema change"
python -m alembic upgrade head
python -m alembic check
```

Do not drop or recreate the database to resolve migration issues. Review autogenerated operations before applying them.

## Known limitations

- No seed users, sample assets, or sample work orders are created.
- The schema does not yet include authentication tokens, audit policy beyond work-order updates, attachments, inventory, or preventive-maintenance scheduling.
