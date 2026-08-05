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
from app.ingestion.ttn_mqtt import MQTTMessageProcessor
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.site import Site
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


def test_mocked_live_mqtt_uplink_is_idempotent_and_isolated(
    api_client: TestClient,
    db_session: Session,
) -> None:
    application_up = _approved_application_up()
    message = SimpleNamespace(payload=json.dumps(application_up).encode())

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
    outflow = db_session.scalar(select(Device).where(Device.site_id == testbed.id))
    assert outflow is not None
    assert outflow.display_name == "Outflow A"
    assert outflow.is_test_device is True
    assert db_session.scalar(select(func.count()).select_from(Device)) == 9
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(UplinkEvent)
            .where(
                UplinkEvent.device_id == outflow.id,
                UplinkEvent.source == LIVE_MQTT_SOURCE,
            )
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(Measurement).where(Measurement.device_id == outflow.id)
        )
        == 2
    )
    stored = db_session.scalar(
        select(UplinkEvent).where(
            UplinkEvent.device_id == outflow.id,
            UplinkEvent.source == LIVE_MQTT_SOURCE,
        )
    )
    assert stored is not None
    assert stored.raw_payload == application_up
    assert "name" not in stored.raw_payload

    orchard = api_client.get("/api/v1/overview", params={"site_id": str(SITE_ID)})
    assert orchard.status_code == 200
    assert orchard.json()["devices"]["total"] == 8
    assert orchard.json()["reference_time"].startswith("2026-06-01T12:00:00")


def test_replay_and_live_mqtt_share_chronological_utc_history(
    api_client: TestClient,
    db_session: Session,
) -> None:
    replay_up = _approved_application_up()
    live_up = copy.deepcopy(replay_up)
    live_up["received_at"] = "2026-08-04T18:38:53.442428Z"
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
    assert detail_body["provenance"] == "live_ttn_mqtt"
    assert detail_body["freshness"]["status_basis"] == "live_mqtt_reference_time"
    channel_id = next(
        channel["id"]
        for channel in detail_body["channels"]
        if channel["channel_code"] == "outflow_measurement_1"
    )

    history = api_client.get(
        f"/api/v1/devices/{outflow.id}/measurements",
        params={
            "start": "2026-08-03T00:00:00Z",
            "end": "2026-08-05T00:00:00Z",
            "sensor_channel_id": channel_id,
            "page_size": 500,
        },
    )
    assert history.status_code == 200
    history_body = history.json()
    assert history_body["total_matching"] == 2
    timestamps = [item["measured_at"] for item in history_body["items"]]
    assert timestamps == sorted(timestamps)
    assert timestamps[-1] == "2026-08-04T18:38:53.442428Z"

    recent = api_client.get(
        f"/api/v1/devices/{outflow.id}/measurements",
        params={
            "start": "2026-08-04T18:38:53Z",
            "end": "2026-08-04T18:38:54Z",
            "sensor_channel_id": channel_id,
            "page_size": 500,
        },
    )
    assert recent.status_code == 200
    assert [item["measured_at"] for item in recent.json()["items"]] == [
        "2026-08-04T18:38:53.442428Z"
    ]

    default_history = api_client.get(
        f"/api/v1/devices/{outflow.id}/measurements",
        params={"sensor_channel_id": channel_id, "page_size": 500},
    )
    assert default_history.status_code == 200
    default_body = default_history.json()
    assert default_body["default_range_applied"] is True
    assert default_body["total_matching"] == 2
    assert default_body["items"][-1]["measured_at"] == detail_body["last_seen_at"]
    assert default_body["provenance"] == "live_ttn_mqtt"

    assert (
        db_session.scalar(
            select(func.count()).select_from(Measurement).where(Measurement.device_id == outflow.id)
        )
        == 4
    )
