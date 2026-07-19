# Change protocol

## Change brief

Before editing, record:

- the requested outcome and explicit non-goals;
- current Git state and baseline check results;
- affected API, schema, migration, UI, domain/analytics, security, tests, generated artifacts, and documentation;
- whether units, metric codes, channels, depths, time semantics, privacy, or missing-data behavior are involved;
- the smallest viable diff and rollback approach.

Ambiguity affecting scientific meaning, privacy, authentication, schema, or compatibility requires clarification.

## Implementation rules

- Keep one behavior per logical commit.
- Do not refactor unrelated code while adding a feature.
- Add tests with each behavior and keep fixtures semantically stable.
- Use migrations for schema changes and test both upgrade and fresh initialization.
- Change `backend/app/metric_catalog.py`, then regenerate the database seed/documentation; never edit catalog copies independently.
- Regenerate TypeScript only from the reviewed OpenAPI document.
- Treat public-schema additions as privacy decisions and review every field.
- Keep incomplete behavior disabled behind explicit configuration.
- Use half-open UTC query windows `[start, end)`. Coverage requires an explicit reporting interval, schedule anchor, and jitter tolerance; do not infer a precise schedule or use rounded window duration as expected count.

## Quality gate

Run targeted checks after each stage and the following complete gate before completion:

```text
Backend: Ruff format check, Ruff lint, mypy, pytest
Database: Alembic upgrade from empty PostgreSQL, catalog synchronization, deterministic seed
Frontend: Prettier, ESLint, TypeScript, Vitest, production Vite build
Contract: export OpenAPI, regenerate TypeScript, fail on generated diff
End to end: Docker stack health and Playwright Chromium smoke suite
Security: pip-audit, npm audit --audit-level=high, gitleaks, manual public-schema/log review
Repository: portability/Replit scan and final Git diff review
```

High and critical dependency findings fail CI. Lower-severity findings remain visible for review. A failing baseline must be reported; tests and security controls must not be weakened to force a pass.

## Impact matrix

| Change              | Required review                                                                     |
| ------------------- | ----------------------------------------------------------------------------------- |
| Metric or unit      | catalog, migration/seed, dictionary generation, API, UI units, fixtures, tests      |
| Sensor channel      | schema, uniqueness, comparability, public metadata, filters, chart labels           |
| Database field      | privacy classification, migration, model/schema/repository, fresh DB test           |
| API contract        | routes/services, OpenAPI, generated TypeScript, consumers, fixtures, contract tests |
| Freshness threshold | configuration, reference-time semantics, status tests, UI copy, assumptions         |
| Ingestion           | auth, size/content checks, idempotency, logs, raw-data privacy, threat model        |
