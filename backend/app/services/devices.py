from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.repositories import devices as device_repository
from app.db.repositories.measurements import current_reference_time
from app.metric_catalog import METRICS_BY_CODE, get_unit
from app.models.enums import DeviceType
from app.schemas.device import (
    DeviceDetail,
    DeviceList,
    DevicePublic,
    DeviceTelemetryPublic,
    MonitoringFeaturePublic,
    SensorChannelPublic,
)
from app.services.errors import ServiceError
from app.services.status import ConnectivityStatus, calculate_freshness
from app.services.transformers import freshness_schema, measurement_value
from app.utils.cursors import decode_device_cursor, encode_cursor


def _validate_device_type(device_type: str | None) -> str | None:
    if device_type is None:
        return None
    allowed = {item.value for item in DeviceType}
    if device_type not in allowed:
        raise ServiceError(
            422,
            "Invalid device type",
            "The device type is not part of the controlled vocabulary.",
            "invalid_device_type",
        )
    return device_type


def _device_public(
    row: device_repository.DeviceWithSite,
    latest: list[device_repository.LatestMeasurement],
    *,
    reference_time: datetime,
    settings: Settings,
) -> DevicePublic:
    freshness = calculate_freshness(
        row.device.last_seen_at,
        reference_time,
        settings.device_stale_after_minutes,
        settings.device_offline_after_minutes,
        demo_mode=settings.demo_mode,
        status_basis=("replay_dataset_reference_time" if row.device.is_test_device else None),
    )
    battery = next((record for record in latest if record.metric_code == "battery_voltage_v"), None)
    return DevicePublic(
        id=row.device.id,
        site_id=row.device.site_id,
        site_name=row.site_name,
        monitoring_feature=(
            MonitoringFeaturePublic(
                id=row.feature_id,
                public_slug=row.feature_slug,
                display_name=row.feature_name,
                feature_type=row.feature_type,
            )
            if row.feature_id is not None
            and row.feature_slug is not None
            and row.feature_name is not None
            and row.feature_type is not None
            else None
        ),
        display_name=row.device.display_name,
        device_type=row.device.device_type,
        sensor_configuration_status=row.device.sensor_configuration_status,
        operational_override=row.device.operational_override,
        last_seen_at=row.device.last_seen_at,
        location_disclosure=row.device.location_disclosure,
        environment=row.device.environment,
        source_system=row.device.source_system,
        ingestion_mode=row.device.ingestion_mode,
        provenance=row.device.provenance,
        is_test_device=row.device.is_test_device,
        freshness=freshness_schema(freshness),
        latest_battery=measurement_value(battery) if battery else None,
    )


def list_devices(
    session: Session,
    settings: Settings,
    *,
    page_size: int,
    cursor: str | None,
    search: str | None,
    site_id: UUID | None,
    feature_slug: str | None,
    device_type: str | None,
    status: ConnectivityStatus | None,
) -> DeviceList:
    reference_time = current_reference_time(session, demo_mode=settings.demo_mode)
    after = decode_device_cursor(cursor) if cursor else None
    rows = device_repository.list_devices(
        session,
        page_size=page_size,
        after=after,
        search=search,
        site_id=site_id,
        feature_slug=feature_slug,
        device_type=_validate_device_type(device_type),
        status=status,
        reference_time=reference_time,
        stale_minutes=settings.device_stale_after_minutes,
        offline_minutes=settings.device_offline_after_minutes,
    )
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    item_reference_times = [row.site_reference_time or reference_time for row in rows]
    latest = device_repository.latest_measurements_by_channel(
        session, [row.device.id for row in rows]
    )
    contains_replay_data = any(row.device.is_test_device for row in rows)
    next_cursor = None
    if has_more and rows:
        last = rows[-1].device
        next_cursor = encode_cursor(
            {
                "test_rank": "1" if last.is_test_device else "0",
                "name": last.display_name.lower(),
                "id": str(last.id),
            }
        )
    return DeviceList(
        items=[
            _device_public(
                row,
                latest.get(row.device.id, []),
                reference_time=row.site_reference_time or reference_time,
                settings=settings,
            )
            for row in rows
        ],
        next_cursor=next_cursor,
        reference_time=max(item_reference_times, default=reference_time),
        synthetic=settings.demo_mode and not contains_replay_data,
        contains_replay_data=contains_replay_data,
    )


def get_device(session: Session, settings: Settings, device_id: UUID) -> DeviceDetail:
    row = device_repository.get_device(session, device_id)
    if row is None:
        raise ServiceError(
            404, "Device not found", "The requested device does not exist.", "not_found"
        )
    fallback_reference_time = current_reference_time(session, demo_mode=settings.demo_mode)
    reference_time = row.site_reference_time or fallback_reference_time
    latest = device_repository.latest_measurements_by_channel(session, [device_id]).get(
        device_id, []
    )
    base = _device_public(row, latest, reference_time=reference_time, settings=settings)
    channels = [
        SensorChannelPublic(
            id=channel.id,
            channel_code=channel.channel_code,
            display_name=channel.display_name,
            metric_code=channel.metric_code,
            metric_name=definition.display_name,
            unit_code=channel.unit_code,
            unit_symbol=get_unit(channel.unit_code).unit_symbol if channel.unit_code else None,
            unit_confirmation_status=channel.unit_confirmation_status,
            installation_depth_cm=channel.depth_cm,
            depth_cm=channel.depth_cm,
            position_label=channel.position_label,
            expected_reporting_interval_seconds=channel.expected_reporting_interval_seconds,
            reporting_schedule_anchor_at=channel.reporting_schedule_anchor_at,
            reporting_jitter_tolerance_seconds=channel.reporting_jitter_tolerance_seconds,
            water_level_reference_or_datum=channel.water_level_reference_or_datum,
            scientific_meaning=channel.scientific_meaning,
            verification_status=channel.verification_status,
            timestamp_basis=channel.timestamp_basis,
            active=channel.active,
        )
        for channel, definition in device_repository.list_channels(session, device_id)
    ]
    telemetry = device_repository.get_telemetry(session, device_id)
    return DeviceDetail(
        **base.model_dump(),
        channels=channels,
        latest_measurements=[measurement_value(item) for item in latest],
        telemetry=(
            DeviceTelemetryPublic(
                observed_at=telemetry.observed_at,
                battery_percent=(
                    float(telemetry.battery_percent)
                    if telemetry.battery_percent is not None
                    else None
                ),
                firmware_version=telemetry.firmware_version,
                hardware_version=telemetry.hardware_version,
                measurement_interval_value=(
                    float(telemetry.measurement_interval_value)
                    if telemetry.measurement_interval_value is not None
                    else None
                ),
                measurement_interval_unit=telemetry.measurement_interval_unit,
                latest_rssi_dbm=(
                    float(telemetry.latest_rssi_dbm)
                    if telemetry.latest_rssi_dbm is not None
                    else None
                ),
                latest_snr_db=(
                    float(telemetry.latest_snr_db) if telemetry.latest_snr_db is not None else None
                ),
                gateway=telemetry.gateway_alias,
            )
            if telemetry is not None
            else None
        ),
    )


def validate_metric_code(metric_code: str | None) -> str | None:
    if metric_code is not None and metric_code not in METRICS_BY_CODE:
        raise ServiceError(
            422,
            "Invalid metric code",
            "The metric code is not part of the controlled vocabulary.",
            "invalid_metric_code",
        )
    return metric_code
