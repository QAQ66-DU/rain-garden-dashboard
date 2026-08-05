import json
from pathlib import Path

from app.ingestion.ttn_console import normalise_application_up
from app.ingestion.ttn_mqtt import MQTTMessageProcessor
from app.services.ttn_ingestion import (
    LIVE_MQTT_CONTEXT,
    PersistResult,
    TTNApplicationUpPayloadError,
    TTNIngestionContext,
    decode_ttn_application_up,
)

FIXTURE = Path(__file__).parent / "fixtures" / "ttn" / "outflow-a-redacted.json"


def test_live_mqtt_envelope_converts_to_the_existing_canonical_uplink() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    application_up = fixture["events"][0]["data"]

    decoded = decode_ttn_application_up(json.dumps(application_up).encode())
    canonical = normalise_application_up(decoded, raw_event=decoded)

    assert canonical.application_id == "synthetic-rain-garden"
    assert canonical.device_id == "synthetic-outflow-a"
    assert canonical.f_port == application_up["uplink_message"]["f_port"]
    assert canonical.f_cnt == application_up["uplink_message"]["f_cnt"]
    assert [(item.measurement_id, int(item.value)) for item in canonical.measurements] == [
        (1, 840),
        (2, 200),
    ]
    assert canonical.raw_event == application_up


def test_mqtt_adapter_delegates_messages_and_does_not_decode_or_persist() -> None:
    processed: list[tuple[bytes, TTNIngestionContext, int]] = []

    class FakeIngestor:
        def ingest_json(
            self,
            payload: bytes,
            *,
            context: TTNIngestionContext,
            max_payload_bytes: int,
        ) -> PersistResult:
            processed.append((payload, context, max_payload_bytes))
            return PersistResult("duplicate")

    processor = MQTTMessageProcessor(FakeIngestor(), max_payload_bytes=1_024)

    assert processor.process(b'{"valid": "next-message"}') == PersistResult("duplicate")
    assert processed == [(b'{"valid": "next-message"}', LIVE_MQTT_CONTEXT, 1_024)]


def test_malformed_json_does_not_stop_later_message_processing() -> None:
    class FakeIngestor:
        def ingest_json(
            self,
            payload: bytes,
            *,
            context: TTNIngestionContext,
            max_payload_bytes: int,
        ) -> PersistResult:
            del context, max_payload_bytes
            if payload == b"not-json":
                raise TTNApplicationUpPayloadError("invalid test payload")
            return PersistResult("duplicate")

    processor = MQTTMessageProcessor(FakeIngestor())

    assert processor.process(b"not-json") is None
    assert processor.process(b'{"valid": "next-message"}') == PersistResult("duplicate")
