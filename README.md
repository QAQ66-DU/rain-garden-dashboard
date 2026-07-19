# Rain Garden Monitoring Dashboard

A portable browser dashboard for an MSc Data Science project investigating LoRaWAN monitoring of rain gardens and related urban green infrastructure.

Phase 0 and Phase 1 are complete and use deterministic synthetic data only. The application does not claim real The Things Network (TTN) compatibility or calculate hydrological performance scores.

## Screenshots

> Screenshot placeholder: add approved stakeholder-facing images after the interface and disclosure wording have been reviewed.

## What is included

- A responsive Overview with device freshness, rainfall, quality, and channel-aware soil-moisture spread.
- A searchable/filterable public device inventory.
- A device detail view with per-channel latest values and a selectable, bounded seven-day raw time series.
- A read-only FastAPI service backed by PostgreSQL 16.
- A deterministic, idempotent seed for one site, three devices, 15 sensor channels, seven days of readings, missing intervals, one duplicate uplink case, and one quality warning.
- Generated TypeScript API types from FastAPI OpenAPI.
- Unit, integration, contract, migration, responsive, and browser smoke tests.

All values and charts display units. Missing records remain missing and are never converted to zero. Synthetic provenance is visible throughout the interface.

## Architecture

- React 19, Vite, strict TypeScript, React Router, TanStack Query, and Recharts frontend.
- FastAPI, Pydantic v2, SQLAlchemy 2, and Alembic backend on Python 3.12.
- PostgreSQL 16 with a non-superuser application role in the Docker workflow.
- FastAPI OpenAPI as the public contract and generated frontend types as its consumer.
- Docker Compose for the platform-independent contributor workflow.

The dependency direction is API routes → services → repositories/domain logic. UI components do not access the database or calculate scientific results. See [architecture](docs/architecture.md), [requirements](docs/requirements.md), [assumptions](docs/assumptions.md), and [threat model](docs/threat-model.md).

## Prerequisites

The canonical workflow requires only:

- Docker Desktop, or another Docker Engine with Compose v2.
- A current browser on macOS, Windows, or Linux.

Host Python and Node.js are optional contributor tools. Dashboard users need neither.

## Docker startup

1. Create the local environment file and replace every `CHANGE_ME` value with a unique local secret:

   ```bash
   cp .env.example .env
   ```

2. Build the pinned application images and start PostgreSQL:

   ```bash
   docker compose build
   docker compose up -d db
   ```

3. Apply the migration and load the deterministic dataset:

   ```bash
   docker compose run --rm backend uv run alembic upgrade head
   docker compose run --rm backend uv run python -m app.db.seed
   ```

4. Start the API and frontend:

   ```bash
   docker compose up -d backend frontend
   docker compose ps
   ```

Open [http://localhost:5173](http://localhost:5173). The API health endpoint is [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health).

The seed command is idempotent; rerunning it does not duplicate the canonical uplinks or measurements. To remove all local containers and database data:

```bash
docker compose down -v
```

## Environment variables

| Variable                                                        | Purpose                                     | Phase 1 behavior                                       |
| --------------------------------------------------------------- | ------------------------------------------- | ------------------------------------------------------ |
| `POSTGRES_ADMIN_USER`, `POSTGRES_ADMIN_PASSWORD`                | PostgreSQL bootstrap credentials            | Required by Compose; not used by the running API       |
| `APP_DB_NAME`, `APP_DB_USER`, `APP_DB_PASSWORD`, `DATABASE_URL` | Non-superuser application database          | Required                                               |
| `APP_ENV`                                                       | `development`, `test`, or `production` mode | Required                                               |
| `DEMO_MODE`                                                     | Enables synthetic-data behavior and labels  | Must be `true` for the Phase 1 seed                    |
| `LOG_LEVEL`                                                     | Backend structured-log level                | Defaults to `INFO`                                     |
| `CORS_ALLOWED_ORIGINS`                                          | Comma-separated browser-origin allowlist    | No wildcard credentials configuration                  |
| `WEBHOOK_BODY_LIMIT_BYTES`                                      | TTN request ceiling                         | Defaults to 262,144 bytes (256 KiB)                    |
| `TTN_WEBHOOK_ENABLED`, `TTN_WEBHOOK_SECRET`                     | Authenticated future ingestion boundary     | Endpoint remains disabled after valid authentication   |
| `PUBLIC_RATE_LIMIT_*`, `INGESTION_RATE_LIMIT_*`                 | Per-process request windows                 | In-memory, single-process only                         |
| `DEVICE_STALE_AFTER_MINUTES`, `DEVICE_OFFLINE_AFTER_MINUTES`    | Freshness thresholds                        | Calculated against the explicit dataset reference time |
| `DEFAULT_MEASUREMENT_RANGE_DAYS`                                | Default raw query window                    | 7 days                                                 |
| `MAX_MEASUREMENT_RANGE_DAYS`                                    | Maximum raw query window                    | 31 days                                                |
| `MAX_MEASUREMENT_RESULT_ROWS`                                   | Raw matching-row preflight ceiling          | 5,000; excess requests are rejected, not truncated     |

`.env.example` contains placeholders only. `.env` is ignored by Git.

## Database migrations and seed data

Run commands from the repository root with Docker:

```bash
docker compose run --rm backend uv run alembic upgrade head
docker compose run --rm backend uv run alembic check
docker compose run --rm backend uv run python -m app.db.seed
```

The initial migration is `backend/migrations/versions/0001_initial_schema.py`. It creates Site, Device, SensorChannel, MetricDefinition, UplinkEvent, and Measurement storage with foreign keys, controlled enums, uniqueness constraints, and query indexes. `backend/app/metric_catalog.py` is the only editable metric/unit catalog; the database and generated `docs/data-dictionary.md` are checked against it.

The one-hour synthetic generator cadence is a test setting, not a confirmed sensor sampling interval. Its fixed anchor, seed, and expected record counts are recorded in `sample-data/synthetic/seed-manifest.json`.

## Quality commands

Backend commands run from `backend/` after recreating the ignored local environment from the
committed lockfile. `uv sync --frozen` replaces a stale or broken `.venv` without committing it:

```bash
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run pytest --cov=app --cov-branch --cov-report=term-missing
uv run alembic upgrade head
uv run alembic check
uv run pip-audit
```

Frontend commands run from `frontend/` after `npm ci`:

```bash
npm run format:check
npm run lint
npm run typecheck
npm run test:run
npm run build
npm run check:api
npx playwright install chromium
npm run test:e2e
npm audit --audit-level=high
```

Playwright writes generated results under `frontend/test-results/` and reports under
`frontend/playwright-report/`. Both directories are ignored by Git and Prettier, so rerunning the
documented format gate after browser tests still checks every tracked source and documentation
file without inspecting generated test output.

Repository-level portability check:

```bash
python3 scripts/check_portability.py
```

GitHub Actions repeats the static, test, PostgreSQL migration, generated-contract, Docker browser, dependency-audit, and gitleaks secret-scanning gates on pushes and pull requests.

## Production deployment principles

The Dockerfiles contain non-root backend and static Nginx frontend production targets, but production deployment is intentionally outside Phase 1. Before deploying non-public data, require HTTPS, an established OIDC provider or authenticated reverse proxy, shared/reverse-proxy rate limiting, managed secrets, restricted network access, database backup/restore tests, retention rules, and a renewed privacy/threat review. Do not expose PostgreSQL publicly.

Exact coordinates, external device identifiers, DevEUI values, and raw uplink payloads are absent from public schemas. The disabled TTN boundary must not be enabled until confirmed payload fixtures and a separately approved Phase 2 adapter exist.

## Known limitations

- No real TTN payload adapter or live ingestion.
- No user authentication; public demo mode is suitable only for synthetic or approved non-sensitive data.
- Rate limiting is process-local and not sufficient for horizontally scaled deployment.
- No private-coordinate endpoint, CSV export, alert engine, maps, advanced data-quality detection, or research analytics.
- No aggregation/downsampling; raw requests are bounded and rejected above the configured ceiling.
- Synthetic status thresholds are configurable operational defaults, not scientifically confirmed values.
- Software licensing remains unresolved pending university, supervisor, and partner confirmation; no licence file is included.

## Scope boundary

Phase 2 and later roadmap work is documented but not implemented. In particular, the repository contains no fabricated TTN payload schema, rainfall-event analysis, hydrological formula, machine-learning result, or performance score. The legacy Replit prototype remains requirements-only and is not a package, service, build input, or runtime dependency.
