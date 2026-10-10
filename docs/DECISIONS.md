# FixFlow Technical Decision Log

This log records decisions that constrain implementation. “Final” means approved for the current MVP unless new evidence justifies a reviewed change. “Provisional” means the direction is approved but one or more implementation details remain to be resolved.

## D-001 — React and Vite for the frontend

- **Decision:** Use React with Vite, JavaScript, HTML, CSS, and React Router.
- **Reason:** Provides a familiar component model, fast local feedback, straightforward routing, and a small build setup appropriate for the demonstration.
- **Trade-offs:** The project must establish its own conventions for state, API access, validation, and styling; Vite is a build tool rather than a complete application framework.
- **Status:** Final for the MVP.

## D-002 — FastAPI for the backend

- **Decision:** Use Python 3.12 with FastAPI and Pydantic.
- **Reason:** FastAPI offers clear HTTP routing, validation, generated API documentation, and good compatibility with Python testing tools.
- **Trade-offs:** The project must make deliberate choices about application structure, dependency boundaries, migrations, and security behavior.
- **Status:** Final for the MVP.

## D-003 — PostgreSQL for persistence

- **Decision:** Use PostgreSQL as the application database.
- **Reason:** It provides durable relational storage, strong constraints, useful indexes, and realistic SQL behavior for a maintenance platform.
- **Trade-offs:** Local development needs a PostgreSQL provisioning workflow; a file-only database is simpler but would not match the planned production-oriented relational model.
- **Status:** Final for the MVP.

## D-004 — SQLAlchemy 2.x and Alembic

- **Decision:** Use SQLAlchemy 2.x for database access and Alembic for schema migrations.
- **Reason:** Keeps models and queries in the Python application while making schema changes reviewable and reproducible.
- **Trade-offs:** ORM session/lifecycle decisions add complexity, and migrations require discipline; direct ad hoc schema changes are not acceptable.
- **Status:** Final for the MVP.

## D-005 — Modular monolith instead of microservices

- **Decision:** Build one deployable backend organized into clear modules.
- **Reason:** The MVP has modest scope and a single organization; a modular monolith reduces operational and integration overhead while preserving separation of concerns.
- **Trade-offs:** Module boundaries must be maintained as the application grows; independent service scaling is not available initially.
- **Status:** Final for the MVP.

## D-006 — Local-first development

- **Decision:** Complete and verify the application locally before Docker packaging or optional AWS deployment.
- **Reason:** The interview demonstration depends on a reliable local workflow, and local verification reduces deployment complexity while requirements are still evolving.
- **Trade-offs:** Deployment concerns are deferred and may expose additional work later.
- **Status:** Final for the project sequence.

## D-007 — Git-based checkpoints

- **Decision:** Use Git for incremental, reviewable checkpoints; do not configure or publish a remote without authorization.
- **Reason:** Versioned checkpoints provide recovery, traceability, and a clear way to inspect phase boundaries.
- **Trade-offs:** Commits require intentional scope and status hygiene.
- **Status:** Final for the project workflow.

## D-008 — Automated testing before deployment

- **Decision:** Test important backend workflows and permissions, and add frontend tests where time permits, before Docker/AWS deployment.
- **Reason:** Permission and state-transition correctness are central to FixFlow; deployment should not be used to discover basic failures.
- **Trade-offs:** Test setup consumes early implementation time but reduces demonstration and regression risk.
- **Status:** Final for the project workflow.

## D-009 — Single organization for the initial release

- **Decision:** Do not implement multi-tenant organization isolation in the MVP.
- **Reason:** It keeps the schema and authorization model appropriate to the October 19, 2026 demonstration and avoids premature complexity.
- **Trade-offs:** The first release cannot serve multiple isolated organizations safely without a later architecture change.
- **Status:** Final for the MVP.

## D-010 — Explicitly provisional implementation details

- **Decision:** Defer UUID versus integer keys, frontend JWT storage and refresh/revocation mechanisms, API envelopes, some technician visibility rules, due-date policy, and maintenance-record cardinality until their implementation phases.
- **Reason:** These details need concrete API/database context; recording them as assumptions prevents accidental invention while preserving forward progress.
- **Trade-offs:** Later phases must resolve and record these decisions before dependent features are considered complete.
- **Status:** Provisional; resolution is required in Phases 3–6 as applicable.

## D-011 — Phase 3 relational design details

- **Decision:** Use integer auto-incrementing primary keys, PostgreSQL timezone-aware timestamps, non-native SQLAlchemy enums backed by database check constraints, restrictive deletion for historical parents, an asset business code plus optional serial/manufacturer/model fields, and one maintenance record per work order through a unique `maintenance_records.work_order_id`.
- **Reason:** These choices are readable for an MVP learner, preserve history, work cleanly with PostgreSQL, and avoid premature native enum lifecycle complexity while keeping allowed values database-enforced.
- **Trade-offs:** Integer identifiers are less globally unique than UUIDs; check constraints require explicit migration updates when vocabularies change; one maintenance record per work order may need revision if repeat service events are later required.
- **Status:** Final for the initial schema, subject to future reviewed requirements changes.

## D-012 — Phase 4 authentication design

- **Decision:** Use `pwdlib` with its recommended Argon2id configuration for password hashes, PyJWT with HS256 for short-lived access tokens, a required environment-provided `JWT_SECRET_KEY`, a 30-minute default expiry, and a local interactive administrator-provisioning command. Logout is client-side token disposal because server-side JWT revocation is not implemented in this phase.
- **Reason:** These are maintained, explicit mechanisms that keep secrets out of source control, avoid plaintext passwords, support FastAPI Bearer documentation, and provide a safe bootstrap without public administrator registration.
- **Trade-offs:** Stateless tokens cannot be individually revoked before expiry; future refresh/revocation requirements may require a token-version or deny-list design. The first administrator must be provisioned from a trusted local environment.
- **Status:** Final for Phase 4, subject to future reviewed security requirements.

## D-013 — Phase 5 equipment API contract

- **Decision:** Use a paginated `{items, total, skip, limit}` response for `GET /api/assets`, deterministic ascending asset-ID ordering, a default page size of 20 with a maximum of 100, case-insensitive contains search over asset code/name, case-insensitive category/location filters, and idempotent deactivation through a dedicated endpoint. All authenticated roles can read; only administrators and managers can create, update, or deactivate.
- **Reason:** The contract is predictable for the future frontend, keeps list queries bounded, preserves historical deactivated records, and matches the approved role matrix.
- **Trade-offs:** Category and location filters are exact case-insensitive matches rather than free-text contains searches; deactivation has no reactivation endpoint in this phase.
- **Status:** Final for Phase 5, subject to future reviewed product requirements.

## D-014 — Phase 6 work-order workflow contract

- **Decision:** Build work-order APIs on the existing five-table schema. Use the approved six statuses (`open`, `assigned`, `in_progress`, `on_hold`, `completed`, and `cancelled`), keep assignment and status changes in dedicated endpoints, append creation/assignment/status/note events to `work_order_updates`, and create exactly one `maintenance_records` row when an assigned work order completes.
- **Reason:** The existing schema already provides the required constrained values, activity event types, timezone-aware timestamps, and unique maintenance-record-per-work-order guarantee. Reusing it avoids an unnecessary migration while preserving history and transaction boundaries.
- **Trade-offs:** Completion requires an assigned technician and a nonblank summary; `work_performed` defaults to the summary when not supplied. Technicians receive 404 for out-of-scope work orders and maintenance history to avoid revealing another technician's records. There is no post-terminal note or reassignment workflow.
- **Status:** Final for Phase 6, subject to future reviewed product requirements.

## D-015 — Phase 7 dashboard and reporting contract

- **Decision:** Provide one authenticated `GET /api/dashboard` summary and paginated `GET /api/reports/work-orders` and `GET /api/reports/maintenance` endpoints. Calculate all metrics from current PostgreSQL records, use inclusive date filters, and apply technician assignment scope before counts, totals, and rows are produced.
- **Reason:** This gives the MVP a compact operational reporting surface without adding a reporting data warehouse, duplicate counters, or schema changes. Existing indexed relationships support database-level filtering and aggregation.
- **Trade-offs:** Dashboard date ranges filter work orders by `created_at` and maintenance by `completed_at`; technician asset totals cover only assets connected to their assigned work orders, so they do not represent organization-wide totals. The frontend dashboard remains deferred to Phase 8.
- **Status:** Final for Phase 7, subject to future reviewed product requirements.

## D-016 — Phase 8 frontend session and API integration

- **Decision:** Use a small shared `fetch` API client configured by `VITE_API_BASE_URL`, store the short-lived access token in browser `sessionStorage`, discard it for logout, and clear the session on an HTTP 401 response. Do not add refresh tokens or frontend-only authorization rules.
- **Reason:** `sessionStorage` limits token lifetime to the browser tab while matching the backend's stateless client-side logout design. Centralizing requests keeps the existing response envelopes and backend permission boundaries visible to every page.
- **Trade-offs:** Closing a tab requires signing in again, and a bearer token remains exposed to JavaScript in the active tab. The backend remains the security boundary; a later reviewed refresh/revocation design may change the client session model.
- **Status:** Final for Phase 8, subject to future reviewed security requirements.
