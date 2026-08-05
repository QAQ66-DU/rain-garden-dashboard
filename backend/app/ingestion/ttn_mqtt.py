from __future__ import annotations

import logging
import signal
import ssl
from threading import Event
from typing import Any, Protocol

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion

from app.core.config import Settings
from app.services.ttn_ingestion import (
    DEFAULT_TTN_PAYLOAD_LIMIT_BYTES,
    LIVE_MQTT_CONTEXT,
    PersistResult,
    TTNApplicationUpPayloadError,
    TTNIngestionContext,
    TTNIngestionPersistenceError,
)

logger = logging.getLogger(__name__)

OUTFLOW_A_TOPIC = "v3/rain-garden@ttn/devices/outflow-a/up"
MIN_RECONNECT_DELAY_SECONDS = 1
MAX_RECONNECT_DELAY_SECONDS = 30


class MQTTConfigurationError(ValueError):
    pass


class TTNJSONIngestor(Protocol):
    def ingest_json(
        self,
        payload: bytes,
        *,
        context: TTNIngestionContext,
        max_payload_bytes: int,
    ) -> PersistResult: ...


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


class MQTTMessageProcessor:
    """Thin MQTT adapter that delegates each message to the shared ingestion service."""

    def __init__(
        self,
        ingestor: TTNJSONIngestor,
        *,
        max_payload_bytes: int = DEFAULT_TTN_PAYLOAD_LIMIT_BYTES,
    ) -> None:
        self._ingestor = ingestor
        self._max_payload_bytes = max_payload_bytes

    def process(self, payload: bytes) -> PersistResult | None:
        try:
            result = self._ingestor.ingest_json(
                payload,
                context=LIVE_MQTT_CONTEXT,
                max_payload_bytes=self._max_payload_bytes,
            )
        except TTNApplicationUpPayloadError:
            logger.warning("Discarded malformed TTN MQTT message")
            return None
        except TTNIngestionPersistenceError as exc:
            logger.error(
                "Failed to process TTN MQTT message; error_type=%s",
                exc.error_type,
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


def run_mqtt_worker(
    settings: Settings,
    *,
    processor: MQTTMessageProcessor,
    stop_event: Event | None = None,
) -> None:
    api_key = require_mqtt_api_key(settings)
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
