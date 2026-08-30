# Requirements

## Purpose and users

The Rain Garden Monitoring Dashboard is a portable browser application for university researchers, supervisors, public-water and council stakeholders, and technical users monitoring LoRaWAN-enabled urban green infrastructure. It supports research inspection of observations and data quality; it is not a generic IoT console and must not fabricate hydrological conclusions.

## Completed baseline and confirmed-inventory scope

- Run through Docker on macOS, Windows, and Linux without host Python or Node.js.
- Store sites, devices, sensor channels, raw uplink events, normalized measurements, and quality metadata in PostgreSQL 16.
- Preserve raw synthetic uplinks privately while returning only public, normalized schemas.
- Display Overview, Explore, Devices, and Device Detail pages.
- Show synthetic provenance, last update, device freshness, units, missing states, and quality warnings.
- Provide a selectable channel-aware time-series chart that returns every matching observation
  below its display threshold and deterministic representative real observations above it.
- Search/filter devices by public attributes.
- Present device source, operational freshness, last receipt, configuration completeness, and
  active-channel unit confirmation as separate inventory fields; never collapse them into one
  ambiguous status.
- Show an interactive Overview map of the eight confirmed Orchard Park sensor locations as
  status-neutral reference markers, with sensor-type differentiation and no inferred TTN mapping.
- Represent the confirmed Orchard Park inventory as eight sensor/end devices grouped under Swale and Tree pit; exclude the outdoor gateway from monitored-device counts.
- Seed at least seven deterministic days for the seven configured swale devices. Keep the tree-pit probe at zero channels and observations until its depth/channel configuration is confirmed.
- Expose versioned read-only REST endpoints and an authenticated but disabled TTN scaffold.
- Support an isolated, local-only offline replay of the reviewed `outflow-a` console export under a
  separate proxy site, while keeping physical meanings and units explicitly unverified.
- Provide an explicitly started, TLS-only MQTT worker for application-wide uplinks, with exactly
  eight approved proxy device IDs, an absent-by-default password, and normal Compose startup
  unaffected.
- Make the eight proxy devices the normal dashboard inventory while excluding the synthetic Orchard
  Park dataset from default live API/UI queries. Preserve the deterministic demo seed separately.
- Provide shareable Device Detail 24-hour, 7-day, 30-day, and custom UTC ranges plus a bounded CSV
  export containing only the selected device, channel, period, normalized values, and reviewed
  interpretation/provenance fields.

## Measurement query contract

- Default range: seven days ending at the explicit dataset reference time in demo mode.
- Maximum range: 31 days.
- Ordering: ascending `(measured_at, id)`.
- Pagination: opaque cursor; no offset pagination.
- Maximum matching raw result set: 5,000 rows, checked before page delivery.
- Oversized raw pagination requests produce an explicit validation error; they are never silently
  truncated or treated as a complete export.
- The single-channel Device Detail chart endpoint returns all points below a configurable 2,000-point
  display target. Above that target it preserves the first and last observations and chronological
  time-bucket minima/maxima, reports total matching and displayed counts, and never invents values
  or changes stored observations.
- Device Detail stores resolved `start` and `end` timestamps in the URL, displays controls in
  `Europe/London`, and sends UTC timestamps to the API using half-open `[start, end)` semantics.
- Device Detail CSV uses the same device/channel/window filters and streams the complete ordered
  normalized result independently of the chart display threshold and raw pagination ceiling. Empty
  periods return headers only; raw uplinks, credentials, external device and gateway identifiers,
  private coordinates, and private network metadata are excluded.
- Device Detail charts use the selected UTC `[start, end)` window as a numeric time-axis domain.
  Europe/London tick labels adapt from hour-level detail at 24 hours to day-level labels at 7 and
  30 days, while tooltips retain local date, year, and seconds.

## Site-wide Time Explorer

- Provide 24-hour, 7-day, 30-day, and custom periods using half-open UTC windows `[start, end)`; reject `start >= end` and periods longer than 31 days.
- Preserve `start`, `end`, feature, metric group, and explicit channel selection in the URL across relevant navigation.
- Display timestamps in the site `Europe/London` timezone while keeping `measured_at` as the scientific axis and `received_at` as separate transmission context, including daylight-saving transitions.
- Filter available devices, channels, charts, summaries, and warnings by monitoring feature; group channel availability by controlled hydrology, soil, weather, and operational/unverified metric groups.
- Keep metrics, units, depths, positions, and unit-confirmation provenance channel-specific. Never combine incompatible series; show compatible channels as synchronized small multiples with units on every panel.
- Return all chart observations when a channel is below the configurable display target. Above the
  target, independently select deterministic real first/last and time-bucket extrema per channel;
  report exact total and displayed counts per series and in aggregate without changing summaries,
  coverage calculations, or stored measurements.
- Calculate expected coverage from explicit reporting interval, schedule anchor, and configurable jitter tolerance. Count schedule-aligned slots inside the requested window rather than applying a rounded duration formula.
- Deduplicate observations by expected slot for coverage, allow one accepted observation per slot, count flagged accepted observations as received but not valid, label late/out-of-tolerance records, and preserve missing as distinct from zero.
- Return coverage as unavailable when interval, anchor, or jitter tolerance is unknown; do not infer a deployed reporting schedule from observations.
- Use metric-specific summaries and exclude flagged values. For mapped unverified numeric outputs,
  provide only count, latest, minimum, median, and maximum while retaining explicit metadata/unit
  warnings. Do not average wind direction or infer hydrological meaning. Report rainfall-intensity
  duration above zero only when cadence and complete valid coverage are sufficient.
- Keep current device freshness separate from selected-period coverage and provide a bounded,
  privacy-reviewed quality-flag summary on Overview using the same window as its quality KPI.

## Soil-moisture summary

Phase 1 does not combine channels into a mean. It returns the latest valid observation per contributing comparable metric channel, their minimum, median, maximum, channel count, channel identifiers/metadata, and timestamp range. It does not claim that depths or positions are scientifically interchangeable.

## Non-functional requirements

- Strict TypeScript, Pydantic v2, SQLAlchemy 2, Alembic, deterministic UTC data, pinned dependencies, lockfiles, and CI.
- Accessible semantic HTML, responsive layout, keyboard-operable controls, clear focus styles, and non-color status cues.
- Safe configuration, bounded requests, public-data minimization, stable API errors, and no secret/payload leakage.
- OpenAPI is the API contract source; generated frontend types must be current.
- The metric catalog, database catalog, and generated data dictionary must reconcile automatically.
- Metric and physical-unit catalogues are separate. A nullable `unit_code` is interpreted only
  through `unit_confirmation_status`. Real numeric ingestion requires an explicitly approved
  device/channel mapping, but pending scientific metadata or units do not by themselves make a
  successfully decoded finite observation suspect.
- Device-level unit summaries use stored active-channel `unit_confirmation_status` values only;
  they must not be inferred from device properties, measurements, payloads, or frontend logic.

## Explicit non-goals

Default-enabled worker startup, live webhook handling, TTN Storage API backfill, cloud deployment,
confirmed physical-unit mapping, threshold editing,
shared distributed rate limiting, authentication/user management, additional maps or unconfirmed public coordinates,
site-wide/bulk CSV export, alert evaluation, mass balance, evapotranspiration, event analytics, anomaly detection,
machine learning, camera data, image recognition, and deployment to a vendor-specific platform are
not implemented.

## Future scope

Controlled MQTT activation on an inventory-only database, confirmed physical payload mapping,
richer quality monitoring, scientifically approved rainfall-event analytics,
authenticated production deployment, backups, and stakeholder evaluation require separate approval.
