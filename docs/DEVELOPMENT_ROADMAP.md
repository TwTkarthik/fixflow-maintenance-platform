# FixFlow Development Roadmap

This roadmap is the intended lifecycle. Work proceeds in order, and the status document records what is actually underway. A later phase must not be treated as complete because its files or plans exist.

## Phase 1 — Project foundation and master documentation

**Objective:** Establish the project definition, constraints, architecture direction, status tracking, and repository foundation.

**Planned tasks:** Inspect the workspace; create `AGENTS.md`, master specification, status, roadmap, decision log, README, and `.gitignore`; create only minimal backend/frontend directories; initialize Git if safe.

**Dependencies:** None beyond a dedicated workspace and Git if available.

**Deliverables:** Foundation documents and clean initial structure.

**Completion criteria:** Required documents exist; approved decisions and open assumptions are distinguishable; status accurately says application functionality is not implemented; no secrets or unrelated files are added; repository state is verified.

## Phase 2 — Environment setup and application skeleton

**Objective:** Create the minimal runnable FastAPI and React/Vite skeleton without implementing business features.

**Planned tasks:** Choose compatible dependency versions; create backend/frontend project configuration; define environment configuration conventions; add health/root endpoints and a minimal frontend shell; document local setup; establish basic lint/test commands where appropriate.

**Dependencies:** Phase 1 complete; local Python 3.12, Node.js/npm, and a documented PostgreSQL provisioning approach.

**Deliverables:** Minimal backend and frontend that start locally, plus setup documentation.

**Completion criteria:** Both processes run using documented commands; health check responds; frontend loads; no feature claims beyond the skeleton; status and tests reflect actual results.

## Phase 3 — Database models and migrations

**Objective:** Implement the relational foundation for users, assets, work orders, updates, and maintenance records.

**Planned tasks:** Resolve key/open schema assumptions; implement SQLAlchemy models, relationships, constraints, indexes, session handling, and Alembic configuration; create initial migration; validate upgrade from an empty database.

**Dependencies:** Phase 2 skeleton and working local PostgreSQL.

**Deliverables:** Models, migration history, database configuration, and model tests.

**Completion criteria:** Empty database upgrades successfully; constraints and relationships match the approved specification; tests isolate database state; no manual-only schema steps are required.

## Phase 4 — Authentication and authorization

**Objective:** Provide secure login, token validation, user identity, and backend-enforced roles.

**Planned tasks:** Implement password hashing, JWT issuance/expiry, login/current-user flows, logout behavior, user administration, authentication dependencies, role guards, and security-focused tests; resolve token storage/revocation decisions.

**Dependencies:** Phases 2 and 3.

**Deliverables:** Auth API, user-management API, role checks, configuration documentation, and tests.

**Completion criteria:** Login failure/success, expiry, inactive users, and each role's access boundaries are tested; secrets are environment-based; sensitive values are not logged.

## Phase 5 — Equipment-management APIs

**Objective:** Implement validated equipment registration and lifecycle management.

**Planned tasks:** Add create/list/detail/update/deactivate endpoints, search/filtering, authorization, active-equipment rules, and API tests.

**Dependencies:** Authenticated database-backed application from Phases 3–4.

**Deliverables:** Equipment API module, schemas/services, migration adjustments if needed, and tests.

**Completion criteria:** Administrator and Manager workflows pass; unauthorized roles are rejected; deactivation preserves references/history; validation and error behavior are documented and tested.

## Phase 6 — Work-order and maintenance APIs

**Objective:** Implement repair requests, assignment, state transitions, updates, notes, and completed maintenance records.

**Planned tasks:** Add work-order CRUD/detail/list filters, priority validation, assignment/reassignment, transition service, append-only history, repair notes, completion validation, maintenance records, and permission tests.

**Dependencies:** Equipment APIs and database/auth foundations.

**Deliverables:** Work-order, update/history, and maintenance API modules with tests.

**Completion criteria:** Valid and invalid transitions behave as specified; technician scope is enforced; assignment and completion rules are atomic; timestamps and history are preserved; important workflows pass automated tests.

## Phase 7 — Dashboard and reporting APIs

**Objective:** Expose useful operational metrics calculated from current records.

**Planned tasks:** Implement authenticated aggregate queries for open/overdue work, priority/status distributions, equipment attention indicators, and role-appropriate visibility; add query and permission tests.

**Dependencies:** Stable work-order, equipment, and maintenance data APIs.

**Deliverables:** Dashboard/reporting endpoints and verified aggregate tests.

**Completion criteria:** Metrics match fixture data, do not rely on hard-coded counters, honor filters/permissions, and remain acceptable for a modest local dataset.

## Phase 8 — Frontend implementation

**Objective:** Build the React pages and user interactions against defined API contracts.

**Planned tasks:** Add routing, auth state, protected routes, application shell, dashboard, equipment screens, work-order screens, history/maintenance views, administrator user management, forms, validation, loading/empty/error states, and role-aware UI.

**Dependencies:** Stable API contracts from Phases 4–7 and the Phase 2 frontend skeleton.

**Deliverables:** Usable frontend pages with local mock/API configuration only where explicitly documented.

**Completion criteria:** Main journeys are navigable; errors and loading states are understandable; UI does not claim access that the backend would reject; key interactions have tests if time permits.

## Phase 9 — Frontend/backend integration

**Objective:** Connect the real React client to the real FastAPI APIs and verify end-to-end flows.

**Planned tasks:** Configure API base URL, login/token handling, request/error utilities, forms and list queries, dashboard data, CORS, and integrated local smoke tests.

**Dependencies:** Phases 5–8.

**Deliverables:** Full local user journeys backed by PostgreSQL.

**Completion criteria:** A clean local environment supports login through completed maintenance and dashboard review; no mock data remains in production paths; integration failures are actionable.

## Phase 10 — Testing, debugging, and security review

**Objective:** Stabilize the MVP and assess correctness and security before packaging.

**Planned tasks:** Expand backend and frontend tests, run migrations from empty state, test role boundaries and invalid input, review secrets/CORS/JWT/error handling, inspect dependencies, fix bugs, and rehearse the demonstration.

**Dependencies:** Integrated MVP from Phase 9.

**Deliverables:** Test results, bug fixes, security review notes, and an updated status record.

**Completion criteria:** Important workflows and permissions pass; no known critical blocker remains; documentation reflects actual setup and commands.

## Phase 11 — Docker packaging and optional AWS deployment

**Objective:** Package the verified local app and optionally prepare a deployment path.

**Planned tasks:** Add Dockerfiles/compose only after local verification; document environment variables, persistent database handling, health checks, and optional AWS architecture/deployment steps.

**Dependencies:** Phase 10 complete and local MVP reliable.

**Deliverables:** Reproducible container workflow and, only if separately approved, deployment artifacts.

**Completion criteria:** Containerized local run is verified; deployment is never claimed without a real verification; production secrets and data handling are documented.

## Phase 12 — Documentation, release verification, presentation preparation, and interview rehearsal

**Objective:** Prepare a truthful, repeatable release and interview demonstration.

**Planned tasks:** Finalize setup/use/API documentation, release checklist, known limitations, sample data procedure, local demo script, architecture explanation, trade-off notes, and rehearsal against the October 19, 2026 target.

**Dependencies:** MVP acceptance and any optional deployment work completed or explicitly excluded.

**Deliverables:** Release-ready documentation and demonstration plan.

**Completion criteria:** Another developer can run the documented project; the demo follows real verified flows; limitations and future work are stated accurately.
