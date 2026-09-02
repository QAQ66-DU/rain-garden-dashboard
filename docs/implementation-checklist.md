# Phase 0 and Phase 1 implementation checklist

This records the original baseline. The later confirmed-inventory alignment supersedes its
three-device synthetic inventory with eight end-device records, 20 configured Swale channels, and
one zero-channel Tree-pit probe whose configuration remains pending.

This checklist incorporates the approved architectural amendments. Unlisted later roadmap work remains explicitly excluded.

## Phase 0: foundation

- [x] Establish governance, requirements, assumptions, change protocol, ADRs, security policy, and threat model.
- [x] Establish pinned Python and Node dependency manifests and lockfiles.
- [x] Define repeatable format, lint, type-check, unit-test, integration-test, migration, build, contract, and end-to-end commands.
- [x] Create portable development and production Docker targets and a PostgreSQL 16 Compose service.
- [x] Configure a non-superuser application database role and fail-safe environment validation.
- [x] Create the metric catalog as the only editable metric/unit vocabulary.
- [x] Model Site, Device, SensorChannel, MetricDefinition, UplinkEvent, and Measurement with constraints and indexes.
- [x] Create and test the first Alembic migration against a fresh PostgreSQL database.
- [x] Add structured logging, correlation IDs, safe API errors, CORS, security headers, body limits, and rate limiting.
- [x] Add an authenticated but disabled TTN endpoint without inventing payload fields.
- [x] Create the React shell, responsive navigation, error boundary, and typed API generation pipeline.
- [x] Add CI and explicit dependency/secret scanning gates.

## Phase 1: tested vertical slice

- [x] Generate a deterministic seven-day synthetic dataset at a one-hour generator cadence.
- [x] Seed one site, three devices, multiple sensor channels, missing intervals, a duplicate uplink, and one invalid observation.
- [x] Calculate unknown/online/stale/offline status from last-seen time, configurable thresholds, and an explicit reference time.
- [x] Implement sites, devices, measurements, and overview repositories/services/APIs.
- [x] Use cursor pagination, deterministic ordering, a seven-day default range, a 31-day maximum, and a 5,000-row raw-result ceiling.
- [x] Reject oversized result sets explicitly; never truncate or downsample silently.
- [x] Implement channel-aware soil-moisture min/median/max summaries with channel identity and timestamp range.
- [x] Build Overview, Devices, and Device Detail pages with loading, error, empty, missing, quality, and synthetic-data states.
- [x] Render a single-series time line with at least eight observations when available; show the selected channel, metric, unit, range, and source status.
- [x] Add backend unit/integration, catalog consistency, frontend component, contract, and Playwright smoke tests.
- [x] Run the complete local and Docker quality gates and inspect the final diff/security posture.
- [x] Commit logical stages atomically and report all known limitations.

## Approved post-baseline extensions

- [x] Repair the reproducible ignored-artifact Prettier workflow and recreate the ignored backend environment from `uv.lock`.
- [x] Align the confirmed Orchard Park inventory while keeping all observations synthetic and the existing local demo database untouched.
- [x] Separate nullable physical-unit mapping from `pending`, `confirmed`, and `synthetic_demo_only` provenance.
- [x] Add the site-wide Time Explorer with URL-persisted periods and filters, synchronized
      unit-separated small multiples, and current-versus-historical status separation; site-wide
      flagged-observation detail is presented on Overview.
- [x] Implement schedule-aligned half-open coverage with duplicate, flagged, missing, late, and out-of-tolerance semantics plus an unavailable state for unknown schedules.
- [x] Restrict rainfall duration above zero to periods with known cadence and complete valid coverage.
