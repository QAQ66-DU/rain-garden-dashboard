from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.device import Device
from app.models.measurement import Measurement
from app.models.metric_definition import MetricDefinition
from app.models.sensor_channel import SensorChannel
from app.models.unit_definition import UnitDefinition
from app.models.uplink_event import UplinkEvent


@dataclass(frozen=True, slots=True)
class MeasurementRecord:
    measurement_id: UUID
    channel_id: UUID
    channel_code: str
    channel_name: str
    metric_code: str
    metric_name: str
    unit_code: str | None
    unit_symbol: str | None
    unit_confirmation_status: str
    verification_status: str
    timestamp_basis: str | None
    depth_cm: float | None
    position_label: str | None
    value: Decimal
    measured_at: datetime
    quality_flag: str
    quality_notes: str | None
    ingestion_mode: str | None
    provenance: str | None


def dataset_reference_time(session: Session) -> datetime | None:
    return session.scalar(select(func.max(UplinkEvent.received_at)))


def device_reference_time(session: Session, device_id: UUID) -> datetime | None:
    return session.scalar(
        select(func.max(UplinkEvent.received_at)).where(UplinkEvent.device_id == device_id)
    )


def site_reference_time(session: Session, site_id: UUID) -> datetime | None:
    return session.scalar(
        select(func.max(UplinkEvent.received_at))
        .join(Device, Device.id == UplinkEvent.device_id)
        .where(Device.site_id == site_id)
    )


def _conditions(
    device_id: UUID,
    start: datetime,
    end: datetime,
    metric_code: str | None,
    sensor_channel_id: UUID | None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [
        Measurement.device_id == device_id,
        Measurement.measured_at >= start,
        Measurement.measured_at < end,
    ]
    if metric_code is not None:
        conditions.append(SensorChannel.metric_code == metric_code)
    if sensor_channel_id is not None:
        conditions.append(Measurement.sensor_channel_id == sensor_channel_id)
    return conditions


def count_measurements(
    session: Session,
    *,
    device_id: UUID,
    start: datetime,
    end: datetime,
    metric_code: str | None,
    sensor_channel_id: UUID | None,
) -> int:
    value = session.scalar(
        select(func.count())
        .select_from(Measurement)
        .join(SensorChannel, SensorChannel.id == Measurement.sensor_channel_id)
        .where(*_conditions(device_id, start, end, metric_code, sensor_channel_id))
    )
    return int(value or 0)


def list_measurements(
    session: Session,
    *,
    device_id: UUID,
    start: datetime,
    end: datetime,
    metric_code: str | None,
    sensor_channel_id: UUID | None,
    after: tuple[datetime, UUID] | None,
    page_size: int,
) -> list[MeasurementRecord]:
    conditions = _conditions(device_id, start, end, metric_code, sensor_channel_id)
    if after is not None:
        timestamp, identifier = after
        conditions.append(
            or_(
                Measurement.measured_at > timestamp,
                and_(Measurement.measured_at == timestamp, Measurement.id > identifier),
            )
        )
    statement = _measurement_statement(conditions).limit(page_size + 1)
    return [_measurement_record(row) for row in session.execute(statement)]


def iter_measurements(
    session: Session,
    *,
    device_id: UUID,
    start: datetime,
    end: datetime,
    metric_code: str | None,
    sensor_channel_id: UUID | None,
    batch_size: int = 1_000,
) -> Iterator[MeasurementRecord]:
    statement = _measurement_statement(
        _conditions(device_id, start, end, metric_code, sensor_channel_id)
    ).execution_options(yield_per=batch_size)
    for row in session.execute(statement):
        yield _measurement_record(row)


def _measurement_statement(conditions: list[ColumnElement[bool]]) -> Any:
    return (
        select(
            Measurement.id,
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
            UplinkEvent.ingestion_mode,
            UplinkEvent.provenance,
        )
        .join(SensorChannel, SensorChannel.id == Measurement.sensor_channel_id)
        .join(MetricDefinition, MetricDefinition.metric_code == SensorChannel.metric_code)
        .outerjoin(UnitDefinition, UnitDefinition.unit_code == SensorChannel.unit_code)
        .join(UplinkEvent, UplinkEvent.id == Measurement.uplink_event_id)
        .where(*conditions)
        .order_by(Measurement.measured_at, Measurement.id)
    )


def _measurement_record(row: Any) -> MeasurementRecord:
    return MeasurementRecord(
        measurement_id=cast(UUID, row[0]),
        channel_id=cast(UUID, row[1]),
        channel_code=cast(str, row[2]),
        channel_name=cast(str, row[3]),
        metric_code=cast(str, row[4]),
        metric_name=cast(str, row[5]),
        unit_code=cast(str | None, row[6]),
        unit_symbol=cast(str | None, row[7]),
        unit_confirmation_status=cast(str, row[8]),
        verification_status=cast(str, row[9]),
        timestamp_basis=cast(str | None, row[10]),
        depth_cm=cast(float | None, row[11]),
        position_label=cast(str | None, row[12]),
        value=cast(Decimal, row[13]),
        measured_at=cast(datetime, row[14]),
        quality_flag=cast(str, row[15]),
        quality_notes=cast(str | None, row[16]),
        ingestion_mode=cast(str | None, row[17]),
        provenance=cast(str | None, row[18]),
    )


def current_reference_time(session: Session, *, demo_mode: bool) -> datetime:
    if demo_mode:
        reference = dataset_reference_time(session)
        if reference is not None:
            return reference
    return datetime.now(UTC)


def current_device_reference_time(
    session: Session, device_id: UUID, *, demo_mode: bool
) -> datetime:
    if demo_mode:
        reference = device_reference_time(session, device_id)
        if reference is not None:
            return reference
    return datetime.now(UTC)


def current_site_reference_time(session: Session, site_id: UUID, *, demo_mode: bool) -> datetime:
    if demo_mode:
        reference = site_reference_time(session, site_id)
        if reference is not None:
            return reference
    return datetime.now(UTC)
