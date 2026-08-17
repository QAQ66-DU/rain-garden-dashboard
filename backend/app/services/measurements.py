import csv
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from uuid import UUID

from sqlalchemy.orm import Session

from app.analytics.chart_downsampling import time_bucket_min_max
from app.core.config import Settings
from app.db.repositories import devices as device_repository
from app.db.repositories import measurements as measurement_repository
from app.db.repositories.devices import DeviceWithSite, get_device
from app.models.sensor_channel import SensorChannel
from app.schemas.measurement import MeasurementChartSeries, MeasurementPage, MeasurementValue
from app.services.devices import validate_metric_code
from app.services.errors import ServiceError
from app.services.time_windows import resolve_measurement_window
from app.utils.cursors import decode_measurement_cursor, encode_cursor

CSV_HEADERS = (
    "observed_at",
    "device_id",
    "device_name",
    "channel_id",
    "channel_name",
    "measurement_value",
    "unit_code",
    "unit_confirmation_status",
    "verification_status",
    "quality_flag",
    "ingestion_mode",
    "provenance",
)


@dataclass(frozen=True, slots=True)
class MeasurementCsvExport:
    content: Iterator[str]
    filename: str


def _resolve_query(
    session: Session,
    settings: Settings,
    device_id: UUID,
    *,
    start: datetime | None,
    end: datetime | None,
    metric_code: str | None,
    sensor_channel_id: UUID | None,
) -> tuple[DeviceWithSite, datetime, datetime, datetime, bool, int]:
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
    resolved_start, resolved_end, default_applied = resolve_measurement_window(
        start,
        end,
        reference_time,
        default_range_days=settings.default_measurement_range_days,
        max_range_days=settings.max_measurement_range_days,
    )
    total = measurement_repository.count_measurements(
        session,
        device_id=device_id,
        start=resolved_start,
        end=resolved_end,
        metric_code=metric_code,
        sensor_channel_id=sensor_channel_id,
    )
    return device_row, resolved_start, resolved_end, reference_time, default_applied, total


def _utc_isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _filename_part(value: str, *, fallback: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or fallback


def _measurement_value(item: measurement_repository.MeasurementRecord) -> MeasurementValue:
    return MeasurementValue(
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


def _device_channel(session: Session, device_id: UUID, sensor_channel_id: UUID) -> SensorChannel:
    channel = next(
        (
            candidate
            for candidate, _ in device_repository.list_channels(session, device_id)
            if candidate.id == sensor_channel_id
        ),
        None,
    )
    if channel is None:
        raise ServiceError(
            404,
            "Sensor channel not found",
            "The selected sensor channel does not belong to the requested device.",
            "channel_not_found",
        )
    return channel


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
    device_row, start, end, reference_time, default_applied, total = _resolve_query(
        session,
        settings,
        device_id,
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
    metric_code = validate_metric_code(metric_code)
    records = measurement_repository.list_measurements(
        session,
        device_id=device_id,
        start=start,
        end=end,
        metric_code=metric_code,
        sensor_channel_id=sensor_channel_id,
        after=decode_measurement_cursor(cursor) if cursor else None,
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
        items=[_measurement_value(item) for item in records],
        next_cursor=next_cursor,
        total_matching=total,
        start=start,
        end=end,
        reference_time=reference_time,
        default_range_applied=default_applied,
        synthetic=settings.demo_mode and not device_row.device.is_test_device,
        provenance=device_row.device.provenance,
    )


def chart_measurements(
    session: Session,
    settings: Settings,
    device_id: UUID,
    *,
    start: datetime | None,
    end: datetime | None,
    sensor_channel_id: UUID,
) -> MeasurementChartSeries:
    device_row, start, end, reference_time, default_applied, total = _resolve_query(
        session,
        settings,
        device_id,
        start=start,
        end=end,
        metric_code=None,
        sensor_channel_id=sensor_channel_id,
    )
    _device_channel(session, device_id, sensor_channel_id)
    records = measurement_repository.iter_measurements(
        session,
        device_id=device_id,
        start=start,
        end=end,
        metric_code=None,
        sensor_channel_id=sensor_channel_id,
    )
    downsampling_applied = total > settings.chart_measurement_target_points
    selected = (
        time_bucket_min_max(
            records,
            start=start,
            end=end,
            target_points=settings.chart_measurement_target_points,
        )
        if downsampling_applied
        else list(records)
    )
    return MeasurementChartSeries(
        items=[_measurement_value(item) for item in selected],
        total_matching=total,
        points_returned=len(selected),
        downsampling_applied=downsampling_applied,
        start=start,
        end=end,
        reference_time=reference_time,
        default_range_applied=default_applied,
        synthetic=settings.demo_mode and not device_row.device.is_test_device,
        provenance=device_row.device.provenance,
    )


def _csv_line(values: Sequence[str]) -> str:
    buffer = StringIO(newline="")
    csv.writer(buffer, lineterminator="\r\n").writerow(values)
    return buffer.getvalue()


def _csv_content(
    records: Iterator[measurement_repository.MeasurementRecord],
    *,
    device_id: UUID,
    device_name: str,
) -> Iterator[str]:
    yield _csv_line(CSV_HEADERS)
    for record in records:
        yield _csv_line(
            (
                _utc_isoformat(record.measured_at),
                str(device_id),
                device_name,
                str(record.channel_id),
                record.channel_name,
                format(record.value, "f"),
                record.unit_code or "",
                record.unit_confirmation_status,
                record.verification_status,
                record.quality_flag,
                record.ingestion_mode or "",
                record.provenance or "",
            )
        )


def export_measurements_csv(
    session: Session,
    settings: Settings,
    device_id: UUID,
    *,
    start: datetime,
    end: datetime,
    sensor_channel_id: UUID,
) -> MeasurementCsvExport:
    device_row, start, end, _, _, _ = _resolve_query(
        session,
        settings,
        device_id,
        start=start,
        end=end,
        metric_code=None,
        sensor_channel_id=sensor_channel_id,
    )
    channel = _device_channel(session, device_id, sensor_channel_id)
    records = measurement_repository.iter_measurements(
        session,
        device_id=device_id,
        start=start,
        end=end,
        metric_code=None,
        sensor_channel_id=sensor_channel_id,
    )
    device_part = _filename_part(device_row.device.display_name, fallback="device")
    channel_part = _filename_part(channel.display_name, fallback="channel")
    filename = (
        f"{device_part}_{channel_part}_{start.date().isoformat()}_{end.date().isoformat()}.csv"
    )
    return MeasurementCsvExport(
        content=_csv_content(
            records,
            device_id=device_id,
            device_name=device_row.device.display_name,
        ),
        filename=filename,
    )
