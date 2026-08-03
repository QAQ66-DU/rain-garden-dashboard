# Architecture

## Context

The browser reads normalized, public sensor data from a versioned FastAPI service. FastAPI coordinates services, pure quality/status functions, and SQLAlchemy repositories. PostgreSQL stores the original private uplink separately from long-format measurements. A future TTN webhook crosses a server-to-server trust boundary but remains disabled. A local offline file replay exercises one fixture-driven TTN ApplicationUp normaliser without crossing that network boundary.

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
4. Measurements reference both the event and a `SensorChannel` carrying separate metric, nullable unit, unit-confirmation, installation-depth, position, and schedule metadata.
5. Public repositories select normalized fields only.
6. Services apply explicit reference times, quality exclusions, comparability rules, and freshness thresholds.
7. Pydantic response schemas exclude private coordinates, external identifiers, and raw payloads.

The offline TTN path adds a file adapter before step 1. It selects only `as.up.data.forward`, then
passes `event.data` to an ApplicationUp normaliser that has no file, network, or database dependency.
Known `outflow-a` events reuse `UplinkEvent` and `Measurement`; unmappable or structurally unsafe
selected events go to private `TTNReplayQuarantine`. This separation permits future reuse but does
not enable the existing webhook or create a live connection.

## Data model

- **Site:** UUID, name, description, public location label, disclosure classification, nullable private latitude/longitude, IANA display timezone, active flag, audit timestamps.
- **MonitoringFeature:** UUID, site FK, controlled feature type, public slug/name, active flag, audit timestamps. A site can contain multiple Swales, tree pits, or future approved feature types without encoding the relationship in presentation text.
- **Device:** UUID, site and monitoring-feature FKs, private external ID, display name, controlled device/configuration types, nullable operational override, nullable private latitude/longitude, disclosure classification, last-seen time, audit timestamps.
- **SensorChannel:** UUID, device FK, unique channel code per device, metric FK, nullable physical-unit FK, controlled unit-confirmation status, nullable installation depth/position, nullable expected interval/schedule anchor/jitter tolerance/water datum, active flag, private metadata JSONB, audit timestamps. The public `installation_depth_cm` field retains `depth_cm` as a Phase 1 compatibility alias.
- **MetricDefinition:** unit-neutral metric code, controlled Explorer group, and reader metadata synchronized from `backend/app/metric_catalog.py`.
- **UnitDefinition:** physical-unit code, name, symbol, and meaning synchronized separately from the same catalogue.
- **UplinkEvent:** UUID, device FK, source/idempotency identity, event timestamps, optional frame counter/schema version, private raw JSONB, ingestion status/error, audit timestamp.
- **Measurement:** UUID, uplink/device/channel FKs, numeric value, measured time, quality flag/notes, audit timestamp.
- **DeviceTelemetry:** Latest replay-derived operational status and radio context, kept separate from
  scientific channels; exact gateway identity remains private and only an allowlisted alias is public.
- **TTNReplayQuarantine:** Private raw selected events that cannot be parsed or mapped safely,
  deduplicated by a deterministic content identity and never exposed by public routes.

Installation depth and position never alter the controlled metric code. Channels at different confirmed depths would both use `soil_moisture` and remain separately identifiable. No tree-pit depths or depth channel count are currently configured.

`unit_confirmation_status` is independent of `unit_code`: pending channels may have no unit; real values require `confirmed`; deterministic demonstration channels use documented demo-normalised units with `synthetic_demo_only`. The status is not a physical unit code. The same separation applies to schedule metadata: coverage is unavailable unless interval and anchor are explicitly configured.

## Time Explorer and coverage

`GET /api/v1/explore` is a bounded, read-only site query. The endpoint validates a maximum 31-day half-open UTC window, performs result-count preflights, and delegates to a service that joins public device/channel records with pure coverage and summary calculations. Browser URLs retain `start`, `end`, feature, metric group, and explicit channel selection so the same analytical view can be shared or carried between Overview, Explore, and Devices.

The scientific time axis is `measured_at`; `received_at` is returned separately for transmission-delay assessment. Expected observations are schedule-aligned slots inside `[start, end)`, calculated from the channel's explicit expected interval and schedule anchor—not from rounded window duration. A configurable jitter tolerance assigns at most one accepted observation to a slot. Duplicate-slot observations do not increase received count; flagged observations are received but not valid; out-of-tolerance and late observations retain explicit timing labels; absent slots remain missing rather than zero. “Late” means reception occurred more than one expected reporting interval after `measured_at`; it does not reuse timestamp-jitter tolerance. If interval, anchor, or tolerance is absent, precise coverage is unavailable.

Period summaries are metric-specific and use valid observations. Wind direction has no arithmetic mean. Rainfall-intensity duration above zero is emitted only when cadence is known and every expected slot has a valid, in-tolerance observation. The frontend receives channel-specific series, groups only matching metric/unit/provenance combinations, renders incompatible units in separate synchronized small-multiple panels, and displays current freshness separately from historical coverage.

## Freshness and operational state

Device connectivity status is calculated, never stored as unquestioned truth:

- `unknown`: no `last_seen_at`.
- `online`: age is no greater than the configured stale threshold.
- `stale`: age is above the stale threshold and no greater than the offline threshold.
- `offline`: age is above the offline threshold.

Phase 1 demo defaults are 90 and 180 minutes. They are operational presentation settings based on the one-hour synthetic generator, not scientific or manufacturer thresholds. The response includes thresholds, age, reference time, and status basis. In demo mode, the reference time is the maximum dataset receipt time, not wall-clock time. Maintenance/disabled overrides are stored and reported separately.

The isolated TTN test device uses the maximum receipt time for its own replay site and reports
`replay_dataset_reference_time`. Orchard Park keeps its own site-scoped synthetic reference, so
replaying later-dated testbed events cannot change Orchard device status.

## API and privacy boundaries

Public endpoints return public IDs, monitoring-feature labels, calculated freshness, normalized measurements, and channel metadata needed for interpretation. They never return raw uplinks, external device IDs, DevEUIs, private channel metadata, or exact coordinates. Confirmed coordinates are stored only on private device fields. Exact-coordinate access would require a separately approved authenticated endpoint.

## Deployment

Docker Compose runs PostgreSQL, backend, and frontend. Development targets provide reload behavior; production targets use a non-root backend process and Nginx static hosting/proxying. Migrations are an explicit deployment step rather than an automatic multi-replica startup side effect. Seed data is an explicit demo-only command.
