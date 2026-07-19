import pytest
from app.db.reset_demo import reset_demo_session
from app.db.seed import SITE_ID, TREE_PIT_FEATURE_ID, seed_session
from app.models.device import Device
from app.models.enums import SensorConfigurationStatus, UnitConfirmationStatus
from app.models.monitoring_feature import MonitoringFeature
from app.models.sensor_channel import SensorChannel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_seed_is_idempotent_and_matches_confirmed_inventory(db_session: Session) -> None:
    seed_session(db_session)
    counts_before = (
        db_session.scalar(
            select(func.count()).select_from(Device).where(Device.site_id == SITE_ID)
        ),
        db_session.scalar(
            select(func.count())
            .select_from(SensorChannel)
            .join(Device, Device.id == SensorChannel.device_id)
            .where(Device.site_id == SITE_ID)
        ),
    )

    assert seed_session(db_session) is None
    assert counts_before == (8, 20)
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(MonitoringFeature)
            .where(MonitoringFeature.site_id == SITE_ID)
        )
        == 2
    )

    devices = list(db_session.scalars(select(Device).where(Device.site_id == SITE_ID)))
    assert len(devices) == 8
    assert all(device.private_latitude is not None for device in devices)
    assert all(device.private_longitude is not None for device in devices)
    assert all(device.location_disclosure == "private" for device in devices)
    assert not any("gateway" in device.external_device_id for device in devices)

    tree_probe = next(
        device for device in devices if device.monitoring_feature_id == TREE_PIT_FEATURE_ID
    )
    assert tree_probe.sensor_configuration_status == SensorConfigurationStatus.PENDING
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SensorChannel)
            .where(SensorChannel.device_id == tree_probe.id)
        )
        == 0
    )

    channels = list(
        db_session.scalars(select(SensorChannel).join(Device).where(Device.site_id == SITE_ID))
    )
    assert all(
        channel.unit_confirmation_status == UnitConfirmationStatus.SYNTHETIC_DEMO_ONLY
        for channel in channels
    )
    assert all(channel.reporting_schedule_anchor_at is not None for channel in channels)
    assert all(channel.expected_reporting_interval_seconds == 3600 for channel in channels)


def test_explicit_demo_reset_can_reseed_atomically(db_session: Session) -> None:
    seed_session(db_session)

    assert reset_demo_session(db_session) is True
    db_session.flush()
    assert seed_session(db_session) is not None
    assert (
        db_session.scalar(select(func.count()).select_from(Device).where(Device.site_id == SITE_ID))
        == 8
    )
