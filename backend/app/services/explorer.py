from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.analytics.explorer import (
    PeriodObservation,
    calculate_coverage,
    calculate_period_summary,
)
from app.core.config import Settings
from app.db.repositories import explorer as explorer_repository
from app.db.repositories import overview as overview_repository
from app.db.repositories import sites as site_repository
from app.db.repositories.measurements import current_site_reference_time
from app.models.enums import MetricGroup
from app.schemas.explorer import (
    ExploreChannel,
    ExploreCoverage,
    ExploreDevice,
    ExploreMissingInterval,
    ExplorePoint,
    ExploreResponse,
    ExploreSeries,
    ExploreSummary,
    ExploreSummaryStatistic,
    QualityWarning,
)
from app.services.errors import ServiceError
from app.services.status import calculate_freshness
from app.services.time_windows import validate_time_window
from app.services.transformers import freshness_schema


def _parse_selected_channels(value: str | None) -> list[UUID] | None:
    if value is None:
        return None
    if not value.strip():
        return []
    try:
        return list(dict.fromkeys(UUID(item.strip()) for item in value.split(",") if item.strip()))
    except ValueError as exc:
        raise ServiceError(
            422,
            "Invalid channel selection",
            "Selected channels must be comma-separated UUID values.",
            "invalid_channel_selection",
        ) from exc


def _channel_schema(record: explorer_repository.ExploreChannelRecord) -> ExploreChannel:
    return ExploreChannel(
        channel_id=record.channel_id,
        device_id=record.device_id,
        device_name=record.device_name,
        feature_id=record.feature_id,
        feature_slug=record.feature_slug,
        feature_name=record.feature_name,
        channel_name=record.channel_name,
        metric_code=record.metric_code,
        metric_name=record.metric_name,
        metric_group=record.metric_group,
        unit_code=record.unit_code,
        unit_symbol=record.unit_symbol,
        unit_confirmation_status=record.unit_confirmation_status,
        installation_depth_cm=record.installation_depth_cm,
        position_label=record.position_label,
        expected_reporting_interval_seconds=record.expected_reporting_interval_seconds,
        reporting_schedule_anchor_at=record.reporting_schedule_anchor_at,
        reporting_jitter_tolerance_seconds=record.reporting_jitter_tolerance_seconds,
        water_level_reference_or_datum=record.water_level_reference_or_datum,
    )


def _safe_warning_explanation(quality_flag: str) -> str:
    if quality_flag == "out_of_range":
        return "Observation falls outside a controlled definition-level validity bound."
    if quality_flag == "suspect":
        return "Observation was marked suspect by the configured quality rule."
    return "Observation was flagged by the configured quality rule."


def get_explorer(
    session: Session,
    settings: Settings,
    *,
    start: datetime,
    end: datetime,
    site_id: UUID | None,
    feature: str | None,
    metric_group: MetricGroup,
    channels: str | None,
) -> ExploreResponse:
    if metric_group is MetricGroup.OPERATIONAL:
        raise ServiceError(
            422,
            "Invalid metric group",
            "Time Explorer supports hydrology, soil, or weather groups.",
            "invalid_metric_group",
        )
    start, end = validate_time_window(
        start, end, max_range_days=settings.max_measurement_range_days
    )
    site = (
        site_repository.get_site(session, site_id)
        if site_id is not None
        else site_repository.get_default_site(session)
    )
    if site is None:
        raise ServiceError(404, "Site not found", "No matching site exists.", "not_found")

    is_replay_site = overview_repository.has_test_device(session, site.id)
    is_proxy_site = overview_repository.has_proxy_device(session, site.id)
    reference_time = (
        datetime.now(UTC)
        if is_proxy_site
        else current_site_reference_time(session, site.id, demo_mode=settings.demo_mode)
    )
    device_records = explorer_repository.list_devices(
        session, site_id=site.id, feature_slug=feature
    )
    channel_records = explorer_repository.list_channels(
        session,
        site_id=site.id,
        feature_slug=feature,
        metric_group=metric_group.value,
    )
    requested = _parse_selected_channels(channels)
    available_by_id = {item.channel_id: item for item in channel_records}
    selected_ids = list(available_by_id) if requested is None else requested
    unknown = set(selected_ids) - set(available_by_id)
    if unknown:
        raise ServiceError(
            422,
            "Invalid channel selection",
            "One or more selected channels are outside the active feature or metric group.",
            "invalid_channel_selection",
        )
    selected_records = [available_by_id[identifier] for identifier in selected_ids]
    total = explorer_repository.count_observations(
        session, channel_ids=selected_ids, start=start, end=end
    )
    if total > settings.max_measurement_result_rows:
        raise ServiceError(
            422,
            "Explorer result set too large",
            (
                f"The request matches {total} observations; the maximum is "
                f"{settings.max_measurement_result_rows}. Narrow the period or channel selection."
            ),
            "result_set_too_large",
        )
    observation_records = explorer_repository.list_observations(
        session, channel_ids=selected_ids, start=start, end=end
    )
    by_channel: dict[UUID, list[explorer_repository.ExploreMeasurementRecord]] = defaultdict(list)
    for observation in observation_records:
        by_channel[observation.channel_id].append(observation)

    series: list[ExploreSeries] = []
    for channel in selected_records:
        records = by_channel[channel.channel_id]
        period_observations = [
            PeriodObservation(
                measurement_id=item.measurement_id,
                measured_at=item.measured_at,
                received_at=item.received_at,
                numeric_value=item.numeric_value,
                quality_flag=item.quality_flag,
            )
            for item in records
        ]
        coverage = calculate_coverage(
            period_observations,
            start=start,
            end=end,
            interval_seconds=channel.expected_reporting_interval_seconds,
            anchor_at=channel.reporting_schedule_anchor_at,
            jitter_tolerance_seconds=channel.reporting_jitter_tolerance_seconds,
        )
        summary = calculate_period_summary(
            channel.metric_code,
            period_observations,
            coverage,
            interval_seconds=channel.expected_reporting_interval_seconds,
        )
        timing_by_id = {item.measurement_id: item for item in coverage.observation_timing}
        points = []
        for item in records:
            timing = timing_by_id[item.measurement_id]
            points.append(
                ExplorePoint(
                    measurement_id=item.measurement_id,
                    measured_at=item.measured_at,
                    received_at=item.received_at,
                    numeric_value=float(item.numeric_value),
                    quality_flag=item.quality_flag,
                    included_in_summary=item.measurement_id in summary.included_measurement_ids,
                    expected_slot_at=timing.expected_slot_at,
                    timing_status=timing.timing_status,
                    transmission_delay_seconds=timing.transmission_delay_seconds,
                )
            )
        series.append(
            ExploreSeries(
                channel=_channel_schema(channel),
                points=points,
                summary=ExploreSummary(
                    status=summary.status,
                    status_detail=summary.status_detail,
                    statistics=[
                        ExploreSummaryStatistic(
                            code=item.code,
                            label=item.label,
                            value=item.value,
                            observed_at=item.observed_at,
                        )
                        for item in summary.statistics
                    ],
                ),
                coverage=ExploreCoverage(
                    status=coverage.status,
                    status_detail=coverage.status_detail,
                    expected_observations=coverage.expected_observations,
                    received_observations=coverage.received_observations,
                    valid_observations=coverage.valid_observations,
                    flagged_observations=coverage.flagged_observations,
                    missing_observations=coverage.missing_observations,
                    coverage_percentage=coverage.coverage_percentage,
                    late_observations=coverage.late_observations,
                    out_of_tolerance_observations=coverage.out_of_tolerance_observations,
                    duplicate_slot_observations=coverage.duplicate_slot_observations,
                    missing_intervals=[
                        ExploreMissingInterval(
                            start=item.start,
                            end=item.end,
                            expected_slots=item.expected_slots,
                        )
                        for item in coverage.missing_intervals
                    ],
                ),
            )
        )

    warning_count = explorer_repository.count_quality_warnings(
        session,
        site_id=site.id,
        feature_slug=feature,
        start=start,
        end=end,
    )
    if warning_count > settings.max_measurement_result_rows:
        raise ServiceError(
            422,
            "Quality result set too large",
            "Narrow the period before loading the quality-warning drill-down.",
            "result_set_too_large",
        )
    warning_records = explorer_repository.list_quality_warnings(
        session,
        site_id=site.id,
        feature_slug=feature,
        start=start,
        end=end,
    )
    return ExploreResponse(
        site_id=site.id,
        site_name=site.name,
        display_timezone=site.display_timezone,
        start=start,
        end=end,
        time_window_semantics=(
            "Half-open UTC interval [start, end); scientific axis is measured_at."
        ),
        feature=feature,
        metric_group=metric_group.value,
        selected_channel_ids=selected_ids,
        available_devices=[
            ExploreDevice(
                device_id=item.device_id,
                device_name=item.device_name,
                device_type=item.device_type,
                sensor_configuration_status=item.sensor_configuration_status,
                feature_id=item.feature_id,
                feature_slug=item.feature_slug,
                feature_name=item.feature_name,
                current_freshness=freshness_schema(
                    calculate_freshness(
                        item.current_last_seen_at,
                        reference_time,
                        settings.device_stale_after_minutes,
                        settings.device_offline_after_minutes,
                        demo_mode=settings.demo_mode and not is_proxy_site,
                        status_basis="current_utc_time" if is_proxy_site else None,
                    )
                ),
            )
            for item in device_records
        ],
        available_channels=[_channel_schema(item) for item in channel_records],
        series=series,
        quality_warnings=[
            QualityWarning(
                measurement_id=item.measurement_id,
                device_name=item.device_name,
                channel_name=item.channel_name,
                observation_time=item.measured_at,
                received_at=item.received_at,
                quality_flag=item.quality_flag,
                explanation=_safe_warning_explanation(item.quality_flag),
                excluded_from_summaries=True,
            )
            for item in warning_records
        ],
        reference_time=reference_time,
        synthetic=settings.demo_mode and not is_replay_site,
    )
