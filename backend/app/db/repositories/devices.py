from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.elements import ColumnElement

from app.models.device import Device
from app.models.device_telemetry import DeviceTelemetry
from app.models.measurement import Measurement
from app.models.metric_definition import MetricDefinition
from app.models.monitoring_feature import MonitoringFeature
from app.models.sensor_channel import SensorChannel
from app.models.site import Site
from app.models.unit_definition import UnitDefinition
from app.models.uplink_event import UplinkEvent
from app.services.status import ConnectivityStatus


@dataclass(frozen=True, slots=True)
class DeviceWithSite:
    device: Device
    site_name: str
    feature_id: UUID | None
    feature_slug: str | None
    feature_name: str | None
    feature_type: str | None
    site_reference_time: datetime | None


@dataclass(frozen=True, slots=True)
class LatestMeasurement:
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


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_status_filter(
    statement: Select[Any],
    status: ConnectivityStatus,
    reference_time: datetime | ColumnElement[datetime],
    stale_minutes: int,
    offline_minutes: int,
) -> Select[Any]:
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
    after: tuple[int, str, UUID] | None,
    search: str | None,
    site_id: UUID | None,
    feature_slug: str | None,
    device_type: str | None,
    status: ConnectivityStatus | None,
    reference_time: datetime,
    stale_minutes: int,
    offline_minutes: int,
) -> list[DeviceWithSite]:
    normalized_name = func.lower(Device.display_name)
    test_rank = case((Device.is_test_device.is_(True), 1), else_=0)
    reference_device = aliased(Device)
    site_reference_time = (
        select(func.max(UplinkEvent.received_at))
        .join(reference_device, reference_device.id == UplinkEvent.device_id)
        .where(reference_device.site_id == Device.site_id)
        .correlate(Device)
        .scalar_subquery()
    )
    statement = (
        select(
            Device,
            Site.name,
            MonitoringFeature.id,
            MonitoringFeature.public_slug,
            MonitoringFeature.display_name,
            MonitoringFeature.feature_type,
            site_reference_time.label("site_reference_time"),
        )
        .join(Site, Site.id == Device.site_id)
        .outerjoin(MonitoringFeature, MonitoringFeature.id == Device.monitoring_feature_id)
    )
    if search:
        pattern = f"%{_escape_like(search.strip())}%"
        statement = statement.where(Device.display_name.ilike(pattern, escape="\\"))
    if site_id is not None:
        statement = statement.where(Device.site_id == site_id)
    if feature_slug is not None:
        statement = statement.where(MonitoringFeature.public_slug == feature_slug)
    if device_type is not None:
        statement = statement.where(Device.device_type == device_type)
    if status is not None:
        effective_reference = case(
            (Device.environment == "proxy", reference_time),
            else_=func.coalesce(site_reference_time, reference_time),
        )
        statement = _apply_status_filter(
            statement, status, effective_reference, stale_minutes, offline_minutes
        )
    if after is not None:
        after_test_rank, name, identifier = after
        statement = statement.where(
            or_(
                test_rank > after_test_rank,
                and_(test_rank == after_test_rank, normalized_name > name),
                and_(
                    test_rank == after_test_rank,
                    normalized_name == name,
                    Device.id > identifier,
                ),
            )
        )
    rows = session.execute(
        statement.order_by(test_rank, normalized_name, Device.id).limit(page_size + 1)
    ).all()
    return [
        DeviceWithSite(
            cast(Device, row[0]),
            cast(str, row[1]),
            cast(UUID | None, row[2]),
            cast(str | None, row[3]),
            cast(str | None, row[4]),
            cast(str | None, row[5]),
            cast(datetime | None, row[6]),
        )
        for row in rows
    ]


def get_device(session: Session, device_id: UUID) -> DeviceWithSite | None:
    reference_device = aliased(Device)
    site_reference_time = (
        select(func.max(UplinkEvent.received_at))
        .join(reference_device, reference_device.id == UplinkEvent.device_id)
        .where(reference_device.site_id == Device.site_id)
        .correlate(Device)
        .scalar_subquery()
    )
    row = session.execute(
        select(
            Device,
            Site.name,
            MonitoringFeature.id,
            MonitoringFeature.public_slug,
            MonitoringFeature.display_name,
            MonitoringFeature.feature_type,
            site_reference_time.label("site_reference_time"),
        )
        .join(Site, Site.id == Device.site_id)
        .outerjoin(MonitoringFeature, MonitoringFeature.id == Device.monitoring_feature_id)
        .where(Device.id == device_id)
    ).one_or_none()
    if row is None:
        return None
    return DeviceWithSite(
        cast(Device, row[0]),
        cast(str, row[1]),
        cast(UUID | None, row[2]),
        cast(str | None, row[3]),
        cast(str | None, row[4]),
        cast(str | None, row[5]),
        cast(datetime | None, row[6]),
    )


def list_channels(
    session: Session, device_id: UUID
) -> list[tuple[SensorChannel, MetricDefinition]]:
    rows = session.execute(
        select(SensorChannel, MetricDefinition)
        .join(MetricDefinition, MetricDefinition.metric_code == SensorChannel.metric_code)
        .where(SensorChannel.device_id == device_id)
        .order_by(SensorChannel.display_name, SensorChannel.id)
    ).all()
    return [(cast(SensorChannel, row[0]), cast(MetricDefinition, row[1])) for row in rows]


def active_unit_confirmation_statuses(
    session: Session, device_ids: list[UUID]
) -> dict[UUID, list[str]]:
    statuses: dict[UUID, list[str]] = {device_id: [] for device_id in device_ids}
    if not device_ids:
        return statuses
    rows = session.execute(
        select(SensorChannel.device_id, SensorChannel.unit_confirmation_status).where(
            SensorChannel.device_id.in_(device_ids),
            SensorChannel.active.is_(True),
        )
    )
    for device_id, status in rows:
        statuses[cast(UUID, device_id)].append(cast(str, status))
    return statuses


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
        .join(MetricDefinition, MetricDefinition.metric_code == SensorChannel.metric_code)
        .outerjoin(UnitDefinition, UnitDefinition.unit_code == SensorChannel.unit_code)
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
        )
    return records


def get_telemetry(session: Session, device_id: UUID) -> DeviceTelemetry | None:
    return session.get(DeviceTelemetry, device_id)
