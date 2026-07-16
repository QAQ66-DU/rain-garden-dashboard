from datetime import datetime
from uuid import UUID

from app.schemas.common import ApiModel, Freshness
from app.schemas.measurement import MeasurementValue


class SensorChannelPublic(ApiModel):
    id: UUID
    channel_code: str
    display_name: str
    metric_code: str
    metric_name: str
    unit_code: str
    unit_symbol: str
    depth_cm: float | None
    position_label: str | None
    active: bool


class DevicePublic(ApiModel):
    id: UUID
    site_id: UUID
    site_name: str
    display_name: str
    device_type: str
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
