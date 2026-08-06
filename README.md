# Rain Garden Monitoring Dashboard

A portable browser dashboard for an MSc Data Science project investigating LoRaWAN monitoring of rain gardens and related urban green infrastructure.

Phase 0 and Phase 1 are complete. The normal dashboard now presents eight approved TTN proxy
devices from the `rain-garden` application. They are not deployed at Orchard Park, and their physical
units remain pending. The confirmed Orchard Park inventory and deterministic synthetic observations
remain available through the explicit demo seed/test workflow, but are hidden from normal live
dashboard responses. The application does not calculate hydrological performance scores.

## Screenshots

> Screenshot placeholder: add approved stakeholder-facing images after the interface and disclosure wording have been reviewed.

## What is included

- A responsive Overview with device freshness, rainfall, quality, and channel-aware soil-moisture spread.
- A site-wide Time Explorer with shareable UTC periods, feature/metric/channel filters, synchronized unit-separated charts, schedule-aligned coverage, and a safe quality-warning drill-down.
- A searchable/filterable public device inventory.
- A device detail view with per-channel latest values, shareable 24-hour, 7-day, 30-day or custom
  raw time ranges, and privacy-reviewed CSV export for the selected device channel and period.
- A read-only FastAPI service backed by PostgreSQL 16.
- A deterministic, idempotent seed for eight confirmed sensor/end-device records: seven configured swale devices with 20 channels and one tree-pit probe whose depth/channel configuration remains pending.
- Generated TypeScript API types from FastAPI OpenAPI.
- Unit, integration, contract, migration, responsive, and browser smoke tests.
- An isolated, idempotent offline replay command for the local `outflow-a` TTN console export.
- An opt-in, profile-gated TTN MQTT worker subscribed to application-wide uplinks for exactly eight
  approved proxy device IDs.

The outdoor LoRaWAN gateway is infrastructure and is not counted as a monitored sensor device. Numeric demo values and charts display both a unit and its `synthetic_demo_only` provenance; this does not confirm the deployed payload or physical-unit mapping. Missing records remain missing and are never converted to zero.

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

3. Apply the migration and load the inventory-only proxy catalogue (no observations or API key):

   ```bash
   docker compose run --rm backend uv run alembic upgrade head
   docker compose run --rm backend uv run python -m app.db.seed_ttn_proxy
   ```

4. Start the API and frontend:

   ```bash
   docker compose up -d backend frontend
   docker compose ps
   ```

Open [http://localhost:5173](http://localhost:5173). The API health endpoint is [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health).

The proxy inventory seed is idempotent and creates exactly eight device records plus their
evidence-backed channel definitions; it creates no uplinks or measurements. The deterministic
Orchard Park seed remains an explicit demo/test workflow:

```bash
docker compose run --rm backend uv run python -m app.db.seed
```

The demo seed is also idempotent; rerunning it does not duplicate canonical uplinks or measurements.
It never deletes or mixes an older Phase 1 inventory. If an existing demo database still contains
that inventory, the seed stops and explains that an explicit demo-only reset is required. After
reviewing the scope and confirming that the database contains no required data, run:

```bash
docker compose run --rm backend uv run python -m app.db.reset_demo --confirm-reset
```

The reset refuses production, non-demo mode, unknown device identifiers, and non-synthetic uplinks. It was not run as part of this change. To remove all local containers and database data:

```bash
docker compose down -v
```

## Offline TTN console replay

After migration and the normal Orchard Park seed, a developer who holds the ignored local source
fixture can replay it without any TTN network access:

```bash
docker compose run --rm backend uv run python -m app.scripts.replay_ttn_export \
  tests/fixtures/ttn/outflow-a-live-data.json
```

The command selects only `as.up.data.forward`, preserves each selected raw event privately, and
upserts `outflow-a` under the separate proxy site. Run it again to verify that every selected uplink
is reported as a skipped duplicate. This compatibility workflow does not create the other seven
devices unless the live worker inventory initialiser runs.

This workflow needs no TTN API key and makes no TTN request. It did not alter the TTN application,
devices, payload formatter, downlinks, MQTT configuration, or Google Sheets webhook. Measurement 1
and Measurement 2 intentionally retain null units and unverified scientific meanings. See the
[offline replay design and privacy notes](docs/offline-ttn-replay.md).

The separately started live MQTT preparation is documented in the
[live TTN MQTT development guide](docs/live-ttn-mqtt.md). Normal Compose startup remains independent
of its API key; do not start the `live` profile until a clean inventory-only database and a new
read-only key have been prepared.

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
| `TTN_MQTT_HOST`, `TTN_MQTT_PORT`                                | Opt-in worker broker connection             | `eu1.cloud.thethings.network`, TLS port `8883`         |
| `TTN_MQTT_USERNAME`, `TTN_MQTT_TOPIC`                           | Application uplink subscription             | Restricted to `rain-garden@ttn` and eight mapped IDs   |
| `TTN_MQTT_API_KEY`                                              | MQTT password for the opt-in worker         | Blank by default; local ignored `.env` only            |
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
docker compose run --rm backend uv run python -m app.db.seed_ttn_proxy
# Explicit demo/test workflow only:
docker compose run --rm backend uv run python -m app.db.seed
```

The initial migration is `backend/migrations/versions/0001_initial_schema.py`. Migration
`0002_confirmed_orchard_inventory.py` adds normalized monitoring features, the confirmed device type,
explicit configuration/schedule metadata, and a separate physical-unit catalogue. Migration
`0003_time_explorer_metric_groups.py` adds the controlled metric grouping used by Time Explorer.
Migration `0004_offline_ttn_replay.py` adds the isolated testbed vocabulary, explicit replay
provenance, unverified-channel metadata, latest operational telemetry, and a private preserve-first
quarantine. Migration `0005_reclassify_ttn_metadata_quality.py` safely reclassifies only accepted
TTN measurements carrying the former blanket metadata-warning notes; the correction is
intentionally one-way so a code rollback cannot make valid observations suspect again. `unit_code`
is nullable while `unit_confirmation_status` records `pending`, `confirmed`, or
`synthetic_demo_only`; “unknown” is never stored as a physical unit.
`backend/app/metric_catalog.py` remains the only editable metric and unit vocabulary, and the
database catalog plus generated `docs/data-dictionary.md` are checked against it.

The one-hour synthetic generator cadence, fixed UTC schedule anchor, and five-minute jitter tolerance are test settings, not confirmed deployed-sensor properties. Their values, seed, and expected record counts are recorded in `sample-data/synthetic/seed-manifest.json`. Live proxy channels remain `pending` with nullable units; a channel requires explicit physical-unit evidence before it can become `confirmed`.

Historical queries use half-open UTC windows `[start, end)`, with display times converted to the site's `Europe/London` timezone. Coverage counts schedule-aligned slots from the explicit interval, anchor, and jitter tolerance; it is unavailable rather than inferred when any schedule input is missing. Duplicate-slot observations do not increase received coverage, flagged slots are received but not valid, and missing never means numeric zero. Rainfall duration above zero is shown only with complete valid scheduled coverage.

For explicitly mapped TTN proxy channels, successfully decoded finite numbers are valid
observations even while their scientific metadata and unit remain pending. The UI keeps those
states visible as `Metadata pending` and `Unit unverified`; unverified channels receive only basic
descriptive summaries and no hydrological interpretation.

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
python3 scripts/check_public_privacy.py
```

GitHub Actions repeats the static, test, PostgreSQL migration, generated-contract, Docker browser, dependency-audit, and gitleaks secret-scanning gates on pushes and pull requests.

## Production deployment principles

The Dockerfiles contain non-root backend and static Nginx frontend production targets, but production deployment is intentionally outside Phase 1. Before deploying non-public data, require HTTPS, an established OIDC provider or authenticated reverse proxy, shared/reverse-proxy rate limiting, managed secrets, restricted network access, database backup/restore tests, retention rules, and a renewed privacy/threat review. Do not expose PostgreSQL publicly.

Exact coordinates, external device identifiers, DevEUI values, and raw uplink payloads are absent from public schemas. The disabled TTN boundary must not be enabled until confirmed payload fixtures and a separately approved Phase 2 adapter exist.

## Known limitations

- No live webhook adapter, downlinks, cloud deployment, TTN Storage API backfill, or automatic
  historical import. The application-wide MQTT worker remains inactive unless the `live` profile is
  explicitly started with a local key and accepts only the eight mapped device IDs.
- No user authentication; public demo mode is suitable only for synthetic or approved non-sensitive data.
- Rate limiting is process-local and not sufficient for horizontally scaled deployment.
- No private-coordinate endpoint, alert engine, maps, advanced data-quality detection, or research
  analytics. Device Detail CSV export is limited to the selected normalized channel and bounded
  time range; it does not export private raw uplinks or network identifiers.
- No downsampling or persisted rollups; raw observations and Explorer drill-downs are bounded and rejected above the configured ceiling.
- Synthetic status thresholds are configurable operational defaults, not scientifically confirmed values.
- Proxy physical units, reporting schedules, and several decoded numeric meanings remain
  unconfirmed. `prototype-board-1` and `vision-ai` have no observed uplink evidence, and `vision-ai`
  has no supplied formatter; both therefore have zero configured channels.
- Software licensing remains unresolved pending university, supervisor, and partner confirmation; no licence file is included.

## Scope boundary

The repository contains no rainfall-event analysis, hydrological formula, machine-learning or
camera result, performance score, cloud deployment, or historical backfill. Decoder labels do not
establish physical units. The legacy Replit prototype remains requirements-only and is not a
package, service, build input, or runtime dependency.
