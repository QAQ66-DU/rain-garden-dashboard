from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.repositories import measurements as measurement_repository
from app.db.repositories.devices import get_device
from app.schemas.measurement import MeasurementPage, MeasurementValue
from app.services.devices import validate_metric_code
from app.services.errors import ServiceError
from app.utils.cursors import decode_measurement_cursor, encode_cursor


def _normalize_time(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ServiceError(
            422,
            "Timezone required",
            "Measurement timestamps must include an explicit timezone offset.",
            "timezone_required",
        )
    return value.astimezone(UTC)


def _resolve_window(
    start: datetime | None,
    end: datetime | None,
    reference_time: datetime,
    settings: Settings,
) -> tuple[datetime, datetime, bool]:
    if (start is None) != (end is None):
        raise ServiceError(
            422,
            "Incomplete measurement range",
            "Provide both start and end timestamps, or omit both for the default range.",
            "incomplete_time_range",
        )
    default_applied = start is None
    if start is None or end is None:
        end = reference_time
        start = end - timedelta(days=settings.default_measurement_range_days)
    start = _normalize_time(start)
    end = _normalize_time(end)
    if start >= end:
        raise ServiceError(
            422,
            "Invalid measurement range",
            "The start timestamp must be earlier than the end timestamp.",
            "invalid_time_range",
        )
    if end - start > timedelta(days=settings.max_measurement_range_days):
        raise ServiceError(
            422,
            "Measurement range too large",
            f"The maximum permitted range is {settings.max_measurement_range_days} days.",
            "time_range_too_large",
        )
    return start, end, default_applied


def list_measurements(
    session: Session,
    settings: Settings,
    device_id: UUID,
    *,
    start: datetime | None,
    end: datetime | None,
    metric_code: str | None,
    sensor_channel_id: UUID | None,
    page_size: int,
    cursor: str | None,
) -> MeasurementPage:
    if get_device(session, device_id) is None:
        raise ServiceError(
            404, "Device not found", "The requested device does not exist.", "not_found"
        )
    metric_code = validate_metric_code(metric_code)
    reference_time = measurement_repository.current_reference_time(
        session, demo_mode=settings.demo_mode
    )
    start, end, default_applied = _resolve_window(start, end, reference_time, settings)
    total = measurement_repository.count_measurements(
        session,
        device_id=device_id,
        start=start,
        end=end,
        metric_code=metric_code,
        sensor_channel_id=sensor_channel_id,
    )
    if total > settings.max_measurement_result_rows:
        raise ServiceError(
            422,
            "Raw result set too large",
            (
                f"The request matches {total} rows; the maximum raw result size is "
                f"{settings.max_measurement_result_rows}. Narrow the time range, metric, or "
                "channel."
            ),
            "result_set_too_large",
        )
    after = decode_measurement_cursor(cursor) if cursor else None
    records = measurement_repository.list_measurements(
        session,
        device_id=device_id,
        start=start,
        end=end,
        metric_code=metric_code,
        sensor_channel_id=sensor_channel_id,
        after=after,
        page_size=page_size,
    )
    has_more = len(records) > page_size
    records = records[:page_size]
    next_cursor = None
    if has_more and records:
        last = records[-1]
        next_cursor = encode_cursor(
            {"measured_at": last.measured_at.isoformat(), "id": str(last.measurement_id)}
        )
    return MeasurementPage(
        items=[
            MeasurementValue(
                channel_id=item.channel_id,
                channel_code=item.channel_code,
                channel_name=item.channel_name,
                metric_code=item.metric_code,
                metric_name=item.metric_name,
                numeric_value=float(item.value),
                unit_code=item.unit_code,
                unit_symbol=item.unit_symbol,
                unit_confirmation_status=item.unit_confirmation_status,
                measured_at=item.measured_at,
                quality_flag=item.quality_flag,
                quality_notes=item.quality_notes,
                installation_depth_cm=item.depth_cm,
                depth_cm=item.depth_cm,
                position_label=item.position_label,
            )
            for item in records
        ],
        next_cursor=next_cursor,
        total_matching=total,
        start=start,
        end=end,
        reference_time=reference_time,
        default_range_applied=default_applied,
        synthetic=settings.demo_mode,
    )
