from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from app.db.sync_catalog import sync_metric_catalog
from app.ingestion.contracts import CanonicalMeasurement, CanonicalUplink
from app.ingestion.service import ingest_canonical_uplink
from app.models.device import Device
from app.models.enums import DeviceType, LocationDisclosure
from app.models.measurement import Measurement
from app.models.sensor_channel import SensorChannel
from app.models.site import Site
from app.models.uplink_event import UplinkEvent
from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

SITE_ID = UUID("5f47476a-bc34-4848-9752-fb46a3d3039e")
DEVICE_ID = UUID("db157df5-494f-43e5-b3b9-7d259e0ad57c")
CHANNEL_ID = UUID("4d9b3124-5a47-4e50-b283-50fd8a041d28")
EVENT_ID = UUID("9fb6c292-c250-4d57-abda-5dd5e51af38f")
MEASUREMENT_ID = UUID("b536a955-3488-409a-999a-3d6f6e4d8516")


def configure_test_channel(session: Session) -> None:
    sync_metric_catalog(session)
    session.flush()
    session.add(
        Site(
            id=SITE_ID,
            name="Integration test site",
            description=None,
            public_location_label="Withheld test location",
            location_disclosure=LocationDisclosure.WITHHELD,
            private_latitude=55.0,
            private_longitude=-3.0,
            display_timezone="Europe/London",
            active=True,
        )
    )
    session.flush()
    session.add(
        Device(
            id=DEVICE_ID,
            site_id=SITE_ID,
            external_device_id="private-test-device-id",
            display_name="Integration weather device",
            device_type=DeviceType.WEATHER_STATION,
            operational_override=None,
            last_seen_at=None,
            private_latitude=55.1,
            private_longitude=-3.1,
            location_disclosure=LocationDisclosure.PRIVATE,
        )
    )
    session.flush()
    session.add(
        SensorChannel(
            id=CHANNEL_ID,
            device_id=DEVICE_ID,
            channel_code="rainfall",
            display_name="Rainfall test channel",
            metric_code="rainfall_mm",
            unit_code="mm",
            depth_cm=None,
            position_label=None,
            active=True,
            channel_metadata={"private_note": "must not be public"},
        )
    )
    session.flush()


def test_duplicate_canonical_uplink_is_idempotent(db_session: Session) -> None:
    configure_test_channel(db_session)
    timestamp = datetime(2026, 6, 1, tzinfo=UTC)
    payload = CanonicalUplink(
        event_id=EVENT_ID,
        source="synthetic-test",
        idempotency_key="stable-test-key",
        external_device_id="private-test-device-id",
        received_at=timestamp,
        measured_at=timestamp,
        raw_payload={"synthetic": True},
        measurements=[
            CanonicalMeasurement(
                measurement_id=MEASUREMENT_ID,
                channel_code="rainfall",
                numeric_value=Decimal("0"),
                measured_at=timestamp,
            )
        ],
    )

    first = ingest_canonical_uplink(db_session, payload)
    second = ingest_canonical_uplink(db_session, payload)
    db_session.flush()

    assert first.created is True
    assert second.created is False
    assert first.event_id == second.event_id == EVENT_ID
    assert (
        db_session.scalar(
            select(func.count()).select_from(UplinkEvent).where(UplinkEvent.id == EVENT_ID)
        )
        == 1
    )
    assert (
        db_session.scalar(
            select(func.count()).select_from(Measurement).where(Measurement.id == MEASUREMENT_ID)
        )
        == 1
    )
    stored = db_session.get(Measurement, MEASUREMENT_ID)
    assert stored is not None
    assert stored.numeric_value == Decimal("0.000000")
