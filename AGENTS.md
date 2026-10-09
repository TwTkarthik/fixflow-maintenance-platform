# FixFlow Agent Instructions

## Before starting work

- Read `docs/PROJECT_SPEC.md`, `docs/PROJECT_STATUS.md`, `docs/DEVELOPMENT_ROADMAP.md`, and `docs/DECISIONS.md` before making changes.
- Inspect the current code and repository state before editing anything.
- Confirm the requested work belongs to the current phase and is a bounded feature or phase increment.

## Architecture and scope

- Follow the approved architecture and technology choices in the project documentation.
- Implement one phase or bounded feature at a time.
- Preserve working functionality and avoid unnecessary dependencies or architectural changes.
- Keep the initial release single-organization and focused on the documented MVP.

## Safety and security

- Never overwrite files or perform destructive operations without explicit authorization.
- Keep credentials, tokens, private keys, and local environment files out of source control.
- Enforce authorization and role permissions in the backend; frontend visibility is not a security boundary.
- Use environment-based configuration and explicit token-expiration policies.
- Use database migrations for schema changes; do not modify a shared database schema manually.

## Quality and verification

- Write or update tests for meaningful functionality and permission boundaries.
- Run applicable checks and tests, and report their actual results.
- Never claim a command, test, feature, or deployment succeeded unless it was verified.
- Inspect diffs and generated files before handing work back.

## Status and handoff

- Update `docs/PROJECT_STATUS.md` at the end of every phase.
- Record actual commands and test results, not planned or assumed results.
- Identify incomplete work, blockers, and decisions awaiting approval.
- Provide an explicit next action for the next development session.
