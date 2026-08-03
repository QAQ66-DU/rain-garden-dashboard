from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.repositories.devices import LatestMeasurement
from app.models.device import Device
from app.models.measurement import Measurement
from app.models.metric_definition import MetricDefinition
from app.models.sensor_channel import SensorChannel
from app.models.unit_definition import UnitDefinition
from app.models.uplink_event import UplinkEvent


def device_last_seen_values(session: Session, site_id: UUID) -> list[datetime | None]:
    return list(
        session.scalars(
            select(Device.last_seen_at).where(Device.site_id == site_id).order_by(Device.id)
        )
    )


def has_test_device(session: Session, site_id: UUID) -> bool:
    value = session.scalar(
        select(func.count())
        .select_from(Device)
        .where(Device.site_id == site_id, Device.is_test_device.is_(True))
    )
    return bool(value)


def last_data_update(session: Session, site_id: UUID) -> datetime | None:
    return session.scalar(
        select(func.max(UplinkEvent.received_at))
        .join(Device, Device.id == UplinkEvent.device_id)
        .where(Device.site_id == site_id)
    )


def latest_valid_metric(
    session: Session, site_id: UUID, metric_code: str
) -> LatestMeasurement | None:
    row = session.execute(
        select(
            Measurement.sensor_channel_id,
            SensorChannel.channel_code,
            SensorChannel.display_name,
            SensorChannel.metric_code,
            MetricDefinition.display_name,
            SensorChannel.unit_code,
            UnitDefinition.unit_symbol,
            SensorChannel.unit_confirmation_status,
            SensorChannel.verification_status,
            SensorChannel.timestamp_basis,
            SensorChannel.depth_cm,
            SensorChannel.position_label,
            Measurement.numeric_value,
            Measurement.measured_at,
            Measurement.quality_flag,
            Measurement.quality_notes,
        )
        .join(SensorChannel, SensorChannel.id == Measurement.sensor_channel_id)
        .join(Device, Device.id == Measurement.device_id)
        .join(MetricDefinition, MetricDefinition.metric_code == SensorChannel.metric_code)
        .outerjoin(UnitDefinition, UnitDefinition.unit_code == SensorChannel.unit_code)
        .where(
            Device.site_id == site_id,
            SensorChannel.metric_code == metric_code,
            Measurement.quality_flag == "valid",
        )
        .order_by(Measurement.measured_at.desc(), Measurement.id.desc())
        .limit(1)
    ).one_or_none()
    if row is None:
        return None
    return LatestMeasurement(
        channel_id=cast(UUID, row[0]),
        channel_code=cast(str, row[1]),
        channel_name=cast(str, row[2]),
        metric_code=cast(str, row[3]),
        metric_name=cast(str, row[4]),
        unit_code=cast(str | None, row[5]),
        unit_symbol=cast(str | None, row[6]),
        unit_confirmation_status=cast(str, row[7]),
        verification_status=cast(str, row[8]),
        timestamp_basis=cast(str | None, row[9]),
        depth_cm=cast(float | None, row[10]),
        position_label=cast(str | None, row[11]),
        value=cast(Decimal, row[12]),
        measured_at=cast(datetime, row[13]),
        quality_flag=cast(str, row[14]),
        quality_notes=cast(str | None, row[15]),
    )


def latest_valid_soil_channels(session: Session, site_id: UUID) -> list[LatestMeasurement]:
    rank = (
        func.row_number()
        .over(
            partition_by=Measurement.sensor_channel_id,
            order_by=(Measurement.measured_at.desc(), Measurement.id.desc()),
        )
        .label("rank")
    )
    ranked = (
        select(
            Measurement.sensor_channel_id.label("channel_id"),
            SensorChannel.channel_code.label("channel_code"),
            SensorChannel.display_name.label("channel_name"),
            SensorChannel.metric_code.label("metric_code"),
            MetricDefinition.display_name.label("metric_name"),
            SensorChannel.unit_code.label("unit_code"),
            UnitDefinition.unit_symbol.label("unit_symbol"),
            SensorChannel.unit_confirmation_status.label("unit_confirmation_status"),
            SensorChannel.verification_status.label("verification_status"),
            SensorChannel.timestamp_basis.label("timestamp_basis"),
            SensorChannel.depth_cm.label("depth_cm"),
            SensorChannel.position_label.label("position_label"),
            Measurement.numeric_value.label("value"),
            Measurement.measured_at.label("measured_at"),
            Measurement.quality_flag.label("quality_flag"),
            Measurement.quality_notes.label("quality_notes"),
            rank,
        )
        .join(SensorChannel, SensorChannel.id == Measurement.sensor_channel_id)
        .join(Device, Device.id == Measurement.device_id)
        .join(MetricDefinition, MetricDefinition.metric_code == SensorChannel.metric_code)
        .outerjoin(UnitDefinition, UnitDefinition.unit_code == SensorChannel.unit_code)
        .where(
            Device.site_id == site_id,
            SensorChannel.metric_code == "soil_moisture",
            Measurement.quality_flag == "valid",
            SensorChannel.active.is_(True),
        )
        .subquery()
    )
    return [
        LatestMeasurement(
            channel_id=cast(UUID, row.channel_id),
            channel_code=cast(str, row.channel_code),
            channel_name=cast(str, row.channel_name),
            metric_code=cast(str, row.metric_code),
            metric_name=cast(str, row.metric_name),
            unit_code=cast(str | None, row.unit_code),
            unit_symbol=cast(str | None, row.unit_symbol),
            unit_confirmation_status=cast(str, row.unit_confirmation_status),
            verification_status=cast(str, row.verification_status),
            timestamp_basis=cast(str | None, row.timestamp_basis),
            depth_cm=cast(float | None, row.depth_cm),
            position_label=cast(str | None, row.position_label),
            value=cast(Decimal, row.value),
            measured_at=cast(datetime, row.measured_at),
            quality_flag=cast(str, row.quality_flag),
            quality_notes=cast(str | None, row.quality_notes),
        )
        for row in session.execute(
            select(ranked).where(ranked.c.rank == 1).order_by(ranked.c.channel_name)
        )
    ]


def quality_warning_count(session: Session, site_id: UUID, start: datetime, end: datetime) -> int:
    value = session.scalar(
        select(func.count())
        .select_from(Measurement)
        .join(Device, Device.id == Measurement.device_id)
        .where(
            Device.site_id == site_id,
            Measurement.measured_at >= start,
            Measurement.measured_at < end,
            Measurement.quality_flag != "valid",
        )
    )
    return int(value or 0)
