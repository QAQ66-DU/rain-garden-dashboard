# Assumptions and unresolved questions

Every assumption is visible and replaceable; none should be mistaken for a confirmed site or sensor property.

## Confirmed inventory and demo assumptions

- Orchard Park, Edinburgh, has confirmed Swale and Tree-pit monitoring features and eight
  sensor/end-device reference locations. Their approved reference coordinates are deliberately
  published in the frontend map, separately from private device records and live proxy identities.
- The outdoor LoRaWAN gateway is network infrastructure, not a sensor/end device, and is excluded from monitored-device counts.
- Generated timestamps and values use a fixed UTC anchor, fixed random seed, and one-hour demo cadence.
- The one-hour cadence is not a claim about real equipment.
- Status is calculated at the dataset reference time with configurable 90-minute stale and 180-minute offline demo defaults.
- The public raw-measurement query defaults to seven days, permits at most 31 days, and rejects matching sets above 5,000 rows.
- Device Detail and Explore visualizations use the same configurable 2,000-point per-series display
  target and deterministic real-point selector. Explore summaries and coverage still use every
  matching observation; complete Device Detail normalized observations remain available through
  streamed CSV export.
- In-memory rate limiting is acceptable only for a single process; a reverse proxy/shared limiter is required for horizontal scaling.
- The future webhook boundary remains disabled and secret-authenticated. Live MQTT ingestion is an
  explicit Compose profile with a local ignored API key and an eight-device mapping allowlist.
- No software licence is added until university and partner intellectual-property ownership is confirmed.
- The reviewed `outflow-a` console export is approved only for an isolated local replay testbed.
  Supplied metadata confirms ID 1 as total volume in mL and ID 2 as volumetric rate in mL/hour;
  calibration and scientific timestamp semantics remain unconfirmed.

## Scientific limits

- Metric names and physical-unit codes are controlled separately. Demo-normalised units are
  `synthetic_demo_only`; live units are confirmed only for the reviewed device-and-measurement-ID
  mappings. Sensor accuracy, calibration, operating ranges, sampling schedules, depth comparability,
  performance thresholds, and all remaining mappings are not confirmed.
- Only definition-level physical bounds, such as relative humidity not exceeding 100%, may create an initial out-of-range flag.
- Synthetic variation is illustrative and is not a rainfall-runoff model or evidence of system performance.
- Soil-moisture values from different depths or positions are not averaged. Phase 1 reports their spread and channel identities.
- Missing observations are absent records, never implicit zeros.
- Time Explorer windows are half-open UTC intervals `[start, end)` and are displayed in `Europe/London`; daylight-saving conversion changes labels, not scientific timestamps or slot membership.
- The deterministic dataset explicitly anchors hourly expected slots at `2026-05-25T12:00:00Z` with a five-minute timestamp-jitter tolerance. These settings support reproducible demo coverage only and must not be promoted to confirmed deployed-device schedules.
- Coverage percentage is received unique schedule slots divided by expected schedule slots. Flagged slots count as received but not valid; duplicate, late, and out-of-tolerance observations are labelled separately. Coverage is unavailable when schedule inputs are unknown.
- Rainfall-intensity duration above zero is a cadence-based period summary, not rainfall-event analysis, and is unavailable unless every expected slot is valid and in tolerance.

## Unresolved questions for later phases

- Exact device model/specification, remaining field meanings, scale interpretation, frame-counter
  reset behavior, reporting schedules, and unresolved unit declarations for the live proxy and
  Orchard Park inventories.
- The tree-pit probe's number of depth channels, installation depths/spacing, payload mapping, and which channels may be compared scientifically.
- Water-level reference/datum, confirmed reporting schedules, configurable jitter tolerances for real devices, data retention, backup, and deletion policy.
- Scientifically justified validity, stale/offline, rainfall-event, response, and recovery thresholds.
- OIDC provider or authenticated reverse proxy, deployment environment, TLS termination, shared rate limiting, and audit requirements.
- Software licensing and intellectual-property ownership.
