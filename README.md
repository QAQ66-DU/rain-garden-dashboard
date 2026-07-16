# Rain Garden Monitoring Dashboard

A portable browser dashboard for an MSc Data Science project investigating LoRaWAN monitoring of rain gardens and related urban green infrastructure.

Phase 0 and Phase 1 use deterministic synthetic data only. The application does not claim real TTN compatibility or calculate hydrological performance scores.

## Architecture

- React/Vite/TypeScript frontend
- FastAPI/Pydantic/SQLAlchemy backend
- PostgreSQL 16 with Alembic migrations
- OpenAPI-generated frontend API types
- Docker Compose local workflow

See `docs/architecture.md`, `docs/requirements.md`, and `docs/threat-model.md` for the reviewed design and boundaries.

## Prerequisites

The canonical workflow needs Docker Desktop or another Docker Engine with Compose v2 and a modern web browser. Host Python and Node.js are optional contributor tools.

## Configuration

Copy `.env.example` to `.env` and replace every `CHANGE_ME` value. Never commit `.env`.

## Local Docker workflow

The following commands will be finalized and verified with the completed vertical slice:

```bash
docker compose build
docker compose up -d db
docker compose run --rm backend uv run alembic upgrade head
docker compose run --rm backend uv run python -m app.db.seed
docker compose up -d backend frontend
```

The development dashboard is served at `http://localhost:5173` and the API at `http://localhost:8000/api/v1`.

## Quality commands

Backend commands run from `backend/`:

```bash
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest --cov=app --cov-report=term-missing
uv run alembic upgrade head
uv run pip-audit
```

Frontend commands run from `frontend/`:

```bash
npm ci
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build
npm audit --audit-level=high
```

## Known limitations

Phase 1 has no real TTN adapter, user authentication, private-coordinate API, shared distributed rate limiting, CSV export, alerts, maps, advanced data-quality detection, or research analytics. Licensing remains unresolved pending university and partner confirmation.
