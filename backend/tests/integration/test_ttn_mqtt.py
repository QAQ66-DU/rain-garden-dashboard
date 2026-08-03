import copy
import json
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.db.repositories.ttn_replay import LIVE_MQTT_SOURCE, TTN_TESTBED_SITE_NAME
from app.db.seed import SITE_ID
from app.ingestion.ttn_mqtt import MQTTMessageProcessor
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.site import Site
from app.models.uplink_event import UplinkEvent
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parents[1] / "fixtures" / "ttn" / "outflow-a-redacted.json"


def test_mocked_live_mqtt_uplink_is_idempotent_and_isolated(
    api_client: TestClient,
    db_session: Session,
) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    application_up = copy.deepcopy(fixture["events"][0]["data"])
    identifiers = application_up["end_device_ids"]
    identifiers["device_id"] = "outflow-a"
    identifiers["application_ids"]["application_id"] = "rain-garden"
    message = SimpleNamespace(payload=json.dumps(application_up).encode())

    @contextmanager
    def session_scope() -> Generator[Session]:
        yield db_session

    processor = MQTTMessageProcessor(session_scope)
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
