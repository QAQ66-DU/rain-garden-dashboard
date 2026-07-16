from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.measurement import Measurement
from app.models.metric_definition import MetricDefinition
from app.models.sensor_channel import SensorChannel
from app.models.site import Site
from app.services.status import ConnectivityStatus


@dataclass(frozen=True, slots=True)
class DeviceWithSite:
    device: Device
    site_name: str


@dataclass(frozen=True, slots=True)
class LatestMeasurement:
    channel_id: UUID
    channel_code: str
    channel_name: str
    metric_code: str
    metric_name: str
    unit_code: str
    unit_symbol: str
    depth_cm: float | None
    position_label: str | None
    value: Decimal
    measured_at: datetime
    quality_flag: str
    quality_notes: str | None


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_status_filter(
    statement: Select[tuple[Device, str]],
    status: ConnectivityStatus,
    reference_time: datetime,
    stale_minutes: int,
    offline_minutes: int,
) -> Select[tuple[Device, str]]:
    stale_boundary = reference_time - timedelta(minutes=stale_minutes)
    offline_boundary = reference_time - timedelta(minutes=offline_minutes)
    if status is ConnectivityStatus.UNKNOWN:
        return statement.where(Device.last_seen_at.is_(None))
    if status is ConnectivityStatus.ONLINE:
        return statement.where(Device.last_seen_at >= stale_boundary)
    if status is ConnectivityStatus.STALE:
        return statement.where(
            Device.last_seen_at < stale_boundary,
            Device.last_seen_at >= offline_boundary,
        )
    return statement.where(Device.last_seen_at < offline_boundary)


def list_devices(
    session: Session,
    *,
    page_size: int,
    after: tuple[str, UUID] | None,
    search: str | None,
    site_id: UUID | None,
    device_type: str | None,
    status: ConnectivityStatus | None,
    reference_time: datetime,
    stale_minutes: int,
    offline_minutes: int,
) -> list[DeviceWithSite]:
    normalized_name = func.lower(Device.display_name)
    statement = select(Device, Site.name).join(Site, Site.id == Device.site_id)
    if search:
        pattern = f"%{_escape_like(search.strip())}%"
        statement = statement.where(Device.display_name.ilike(pattern, escape="\\"))
    if site_id is not None:
        statement = statement.where(Device.site_id == site_id)
    if device_type is not None:
        statement = statement.where(Device.device_type == device_type)
    if status is not None:
        statement = _apply_status_filter(
            statement, status, reference_time, stale_minutes, offline_minutes
        )
    if after is not None:
        name, identifier = after
        statement = statement.where(
            or_(
                normalized_name > name,
                and_(normalized_name == name, Device.id > identifier),
            )
        )
    rows = session.execute(
        statement.order_by(normalized_name, Device.id).limit(page_size + 1)
    ).all()
    return [DeviceWithSite(cast(Device, row[0]), cast(str, row[1])) for row in rows]


def get_device(session: Session, device_id: UUID) -> DeviceWithSite | None:
    row = session.execute(
        select(Device, Site.name)
        .join(Site, Site.id == Device.site_id)
        .where(Device.id == device_id)
    ).one_or_none()
    if row is None:
        return None
    return DeviceWithSite(cast(Device, row[0]), cast(str, row[1]))


def list_channels(
    session: Session, device_id: UUID
) -> list[tuple[SensorChannel, MetricDefinition]]:
    rows = session.execute(
        select(SensorChannel, MetricDefinition)
        .join(
            MetricDefinition,
            and_(
                MetricDefinition.metric_code == SensorChannel.metric_code,
                MetricDefinition.unit_code == SensorChannel.unit_code,
            ),
        )
        .where(SensorChannel.device_id == device_id)
        .order_by(SensorChannel.display_name, SensorChannel.id)
    ).all()
    return [(cast(SensorChannel, row[0]), cast(MetricDefinition, row[1])) for row in rows]


def latest_measurements_by_channel(
    session: Session, device_ids: list[UUID]
) -> dict[UUID, list[LatestMeasurement]]:
    if not device_ids:
        return {}
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
            Measurement.device_id.label("device_id"),
            Measurement.sensor_channel_id.label("channel_id"),
            SensorChannel.channel_code.label("channel_code"),
            SensorChannel.display_name.label("channel_name"),
            SensorChannel.metric_code.label("metric_code"),
            MetricDefinition.display_name.label("metric_name"),
            SensorChannel.unit_code.label("unit_code"),
            MetricDefinition.unit_symbol.label("unit_symbol"),
            SensorChannel.depth_cm.label("depth_cm"),
            SensorChannel.position_label.label("position_label"),
            Measurement.numeric_value.label("value"),
            Measurement.measured_at.label("measured_at"),
            Measurement.quality_flag.label("quality_flag"),
            Measurement.quality_notes.label("quality_notes"),
            rank,
        )
        .join(SensorChannel, SensorChannel.id == Measurement.sensor_channel_id)
        .join(
            MetricDefinition,
            and_(
                MetricDefinition.metric_code == SensorChannel.metric_code,
                MetricDefinition.unit_code == SensorChannel.unit_code,
            ),
        )
        .where(Measurement.device_id.in_(device_ids))
        .subquery()
    )
    records: dict[UUID, list[LatestMeasurement]] = {identifier: [] for identifier in device_ids}
    for row in session.execute(select(ranked).where(ranked.c.rank == 1)):
        records[cast(UUID, row.device_id)].append(
            LatestMeasurement(
                channel_id=cast(UUID, row.channel_id),
                channel_code=cast(str, row.channel_code),
                channel_name=cast(str, row.channel_name),
                metric_code=cast(str, row.metric_code),
                metric_name=cast(str, row.metric_name),
                unit_code=cast(str, row.unit_code),
                unit_symbol=cast(str, row.unit_symbol),
                depth_cm=cast(float | None, row.depth_cm),
                position_label=cast(str | None, row.position_label),
                value=cast(Decimal, row.value),
                measured_at=cast(datetime, row.measured_at),
                quality_flag=cast(str, row.quality_flag),
                quality_notes=cast(str | None, row.quality_notes),
            )
        )
    return records
