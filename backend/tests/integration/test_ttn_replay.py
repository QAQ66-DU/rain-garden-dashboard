import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.db.repositories.ttn_replay import REPLAY_SOURCE, TTN_TESTBED_SITE_NAME
from app.db.seed import SITE_ID, seed_session
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.sensor_channel import SensorChannel
from app.models.site import Site
from app.models.ttn_replay_quarantine import TTNReplayQuarantine
from app.models.uplink_event import UplinkEvent
from app.services.ttn_replay import replay_ttn_export
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration

REDACTED_FIXTURE = Path(__file__).parents[1] / "fixtures" / "ttn" / "outflow-a-redacted.json"


def _approved_replay_fixture(tmp_path: Path) -> Path:
    fixture = json.loads(REDACTED_FIXTURE.read_text(encoding="utf-8"))
    approved = copy.deepcopy(fixture)
    for index, event in enumerate(approved["events"]):
        if event.get("name") != "as.up.data.forward":
            continue
        identifiers = event["data"]["end_device_ids"]
        identifiers["device_id"] = "outflow-a"
        identifiers["application_ids"]["application_id"] = "rain-garden"
        event["data"]["received_at"] = f"2099-08-03T16:{10 + index:02d}:00Z"
        event["data"]["uplink_message"]["session_key_id"] = f"integration-offline-replay-{index}"
        event["data"]["uplink_message"]["f_cnt"] = 910_000 + index
    destination = tmp_path / "approved-redacted-replay.json"
    destination.write_text(json.dumps(approved), encoding="utf-8")
    return destination


def test_replay_is_deterministic_idempotent_and_isolated(
    db_session: Session, tmp_path: Path
) -> None:
    seed_session(db_session)
    fixture = _approved_replay_fixture(tmp_path)
    existing_outflow = db_session.scalar(
        select(Device).where(Device.external_device_id == "outflow-a")
    )
    raw_before = (
        db_session.scalar(
            select(func.count())
            .select_from(UplinkEvent)
            .where(UplinkEvent.device_id == existing_outflow.id)
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

    first = replay_ttn_export(db_session, fixture)
    db_session.flush()
    second = replay_ttn_export(db_session, fixture)
    db_session.flush()

    assert first.total_events == 4
    assert first.selected_uplinks == 3
    assert first.raw_inserted == 3
    assert first.measurements_created == 4
    assert first.invalid_preserved == 1
    assert first.status_processed == 1
    assert first.quarantined == first.failed == 0
    assert second.raw_inserted == 0
    assert second.duplicates_skipped == 3
    assert second.measurements_created == 0

    orchard_devices = db_session.scalar(
        select(func.count()).select_from(Device).where(Device.site_id == SITE_ID)
    )
    orchard_channels = db_session.scalar(
        select(func.count())
        .select_from(SensorChannel)
        .join(Device, Device.id == SensorChannel.device_id)
        .where(Device.site_id == SITE_ID)
    )
    assert (orchard_devices, orchard_channels) == (8, 20)

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
    channels = list(
        db_session.scalars(select(SensorChannel).where(SensorChannel.device_id == outflow.id))
    )
    assert sorted(channel.channel_code for channel in channels) == [
        "outflow_measurement_1",
        "outflow_measurement_2",
    ]
    assert all(channel.unit_code is None for channel in channels)
    assert all(channel.unit_confirmation_status == "pending" for channel in channels)
    assert all(channel.verification_status == "unverified" for channel in channels)
    assert (
        db_session.scalar(
            select(func.count()).select_from(UplinkEvent).where(UplinkEvent.device_id == outflow.id)
        )
        == raw_before + 3
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(Measurement).where(Measurement.device_id == outflow.id)
        )
        == measurements_before + 4
    )
    stored_events = list(
        db_session.scalars(
            select(UplinkEvent)
            .where(
                UplinkEvent.device_id == outflow.id,
                UplinkEvent.source == REPLAY_SOURCE,
                UplinkEvent.received_at >= datetime(2099, 8, 3, tzinfo=UTC),
            )
            .order_by(UplinkEvent.received_at)
        )
    )
    assert all(event.raw_payload["name"] == "as.up.data.forward" for event in stored_events)
    assert all(event.raw_payload["data"]["uplink_message"] for event in stored_events)
    stored_measurements = list(
        db_session.scalars(
            select(Measurement).where(
                Measurement.device_id == outflow.id,
                Measurement.measured_at >= datetime(2099, 8, 3, tzinfo=UTC),
            )
        )
    )
    event_times = {event.id: event.received_at for event in stored_events}
    assert all(
        measurement.measured_at == event_times[measurement.uplink_event_id]
        for measurement in stored_measurements
    )
    assert all(measurement.quality_flag == "valid" for measurement in stored_measurements)
    assert all(measurement.quality_notes is None for measurement in stored_measurements)
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(TTNReplayQuarantine)
            .where(TTNReplayQuarantine.source == REPLAY_SOURCE)
        )
        == 0
    )


def test_replay_device_is_publicly_labelled_without_private_payload_fields(
    api_client: TestClient, db_session: Session, tmp_path: Path
) -> None:
    replay_ttn_export(db_session, _approved_replay_fixture(tmp_path))
    db_session.flush()

    devices = api_client.get("/api/v1/devices", params={"page_size": 100})
    assert devices.status_code == 200
    items = devices.json()["items"]
    assert 1 <= len(items) <= 8
    assert devices.json()["synthetic"] is False
    outflow_item = next(item for item in items if item["display_name"] == "outflow-a")
    assert outflow_item["is_test_device"] is True
    assert outflow_item["freshness"]["status_basis"] == "replay_dataset_reference_time"

    detail = api_client.get(f"/api/v1/devices/{outflow_item['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["channels"]) == 2
    assert {channel["verification_status"] for channel in body["channels"]} == {"unverified"}
    assert all(channel["unit_code"] is None for channel in body["channels"])
    assert body["telemetry"]["gateway"] == "Replay gateway (identifier withheld)"
    assert body["telemetry"]["firmware_version"] == "3.0"
    serialized = detail.text.lower()
    for forbidden in (
        "raw_payload",
        "session_key_id",
        "dev_eui",
        "join_eui",
        "uplink_token",
        "synthetic-session-key-id",
    ):
        assert forbidden not in serialized

    measurements = api_client.get(
        f"/api/v1/devices/{outflow_item['id']}/measurements",
        params={
            "start": "2099-08-03T00:00:00Z",
            "end": "2099-08-04T00:00:00Z",
            "sensor_channel_id": body["channels"][0]["id"],
            "page_size": 500,
        },
    )
    assert measurements.status_code == 200
    measurement_body = measurements.json()
    assert measurement_body["synthetic"] is False
    assert measurement_body["provenance"] == "exported_live_data"
    assert measurement_body["total_matching"] == 2
    assert all(item["unit_code"] is None for item in measurement_body["items"])
    assert all(item["verification_status"] == "unverified" for item in measurement_body["items"])
    assert all(item["quality_flag"] == "valid" for item in measurement_body["items"])
    assert all(item["quality_notes"] is None for item in measurement_body["items"])

    orchard = api_client.get("/api/v1/overview", params={"site_id": str(SITE_ID)})
    assert orchard.status_code == 200
    assert orchard.json()["devices"]["total"] == 8
    assert orchard.json()["reference_time"].startswith("2026-06-01T12:00:00")
    assert orchard.json()["devices"] == {
        "total": 8,
        "online": 3,
        "stale": 2,
        "offline": 2,
        "unknown": 1,
    }
    orchard_devices = api_client.get(
        "/api/v1/devices", params={"site_id": str(SITE_ID), "page_size": 100}
    )
    assert orchard_devices.status_code == 200
    assert orchard_devices.json()["synthetic"] is True
    assert orchard_devices.json()["contains_replay_data"] is False


def test_malformed_selected_event_is_preserved_in_private_quarantine(
    db_session: Session, tmp_path: Path
) -> None:
    fixture = json.loads(_approved_replay_fixture(tmp_path).read_text(encoding="utf-8"))
    malformed = fixture["events"][0]
    del malformed["data"]["uplink_message"]["session_key_id"]
    malformed_path = tmp_path / "malformed-replay.json"
    malformed_path.write_text(json.dumps([malformed]), encoding="utf-8")

    summary = replay_ttn_export(db_session, malformed_path)
    db_session.flush()

    assert summary.selected_uplinks == 1
    assert summary.raw_inserted == 0
    assert summary.quarantined == 1
    quarantined = db_session.scalar(
        select(TTNReplayQuarantine).where(
            TTNReplayQuarantine.failure_code == "missing_idempotency_identity"
        )
    )
    assert quarantined is not None
    assert quarantined.raw_payload["name"] == "as.up.data.forward"
