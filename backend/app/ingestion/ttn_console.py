"""Pure parser for TTN Live Data console exports.

This module performs no network or database operations. The ApplicationUp
normaliser is intentionally separate so a future, separately approved ingress
adapter can reuse it without depending on the console-export envelope.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.ingestion.ttn_devices import TTN_DEVICE_MAPPINGS

FORWARD_EVENT_NAME = "as.up.data.forward"
PARSER_VERSION = "rain-garden-application-up-v2"


class TTNReplayParseError(ValueError):
    def __init__(self, failure_code: str, detail: str) -> None:
        super().__init__(detail)
        self.failure_code = failure_code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class NormalisedMeasurement:
    measurement_id: int
    value: Decimal


@dataclass(frozen=True, slots=True)
class NormalisedStatus:
    battery_percent: Decimal | None
    firmware_version: str | None
    hardware_version: str | None
    measurement_interval_value: Decimal | None
    threshold_measurement_interval_value: Decimal | None


@dataclass(frozen=True, slots=True)
class NormalisedNetworkMetadata:
    gateway_identifier: str | None
    rssi_dbm: Decimal | None
    snr_db: Decimal | None
    frequency: str | None


@dataclass(frozen=True, slots=True)
class NormalisedTTNUplink:
    application_id: str
    device_id: str
    received_at: datetime
    session_key_id: str
    f_port: int
    f_cnt: int
    frm_payload: str | None
    confirmed: bool | None
    correlation_ids: tuple[str, ...]
    external_event_identifier: str | None
    decoded_payload: dict[str, Any] | None
    decoded_valid: bool
    invalid_reason: str | None
    measurements: tuple[NormalisedMeasurement, ...]
    status: NormalisedStatus | None
    network: NormalisedNetworkMetadata
    raw_event: dict[str, Any]
    parser_version: str = PARSER_VERSION


def _require_mapping(value: Any, failure_code: str, detail: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TTNReplayParseError(failure_code, detail)
    return value


def _require_string(value: Any, failure_code: str, detail: str) -> str:
    if not isinstance(value, str) or not value:
        raise TTNReplayParseError(failure_code, detail)
    return value


def _require_nonnegative_int(value: Any, failure_code: str, detail: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TTNReplayParseError(failure_code, detail)
    return value


def _parse_datetime(value: Any) -> datetime:
    text = _require_string(value, "missing_received_at", "TTN received_at is required")
    # TTN console exports can contain nanoseconds; PostgreSQL/Python retain microseconds.
    normalized = re.sub(r"(\.\d{6})\d+(?=Z$|[+-]\d\d:\d\d$)", r"\1", text)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TTNReplayParseError("invalid_received_at", "TTN received_at is invalid") from exc
    if parsed.tzinfo is None:
        raise TTNReplayParseError("invalid_received_at", "TTN received_at must include a zone")
    return parsed.astimezone(UTC)


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _measurement_id(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    return None


def _flatten_messages(decoded: dict[str, Any]) -> list[dict[str, Any]] | None:
    groups = decoded.get("messages")
    if not isinstance(groups, list):
        return None
    if all(isinstance(message, dict) for message in groups):
        return groups
    messages: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, list):
            return None
        if not all(isinstance(message, dict) for message in group):
            return None
        messages.extend(group)
    return messages


def _normalise_status(messages: list[dict[str, Any]]) -> NormalisedStatus | None:
    status = next(
        (
            message
            for message in messages
            if "Battery(%)" in message
            or "Firmware Version" in message
            or "Hardware Version" in message
        ),
        None,
    )
    battery_message = next(
        (message for message in messages if message.get("type") == "upload_battery"),
        None,
    )
    interval_message = next(
        (message for message in messages if message.get("type") == "upload_interval"),
        None,
    )
    if status is None and battery_message is None and interval_message is None:
        return None
    status = status or {}
    battery_message = battery_message or {}
    interval_message = interval_message or {}
    firmware = status.get("Firmware Version")
    hardware = status.get("Hardware Version")
    return NormalisedStatus(
        battery_percent=_decimal(status.get("Battery(%)", battery_message.get("battery"))),
        firmware_version=str(firmware) if firmware is not None else None,
        hardware_version=str(hardware) if hardware is not None else None,
        measurement_interval_value=_decimal(
            status.get("measureInterval", interval_message.get("interval"))
        ),
        threshold_measurement_interval_value=_decimal(status.get("thresholdMeasureInterval")),
    )


def _normalise_network(uplink: dict[str, Any]) -> NormalisedNetworkMetadata:
    metadata = uplink.get("rx_metadata")
    first = metadata[0] if isinstance(metadata, list) and metadata else {}
    if not isinstance(first, dict):
        first = {}
    gateway_ids = first.get("gateway_ids")
    if not isinstance(gateway_ids, dict):
        gateway_ids = {}
    settings = uplink.get("settings")
    if not isinstance(settings, dict):
        settings = {}
    gateway = gateway_ids.get("gateway_id")
    frequency = settings.get("frequency")
    return NormalisedNetworkMetadata(
        gateway_identifier=str(gateway) if gateway is not None else None,
        rssi_dbm=_decimal(first.get("rssi")),
        snr_db=_decimal(first.get("snr")),
        frequency=str(frequency) if frequency is not None else None,
    )


def normalise_application_up(
    payload: dict[str, Any], *, raw_event: dict[str, Any]
) -> NormalisedTTNUplink:
    identifiers = _require_mapping(
        payload.get("end_device_ids"),
        "missing_device_identifiers",
        "ApplicationUp end_device_ids is required",
    )
    application_ids = _require_mapping(
        identifiers.get("application_ids"),
        "missing_application_identifier",
        "ApplicationUp application_ids is required",
    )
    application_id = _require_string(
        application_ids.get("application_id"),
        "missing_application_identifier",
        "TTN application_id is required",
    )
    device_id = _require_string(
        identifiers.get("device_id"),
        "missing_device_identifier",
        "TTN device_id is required",
    )
    mapping = TTN_DEVICE_MAPPINGS.get(device_id)
    received_at = _parse_datetime(payload.get("received_at"))
    uplink = _require_mapping(
        payload.get("uplink_message"),
        "missing_uplink_message",
        "ApplicationUp uplink_message is required",
    )
    session_key_id = _require_string(
        uplink.get("session_key_id"),
        "missing_idempotency_identity",
        "session_key_id is required for replay idempotency",
    )
    f_port = _require_nonnegative_int(
        uplink.get("f_port"),
        "missing_idempotency_identity",
        "f_port is required for replay idempotency",
    )
    f_cnt = _require_nonnegative_int(
        uplink.get("f_cnt"),
        "missing_idempotency_identity",
        "f_cnt is required for replay idempotency",
    )
    decoded_value = uplink.get("decoded_payload")
    decoded = decoded_value if isinstance(decoded_value, dict) else None
    decoded_valid = bool(
        decoded is not None and decoded.get("valid") is True and decoded.get("err") == 0
    )
    invalid_reason: str | None = None
    measurements: list[NormalisedMeasurement] = []
    status: NormalisedStatus | None = None
    if decoded_valid and decoded is not None:
        messages = _flatten_messages(decoded)
        if messages is None:
            decoded_valid = False
            invalid_reason = "malformed_decoded_messages"
        else:
            status = _normalise_status(messages)
            channel_mappings = (
                {channel.measurement_id: channel for channel in mapping.channels}
                if mapping is not None
                else {}
            )
            measurement_messages = [message for message in messages if "measurementId" in message]
            identifiers_seen = {
                _measurement_id(message.get("measurementId")) for message in measurement_messages
            }
            types_match = True
            for message in measurement_messages:
                mapped_id = _measurement_id(message.get("measurementId"))
                if (
                    mapped_id is None
                    or mapped_id not in channel_mappings
                    or message.get("type") != channel_mappings[mapped_id].decoded_type
                ):
                    types_match = False
                    break
            if (
                mapping is None
                or not identifiers_seen.issubset(channel_mappings)
                or not types_match
            ):
                decoded_valid = False
                invalid_reason = "unmapped_measurement_id"
            else:
                for message in measurement_messages:
                    measurement_id = _measurement_id(message.get("measurementId"))
                    value = _decimal(message.get("measurementValue"))
                    if measurement_id is None or value is None:
                        decoded_valid = False
                        invalid_reason = "malformed_measurement"
                        measurements.clear()
                        break
                    measurements.append(NormalisedMeasurement(measurement_id, value))
    else:
        invalid_reason = "decoded_payload_not_valid"

    correlation_values = payload.get("correlation_ids")
    correlations = (
        tuple(value for value in correlation_values if isinstance(value, str))
        if isinstance(correlation_values, list)
        else ()
    )
    external_identifier = raw_event.get("unique_id")
    frm_payload = uplink.get("frm_payload")
    confirmed = uplink.get("confirmed")
    return NormalisedTTNUplink(
        application_id=application_id,
        device_id=device_id,
        received_at=received_at,
        session_key_id=session_key_id,
        f_port=f_port,
        f_cnt=f_cnt,
        frm_payload=str(frm_payload) if frm_payload is not None else None,
        confirmed=confirmed if isinstance(confirmed, bool) else None,
        correlation_ids=correlations,
        external_event_identifier=(
            str(external_identifier) if external_identifier is not None else None
        ),
        decoded_payload=decoded,
        decoded_valid=decoded_valid,
        invalid_reason=invalid_reason,
        measurements=tuple(measurements) if decoded_valid else (),
        status=status if decoded_valid else None,
        network=_normalise_network(uplink),
        raw_event=raw_event,
    )


def parse_console_export_event(event: dict[str, Any]) -> NormalisedTTNUplink | None:
    if event.get("name") != FORWARD_EVENT_NAME:
        return None
    payload = _require_mapping(
        event.get("data"),
        "missing_application_up",
        "Console event data must contain an ApplicationUp object",
    )
    return normalise_application_up(payload, raw_event=event)
