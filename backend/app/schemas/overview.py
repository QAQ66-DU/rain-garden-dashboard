from datetime import datetime
from uuid import UUID

from app.schemas.common import ApiModel
from app.schemas.measurement import MeasurementValue


class DeviceStatusCounts(ApiModel):
    total: int
    online: int
    stale: int
    offline: int
    unknown: int


class SoilChannelObservation(MeasurementValue):
    pass


class SoilMoistureSummary(ApiModel):
    metric_code: str
    unit_code: str
    unit_symbol: str
    minimum: float
    median: float
    maximum: float
    contributing_channel_count: int
    timestamp_start: datetime
    timestamp_end: datetime
    contributing_channels: list[SoilChannelObservation]
    comparability_note: str


class QualityWindow(ApiModel):
    start: datetime | None
    end: datetime | None
    warning_count: int


class Overview(ApiModel):
    site_id: UUID
    site_name: str
    public_location_label: str
    display_timezone: str
    synthetic: bool
    synthetic_notice: str | None
    reference_time: datetime
    last_data_update: datetime | None
    devices: DeviceStatusCounts
    latest_rainfall: MeasurementValue | None
    soil_moisture: SoilMoistureSummary | None
    data_quality: QualityWindow
