from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.repositories import measurements as measurement_repository
from app.db.repositories.devices import get_device
from app.schemas.measurement import MeasurementPage, MeasurementValue
from app.services.devices import validate_metric_code
from app.services.errors import ServiceError
from app.services.time_windows import resolve_measurement_window
from app.utils.cursors import decode_measurement_cursor, encode_cursor


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
    device_row = get_device(session, device_id)
    if device_row is None:
        raise ServiceError(
            404, "Device not found", "The requested device does not exist.", "not_found"
        )
    metric_code = validate_metric_code(metric_code)
    reference_time = (
        datetime.now(UTC)
        if device_row.device.environment == "proxy"
        and device_row.device.ingestion_mode != "offline_replay"
        else measurement_repository.current_device_reference_time(
            session, device_id, demo_mode=settings.demo_mode
        )
    )
    start, end, default_applied = resolve_measurement_window(
        start,
        end,
        reference_time,
        default_range_days=settings.default_measurement_range_days,
        max_range_days=settings.max_measurement_range_days,
    )
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
                verification_status=item.verification_status,
                timestamp_basis=item.timestamp_basis,
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
        synthetic=settings.demo_mode and not device_row.device.is_test_device,
        provenance=device_row.device.provenance,
    )
