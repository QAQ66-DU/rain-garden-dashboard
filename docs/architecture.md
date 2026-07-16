# Architecture

## Context

The browser reads normalized, public sensor data from a versioned FastAPI service. FastAPI coordinates services, pure quality/status functions, and SQLAlchemy repositories. PostgreSQL stores the original private uplink separately from long-format measurements. A future TTN webhook crosses a server-to-server trust boundary but remains disabled in Phase 1.

```mermaid
flowchart LR
    Browser[Browser: React and Vite] -->|HTTPS JSON /api/v1| API[FastAPI]
    TTN[The Things Network: future] -.->|authenticated webhook| API
    API --> Services[Application services]
    Services --> Domain[Pure status and quality logic]
    Services --> Repositories[SQLAlchemy repositories]
    Repositories --> DB[(PostgreSQL 16)]
    API --> Schema[OpenAPI]
    Schema --> Generated[Generated TypeScript API types]
    Generated --> Browser
```

## Components and dependency direction

- Frontend pages compose features and present view models.
- The typed client is generated from OpenAPI and is the only browser network boundary.
- TanStack Query owns server-state fetching and caching.
- Recharts receives already prepared numeric series; it performs no scientific calculations.
- API endpoints validate transport input and call services.
- Services define use cases and calculation reference times.
- Repositories contain persistence and bounded query logic.
- `analytics` and status modules contain pure, independently tested functions.

Required dependency direction is `API -> services -> domain/repositories`. Repositories and domain code never depend on API routes. Backend and frontend source trees never import each other.

## Data flow

1. A canonical internal uplink is validated independently of TTN-specific fields.
2. The ingestion service obtains idempotency through unique `(source, idempotency_key)` storage.
3. The private raw JSONB event is stored once.
4. Measurements reference both the event and a `SensorChannel` carrying metric, unit, depth, and position metadata.
5. Public repositories select normalized fields only.
6. Services apply explicit reference times, quality exclusions, comparability rules, and freshness thresholds.
7. Pydantic response schemas exclude private coordinates, external identifiers, and raw payloads.

## Data model

- **Site:** UUID, name, description, public location label, disclosure classification, nullable private latitude/longitude, IANA display timezone, active flag, audit timestamps.
- **Device:** UUID, site FK, private external ID, display name, device type, nullable operational override, nullable private latitude/longitude, disclosure classification, last-seen time, audit timestamps.
- **SensorChannel:** UUID, device FK, unique channel code per device, display name, metric/unit pair, nullable depth and position, active flag, private metadata JSONB, audit timestamps.
- **MetricDefinition:** code/unit pair and reader metadata synchronized from `backend/app/metric_catalog.py`.
- **UplinkEvent:** UUID, device FK, source/idempotency identity, event timestamps, optional frame counter/schema version, private raw JSONB, ingestion status/error, audit timestamp.
- **Measurement:** UUID, uplink/device/channel FKs, numeric value, measured time, quality flag/notes, audit timestamp.

Depth and position never alter the controlled metric code. A 10 cm and a 20 cm channel both use `soil_moisture_vwc_pct` and remain separately identifiable.

## Freshness and operational state

Device connectivity status is calculated, never stored as unquestioned truth:

- `unknown`: no `last_seen_at`.
- `online`: age is no greater than the configured stale threshold.
- `stale`: age is above the stale threshold and no greater than the offline threshold.
- `offline`: age is above the offline threshold.

Phase 1 demo defaults are 90 and 180 minutes. They are operational presentation settings based on the one-hour synthetic generator, not scientific or manufacturer thresholds. The response includes thresholds, age, reference time, and status basis. In demo mode, the reference time is the maximum dataset receipt time, not wall-clock time. Maintenance/disabled overrides are stored and reported separately.

## API and privacy boundaries

Public endpoints return public IDs, labels, calculated freshness, normalized measurements, channel metadata needed for interpretation, and approximate disclosure labels. They never return raw uplinks, external device IDs, DevEUIs, private channel metadata, or exact coordinates. Exact-coordinate access would require a separately approved authenticated endpoint.

## Deployment

Docker Compose runs PostgreSQL, backend, and frontend. Development targets provide reload behavior; production targets use a non-root backend process and Nginx static hosting/proxying. Migrations are an explicit deployment step rather than an automatic multi-replica startup side effect. Seed data is an explicit demo-only command.

