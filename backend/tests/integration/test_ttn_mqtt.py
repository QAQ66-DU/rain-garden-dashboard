import copy
import json
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from app.db.repositories.ttn_replay import (
    LIVE_MQTT_CONTEXT,
    LIVE_MQTT_SOURCE,
    OFFLINE_REPLAY_CONTEXT,
    TTN_TESTBED_SITE_NAME,
)
from app.db.seed import SITE_ID
from app.db.seed_ttn_proxy import seed_ttn_proxy_inventory
from app.ingestion.ttn_devices import TTN_PROXY_DEVICE_IDS
from app.ingestion.ttn_mqtt import MQTTMessageProcessor
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.sensor_channel import SensorChannel
from app.models.site import Site
from app.models.ttn_replay_quarantine import TTNReplayQuarantine
from app.models.uplink_event import UplinkEvent
from app.services.ttn_ingestion import TTNIngestionService, ingest_ttn_application_up
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parents[1] / "fixtures" / "ttn" / "outflow-a-redacted.json"


def _approved_application_up() -> dict[str, Any]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    application_up = copy.deepcopy(fixture["events"][0]["data"])
    identifiers = application_up["end_device_ids"]
    identifiers["device_id"] = "outflow-a"
    identifiers["application_ids"]["application_id"] = "rain-garden"
    return cast(dict[str, Any], application_up)


def test_proxy_inventory_seed_is_idempotent_and_creates_no_observations(
    db_session: Session,
) -> None:
    raw_before = db_session.scalar(select(func.count()).select_from(UplinkEvent)) or 0
    measurements_before = db_session.scalar(select(func.count()).select_from(Measurement)) or 0

    seed_ttn_proxy_inventory(db_session)
    seed_ttn_proxy_inventory(db_session)
    db_session.flush()

    assert (
        db_session.scalar(
            select(func.count()).select_from(Device).where(Device.environment == "proxy")
        )
        == 8
    )
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SensorChannel)
            .join(Device, Device.id == SensorChannel.device_id)
            .where(Device.environment == "proxy", SensorChannel.active.is_(True))
        )
        == 24
    )
    assert db_session.scalar(select(func.count()).select_from(UplinkEvent)) == raw_before
    assert db_session.scalar(select(func.count()).select_from(Measurement)) == measurements_before


@pytest.mark.parametrize(
    ("device_id", "measurement_count"),
    [
        ("soil-moisture-1", 1),
        ("weather-station-2", 8),
        ("weather-station", 8),
        ("ph-sensor", 2),
        ("soilmoisture-temp-sensor", 3),
    ],
)
def test_each_supplied_formatter_shape_persists_idempotently(
    db_session: Session,
    device_id: str,
    measurement_count: int,
) -> None:
    fixture_path = FIXTURE.parent / f"{device_id}-redacted.json"
    application_up = json.loads(fixture_path.read_text(encoding="utf-8"))
    existing_device = db_session.scalar(
        select(Device).where(Device.external_device_id == device_id)
    )
    measurements_before = (
        db_session.scalar(
            select(func.count())
            .select_from(Measurement)
            .where(Measurement.device_id == existing_device.id)
        )
        if existing_device is not None
        else 0
    ) or 0

    first = ingest_ttn_application_up(
        db_session,
        application_up,
        raw_event=application_up,
        context=LIVE_MQTT_CONTEXT,
    )
    second = ingest_ttn_application_up(
        db_session,
        application_up,
        raw_event=application_up,
        context=LIVE_MQTT_CONTEXT,
    )
    db_session.flush()

    assert first.outcome == "inserted"
    assert first.measurements_created == measurement_count
    assert second.outcome == "duplicate"
    device = db_session.scalar(select(Device).where(Device.external_device_id == device_id))
    assert device is not None
    assert device.environment == "proxy"
    assert device.provenance == "proxy"
    assert (
        db_session.scalar(
            select(func.count()).select_from(Measurement).where(Measurement.device_id == device.id)
        )
        == measurements_before + measurement_count
    )
    inserted_event = db_session.scalar(
        select(UplinkEvent).where(
            UplinkEvent.device_id == device.id,
            UplinkEvent.source == LIVE_MQTT_SOURCE,
            UplinkEvent.frame_counter == application_up["uplink_message"]["f_cnt"],
        )
    )
    assert inserted_event is not None
    inserted_measurements = list(
        db_session.scalars(
            select(Measurement).where(
                Measurement.device_id == device.id,
                Measurement.uplink_event_id == inserted_event.id,
            )
        )
    )
    assert len(inserted_measurements) == measurement_count
    assert all(item.quality_flag == "valid" for item in inserted_measurements)
    assert all(item.quality_notes is None for item in inserted_measurements)


def test_default_api_exposes_exactly_the_eight_proxy_devices(
    api_client: TestClient,
    db_session: Session,
) -> None:
    application_up = _approved_application_up()
    result = ingest_ttn_application_up(
        db_session,
        application_up,
        raw_event=application_up,
        context=LIVE_MQTT_CONTEXT,
    )
    db_session.flush()
    assert result.outcome == "inserted"

    devices = api_client.get("/api/v1/devices", params={"page_size": 100})
    assert devices.status_code == 200
    body = devices.json()
    assert {item["display_name"] for item in body["items"]} == set(TTN_PROXY_DEVICE_IDS)
    assert len(body["items"]) == 8
    assert all(item["environment"] == "proxy" for item in body["items"])

    sites = api_client.get("/api/v1/sites", params={"page_size": 100})
    assert sites.status_code == 200
    assert [item["name"] for item in sites.json()["items"]] == [TTN_TESTBED_SITE_NAME]

    overview = api_client.get("/api/v1/overview")
    assert overview.status_code == 200
    assert overview.json()["devices"]["total"] == 8
    assert overview.json()["site_name"] == TTN_TESTBED_SITE_NAME
    assert "not deployed at Orchard Park" in overview.json()["synthetic_notice"]

    proxy_channels = db_session.scalar(
        select(func.count())
        .select_from(SensorChannel)
        .join(Device, Device.id == SensorChannel.device_id)
        .where(Device.environment == "proxy", SensorChannel.active.is_(True))
    )
    assert proxy_channels == 24
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SensorChannel)
            .join(Device, Device.id == SensorChannel.device_id)
            .where(Device.environment == "proxy", SensorChannel.unit_code.is_not(None))
        )
        == 0
    )

    orchard = api_client.get("/api/v1/overview", params={"site_id": str(SITE_ID)})
    assert orchard.status_code == 200
    assert orchard.json()["devices"]["total"] == 8


def test_unknown_application_device_is_quarantined_without_measurements(
    db_session: Session,
) -> None:
    application_up = _approved_application_up()
    application_up["end_device_ids"]["device_id"] = "unknown-device"

    result = ingest_ttn_application_up(
        db_session,
        application_up,
        raw_event=application_up,
        context=LIVE_MQTT_CONTEXT,
    )
    db_session.flush()

    assert result.outcome == "quarantined"
    quarantine = db_session.scalar(
        select(TTNReplayQuarantine).where(TTNReplayQuarantine.source == LIVE_MQTT_SOURCE)
    )
    assert quarantine is not None
    assert quarantine.failure_code == "unknown_ttn_device"


def test_mocked_live_mqtt_uplink_is_idempotent_and_isolated(
    api_client: TestClient,
    db_session: Session,
) -> None:
    application_up = _approved_application_up()
    application_up["received_at"] = "2098-08-03T16:11:01Z"
    application_up["uplink_message"]["session_key_id"] = "integration-mqtt-idempotency"
    application_up["uplink_message"]["f_cnt"] = 900_001
    message = SimpleNamespace(payload=json.dumps(application_up).encode())

    existing_outflow = db_session.scalar(
        select(Device).where(Device.external_device_id == "outflow-a")
    )
    raw_before = (
        db_session.scalar(
            select(func.count())
            .select_from(UplinkEvent)
            .where(
                UplinkEvent.device_id == existing_outflow.id,
                UplinkEvent.source == LIVE_MQTT_SOURCE,
            )
        )
        if existing_outflow is not None
        else 0
    ) or 0
    measurements_before = (
        db_session.scalar(
            select(func.count())
            .select_from(Measurement)
            .where(Measurement.device_id == existing_outflow.id)
        )
        if existing_outflow is not None
        else 0
    ) or 0
    warnings_before = (
        db_session.scalar(
            select(func.count())
            .select_from(Measurement)
            .join(Device, Device.id == Measurement.device_id)
            .where(Device.environment == "proxy", Measurement.quality_flag != "valid")
        )
        or 0
    )

    @contextmanager
    def session_scope() -> Generator[Session]:
        yield db_session

    processor = MQTTMessageProcessor(TTNIngestionService(session_scope))
    first = processor.process(message.payload)
    db_session.flush()
    second = processor.process(message.payload)
    db_session.flush()

    assert first is not None
    assert first.outcome == "inserted"
    assert first.measurements_created == 2
    assert second is not None
    assert second.outcome == "duplicate"
    assert second.measurements_created == 0

    testbed = db_session.scalar(select(Site).where(Site.name == TTN_TESTBED_SITE_NAME))
    assert testbed is not None
    outflow = db_session.scalar(
        select(Device).where(
            Device.site_id == testbed.id,
            Device.external_device_id == "outflow-a",
        )
    )
    assert outflow is not None
    assert outflow.display_name == "outflow-a"
    assert outflow.is_test_device is True
    assert db_session.scalar(select(func.count()).select_from(Device)) == 16
    proxy_ids = set(
        db_session.scalars(select(Device.external_device_id).where(Device.site_id == testbed.id))
    )
    assert proxy_ids == set(TTN_PROXY_DEVICE_IDS)
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(UplinkEvent)
            .where(
                UplinkEvent.device_id == outflow.id,
                UplinkEvent.source == LIVE_MQTT_SOURCE,
            )
        )
        == raw_before + 1
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(Measurement).where(Measurement.device_id == outflow.id)
        )
        == measurements_before + 2
    )
    stored = db_session.scalar(
        select(UplinkEvent).where(
            UplinkEvent.device_id == outflow.id,
            UplinkEvent.source == LIVE_MQTT_SOURCE,
            UplinkEvent.frame_counter == 900_001,
        )
    )
    assert stored is not None
    new_measurements = list(
        db_session.scalars(select(Measurement).where(Measurement.uplink_event_id == stored.id))
    )
    assert len(new_measurements) == 2
    assert all(item.quality_flag == "valid" for item in new_measurements)
    assert all(item.quality_notes is None for item in new_measurements)
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(Measurement)
            .join(Device, Device.id == Measurement.device_id)
            .where(Device.environment == "proxy", Measurement.quality_flag != "valid")
        )
        == warnings_before
    )
    assert stored.raw_payload == application_up
    assert "name" not in stored.raw_payload

    explorer = api_client.get(
        "/api/v1/explore",
        params={
            "start": "2098-08-03T16:00:00Z",
            "end": "2098-08-03T17:00:00Z",
            "metric_group": "operational",
        },
    )
    assert explorer.status_code == 200
    explorer_body = explorer.json()
    assert explorer_body["quality_warnings"] == []
    outflow_series = [
        item for item in explorer_body["series"] if item["channel"]["device_name"] == "outflow-a"
    ]
    assert len(outflow_series) == 2
    assert all(item["channel"]["verification_status"] == "unverified" for item in outflow_series)
    assert all(item["channel"]["unit_confirmation_status"] == "pending" for item in outflow_series)
    assert all(
        [statistic["code"] for statistic in item["summary"]["statistics"]]
        == ["latest", "count", "minimum", "median", "maximum"]
        for item in outflow_series
    )

    orchard = api_client.get("/api/v1/overview", params={"site_id": str(SITE_ID)})
    assert orchard.status_code == 200
    assert orchard.json()["devices"]["total"] == 8
    assert orchard.json()["reference_time"].startswith("2026-06-01T12:00:00")


def test_replay_and_live_mqtt_share_chronological_utc_history(
    api_client: TestClient,
    db_session: Session,
) -> None:
    replay_up = _approved_application_up()
    replay_up["received_at"] = "2025-08-03T18:38:53.442428Z"
    replay_up["uplink_message"]["session_key_id"] = "integration-shared-history"
    replay_up["uplink_message"]["f_cnt"] = 900_010
    live_up = copy.deepcopy(replay_up)
    live_up["received_at"] = "2025-08-04T18:38:53.442428Z"
    live_up["uplink_message"]["f_cnt"] += 1

    live_result = ingest_ttn_application_up(
        db_session,
        live_up,
        raw_event=live_up,
        context=LIVE_MQTT_CONTEXT,
    )
    replay_result = ingest_ttn_application_up(
        db_session,
        replay_up,
        raw_event=replay_up,
        context=OFFLINE_REPLAY_CONTEXT,
    )
    duplicate_result = ingest_ttn_application_up(
        db_session,
        live_up,
        raw_event=live_up,
        context=LIVE_MQTT_CONTEXT,
    )
    db_session.flush()

    assert replay_result.outcome == "inserted"
    assert live_result.outcome == "inserted"
    assert duplicate_result.outcome == "duplicate"
    assert duplicate_result.measurements_created == 0

    outflow = db_session.scalar(select(Device).where(Device.external_device_id == "outflow-a"))
    assert outflow is not None
    detail = api_client.get(f"/api/v1/devices/{outflow.id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["ingestion_mode"] == "live_mqtt"
    assert detail_body["provenance"] == "proxy"
    assert detail_body["freshness"]["status_basis"] == "live_mqtt_reference_time"
    channel_id = next(
        channel["id"]
        for channel in detail_body["channels"]
        if channel["channel_code"] == "outflow_measurement_1"
    )

    history = api_client.get(
        f"/api/v1/devices/{outflow.id}/measurements",
        params={
            "start": "2025-08-03T00:00:00Z",
            "end": "2025-08-05T00:00:00Z",
            "sensor_channel_id": channel_id,
            "page_size": 500,
        },
    )
    assert history.status_code == 200
    history_body = history.json()
    assert history_body["total_matching"] == 2
    timestamps = [item["measured_at"] for item in history_body["items"]]
    assert timestamps == sorted(timestamps)
    assert timestamps[-1] == "2025-08-04T18:38:53.442428Z"

    recent = api_client.get(
        f"/api/v1/devices/{outflow.id}/measurements",
        params={
            "start": "2025-08-04T18:38:53Z",
            "end": "2025-08-04T18:38:54Z",
            "sensor_channel_id": channel_id,
            "page_size": 500,
        },
    )
    assert recent.status_code == 200
    assert [item["measured_at"] for item in recent.json()["items"]] == [
        "2025-08-04T18:38:53.442428Z"
    ]
