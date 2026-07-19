from app.db.repositories.devices import LatestMeasurement
from app.schemas.common import Freshness
from app.schemas.measurement import MeasurementValue
from app.services.status import FreshnessResult


def freshness_schema(result: FreshnessResult) -> Freshness:
    return Freshness(
        calculated_status=result.status,
        reference_time=result.reference_time,
        age_seconds=result.age_seconds,
        stale_after_minutes=result.stale_after_minutes,
        offline_after_minutes=result.offline_after_minutes,
        status_basis=result.status_basis,
    )


def measurement_value(record: LatestMeasurement) -> MeasurementValue:
    return MeasurementValue(
        channel_id=record.channel_id,
        channel_code=record.channel_code,
        channel_name=record.channel_name,
        metric_code=record.metric_code,
        metric_name=record.metric_name,
        numeric_value=float(record.value),
        unit_code=record.unit_code,
        unit_symbol=record.unit_symbol,
        unit_confirmation_status=record.unit_confirmation_status,
        measured_at=record.measured_at,
        quality_flag=record.quality_flag,
        quality_notes=record.quality_notes,
        installation_depth_cm=record.depth_cm,
        depth_cm=record.depth_cm,
        position_label=record.position_label,
    )
