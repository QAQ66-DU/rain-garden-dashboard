import json
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import pytest
from app.db.repositories.ttn_replay import PersistResult
from app.ingestion import ttn_mqtt
from app.ingestion.ttn_console import normalise_application_up
from app.ingestion.ttn_mqtt import MQTTMessageProcessor, decode_mqtt_application_up
from sqlalchemy.orm import Session

FIXTURE = Path(__file__).parent / "fixtures" / "ttn" / "outflow-a-redacted.json"


def test_live_mqtt_envelope_converts_to_the_existing_canonical_uplink() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    application_up = fixture["events"][0]["data"]

    decoded = decode_mqtt_application_up(json.dumps(application_up).encode())
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


def test_malformed_json_does_not_stop_later_message_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    processed: list[dict[str, object]] = []

    def fake_ingest(
        _session: Session,
        payload: dict[str, object],
        **_kwargs: object,
    ) -> PersistResult:
        processed.append(payload)
        return PersistResult("duplicate")

    @contextmanager
    def session_scope() -> Generator[Session]:
        yield cast(Session, object())

    monkeypatch.setattr(ttn_mqtt, "ingest_ttn_application_up", fake_ingest)
    processor = MQTTMessageProcessor(session_scope)

    assert processor.process(b"not-json") is None
    assert processor.process(b'{"valid": "next-message"}') == PersistResult("duplicate")
    assert processed == [{"valid": "next-message"}]
