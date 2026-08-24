from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.ttn_console import PARSER_VERSION, NormalisedTTNUplink
from app.ingestion.ttn_devices import (
    TTN_APPLICATION_ID,
    TTN_DEVICE_MAPPINGS,
    TTN_PROXY_FEATURE_NAME,
    TTN_PROXY_FEATURE_SLUG,
    TTN_PROXY_SITE_NAME,
)
from app.models.device import Device
from app.models.device_telemetry import DeviceTelemetry
from app.models.measurement import Measurement
from app.models.monitoring_feature import MonitoringFeature
from app.models.sensor_channel import SensorChannel
from app.models.site import Site
from app.models.ttn_replay_quarantine import TTNReplayQuarantine
from app.models.uplink_event import UplinkEvent

TTN_DEVICE_ID = "outflow-a"
REPLAY_SOURCE = "ttn_offline_replay"
REPLAY_PROVENANCE = "exported_live_data"
LIVE_MQTT_SOURCE = "ttn_mqtt"
LIVE_MQTT_PROVENANCE = "proxy"
# Kept as import aliases for the existing offline replay compatibility surface.
TTN_TESTBED_SITE_NAME = TTN_PROXY_SITE_NAME
TTN_TESTBED_FEATURE_SLUG = TTN_PROXY_FEATURE_SLUG


@dataclass(frozen=True, slots=True)
class TTNIngestionContext:
    source: str
    ingestion_mode: str
    provenance: str
    gateway_alias: str


OFFLINE_REPLAY_CONTEXT = TTNIngestionContext(
    source=REPLAY_SOURCE,
    ingestion_mode="offline_replay",
    provenance=REPLAY_PROVENANCE,
    gateway_alias="Replay gateway (identifier withheld)",
)
LIVE_MQTT_CONTEXT = TTNIngestionContext(
    source=LIVE_MQTT_SOURCE,
    ingestion_mode="live_mqtt",
    provenance=LIVE_MQTT_PROVENANCE,
    gateway_alias="TTN gateway (identifier withheld)",
)


@dataclass(frozen=True, slots=True)
class PersistResult:
    outcome: str
    measurements_created: int = 0
    status_processed: bool = False


def _stable_uuid(label: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"rain-garden-dashboard:{label}")


def _identity_hash(uplink: NormalisedTTNUplink) -> str:
    identity = "\x1f".join(
        (
            uplink.application_id,
            uplink.device_id,
            uplink.session_key_id,
            str(uplink.f_port),
            str(uplink.f_cnt),
        )
    )
    return hashlib.sha256(identity.encode()).hexdigest()


def _raw_hash(raw_event: dict[str, object]) -> str:
    serialized = json.dumps(raw_event, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _ensure_proxy_site(session: Session) -> tuple[Site, MonitoringFeature]:
    site_id = _stable_uuid("site:ttn-testbed")
    site = session.get(Site, site_id)
    if site is None:
        site = Site(
            id=site_id,
            name=TTN_PROXY_SITE_NAME,
            description="Live proxy sensor data; these devices are not deployed at Orchard Park.",
            public_location_label="Proxy network; not Orchard Park",
            location_disclosure="withheld",
            private_latitude=None,
            private_longitude=None,
            display_timezone="Europe/London",
            active=True,
        )
        session.add(site)
        session.flush()
    else:
        site.name = TTN_PROXY_SITE_NAME
        site.description = "Live proxy sensor data; these devices are not deployed at Orchard Park."
        site.public_location_label = "Proxy network; not Orchard Park"
        site.location_disclosure = "withheld"
        site.active = True

    feature_id = _stable_uuid("feature:ttn-testbed")
    feature = session.get(MonitoringFeature, feature_id)
    if feature is None:
        feature = MonitoringFeature(
            id=feature_id,
            site_id=site.id,
            public_slug=TTN_PROXY_FEATURE_SLUG,
            display_name=TTN_PROXY_FEATURE_NAME,
            feature_type="testbed",
            active=True,
        )
        session.add(feature)
        session.flush()
    else:
        feature.site_id = site.id
        feature.public_slug = TTN_PROXY_FEATURE_SLUG
        feature.display_name = TTN_PROXY_FEATURE_NAME
        feature.feature_type = "testbed"
        feature.active = True
    return site, feature


def ensure_ttn_proxy_inventory(
    session: Session,
    *,
    context: TTNIngestionContext = LIVE_MQTT_CONTEXT,
    include_all_devices: bool = True,
) -> dict[str, Device]:
    site, feature = _ensure_proxy_site(session)
    mappings = (
        TTN_DEVICE_MAPPINGS.values()
        if include_all_devices
        else (TTN_DEVICE_MAPPINGS[TTN_DEVICE_ID],)
    )
    devices: dict[str, Device] = {}
    for mapping in mappings:
        device = session.scalar(
            select(Device).where(Device.external_device_id == mapping.device_id)
        )
        if device is None:
            device = Device(
                id=_stable_uuid(f"device:{mapping.device_id}"),
                site_id=site.id,
                monitoring_feature_id=feature.id,
                external_device_id=mapping.device_id,
                display_name=mapping.device_id,
                device_type=mapping.device_type,
                sensor_configuration_status="pending",
                operational_override=None,
                last_seen_at=None,
                private_latitude=None,
                private_longitude=None,
                location_disclosure="withheld",
                environment="proxy",
                source_system="ttn",
                ingestion_mode=None,
                provenance=context.provenance,
                is_test_device=True,
            )
            session.add(device)
            session.flush()
        elif device.site_id != site.id or not device.is_test_device:
            raise ValueError(
                f"The {mapping.device_id} external identifier is already assigned "
                "outside the TTN proxy network"
            )
        else:
            device.monitoring_feature_id = feature.id
            device.display_name = mapping.device_id
            device.device_type = mapping.device_type
            device.sensor_configuration_status = "pending"
            device.environment = "proxy"
            device.source_system = "ttn"
            if context.source == LIVE_MQTT_SOURCE:
                device.provenance = context.provenance

        existing = {
            channel.channel_code: channel
            for channel in session.scalars(
                select(SensorChannel).where(SensorChannel.device_id == device.id)
            )
        }
        for channel in existing.values():
            channel.active = False
        for channel_mapping in mapping.channels:
            stored_channel = existing.get(channel_mapping.channel_code)
            if stored_channel is None:
                stored_channel = SensorChannel(
                    id=_stable_uuid(
                        f"channel:{mapping.device_id}:{channel_mapping.measurement_id}"
                    ),
                    device_id=device.id,
                    channel_code=channel_mapping.channel_code,
                )
                session.add(stored_channel)
            stored_channel.display_name = channel_mapping.display_name
            stored_channel.metric_code = channel_mapping.metric_code
            stored_channel.unit_code = channel_mapping.unit_code
            stored_channel.unit_confirmation_status = (
                "confirmed" if channel_mapping.unit_code is not None else "pending"
            )
            stored_channel.depth_cm = None
            stored_channel.position_label = None
            stored_channel.expected_reporting_interval_seconds = None
            stored_channel.reporting_schedule_anchor_at = None
            stored_channel.reporting_jitter_tolerance_seconds = None
            stored_channel.water_level_reference_or_datum = None
            stored_channel.scientific_meaning = channel_mapping.scientific_meaning
            stored_channel.verification_status = channel_mapping.verification_status
            stored_channel.timestamp_basis = "ttn_received_at"
            stored_channel.active = True
            stored_channel.channel_metadata = {
                "ttn_measurement_id": channel_mapping.measurement_id,
                "decoded_type": channel_mapping.decoded_type,
                "interpretation_status": (
                    "confirmed_metric_and_unit"
                    if channel_mapping.unit_code is not None
                    else (
                        "decoder_label_known_unit_pending"
                        if channel_mapping.scientific_meaning
                        else "unverified"
                    )
                ),
            }
        devices[mapping.device_id] = device
    if context.source == LIVE_MQTT_SOURCE:
        session.execute(
            update(UplinkEvent)
            .where(
                UplinkEvent.source == LIVE_MQTT_SOURCE,
                UplinkEvent.provenance != LIVE_MQTT_PROVENANCE,
            )
            .values(provenance=LIVE_MQTT_PROVENANCE)
        )
    session.flush()
    return devices


def ensure_ttn_testbed_inventory(
    session: Session, *, context: TTNIngestionContext = OFFLINE_REPLAY_CONTEXT
) -> Device:
    """Compatibility wrapper for the existing Outflow A offline replay path."""

    return ensure_ttn_proxy_inventory(
        session,
        context=context,
        include_all_devices=False,
    )[TTN_DEVICE_ID]


def quarantine_event(
    session: Session,
    raw_event: dict[str, object],
    *,
    failure_code: str,
    failure_detail: str | None,
    received_at: datetime | None = None,
    source: str = REPLAY_SOURCE,
) -> bool:
    key = _raw_hash(raw_event)
    existing = session.scalar(
        select(TTNReplayQuarantine).where(
            TTNReplayQuarantine.source == source,
            TTNReplayQuarantine.idempotency_key == key,
        )
    )
    if existing is not None:
        return False
    session.add(
        TTNReplayQuarantine(
            id=_stable_uuid(f"quarantine:{source}:{key}"),
            source=source,
            idempotency_key=key,
            event_name=(str(raw_event.get("name")) if raw_event.get("name") is not None else None),
            received_at=received_at,
            failure_code=failure_code,
            parser_version=PARSER_VERSION,
            failure_detail=failure_detail,
            raw_payload=raw_event,
        )
    )
    return True


def _update_telemetry(
    session: Session,
    device: Device,
    uplink: NormalisedTTNUplink,
    *,
    context: TTNIngestionContext,
) -> bool:
    telemetry = session.get(DeviceTelemetry, device.id)
    if telemetry is not None and uplink.received_at < telemetry.observed_at:
        return False
    if telemetry is None:
        telemetry = DeviceTelemetry(device_id=device.id, observed_at=uplink.received_at)
        session.add(telemetry)
    telemetry.observed_at = uplink.received_at
    telemetry.latest_rssi_dbm = uplink.network.rssi_dbm
    telemetry.latest_snr_db = uplink.network.snr_db
    telemetry.gateway_alias = context.gateway_alias if uplink.network.gateway_identifier else None
    if uplink.status is not None:
        telemetry.battery_percent = uplink.status.battery_percent
        telemetry.firmware_version = uplink.status.firmware_version
        telemetry.hardware_version = uplink.status.hardware_version
        telemetry.measurement_interval_value = uplink.status.measurement_interval_value
        telemetry.measurement_interval_unit = None
        telemetry.threshold_measurement_interval_value = (
            uplink.status.threshold_measurement_interval_value
        )
        return True
    return False


def persist_ttn_uplink(
    session: Session,
    uplink: NormalisedTTNUplink,
    *,
    device: Device | None,
    context: TTNIngestionContext = OFFLINE_REPLAY_CONTEXT,
) -> PersistResult:
    if (
        uplink.application_id != TTN_APPLICATION_ID
        or uplink.device_id not in TTN_DEVICE_MAPPINGS
        or device is None
        or device.external_device_id != uplink.device_id
    ):
        created = quarantine_event(
            session,
            uplink.raw_event,
            failure_code="unknown_ttn_device",
            failure_detail="No approved internal device mapping exists for this TTN identity",
            received_at=uplink.received_at,
            source=context.source,
        )
        return PersistResult("quarantined" if created else "duplicate_quarantine")

    idempotency_key = _identity_hash(uplink)
    existing = session.scalar(
        select(UplinkEvent).where(
            UplinkEvent.source == context.source,
            UplinkEvent.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return PersistResult("duplicate")

    event = UplinkEvent(
        id=_stable_uuid(f"uplink:{context.source}:{idempotency_key}"),
        device_id=device.id,
        source=context.source,
        idempotency_key=idempotency_key,
        external_event_identifier=uplink.external_event_identifier,
        received_at=uplink.received_at,
        measured_at=uplink.received_at,
        frame_counter=uplink.f_cnt,
        raw_payload=uplink.raw_event,
        payload_schema_version=uplink.parser_version,
        ingestion_status="accepted" if uplink.decoded_valid else "rejected",
        ingestion_error=uplink.invalid_reason,
        ingestion_mode=context.ingestion_mode,
        provenance=context.provenance,
    )
    try:
        with session.begin_nested():
            session.add(event)
            session.flush()
            channels = {
                int(channel.channel_metadata["ttn_measurement_id"]): channel
                for channel in session.scalars(
                    select(SensorChannel).where(SensorChannel.device_id == device.id)
                )
                if "ttn_measurement_id" in channel.channel_metadata
            }
            for item in uplink.measurements:
                channel = channels[item.measurement_id]
                session.add(
                    Measurement(
                        id=_stable_uuid(
                            f"measurement:{context.source}:{idempotency_key}:{item.measurement_id}"
                        ),
                        uplink_event_id=event.id,
                        device_id=device.id,
                        sensor_channel_id=channel.id,
                        numeric_value=item.value,
                        measured_at=uplink.received_at,
                        quality_flag="valid",
                        quality_notes=None,
                    )
                )
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(UplinkEvent).where(
                UplinkEvent.source == context.source,
                UplinkEvent.idempotency_key == idempotency_key,
            )
        )
        if existing is None:
            raise
        return PersistResult("duplicate")

    status_processed = _update_telemetry(session, device, uplink, context=context)
    if device.last_seen_at is None or uplink.received_at >= device.last_seen_at:
        device.last_seen_at = uplink.received_at
        device.ingestion_mode = context.ingestion_mode
        device.provenance = context.provenance
    return PersistResult(
        "inserted_invalid" if not uplink.decoded_valid else "inserted",
        measurements_created=len(uplink.measurements),
        status_processed=status_processed,
    )
