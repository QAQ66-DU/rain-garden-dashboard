from datetime import datetime
from uuid import UUID

from app.schemas.common import ApiModel, Freshness
from app.schemas.measurement import MeasurementValue


class MonitoringFeaturePublic(ApiModel):
    id: UUID
    public_slug: str
    display_name: str
    feature_type: str


class SensorChannelPublic(ApiModel):
    id: UUID
    channel_code: str
    display_name: str
    metric_code: str
    metric_name: str
    unit_code: str | None
    unit_symbol: str | None
    unit_confirmation_status: str
    installation_depth_cm: float | None
    # Backward-compatible Phase 1 alias; installation_depth_cm is the explicit field.
    depth_cm: float | None
    position_label: str | None
    expected_reporting_interval_seconds: int | None
    reporting_schedule_anchor_at: datetime | None
    reporting_jitter_tolerance_seconds: int | None
    water_level_reference_or_datum: str | None
    active: bool


class DevicePublic(ApiModel):
    id: UUID
    site_id: UUID
    site_name: str
    monitoring_feature: MonitoringFeaturePublic | None
    display_name: str
    device_type: str
    sensor_configuration_status: str
    operational_override: str | None
    last_seen_at: datetime | None
    location_disclosure: str
    freshness: Freshness
    latest_battery: MeasurementValue | None


class DeviceDetail(DevicePublic):
    channels: list[SensorChannelPublic]
    latest_measurements: list[MeasurementValue]


class DeviceList(ApiModel):
    items: list[DevicePublic]
    next_cursor: str | None
    reference_time: datetime
    synthetic: bool
