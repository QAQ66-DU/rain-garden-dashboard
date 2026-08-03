from datetime import timedelta
from statistics import median
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.repositories import overview as overview_repository
from app.db.repositories import sites as site_repository
from app.db.repositories.measurements import current_site_reference_time
from app.schemas.overview import (
    DeviceStatusCounts,
    Overview,
    QualityWindow,
    SoilMoistureSummary,
)
from app.services.errors import ServiceError
from app.services.status import ConnectivityStatus, calculate_freshness
from app.services.transformers import measurement_value


def get_overview(session: Session, settings: Settings, site_id: UUID | None) -> Overview:
    site = (
        site_repository.get_site(session, site_id)
        if site_id is not None
        else site_repository.get_default_site(session)
    )
    if site is None:
        raise ServiceError(404, "Site not found", "No matching site exists.", "not_found")

    is_replay_site = overview_repository.has_test_device(session, site.id)
    reference_time = current_site_reference_time(session, site.id, demo_mode=settings.demo_mode)
    statuses = [
        calculate_freshness(
            last_seen,
            reference_time,
            settings.device_stale_after_minutes,
            settings.device_offline_after_minutes,
            demo_mode=settings.demo_mode,
        ).status
        for last_seen in overview_repository.device_last_seen_values(session, site.id)
    ]
    counts = DeviceStatusCounts(
        total=len(statuses),
        online=statuses.count(ConnectivityStatus.ONLINE),
        stale=statuses.count(ConnectivityStatus.STALE),
        offline=statuses.count(ConnectivityStatus.OFFLINE),
        unknown=statuses.count(ConnectivityStatus.UNKNOWN),
    )

    rainfall = overview_repository.latest_valid_metric(session, site.id, "rainfall_intensity")
    soil_records = overview_repository.latest_valid_soil_channels(session, site.id)
    soil_summary = None
    if soil_records:
        values = [item.value for item in soil_records]
        timestamps = [item.measured_at for item in soil_records]
        soil_summary = SoilMoistureSummary(
            metric_code="soil_moisture",
            unit_code=soil_records[0].unit_code,
            unit_symbol=soil_records[0].unit_symbol,
            unit_confirmation_status=soil_records[0].unit_confirmation_status,
            minimum=float(min(values)),
            median=float(median(values)),
            maximum=float(max(values)),
            contributing_channel_count=len(soil_records),
            timestamp_start=min(timestamps),
            timestamp_end=max(timestamps),
            contributing_channels=[measurement_value(item) for item in soil_records],
            comparability_note=(
                "Latest valid observations are shown as a spread; channels are not averaged or "
                "assumed comparable across depth, position, or time."
            ),
        )

    updated_at = overview_repository.last_data_update(session, site.id)
    if updated_at is None:
        quality = QualityWindow(start=None, end=None, warning_count=0)
    else:
        quality_start = updated_at - timedelta(hours=24)
        quality = QualityWindow(
            start=quality_start,
            end=updated_at,
            warning_count=overview_repository.quality_warning_count(
                session, site.id, quality_start, updated_at
            ),
        )
    return Overview(
        site_id=site.id,
        site_name=site.name,
        public_location_label=site.public_location_label,
        display_timezone=site.display_timezone,
        synthetic=settings.demo_mode and not is_replay_site,
        synthetic_notice=(
            "Offline replay data — not a live TTN connection."
            if is_replay_site
            else (
                "Synthetic demonstration data — not live observations."
                if settings.demo_mode
                else None
            )
        ),
        reference_time=reference_time,
        last_data_update=updated_at,
        devices=counts,
        latest_rainfall_intensity=measurement_value(rainfall) if rainfall else None,
        soil_moisture=soil_summary,
        data_quality=quality,
    )
