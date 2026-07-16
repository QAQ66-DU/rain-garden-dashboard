# Repository working agreement

These rules apply to every change in this repository. The project is maintained primarily by one MSc student, so changes must remain small, reviewable, portable, and reproducible.

## Before changing code

1. Run `git status --short --branch` and identify unrelated changes.
2. Read this file and the relevant sections of `docs/architecture.md`, `docs/requirements.md`, and `docs/change-protocol.md`.
3. Run the existing baseline checks for the affected area.
4. Identify direct and indirect impacts across API, schema, migration, UI, analytics, security, tests, and documentation.
5. State explicit non-goals and choose the smallest viable diff.
6. Stop for clarification if an ambiguity would change scientific meaning, units, missing-data treatment, security, or a public contract.

## While changing code

1. Modify only files required by the task; do not combine features with unrelated refactoring.
2. Preserve backward compatibility unless a breaking change is explicitly approved.
3. Add or update tests with the behavior.
4. Keep reusable domain logic in one canonical location.
5. Never manually duplicate generated API types or the metric and unit catalog.
6. Never silently change units, metric codes, thresholds, channel comparability, or missing-data behavior.
7. Use Alembic for every database schema change.
8. Do not use blanket type ignores, broad exception catches, weakened assertions, or unreviewed snapshot updates.
9. Do not log secrets, complete raw uplinks, exact coordinates, DevEUIs, or external device identifiers.
10. Keep commits small and atomic by logical stage.

## After changing code

1. Run targeted tests, then the full quality gate described in `docs/change-protocol.md`.
2. Validate formatting, lint, static types, tests, production build, OpenAPI generation, migrations from an empty PostgreSQL database, and Playwright smoke tests.
3. Inspect `git diff` for unrelated changes and perform a security self-review.
4. Update documentation and the changelog when behavior changes.
5. Distinguish pre-existing failures from new failures and report limitations honestly.

## Architectural constraints

- Frontend pages compose features; components do not call `fetch`.
- Frontend API access goes through the generated typed API layer and TanStack Query.
- Charts receive prepared view models and always show units.
- API routes call services; services call repositories and pure domain modules.
- Database access stays in repository/database modules.
- Scientific calculations do not belong in routes or React components.
- `backend/app/metric_catalog.py` is the only editable metric and unit vocabulary.
- Exact coordinates, raw uplinks, DevEUIs, and external device IDs are private by default.
- Phase 0 and Phase 1 contain synthetic data only. Do not imply TTN compatibility or real observations.
- Do not add Replit dependencies, SQLite, microservices, Kubernetes, Kafka, Redis, Celery, GraphQL, or advanced research analytics.

