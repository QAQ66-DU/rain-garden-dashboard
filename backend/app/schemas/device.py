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
    scientific_meaning: str | None
    verification_status: str
    timestamp_basis: str | None
    active: bool


class DeviceTelemetryPublic(ApiModel):
    observed_at: datetime
    battery_percent: float | None
    firmware_version: str | None
    hardware_version: str | None
    measurement_interval_value: float | None
    measurement_interval_unit: str | None
    latest_rssi_dbm: float | None
    latest_snr_db: float | None
    gateway: str | None


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
    environment: str | None
    source_system: str | None
    ingestion_mode: str | None
    provenance: str | None
    is_test_device: bool
    freshness: Freshness
    latest_battery: MeasurementValue | None


class DeviceDetail(DevicePublic):
    channels: list[SensorChannelPublic]
    latest_measurements: list[MeasurementValue]
    telemetry: DeviceTelemetryPublic | None


class DeviceList(ApiModel):
    items: list[DevicePublic]
    next_cursor: str | None
    reference_time: datetime
    synthetic: bool
    contains_replay_data: bool
