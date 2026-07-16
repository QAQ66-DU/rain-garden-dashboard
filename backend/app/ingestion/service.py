from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.analytics.quality import assess_measurement
from app.ingestion.contracts import CanonicalUplink
from app.models.device import Device
from app.models.enums import IngestionStatus
from app.models.measurement import Measurement
from app.models.sensor_channel import SensorChannel
from app.models.uplink_event import UplinkEvent


class CanonicalIngestionError(ValueError):
    """Canonical payload cannot be associated with configured devices/channels."""


@dataclass(frozen=True, slots=True)
class IngestionResult:
    event_id: UUID
    created: bool


def ingest_canonical_uplink(session: Session, payload: CanonicalUplink) -> IngestionResult:
    existing = session.scalar(
        select(UplinkEvent).where(
            UplinkEvent.source == payload.source,
            UplinkEvent.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        return IngestionResult(event_id=existing.id, created=False)

    device = session.scalar(
        select(Device).where(Device.external_device_id == payload.external_device_id)
    )
    if device is None:
        raise CanonicalIngestionError("Canonical uplink references an unknown device")

    channels = {
        channel.channel_code: channel
        for channel in session.scalars(
            select(SensorChannel).where(SensorChannel.device_id == device.id)
        )
    }
    unknown_channels = {
        measurement.channel_code
        for measurement in payload.measurements
        if measurement.channel_code not in channels
    }
    if unknown_channels:
        raise CanonicalIngestionError("Canonical uplink references an unknown sensor channel")

    event = UplinkEvent(
        id=payload.event_id,
        device_id=device.id,
        source=payload.source,
        idempotency_key=payload.idempotency_key,
        external_event_identifier=payload.external_event_identifier,
        received_at=payload.received_at,
        measured_at=payload.measured_at,
        frame_counter=payload.frame_counter,
        raw_payload=payload.raw_payload,
        payload_schema_version=payload.payload_schema_version,
        ingestion_status=IngestionStatus.ACCEPTED,
        ingestion_error=None,
    )
    try:
        with session.begin_nested():
            session.add(event)
            session.flush()
            for item in payload.measurements:
                channel = channels[item.channel_code]
                assessment = assess_measurement(channel.metric_code, item.numeric_value)
                session.add(
                    Measurement(
                        id=item.measurement_id,
                        uplink_event_id=event.id,
                        device_id=device.id,
                        sensor_channel_id=channel.id,
                        numeric_value=item.numeric_value,
                        measured_at=item.measured_at,
                        quality_flag=assessment.flag,
                        quality_notes=assessment.notes,
                    )
                )
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(UplinkEvent).where(
                UplinkEvent.source == payload.source,
                UplinkEvent.idempotency_key == payload.idempotency_key,
            )
        )
        if existing is None:
            raise
        return IngestionResult(event_id=existing.id, created=False)

    if device.last_seen_at is None or payload.received_at > device.last_seen_at:
        device.last_seen_at = payload.received_at
    return IngestionResult(event_id=event.id, created=True)
