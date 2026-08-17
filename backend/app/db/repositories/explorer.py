from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.measurement import Measurement
from app.models.metric_definition import MetricDefinition
from app.models.monitoring_feature import MonitoringFeature
from app.models.sensor_channel import SensorChannel
from app.models.unit_definition import UnitDefinition
from app.models.uplink_event import UplinkEvent


@dataclass(frozen=True, slots=True)
class ExploreDeviceRecord:
    device_id: UUID
    device_name: str
    device_type: str
    sensor_configuration_status: str
    current_last_seen_at: datetime | None
    feature_id: UUID
    feature_slug: str
    feature_name: str
    feature_type: str


@dataclass(frozen=True, slots=True)
class ExploreChannelRecord:
    channel_id: UUID
    device_id: UUID
    device_name: str
    feature_id: UUID
    feature_slug: str
    feature_name: str
    channel_name: str
    metric_code: str
    metric_name: str
    metric_group: str
    unit_code: str | None
    unit_symbol: str | None
    unit_confirmation_status: str
    verification_status: str
    installation_depth_cm: float | None
    position_label: str | None
    expected_reporting_interval_seconds: int | None
    reporting_schedule_anchor_at: datetime | None
    reporting_jitter_tolerance_seconds: int | None
    water_level_reference_or_datum: str | None


@dataclass(frozen=True, slots=True)
class ExploreMeasurementRecord:
    measurement_id: UUID
    channel_id: UUID
    measured_at: datetime
    received_at: datetime
    numeric_value: Decimal
    quality_flag: str

    @property
    def value(self) -> Decimal:
        """Expose the canonical chart-sampling value without changing stored semantics."""
        return self.numeric_value


@dataclass(frozen=True, slots=True)
class ExploreQualityWarningRecord:
    measurement_id: UUID
    measured_at: datetime
    received_at: datetime
    quality_flag: str
    device_name: str
    channel_name: str


def list_devices(
    session: Session, *, site_id: UUID, feature_slug: str | None
) -> list[ExploreDeviceRecord]:
    statement = (
        select(
            Device.id,
            Device.display_name,
            Device.device_type,
            Device.sensor_configuration_status,
            Device.last_seen_at,
            MonitoringFeature.id,
            MonitoringFeature.public_slug,
            MonitoringFeature.display_name,
            MonitoringFeature.feature_type,
        )
        .join(MonitoringFeature, MonitoringFeature.id == Device.monitoring_feature_id)
        .where(Device.site_id == site_id)
    )
    if feature_slug is not None:
        statement = statement.where(MonitoringFeature.public_slug == feature_slug)
    return [
        ExploreDeviceRecord(
            device_id=cast(UUID, row[0]),
            device_name=cast(str, row[1]),
            device_type=cast(str, row[2]),
            sensor_configuration_status=cast(str, row[3]),
            current_last_seen_at=cast(datetime | None, row[4]),
            feature_id=cast(UUID, row[5]),
            feature_slug=cast(str, row[6]),
            feature_name=cast(str, row[7]),
            feature_type=cast(str, row[8]),
        )
        for row in session.execute(statement.order_by(Device.display_name, Device.id))
    ]


def list_channels(
    session: Session,
    *,
    site_id: UUID,
    feature_slug: str | None,
    metric_group: str,
) -> list[ExploreChannelRecord]:
    statement = (
        select(
            SensorChannel.id,
            Device.id,
            Device.display_name,
            MonitoringFeature.id,
            MonitoringFeature.public_slug,
            MonitoringFeature.display_name,
            SensorChannel.display_name,
            SensorChannel.metric_code,
            MetricDefinition.display_name,
            MetricDefinition.metric_group,
            SensorChannel.unit_code,
            UnitDefinition.unit_symbol,
            SensorChannel.unit_confirmation_status,
            SensorChannel.verification_status,
            SensorChannel.depth_cm,
            SensorChannel.position_label,
            SensorChannel.expected_reporting_interval_seconds,
            SensorChannel.reporting_schedule_anchor_at,
            SensorChannel.reporting_jitter_tolerance_seconds,
            SensorChannel.water_level_reference_or_datum,
        )
        .join(Device, Device.id == SensorChannel.device_id)
        .join(MonitoringFeature, MonitoringFeature.id == Device.monitoring_feature_id)
        .join(MetricDefinition, MetricDefinition.metric_code == SensorChannel.metric_code)
        .outerjoin(UnitDefinition, UnitDefinition.unit_code == SensorChannel.unit_code)
        .where(
            Device.site_id == site_id,
            SensorChannel.active.is_(True),
            MetricDefinition.metric_group == metric_group,
        )
    )
    if feature_slug is not None:
        statement = statement.where(MonitoringFeature.public_slug == feature_slug)
    return [
        ExploreChannelRecord(
            channel_id=cast(UUID, row[0]),
            device_id=cast(UUID, row[1]),
            device_name=cast(str, row[2]),
            feature_id=cast(UUID, row[3]),
            feature_slug=cast(str, row[4]),
            feature_name=cast(str, row[5]),
            channel_name=cast(str, row[6]),
            metric_code=cast(str, row[7]),
            metric_name=cast(str, row[8]),
            metric_group=cast(str, row[9]),
            unit_code=cast(str | None, row[10]),
            unit_symbol=cast(str | None, row[11]),
            unit_confirmation_status=cast(str, row[12]),
            verification_status=cast(str, row[13]),
            installation_depth_cm=cast(float | None, row[14]),
            position_label=cast(str | None, row[15]),
            expected_reporting_interval_seconds=cast(int | None, row[16]),
            reporting_schedule_anchor_at=cast(datetime | None, row[17]),
            reporting_jitter_tolerance_seconds=cast(int | None, row[18]),
            water_level_reference_or_datum=cast(str | None, row[19]),
        )
        for row in session.execute(
            statement.order_by(
                MetricDefinition.display_name,
                Device.display_name,
                SensorChannel.display_name,
                SensorChannel.id,
            )
        )
    ]


def list_observations(
    session: Session, *, channel_ids: list[UUID], start: datetime, end: datetime
) -> list[ExploreMeasurementRecord]:
    if not channel_ids:
        return []
    rows = session.execute(
        select(
            Measurement.id,
            Measurement.sensor_channel_id,
            Measurement.measured_at,
            UplinkEvent.received_at,
            Measurement.numeric_value,
            Measurement.quality_flag,
        )
        .join(UplinkEvent, UplinkEvent.id == Measurement.uplink_event_id)
        .where(
            Measurement.sensor_channel_id.in_(channel_ids),
            Measurement.measured_at >= start,
            Measurement.measured_at < end,
        )
        .order_by(Measurement.measured_at, Measurement.id)
    )
    return [
        ExploreMeasurementRecord(
            measurement_id=cast(UUID, row[0]),
            channel_id=cast(UUID, row[1]),
            measured_at=cast(datetime, row[2]),
            received_at=cast(datetime, row[3]),
            numeric_value=cast(Decimal, row[4]),
            quality_flag=cast(str, row[5]),
        )
        for row in rows
    ]


def count_quality_warnings(
    session: Session,
    *,
    site_id: UUID,
    feature_slug: str | None,
    start: datetime,
    end: datetime,
) -> int:
    statement = (
        select(func.count())
        .select_from(Measurement)
        .join(Device, Device.id == Measurement.device_id)
        .join(MonitoringFeature, MonitoringFeature.id == Device.monitoring_feature_id)
        .where(
            Device.site_id == site_id,
            Measurement.measured_at >= start,
            Measurement.measured_at < end,
            Measurement.quality_flag != "valid",
        )
    )
    if feature_slug is not None:
        statement = statement.where(MonitoringFeature.public_slug == feature_slug)
    return int(session.scalar(statement) or 0)


def list_quality_warnings(
    session: Session,
    *,
    site_id: UUID,
    feature_slug: str | None,
    start: datetime,
    end: datetime,
) -> list[ExploreQualityWarningRecord]:
    statement = (
        select(
            Measurement.id,
            Measurement.measured_at,
            UplinkEvent.received_at,
            Measurement.quality_flag,
            Device.display_name,
            SensorChannel.display_name,
        )
        .join(UplinkEvent, UplinkEvent.id == Measurement.uplink_event_id)
        .join(Device, Device.id == Measurement.device_id)
        .join(SensorChannel, SensorChannel.id == Measurement.sensor_channel_id)
        .join(MonitoringFeature, MonitoringFeature.id == Device.monitoring_feature_id)
        .where(
            Device.site_id == site_id,
            Measurement.measured_at >= start,
            Measurement.measured_at < end,
            Measurement.quality_flag != "valid",
        )
    )
    if feature_slug is not None:
        statement = statement.where(MonitoringFeature.public_slug == feature_slug)
    return [
        ExploreQualityWarningRecord(
            measurement_id=cast(UUID, row[0]),
            measured_at=cast(datetime, row[1]),
            received_at=cast(datetime, row[2]),
            quality_flag=cast(str, row[3]),
            device_name=cast(str, row[4]),
            channel_name=cast(str, row[5]),
        )
        for row in session.execute(statement.order_by(Measurement.measured_at, Measurement.id))
    ]
