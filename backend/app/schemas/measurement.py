from datetime import datetime
from uuid import UUID

from app.schemas.common import ApiModel


class MeasurementValue(ApiModel):
    channel_id: UUID
    channel_code: str
    channel_name: str
    metric_code: str
    metric_name: str
    numeric_value: float
    unit_code: str | None
    unit_symbol: str | None
    unit_confirmation_status: str
    verification_status: str
    timestamp_basis: str | None
    measured_at: datetime
    quality_flag: str
    quality_notes: str | None
    installation_depth_cm: float | None
    # Backward-compatible Phase 1 alias; installation_depth_cm is the explicit field.
    depth_cm: float | None
    position_label: str | None


class MeasurementPage(ApiModel):
    items: list[MeasurementValue]
    next_cursor: str | None
    total_matching: int
    start: datetime
    end: datetime
    reference_time: datetime
    default_range_applied: bool
    synthetic: bool
    provenance: str | None
