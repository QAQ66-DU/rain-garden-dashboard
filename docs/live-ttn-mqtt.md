# Live TTN MQTT development worker

The live MQTT path is an explicitly started worker for exactly eight approved proxy device IDs in
the `rain-garden` TTN application. These devices are not deployed at Orchard Park. The worker is not
part of normal Docker Compose startup and does not change TTN Console, the Google Sheets webhook,
the FastAPI webhook scaffold, or the separate Orchard Park demo inventory.

## Architecture and data flow

1. The dedicated `ttn-mqtt-worker` container opens a TLS-authenticated MQTT 3.1.1 connection to the
   configured TTN cluster.
2. It subscribes to `v3/rain-garden@ttn/devices/+/up` and the shared ingestion service rejects and
   quarantines any device ID outside the eight-entry allowlist.
3. Each message must be a UTF-8 JSON TTN ApplicationUp object. The adapter does not expect the
   outer TTN Live Data console-export event wrapper.
4. The ApplicationUp object enters the transport-independent shared normaliser and persistence
   service, which selects the device-specific evidence-backed mapping.
5. A database transaction privately stores the raw ApplicationUp, creates unverified unitless
   measurements when decoding is valid, updates testbed telemetry, and applies the existing
   deterministic idempotency rule. Unsafe mapped JSON is retained in private quarantine; malformed
   non-JSON messages are discarded without terminating the worker or logging their content.

The scientific query axis is UTC `measured_at`. The reviewed payloads have no separate, verified
device observation timestamp, so the adapter currently uses the TTN ApplicationUp
`received_at` timestamp. A future verified device/application observation field would take
precedence only through an explicitly reviewed payload mapping; otherwise this fallback remains.

The worker uses bounded MQTT reconnect delays from 1 to 30 seconds and handles `SIGINT`/`SIGTERM`
for a clean disconnect. Compose restarts it unless it is explicitly stopped. It never logs the MQTT
password or complete connection credentials.

## Local configuration

Copy `.env.example` to the ignored repository-root `.env` as described in the README. These are the
only MQTT settings:

```dotenv
TTN_MQTT_HOST=eu1.cloud.thethings.network
TTN_MQTT_PORT=8883
TTN_MQTT_USERNAME=rain-garden@ttn
TTN_MQTT_TOPIC=v3/rain-garden@ttn/devices/+/up
TTN_MQTT_API_KEY=
```

Keep the complete read-only TTN Application API key only in the ignored local `.env`; never put it
in `.env.example`, source code, logs, screenshots, or Git. The worker fails clearly if the key is
blank, while the normal database, backend, frontend, tests, and offline replay continue to work.
Run `python -m app.db.seed_ttn_proxy` through Compose to create the same inventory without starting
MQTT or creating observations; the worker repeats this idempotent inventory step at startup.

## Start and stop

After manually adding the read-only key to `.env`, start only the profile-gated worker and its
database dependency:

```bash
docker compose --profile live up --build -d ttn-mqtt-worker
```

The dashboard polls its active live queries every 30 seconds while the page is open and visible.
Background refreshes preserve cached data if one request fails; the browser does not reload the
page or change the selected channel.

Stop it cleanly from another terminal:

```bash
docker compose --profile live stop ttn-mqtt-worker
```

Do not run the live profile against a database containing synthetic Orchard Park observations for a
real-data trial. Use the separately approved inventory-only clean database required by the project
handoff before activation.

## Confirm private storage without printing raw uplinks

After TTN has delivered new uplinks, use a local aggregate database query that reports only counts,
approved public device IDs, and latest receipt times. Never select `raw_payload`, decoded JSON,
session identifiers, DevEUIs, gateway IDs, or credentials.

The approved public IDs are `outflow-a`, `soil-moisture-1`, `prototype-board-1`,
`weather-station-2`, `weather-station`, `vision-ai`, `ph-sensor`, and
`soilmoisture-temp-sensor`. `vision-ai` has no supplied formatter or uplink evidence and remains
`Never seen / No data` with zero channels. No physical unit is confirmed by this integration.

| Device                     | Evidence-backed measurement mapping                                                                                                                                  | Remaining uncertainty          |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `outflow-a`                | IDs 1 and 2, generic `Measurement` fields                                                                                                                            | Meaning and units pending      |
| `soil-moisture-1`          | ID 1, generic `Measurement` field                                                                                                                                    | Meaning and unit pending       |
| `prototype-board-1`        | No observed uplink; zero channels                                                                                                                                    | Payload and channels pending   |
| `weather-station-2`        | Air Temperature 4097, Air Humidity 4098, Light Intensity 4099, UV Index 4190, Wind Speed 4105, Wind Direction Sensor 4104, Rain Gauge 4113, Barometric Pressure 4101 | All physical units pending     |
| `weather-station`          | Same eight decoder-labelled fields as `weather-station-2`                                                                                                            | All physical units pending     |
| `vision-ai`                | No formatter or observed uplink; zero channels                                                                                                                       | Entire payload mapping pending |
| `ph-sensor`                | Generic telemetry IDs 4097 and 4106                                                                                                                                  | Meanings and units pending     |
| `soilmoisture-temp-sensor` | Generic telemetry IDs 4102, 4103, and 4108                                                                                                                           | Meanings and units pending     |

This integration does not configure TTN, alter the existing Google Sheets webhook, send downlinks,
use the TTN Storage API, or backfill the supplied console exports.
