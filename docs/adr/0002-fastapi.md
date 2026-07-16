# ADR 0002: FastAPI backend

- Status: accepted
- Decision: use Python 3.12, FastAPI, Pydantic v2, synchronous SQLAlchemy 2 sessions, Alembic, Psycopg 3, Ruff, mypy, and pytest.
- Rationale: explicit validation, generated OpenAPI, accessible research code, and a simple single-service deployment.
- Consequence: blocking database work runs through FastAPI's synchronous dependency path; advanced async infrastructure is intentionally avoided.
