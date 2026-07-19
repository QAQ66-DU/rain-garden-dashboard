from datetime import datetime
from uuid import UUID

from app.schemas.common import ApiModel, Freshness


class ExploreDevice(ApiModel):
    device_id: UUID
    device_name: str
    device_type: str
    sensor_configuration_status: str
    feature_id: UUID
    feature_slug: str
    feature_name: str
    current_freshness: Freshness


class ExploreChannel(ApiModel):
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
    installation_depth_cm: float | None
    position_label: str | None
    expected_reporting_interval_seconds: int | None
    reporting_schedule_anchor_at: datetime | None
    reporting_jitter_tolerance_seconds: int | None
    water_level_reference_or_datum: str | None


class ExplorePoint(ApiModel):
    measurement_id: UUID
    measured_at: datetime
    received_at: datetime
    numeric_value: float
    quality_flag: str
    included_in_summary: bool
    expected_slot_at: datetime | None
    timing_status: str
    transmission_delay_seconds: float


class ExploreMissingInterval(ApiModel):
    start: datetime
    end: datetime
    expected_slots: int


class ExploreCoverage(ApiModel):
    status: str
    status_detail: str
    expected_observations: int | None
    received_observations: int | None
    valid_observations: int | None
    flagged_observations: int | None
    missing_observations: int | None
    coverage_percentage: float | None
    late_observations: int
    out_of_tolerance_observations: int
    duplicate_slot_observations: int
    missing_intervals: list[ExploreMissingInterval]


class ExploreSummaryStatistic(ApiModel):
    code: str
    label: str
    value: float
    observed_at: datetime | None


class ExploreSummary(ApiModel):
    status: str
    status_detail: str
    statistics: list[ExploreSummaryStatistic]


class ExploreSeries(ApiModel):
    channel: ExploreChannel
    points: list[ExplorePoint]
    summary: ExploreSummary
    coverage: ExploreCoverage


class QualityWarning(ApiModel):
    measurement_id: UUID
    device_name: str
    channel_name: str
    observation_time: datetime
    received_at: datetime
    quality_flag: str
    explanation: str
    excluded_from_summaries: bool


class ExploreResponse(ApiModel):
    site_id: UUID
    site_name: str
    display_timezone: str
    start: datetime
    end: datetime
    time_window_semantics: str
    feature: str | None
    metric_group: str
    selected_channel_ids: list[UUID]
    available_devices: list[ExploreDevice]
    available_channels: list[ExploreChannel]
    series: list[ExploreSeries]
    quality_warnings: list[QualityWarning]
    reference_time: datetime
    synthetic: bool
