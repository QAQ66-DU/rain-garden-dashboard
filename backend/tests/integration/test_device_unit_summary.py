from decimal import Decimal

import pytest
from app.db.seed import SITE_ID
from app.db.synthetic import stable_uuid
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.sensor_channel import SensorChannel
from app.models.uplink_event import UplinkEvent
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration

WEATHER_DEVICE_ID = stable_uuid("device:synthetic-v2-swale-weather-001")
TREE_PROBE_ID = stable_uuid("device:synthetic-v2-tree-pit-probe-001")


def test_device_list_and_detail_share_authoritative_unit_summary(
    api_client: TestClient,
) -> None:
    listed = api_client.get("/api/v1/devices", params={"site_id": str(SITE_ID)})
    detail = api_client.get(f"/api/v1/devices/{WEATHER_DEVICE_ID}")
    tree_detail = api_client.get(f"/api/v1/devices/{TREE_PROBE_ID}")

    assert listed.status_code == detail.status_code == tree_detail.status_code == 200
    listed_weather = next(
        item for item in listed.json()["items"] if item["id"] == str(WEATHER_DEVICE_ID)
    )
    assert listed_weather["unit_confirmation_summary"] == "synthetic_demo_only"
    assert detail.json()["unit_confirmation_summary"] == "synthetic_demo_only"
    assert tree_detail.json()["unit_confirmation_summary"] == "no_active_channels"


def test_unit_summary_uses_active_channels_only(
    api_client: TestClient, db_session: Session
) -> None:
    channels = db_session.scalars(
        select(SensorChannel)
        .where(SensorChannel.device_id == WEATHER_DEVICE_ID)
        .order_by(SensorChannel.channel_code)
    ).all()
    channels[0].unit_confirmation_status = "confirmed"
    db_session.flush()

    mixed = api_client.get(f"/api/v1/devices/{WEATHER_DEVICE_ID}")
    assert mixed.status_code == 200
    assert mixed.json()["unit_confirmation_summary"] == "mixed"

    channels[0].active = False
    db_session.flush()

    without_inactive = api_client.get(f"/api/v1/devices/{WEATHER_DEVICE_ID}")
    assert without_inactive.status_code == 200
    assert without_inactive.json()["unit_confirmation_summary"] == "synthetic_demo_only"


def test_unit_summary_does_not_infer_from_device_measurement_or_payload_fields(
    api_client: TestClient, db_session: Session
) -> None:
    device = db_session.get(Device, WEATHER_DEVICE_ID)
    assert device is not None
    device.display_name = "Renamed test telemetry device"
    device.device_type = "test_telemetry_device"
    device.is_test_device = True

    channel = db_session.scalars(
        select(SensorChannel).where(SensorChannel.device_id == WEATHER_DEVICE_ID).limit(1)
    ).one()
    channel.display_name = "Payload field 9999"

    measurement = db_session.scalars(
        select(Measurement).where(Measurement.device_id == WEATHER_DEVICE_ID).limit(1)
    ).one()
    measurement.numeric_value = Decimal("987654.321")

    uplink = db_session.scalars(
        select(UplinkEvent).where(UplinkEvent.device_id == WEATHER_DEVICE_ID).limit(1)
    ).one()
    uplink.raw_payload = {"unit": "invented", "confirmed": True}
    db_session.flush()

    detail = api_client.get(f"/api/v1/devices/{WEATHER_DEVICE_ID}")

    assert detail.status_code == 200
    assert detail.json()["unit_confirmation_summary"] == "synthetic_demo_only"
