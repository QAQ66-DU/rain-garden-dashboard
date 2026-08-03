# Current project state

> **Dated snapshot, not a live source of truth.** This handoff records the verified state on
> 2026-07-19. Recheck Git, migrations, configuration, and the running environment before relying on
> it later.
>
> A later local-only TTN replay implementation is documented in
> [offline-ttn-replay.md](offline-ttn-replay.md). The historical snapshot below intentionally remains
> tied to its original commit and therefore does not describe migration `0004` or the TTN Testbed.

## Snapshot identity

- Snapshot date: 2026-07-19 (Europe/London)
- Branch: `master`
- Application HEAD verified before this documentation-only handoff:
  `a5c42798104f83074663ca02582702d5fb945574` (`feat: add site-wide time explorer`)
- Running database migration: `0003` (`head`)
- Repository state at verification: clean

The handoff document itself is added by the subsequent documentation-only commit reported in the
session that created it; the application baseline above is the commit whose behavior was verified.

## Architecture and data flow

The browser application uses React, Vite, strict TypeScript, React Router, TanStack Query, and
Recharts. Its only network boundary is the typed API client generated from FastAPI OpenAPI.
FastAPI/Pydantic routes validate transport input, services coordinate use cases, repositories own
SQLAlchemy access, and pure domain/analytics modules calculate status, quality, coverage, and period
summaries. PostgreSQL 16 stores normalized long-format measurements and their source uplink events.

The intended flow is:

`browser -> /api/v1 -> route -> service -> repository/domain -> PostgreSQL`

A canonical ingestion boundary already preserves private raw events and derives normalized
measurements with transactional idempotency. The TTN-specific adapter remains disabled because no
real payload contract has been confirmed. Public schemas exclude raw payloads and private device
fields.

## Database and confirmed Orchard Park inventory

The running local stack was rebuilt from an empty disposable PostgreSQL volume, migrated through
`0003`, and loaded with the normal confirmed-inventory synthetic seed. Its verified inventory is:

- 1 site: Orchard Park monitoring site
- 2 monitoring features: Swale and Tree pit
- 8 sensor/end devices; the outdoor LoRaWAN gateway is infrastructure and is not counted
- 3 Swale soil sensors, each with 3 configured channels
- 3 Swale water-level sensors, each with 1 configured channel
- 1 Swale weather station with 8 configured channels
- 1 Tree-pit multi-depth probe with configuration `pending` and 0 channels
- 20 configured channels in total, all currently attached to Swale devices

No tree-pit depths, depth spacing, or depth channels have been invented.

## Synthetic-data status

> **No real TTN, deployed-sensor, or research observations have been collected or ingested.** Every
> current uplink, measurement, chart, status, coverage value, and summary is deterministic synthetic
> demonstration data and must not be presented as field evidence or system performance.

The current seed uses random seed `20260716`, a fixed UTC reference time, an explicit one-hour demo
schedule, demo-normalised units labelled `synthetic_demo_only`, 1,168 unique synthetic uplinks, and
3,345 synthetic measurements. A second seed run changed no rows and retained the same database
fingerprint. These units, schedules, thresholds, and values do not confirm deployed-device behavior.

## Implemented interface and API

Implemented pages:

- **Overview:** synthetic provenance, current freshness, rainfall, quality, and channel-aware
  soil-moisture spread.
- **Explore:** shareable 24-hour, 7-day, 30-day, and custom periods; feature, metric-group, and
  channel filters; synchronized compatible-unit small multiples; metric-specific summaries;
  schedule-aligned coverage; and quality-warning drill-down.
- **Devices:** searchable and filterable public inventory.
- **Device Detail:** public channel metadata, latest values, and bounded selectable raw time series.

Major API capabilities include health, sites, filtered device inventory, device detail, cursor-based
measurement queries, overview summaries, site-wide exploration, quality warnings, generated OpenAPI,
bounded query preflights, and an authenticated but disabled TTN webhook scaffold. The API is
read-only apart from that disabled ingestion boundary.

## Important decisions

- Dependency direction is `routes -> services -> repositories/domain`; scientific calculations do
  not belong in routes or React components.
- `backend/app/metric_catalog.py` is the canonical editable metric and physical-unit vocabulary;
  database catalogs, the data dictionary, OpenAPI, and generated TypeScript must remain reconciled.
- `unit_code` is nullable and separate from `unit_confirmation_status` (`pending`, `confirmed`, or
  `synthetic_demo_only`). Unknown is a status, not a physical unit.
- Non-synthetic numeric ingestion requires an explicitly confirmed metric and unit mapping.
- Historical windows are half-open UTC intervals `[start, end)`. `measured_at` determines the
  scientific slot; `received_at` is separate transmission-delay context.
- Coverage requires an explicit interval, schedule anchor, and jitter tolerance. Duplicate slots do
  not inflate received coverage; flagged values are received but not valid; missing is never zero;
  unknown schedules produce unavailable coverage.
- Incompatible metrics, units, positions, or depths remain separate. Wind direction is not averaged,
  and rainfall duration above zero requires known cadence and complete valid coverage.
- Exact coordinates, external identifiers, DevEUIs, raw uplinks, and private channel metadata are
  excluded from browser and public API schemas.
- Current freshness and selected-period historical coverage are separate concepts.

## Known limitations and unresolved information

- No real TTN payload adapter, live ingestion, or confirmed field mapping exists.
- Device models, firmware, TTN identifiers, payload schemas, frame-counter behavior, deployed units,
  calibration, accuracy, and operating ranges remain unconfirmed.
- The Tree-pit probe's channel count, installation depths/spacing, mappings, and scientific
  comparability remain unknown.
- Water-level reference/datum and real reporting schedules/jitter tolerances remain unconfirmed.
- Scientific validity thresholds, rainfall-event definitions, response/recovery thresholds, and
  performance calculations require separate approval.
- Authentication, production deployment, shared rate limiting, backups, retention/deletion policy,
  formal audit logging, and software licensing remain unresolved.
- Maps, public coordinates, CSV export, alerts, event analytics, anomaly detection, machine learning,
  and camera/image work are not implemented.

## Current local access and operations

At snapshot verification, the local Compose stack was healthy at:

- Frontend: <http://localhost:5173>
- Backend API base: <http://localhost:8000/api/v1>
- API documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/v1/health>

Use the existing [README](../README.md) for prerequisites, Docker startup, migrations, the confirmed
seed, guarded demo reset, quality commands, and operational limitations. Do not copy commands from
this dated snapshot without first checking the README and current repository state.

## Recommended next phase: TTN live ingestion

The recommended next phase is a narrow, fixture-driven TTN live-ingestion implementation. Do not
enable the existing webhook adapter or infer a payload schema from dashboard expectations.

Preconditions:

1. Obtain reviewed real payload samples covering normal, missing, malformed, duplicate, and relevant
   firmware-version cases.
2. Confirm the TTN application identifier and each device identifier, keeping external identifiers
   private by default.
3. Confirm every payload-field-to-channel/metric mapping, physical unit, scale, signedness, null
   convention, timestamp source, and firmware/schema version.
4. Establish webhook authentication, TLS termination, secret storage, rotation, request-size limits,
   and production-safe error behavior.
5. Preserve each original raw event privately before normalization; never log complete raw uplinks or
   private identifiers.
6. Define stable idempotency keys and duplicate/replay behavior, including frame-counter reset and
   retry cases.
7. Record provenance from TTN receipt through normalized observation: source, received time, measured
   time, mapping/schema version, unit-confirmation basis, and quality treatment.
8. Start live ingestion from a clean, migrated, **inventory-only** database with no synthetic
   observations. Never mix the current demonstration measurements with real TTN data.
9. Add redacted fixtures, contract tests, database integration tests, privacy review, migration tests,
   and end-to-end verification before enabling the adapter.

## Recovery prompt for a new Codex chat

> Continue the Rain Garden Monitoring Dashboard from `docs/CURRENT_PROJECT_STATE.md`. Treat it as a
> 2026-07-19 snapshot tied to application commit `a5c4279`, then verify current `git status`, HEAD,
> `AGENTS.md`, README, architecture, requirements, assumptions, migrations, and the running Compose
> stack before acting. The next recommended phase is fixture-driven TTN live ingestion. Do not invent
> TTN fields, units, tree-pit depths, identifiers, schedules, or scientific thresholds; require real
> payload samples and confirmed mappings first. Preserve raw events privately, enforce idempotency and
> provenance, and use a clean inventory-only database with no synthetic observations for live data.
