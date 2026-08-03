from __future__ import annotations

import json
import logging
import signal
import ssl
from collections.abc import Callable
from contextlib import AbstractContextManager
from threading import Event
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.repositories.ttn_replay import LIVE_MQTT_CONTEXT, PersistResult
from app.services.ttn_ingestion import ingest_ttn_application_up

logger = logging.getLogger(__name__)

OUTFLOW_A_TOPIC = "v3/rain-garden@ttn/devices/outflow-a/up"
MIN_RECONNECT_DELAY_SECONDS = 1
MAX_RECONNECT_DELAY_SECONDS = 30

SessionScope = Callable[[], AbstractContextManager[Session]]


class MQTTConfigurationError(ValueError):
    pass


class MQTTMessageError(ValueError):
    pass


def require_mqtt_api_key(settings: Settings) -> str:
    if settings.ttn_mqtt_topic != OUTFLOW_A_TOPIC:
        raise MQTTConfigurationError(
            "TTN_MQTT_TOPIC must remain restricted to the approved Outflow A uplink topic"
        )
    if settings.ttn_mqtt_api_key is None:
        raise MQTTConfigurationError(
            "TTN_MQTT_API_KEY is required when starting the live MQTT worker"
        )
    api_key = settings.ttn_mqtt_api_key.get_secret_value()
    if not api_key.strip():
        raise MQTTConfigurationError(
            "TTN_MQTT_API_KEY is required when starting the live MQTT worker"
        )
    return api_key


def decode_mqtt_application_up(
    payload: bytes, *, max_payload_bytes: int = 262_144
) -> dict[str, Any]:
    if len(payload) > max_payload_bytes:
        raise MQTTMessageError("MQTT message exceeds the configured payload limit")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MQTTMessageError("MQTT message must contain a valid UTF-8 JSON object") from exc
    if not isinstance(decoded, dict):
        raise MQTTMessageError("MQTT message must contain a JSON object")
    return decoded


class MQTTMessageProcessor:
    def __init__(self, session_scope: SessionScope, *, max_payload_bytes: int = 262_144) -> None:
        self._session_scope = session_scope
        self._max_payload_bytes = max_payload_bytes

    def process(self, payload: bytes) -> PersistResult | None:
        try:
            application_up = decode_mqtt_application_up(
                payload,
                max_payload_bytes=self._max_payload_bytes,
            )
        except MQTTMessageError:
            logger.warning("Discarded malformed TTN MQTT message")
            return None

        try:
            with self._session_scope() as session:
                result = ingest_ttn_application_up(
                    session,
                    application_up,
                    raw_event=application_up,
                    context=LIVE_MQTT_CONTEXT,
                )
        except SQLAlchemyError as exc:
            logger.error(
                "Failed to process TTN MQTT message; error_type=%s",
                type(exc).__name__,
            )
            return None

        logger.info(
            "Processed TTN MQTT message; outcome=%s measurements_created=%d",
            result.outcome,
            result.measurements_created,
        )
        return result


def build_mqtt_client(
    settings: Settings,
    *,
    api_key: str,
    processor: MQTTMessageProcessor,
) -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        protocol=MQTTProtocolVersion.MQTTv311,
    )
    client.username_pw_set(settings.ttn_mqtt_username, password=api_key)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.tls_insecure_set(False)
    client.reconnect_delay_set(
        min_delay=MIN_RECONNECT_DELAY_SECONDS,
        max_delay=MAX_RECONNECT_DELAY_SECONDS,
    )

    def on_connect(
        connected_client: mqtt.Client,
        _userdata: object,
        _flags: Any,
        reason_code: Any,
        _properties: Any,
    ) -> None:
        if reason_code != 0:
            logger.error("TTN MQTT connection rejected; reason=%s", reason_code)
            return
        connected_client.subscribe(settings.ttn_mqtt_topic)
        logger.info("Connected to TTN MQTT and subscribed to the approved Outflow A topic")

    def on_disconnect(
        _client: mqtt.Client,
        _userdata: object,
        _disconnect_flags: Any,
        reason_code: Any,
        _properties: Any,
    ) -> None:
        if reason_code != 0:
            logger.warning("TTN MQTT connection lost; bounded reconnect is active")

    def on_message(
        _client: mqtt.Client,
        _userdata: object,
        message: mqtt.MQTTMessage,
    ) -> None:
        processor.process(message.payload)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    return client


def run_mqtt_worker(settings: Settings, *, stop_event: Event | None = None) -> None:
    api_key = require_mqtt_api_key(settings)

    from app.db.session import SessionLocal

    processor = MQTTMessageProcessor(
        SessionLocal.begin,
        max_payload_bytes=settings.webhook_body_limit_bytes,
    )
    client = build_mqtt_client(settings, api_key=api_key, processor=processor)
    resolved_stop_event = stop_event or Event()

    def request_shutdown(_signum: int, _frame: object) -> None:
        logger.info("Stopping TTN MQTT worker")
        resolved_stop_event.set()

    if stop_event is None:
        signal.signal(signal.SIGINT, request_shutdown)
        signal.signal(signal.SIGTERM, request_shutdown)

    client.connect_async(settings.ttn_mqtt_host, settings.ttn_mqtt_port, keepalive=60)
    client.loop_start()
    logger.info("TTN MQTT worker started with TLS and bounded reconnect")
    try:
        resolved_stop_event.wait()
    finally:
        client.disconnect()
        client.loop_stop()
        logger.info("TTN MQTT worker stopped")
