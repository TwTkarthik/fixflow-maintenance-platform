# FixFlow Project Specification

**Status:** Approved project definition with explicitly marked provisional assumptions
**Target demonstration:** October 19, 2026
**Scope:** Single-organization MVP for local interview demonstration

## 1. Project summary

FixFlow is a web-based maintenance and repair management platform for small and medium-sized organizations. It centralizes equipment records, repair requests, technician assignments, repair progress, maintenance history, and operational reporting in one application.

### Problem

Organizations such as offices, educational institutions, hotels, small factories, and facilities-management teams often track faults through spreadsheets, phone calls, or messaging applications. This leads to missed requests, unclear ownership, delayed repairs, incomplete records, and difficulty identifying equipment that fails repeatedly.

### Proposed solution

FixFlow provides authenticated role-based workflows for registering equipment, creating and prioritizing work orders, assigning technicians, tracking status and notes, recording completed maintenance, and viewing dashboard metrics calculated from real database records.

### Target users

- Administrators who manage accounts, roles, equipment, and work orders.
- Managers who manage equipment, create and prioritize requests, assign technicians, and monitor work.
- Technicians who view assigned work, update permitted statuses, record repair notes, and document outcomes.

The first release supports one organization. Complex multi-tenant infrastructure is explicitly out of scope.

## 2. Objectives and measurable acceptance criteria

The MVP should:

1. Let an authorized user authenticate and log out securely.
2. Enforce Administrator, Manager, and Technician permissions in backend endpoints.
3. Let authorized users create, list, edit, search, filter, and deactivate equipment records.
4. Let authorized users create, view, assign, reassign, and progress work orders.
5. Enforce the documented priority values and valid status transitions.
6. Preserve timestamped status history, repair notes, and completed maintenance records.
7. Provide a dashboard whose counts and summaries come from persisted database records.
8. Return useful validation and authorization errors and expose loading/error states in the UI.
9. Have automated coverage for important workflows and permission boundaries.
10. Provide reproducible setup, migration, test, and run instructions for another developer.

The MVP is accepted only when the implemented workflows, tests, documentation, and local demonstration have been verified together. The current repository contains only the Phase 2 skeleton and Phase 3 database foundation; business application implementation has not started.

## 3. Functional requirements

### Authentication and users

- Users can log in with credentials and log out.
- Passwords are stored only as secure password hashes.
- Authenticated requests use a JWT with an explicit expiration policy.
- Administrators can manage user accounts and roles.
- Backend dependencies or equivalent guards enforce authentication and role authorization.

### Equipment management

- Administrators and Managers can register equipment.
- Each equipment record has an identity, name, category, location, optional serial number, optional manufacturer/model, status, and audit timestamps.
- Equipment can be edited and deactivated without deleting its historical work orders.
- Equipment lists support text search and useful filters, including active/deactivated state and category or location where implemented.
- Deactivated equipment cannot receive new work orders unless the final business rule is explicitly approved.

### Work orders

- Administrators and Managers can create work orders for equipment.
- A work order includes a title or problem summary, description, priority, status, equipment reference, creator, optional assignee, and timestamps.
- Supported priorities are `Low`, `Medium`, `High`, and `Critical`.
- Administrators and Managers can assign and reassign technicians.
- Technicians can view work orders assigned to them and perform only their permitted updates.
- Work-order lists support search and filtering by status, priority, assignee, equipment, and overdue/open state as appropriate.

### History, notes, and maintenance

- Status changes create timestamped work-order update/history records.
- Repair notes are timestamped and associated with the work order and author.
- Completed work can create a maintenance record containing the outcome, work performed, completion timestamp, and responsible user/technician.
- Historical records remain available after equipment deactivation.

### Dashboard and reporting

- An authenticated dashboard shows calculated metrics such as open work orders, overdue work orders, priority distribution, status distribution, and equipment needing attention.
- Dashboard data is queried from current persisted records; it is not hard-coded or maintained as an unreliable duplicate counter.

## 4. Non-functional requirements

- **Correctness:** validation, relationships, state transitions, and permission checks must be enforced server-side.
- **Security:** secrets come from environment configuration; passwords are hashed; JWT expiry is explicit; unauthorized access returns appropriate errors; sensitive data is not logged.
- **Maintainability:** use a modular monolith with clear backend modules, typed Pydantic boundaries, SQLAlchemy 2.x models, and migrations.
- **Reliability:** database operations should use transactions and preserve history; errors should be handled consistently.
- **Usability:** forms provide useful validation messages, and pages provide loading, empty, and error states.
- **Performance:** the local MVP should remain responsive for a modest organization-sized dataset; list endpoints should support bounded results and filters.
- **Testability:** core services and API workflows should be testable with Pytest and FastAPI TestClient; important UI behavior should be covered with Vitest and React Testing Library if time permits.
- **Reproducibility:** a new developer should be able to configure, migrate, run, and test the application using repository documentation.
- **Scope discipline:** no machine learning, microservices, Kubernetes, or complex multi-tenancy in the MVP.

## 5. Roles and permissions

| Capability | Administrator | Manager | Technician |
|---|---:|---:|---:|
| Log in and view authorized application areas | Yes | Yes | Yes |
| Manage users and roles | Yes | No | No |
| Register/edit/deactivate equipment | Yes | Yes | No |
| View equipment | Yes | Yes | Yes, as needed for assigned work |
| Create work orders | Yes | Yes | No, unless later approved |
| View all work orders | Yes | Yes | No; assigned work only |
| Assign/reassign technicians | Yes | Yes | No |
| Update assigned work status | Yes | Yes | Yes, within permitted transitions |
| Add repair notes | Yes | Yes | Yes, for permitted work |
| Complete/document assigned work | Yes | Yes | Yes |
| Administer work orders | Yes | Yes | No |
| View dashboard/reporting | Yes | Yes | Limited/role-appropriate view |

The exact technician visibility for equipment and dashboard detail is a provisional product decision to be confirmed during implementation. Every permission must be enforced by the backend regardless of UI behavior.

## 6. Equipment-management workflow

1. An Administrator or Manager creates an equipment record with required identity and location details.
2. The record is active by default and appears in searchable equipment listings.
3. A Manager or Administrator edits details when equipment moves, changes ownership, or is corrected.
4. A work order can reference active equipment.
5. When equipment is retired or should no longer receive new requests, an authorized user deactivates it rather than deleting it.
6. Historical work orders and maintenance records remain queryable for the deactivated equipment.

## 7. Work-order lifecycle

### Initial statuses

The approved initial status vocabulary is:

- `Open`: request has been created and is awaiting triage or assignment.
- `Assigned`: a technician has been assigned.
- `In Progress`: repair work is underway.
- `On Hold`: work is temporarily blocked or waiting for information/parts.
- `Completed`: repair work is finished and an outcome is documented.
- `Cancelled`: request will not be completed.

### Allowed transitions

The initial transition policy is:

| From | Allowed next states |
|---|---|
| Open | Assigned, Cancelled |
| Assigned | In Progress, On Hold, Open, Cancelled |
| In Progress | On Hold, Completed, Assigned, Cancelled |
| On Hold | Assigned, In Progress, Cancelled |
| Completed | None in the MVP |
| Cancelled | None in the MVP |

Assignment and status rules are related but distinct: assignment should normally be present before `Assigned` or `In Progress`, and completion requires an outcome/maintenance record according to the final validation rule. These enforcement details are provisional until the API design phase confirms the exact transaction behavior.

Every accepted status change records the previous state, new state, actor, timestamp, and optional note in `work_order_updates`. Rejected transitions return a useful validation error and do not partially update the record.

## 8. Planned database model

The following is the planned relational model. Phase 3 resolves the initial implementation details in `docs/DATABASE_DESIGN.md`; future schema changes still require migrations and a reviewed decision.

### `users`

| Field | Planned type/constraint | Description |
|---|---|---|
| `id` | integer auto-incrementing primary key | Stable user identity |
| `full_name` | required bounded string | Display name |
| `email` | required, unique, indexed | Login identity |
| `password_hash` | required string | Secure password hash; never a plaintext password |
| `role` | required enum/check | `ADMINISTRATOR`, `MANAGER`, or `TECHNICIAN` |
| `is_active` | required boolean | Account access flag |
| `created_at` | required timestamp | Creation audit time |
| `updated_at` | required timestamp | Last modification time |

### `assets`

| Field | Planned type/constraint | Description |
|---|---|---|
| `id` | primary key | Equipment identity |
| `asset_code` | required, unique business identifier | Human-readable equipment identity |
| `name` | required bounded string | Human-readable equipment name |
| `category` | required bounded string | Equipment category |
| `serial_number` | optional string, indexed where useful | Manufacturer serial number |
| `manufacturer` | optional string | Manufacturer |
| `model` | optional string | Model |
| `location` | required bounded string | Physical location |
| `status` | required enum/check | Active or deactivated/retired state |
| `created_by_id` | foreign key to `users.id` | Creator |
| `created_at` | required timestamp | Creation audit time |
| `updated_at` | required timestamp | Last modification time |

### `work_orders`

| Field | Planned type/constraint | Description |
|---|---|---|
| `id` | primary key | Work-order identity |
| `asset_id` | required foreign key to `assets.id` | Equipment affected |
| `title` | required bounded string | Short problem summary |
| `description` | required text | Detailed request |
| `priority` | required enum/check | Low, Medium, High, or Critical |
| `status` | required enum/check | Lifecycle status above |
| `created_by_id` | required foreign key to `users.id` | Request creator |
| `assigned_to_id` | nullable foreign key to `users.id` | Assigned technician |
| `due_at` | nullable timestamp | Target completion time, if used |
| `created_at` | required timestamp | Creation audit time |
| `updated_at` | required timestamp | Last modification time |
| `completed_at` | nullable timestamp | Completion time |

### `work_order_updates`

| Field | Planned type/constraint | Description |
|---|---|---|
| `id` | primary key | Update identity |
| `work_order_id` | required foreign key to `work_orders.id` | Parent work order |
| `author_id` | required foreign key to `users.id` | Actor who made the update |
| `update_type` | required enum/check | Status change, note, assignment, or other approved update |
| `from_status` | nullable status | Prior status for a status change |
| `to_status` | nullable status | New status for a status change |
| `note` | nullable text | Repair note or transition explanation |
| `created_at` | required timestamp | Immutable event time |

### `maintenance_records`

| Field | Planned type/constraint | Description |
|---|---|---|
| `id` | primary key | Maintenance record identity |
| `work_order_id` | required unique foreign key | One maintenance record per completed work order in the initial schema |
| `asset_id` | required foreign key to `assets.id` | Equipment serviced |
| `performed_by_id` | required foreign key to `users.id` | Technician or responsible user |
| `outcome` | required text | Result of repair |
| `work_performed` | required text | Work completed |
| `completed_at` | required timestamp | Maintenance completion time |
| `created_at` | required timestamp | Record creation time |

### Relationships and integrity rules

- One user can create many assets and work orders, author many updates, and perform many maintenance records.
- One asset can have many work orders and maintenance records.
- One work order belongs to one asset, has one creator, has zero or one current assignee, has many updates, and has at most one maintenance record.
- A completed work order must have a documented outcome and a maintenance record under the final implementation rule.
- Foreign keys must prevent orphaned records.
- Deactivation is preferred to deletion for assets with history.
- Email uniqueness, enum/check constraints, non-null requirements, and useful indexes must be enforced in the database as well as validated by the API where appropriate.

## 9. Planned API modules and responsibilities

The backend will be a modular monolith with versioned HTTP routes, likely under `/api/v1`. Exact paths and response envelopes are provisional until the API implementation phase.

- **Auth module:** login, token issuance/expiry, current-user lookup, logout behavior appropriate to the chosen token storage strategy.
- **Users module:** administrator-only user and role administration.
- **Assets module:** equipment create/list/detail/update/deactivate, search, and filters.
- **Work orders module:** create/list/detail/update, priority/status validation, assignment/reassignment, and permitted technician actions.
- **Work-order updates module:** append-only notes and status/assignment history, exposed through work-order detail/history responses.
- **Maintenance module:** completed-repair records and history queries.
- **Dashboard module:** aggregate metrics and filtered operational summaries.

All modules must validate input with Pydantic, use SQLAlchemy through service/repository boundaries appropriate to the codebase, return consistent errors, and enforce authorization in the backend.

## 10. Frontend pages and user journeys

Planned React/Vite pages:

- Login page.
- Authenticated application shell with navigation and logout.
- Dashboard page.
- Equipment list, equipment form/detail, and deactivation action.
- Work-order list with search/filter controls.
- Work-order create form.
- Work-order detail with assignment, status actions, repair notes, and history.
- Maintenance history view, either standalone or integrated into equipment/work-order detail.
- Administrator user-management page.

Main journeys:

1. User logs in and reaches a role-appropriate dashboard.
2. Manager registers equipment, creates a high-priority repair request, and assigns a technician.
3. Technician opens assigned work, moves it through permitted states, and records notes/outcome.
4. Manager reviews current workload, overdue work, and equipment maintenance history.
5. Administrator manages users and can administer all operational records.

React Router will manage page navigation. The frontend will use the Fetch API or another lightweight client only if justified. UI restrictions complement but do not replace backend authorization.

## 11. Architecture and delivery

### Backend

Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.x, and Alembic. The backend is a modular monolith with configuration loaded from environment variables and a PostgreSQL connection managed through application settings.

### Frontend

React with Vite, JavaScript, HTML, CSS, and React Router. The frontend consumes the backend API and owns presentation, navigation, and user feedback states.

### Database

PostgreSQL is the persistent store. Alembic owns schema evolution. Local development should be possible without cloud infrastructure; Docker is added only after the local application works.

### Deployment

Local-first development and verification come before Docker packaging or optional AWS deployment. AWS architecture, infrastructure-as-code, and production operations are not part of this phase and are not prerequisites for the interview demo.

## 12. Authentication and security requirements

- Use a maintained password-hashing implementation with a deliberate work factor.
- Never store or log plaintext passwords or tokens.
- Use signed JWTs with an explicit, documented expiration duration and a secure secret from environment configuration.
- Validate token claims and reject expired, malformed, or insufficiently privileged tokens.
- Keep authorization checks in backend route/service boundaries.
- Validate request fields, lengths, enum values, foreign-key ownership, and state transitions.
- Use safe database access patterns and avoid string-built SQL.
- Configure CORS narrowly for the local frontend origin and document any development exception.
- Do not commit `.env` files or credentials; provide a safe example configuration later.
- Return useful but non-sensitive error messages.
- Review authentication, authorization, input handling, secret handling, and dependency risks before release.

The exact JWT storage strategy in the browser and refresh/revocation approach are provisional decisions for the authentication phase. The MVP must still have an explicit threat-aware choice before implementation is considered complete.

## 13. Testing expectations

- Backend unit/API tests with Pytest and FastAPI TestClient.
- Coverage for login success/failure, token expiry handling, each role's important permissions, invalid state transitions, equipment lifecycle, work-order assignment, technician updates, maintenance creation, and dashboard calculations.
- Database tests should use an isolated test database or transaction strategy and should not depend on production data.
- Frontend tests with Vitest and React Testing Library are planned if time permits, prioritizing login, route protection, forms, loading/error states, and key work-order interactions.
- Run applicable tests and report actual outcomes before calling a phase complete.

## 14. Technology choices

| Choice | Reason |
|---|---|
| React + Vite | Small, familiar, fast local frontend development and a clear production build |
| JavaScript | Matches the planned project scope and reduces setup overhead for the demonstration |
| FastAPI | Clear Python API development, validation, automatic API documentation, and strong testing ergonomics |
| Pydantic | Explicit request/response validation and readable data contracts |
| SQLAlchemy 2.x | Maintained Python ORM and explicit database access patterns |
| PostgreSQL | Reliable relational constraints, query support, and realistic production-oriented persistence |
| Alembic | Versioned, reviewable schema migrations |
| JWT authentication | Stateless API-friendly authentication with explicit expiry when implemented securely |
| Pytest + TestClient | Practical backend workflow and permission testing |
| Git | Reviewable checkpoints and recovery during incremental development |

The architecture remains a modular monolith. Additional frameworks or services require a documented reason and decision-log entry.

## 15. Approved decisions versus assumptions

### Approved

- Project scope and MVP features listed in this document.
- Single-organization deployment for the initial release.
- Planned stack and modular-monolith architecture.
- Backend-enforced permissions.
- Local-first implementation order.
- Database migrations and automated testing before deployment.
- Phase order in `docs/DEVELOPMENT_ROADMAP.md`.
- Integer primary keys, timezone-aware timestamps, database-enforced value constraints, and one maintenance record per work order for the initial schema.

### Assumptions requiring verification during implementation

- Exact JWT storage, refresh, revocation, and logout strategy.
- Exact API path and response envelope conventions.
- Whether `due_at` is required for all work orders or optional.
- Final technician visibility for equipment, dashboard, and unassigned work.
- Final UI styling system and responsive breakpoints.
- Local PostgreSQL credential provisioning and database lifecycle for development.

Open assumptions must be resolved in the relevant implementation phase and recorded in `docs/DECISIONS.md` when they become project decisions.

## 16. Known limitations

- No business API, authentication, or live database integration exists yet; the Phase 3 ORM models, migration code, and metadata tests are implemented.
- The MVP is not multi-tenant.
- Notifications, file attachments, inventory/parts, preventive-maintenance scheduling, mobile apps, machine learning, advanced analytics, microservices, Kubernetes, and production AWS operations are excluded unless later approved.
- The current specification describes planned behavior; implementation and verification remain outstanding.

## 17. MVP completion criteria

The MVP can be considered complete only when:

1. A clean local setup can run the backend, frontend, and PostgreSQL using documented steps.
2. Migrations create the required schema from an empty database.
3. Authentication, role checks, equipment, work orders, updates, maintenance records, search/filtering, and dashboard behavior are implemented and verified.
4. Important success and failure paths have passing automated tests.
5. No known critical security, data-integrity, or permission blocker remains.
6. The README and setup documentation match the actual commands and configuration.
7. A repeatable local demonstration has been completed before optional Docker/AWS work.

## 18. Optional future improvements

Notifications, email/in-app alerts, attachments, parts inventory, preventive maintenance schedules, recurring work, richer analytics, audit exports, multi-tenant organizations, SSO, mobile support, Docker orchestration, and AWS deployment may be considered after the MVP is stable and the decision log is updated.
