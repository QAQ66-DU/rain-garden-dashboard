# Phase 0 and Phase 1 implementation checklist

This checklist incorporates the approved architectural amendments. Phase 2 and later work is explicitly excluded.

## Phase 0: foundation

- [ ] Establish governance, requirements, assumptions, change protocol, ADRs, security policy, and threat model.
- [ ] Establish pinned Python and Node dependency manifests and lockfiles.
- [ ] Define repeatable format, lint, type-check, unit-test, integration-test, migration, build, contract, and end-to-end commands.
- [ ] Create portable development and production Docker targets and a PostgreSQL 16 Compose service.
- [ ] Configure a non-superuser application database role and fail-safe environment validation.
- [ ] Create the metric catalog as the only editable metric/unit vocabulary.
- [ ] Model Site, Device, SensorChannel, MetricDefinition, UplinkEvent, and Measurement with constraints and indexes.
- [ ] Create and test the first Alembic migration against a fresh PostgreSQL database.
- [ ] Add structured logging, correlation IDs, safe API errors, CORS, security headers, body limits, and rate limiting.
- [ ] Add an authenticated but disabled TTN endpoint without inventing payload fields.
- [ ] Create the React shell, responsive navigation, error boundary, and typed API generation pipeline.
- [ ] Add CI and explicit dependency/secret scanning gates.

## Phase 1: tested vertical slice

- [ ] Generate a deterministic seven-day synthetic dataset at a one-hour generator cadence.
- [ ] Seed one site, three devices, multiple sensor channels, missing intervals, a duplicate uplink, and one invalid observation.
- [ ] Calculate unknown/online/stale/offline status from last-seen time, configurable thresholds, and an explicit reference time.
- [ ] Implement sites, devices, measurements, and overview repositories/services/APIs.
- [ ] Use cursor pagination, deterministic ordering, a seven-day default range, a 31-day maximum, and a 5,000-row raw-result ceiling.
- [ ] Reject oversized result sets explicitly; never truncate or downsample silently.
- [ ] Implement channel-aware soil-moisture min/median/max summaries with channel identity and timestamp range.
- [ ] Build Overview, Devices, and Device Detail pages with loading, error, empty, missing, quality, and synthetic-data states.
- [ ] Render a single-series time line with at least eight observations when available; show the selected channel, metric, unit, range, and source status.
- [ ] Add backend unit/integration, catalog consistency, frontend component, contract, and Playwright smoke tests.
- [ ] Run the complete local and Docker quality gates and inspect the final diff/security posture.
- [ ] Commit logical stages atomically and report all known limitations.

