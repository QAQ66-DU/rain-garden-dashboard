# Offline TTN replay

The offline replay is a local, file-driven verification path for the `outflow-a` TTN Live Data
console export. It is not a live TTN connection and does not enable the disabled webhook endpoint or
implement MQTT.

## Running the replay

Keep the validated full export at the ignored local path
`backend/tests/fixtures/ttn/outflow-a-live-data.json`, apply migrations through `0004`, and run from
the repository root:

```bash
docker compose run --rm backend uv run python -m app.scripts.replay_ttn_export \
  tests/fixtures/ttn/outflow-a-live-data.json
```

No TTN API key is required. The command reads one local file and makes no network request to TTN. It
does not modify the TTN application, device settings, payload formatter, downlink settings, MQTT
configuration, or the existing Google Sheets webhook.

The command reports total console records, selected uplinks, raw inserts, duplicates, normalized
measurements, invalid decoded uplinks preserved without measurements, status blocks, quarantine
records, and failures. Replaying the same export again must insert no raw events or measurements and
must report every selected uplink as a duplicate.

## Selection and data flow

Only events named `as.up.data.forward` are candidates. Network Server processing events, downlink
attempts, webhook failures, connection-status events, and all other console records are ignored for
ingestion.

The implementation separates:

1. `parse_console_export_event(event)`, which handles the console wrapper and event selection;
2. `normalise_application_up(payload)`, which accepts the top-level ApplicationUp shape and can be
   reused by a future separately approved webhook or MQTT adapter;
3. `persist_ttn_uplink(normalised_event)`, which preserves raw data, applies the approved device
   mapping, and writes normalized testbed records; and
4. the local replay command, which reads the file and reports outcomes.

The replay upserts one `outflow-a` test device under the separate `TTN proxy network` site and monitoring
feature. It never associates the device with Orchard Park. Orchard Park Overview, Explorer, device
counts, availability, quality warnings, and summaries remain site-scoped and unchanged.

## Measurement and timestamp semantics

Decoder measurement ID 1 maps to `Outflow A (Total)` in mL and ID 2 maps to `Outflow A` in mL/hour,
using the supplied sensor metadata rather than the decoder label alone. Their stored unit
confirmation and verification statuses are `confirmed` and `catalogued`. Successfully decoded,
mapped, finite numeric values are marked `valid`. Basic count, latest, minimum, median, and maximum
summaries remain numeric descriptions only; the replay performs no calibration, unit conversion,
or hydrological performance interpretation.

Normalized values are created only when the decoder says `valid: true` and `err: 0`. Invalid or
malformed decoded content is still preserved privately but creates no normalized measurements. The
export contains no device measurement timestamp, so this isolated operational view uses the source
TTN `received_at` as its explicit timestamp basis. It does not claim that receipt time is a confirmed
scientific sampling time.

Battery, firmware, hardware, and decoder interval values are kept in separate operational telemetry,
not fake measurement channels. The interval value has no displayed time unit because the supplied
evidence does not confirm one. Device freshness uses the latest replayed dataset timestamp and the
UI states `Status basis: Replay dataset reference time`.

## Privacy, preservation, and duplicates

The full selected console event is retained in private JSONB before transformation. Public schemas
do not expose raw JSON, external application/device identifiers, DevEUI, JoinEUI, session-key IDs,
uplink tokens, correlations, or exact gateway identifiers. The UI uses a gateway alias indicating
that an identifier was recorded and withheld.

Known-device invalid decodes are stored as rejected raw uplinks with a controlled error code.
Selected events that cannot be safely parsed or mapped are stored in the private replay quarantine.
Logs and command summaries contain counts and controlled outcomes only, never complete payloads or
private identifiers.

Idempotency hashes the approved identity tuple `(application ID, device ID, session key ID, f_port,
f_cnt)` and uses the existing unique `(source, idempotency_key)` database constraint. Measurements
also use deterministic identifiers and retain event/channel uniqueness.

The full export and reference decoder remain ignored, read-only local fixtures because they contain
private TTN identifiers and the export is too large for normal source control. Automated tests use
`outflow-a-redacted.json`, a four-event derivative with stable synthetic identifiers. Its invalid
case is an explicitly documented test mutation because the supplied export contains no invalid
forwarded uplink.

## What remains unimplemented

The offline command never starts a live connection. A separate profile-gated MQTT development
worker now accepts the eight explicitly mapped application devices, while the live webhook, production authentication,
retention policy, and confirmed scientific payload mapping remain unimplemented. Controlled live
use still requires confirmed fields, quantities, units, scaling and signedness, timestamp rules,
reporting schedules, sensor specifications, key rotation, and a clean inventory-only database.
