# Requirements

## Purpose and users

The Rain Garden Monitoring Dashboard is a portable browser application for university researchers, supervisors, public-water and council stakeholders, and technical users monitoring LoRaWAN-enabled urban green infrastructure. It supports research inspection of observations and data quality; it is not a generic IoT console and must not fabricate hydrological conclusions.

## Phase 0 and Phase 1 functional scope

- Run through Docker on macOS, Windows, and Linux without host Python or Node.js.
- Store sites, devices, sensor channels, raw uplink events, normalized measurements, and quality metadata in PostgreSQL 16.
- Preserve raw synthetic uplinks privately while returning only public, normalized schemas.
- Display Overview, Devices, and Device Detail pages.
- Show synthetic provenance, last update, device freshness, units, missing states, and quality warnings.
- Provide a selectable channel-aware time-series chart with a bounded raw query.
- Search/filter devices by public attributes.
- Seed at least seven deterministic days for one site and three devices.
- Expose versioned read-only REST endpoints and an authenticated but disabled TTN scaffold.

## Measurement query contract

- Default range: seven days ending at the explicit dataset reference time in demo mode.
- Maximum range: 31 days.
- Ordering: ascending `(measured_at, id)`.
- Pagination: opaque cursor; no offset pagination.
- Maximum matching raw result set: 5,000 rows, checked before page delivery.
- Oversized matching sets produce an explicit validation error; they are never truncated or downsampled.

## Soil-moisture summary

Phase 1 does not combine channels into a mean. It returns the latest valid observation per contributing comparable metric channel, their minimum, median, maximum, channel count, channel identifiers/metadata, and timestamp range. It does not claim that depths or positions are scientifically interchangeable.

## Non-functional requirements

- Strict TypeScript, Pydantic v2, SQLAlchemy 2, Alembic, deterministic UTC data, pinned dependencies, lockfiles, and CI.
- Accessible semantic HTML, responsive layout, keyboard-operable controls, clear focus styles, and non-color status cues.
- Safe configuration, bounded requests, public-data minimization, stable API errors, and no secret/payload leakage.
- OpenAPI is the API contract source; generated frontend types must be current.
- The metric catalog, database catalog, and generated data dictionary must reconcile automatically.

## Explicit non-goals

Real TTN payload mapping, threshold editing, shared distributed rate limiting, authentication/user management, maps, public coordinates, CSV export, alert evaluation, mass balance, evapotranspiration, event analytics, anomaly detection, machine learning, camera data, image recognition, and deployment to a vendor-specific platform are not implemented.

## Future scope

Real TTN integration, richer quality monitoring, safe CSV export, scientifically approved rainfall-event analytics, authenticated production deployment, backups, and stakeholder evaluation require separate approval.
