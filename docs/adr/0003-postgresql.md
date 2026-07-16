# ADR 0003: PostgreSQL only

- Status: accepted
- Decision: PostgreSQL 16 is used for development, tests, and production; SQLite is not supported.
- Rationale: JSONB, constraints, indexing, and consistent database behavior matter more than a second lightweight database path.
- Consequence: integration tests and local execution require PostgreSQL, normally through Docker.
