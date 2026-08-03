# Live TTN MQTT development worker

The live MQTT path is an explicitly started development worker for the single approved `Outflow A`
TTN Testbed device. It is not part of the normal Docker Compose startup and it does not change the
existing TTN Console configuration, Google Sheets webhook, FastAPI webhook scaffold, or Orchard
Park inventory.

## Architecture and data flow

1. The dedicated `ttn-mqtt-worker` container opens a TLS-authenticated MQTT 3.1.1 connection to the
   configured TTN cluster.
2. It subscribes only to `v3/rain-garden@ttn/devices/outflow-a/up`.
3. Each message must be a UTF-8 JSON TTN ApplicationUp object. The adapter does not expect the
   outer TTN Live Data console-export event wrapper.
4. The ApplicationUp object enters the shared Outflow A normaliser and persistence service.
5. A database transaction privately stores the raw ApplicationUp, creates unverified unitless
   measurements when decoding is valid, updates testbed telemetry, and applies the existing
   deterministic idempotency rule. Unsafe mapped JSON is retained in private quarantine; malformed
   non-JSON messages are discarded without terminating the worker or logging their content.

The worker uses bounded MQTT reconnect delays from 1 to 30 seconds and handles `SIGINT`/`SIGTERM`
for a clean disconnect. It never logs the MQTT password or complete connection credentials.

## Local configuration

Copy `.env.example` to the ignored repository-root `.env` as described in the README. These are the
only MQTT settings:

```dotenv
TTN_MQTT_HOST=eu1.cloud.thethings.network
TTN_MQTT_PORT=8883
TTN_MQTT_USERNAME=rain-garden@ttn
TTN_MQTT_TOPIC=v3/rain-garden@ttn/devices/outflow-a/up
TTN_MQTT_API_KEY=
```

Keep the complete read-only TTN Application API key only in the ignored local `.env`; never put it
in `.env.example`, source code, logs, screenshots, or Git. The worker fails clearly if the key is
blank, while the normal database, backend, frontend, tests, and offline replay continue to work.

## Start and stop

After manually adding the read-only key to `.env`, start only the profile-gated worker and its
database dependency:

```bash
docker compose --profile live up --build ttn-mqtt-worker
```

Stop it cleanly from another terminal:

```bash
docker compose --profile live stop ttn-mqtt-worker
```

Do not run the live profile against a database containing synthetic Orchard Park observations for a
real-data trial. Use the separately approved inventory-only clean database required by the project
handoff before activation.

## Confirm private storage without printing raw uplinks

After TTN has delivered a new Outflow A uplink, run this local aggregate query. It reports only the
count and latest receipt time, not raw payloads or external identifiers:

```bash
docker compose exec db sh -lc 'psql -U "$POSTGRES_USER" -d "$APP_DB_NAME" -c "SELECT COUNT(*) AS mqtt_raw_uplinks, MAX(ue.received_at) AS latest_received_at FROM uplink_events ue JOIN devices d ON d.id = ue.device_id WHERE ue.source = '\''ttn_mqtt'\'' AND d.display_name = '\''Outflow A'\'' AND d.is_test_device = true;"'
```

This preparation does not configure TTN, alter the existing Google Sheets webhook, send downlinks,
or subscribe to any other device.
