from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast

import pytest
from app.services import ttn_ingestion
from app.services.ttn_ingestion import (
    LIVE_MQTT_CONTEXT,
    PersistResult,
    TTNApplicationUpPayloadError,
    TTNIngestionPersistenceError,
    TTNIngestionService,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


def test_shared_service_owns_decoding_transaction_and_raw_preservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = cast(Session, object())
    calls: list[tuple[Session, dict[str, Any], dict[str, Any], object]] = []

    @contextmanager
    def session_scope() -> Generator[Session]:
        yield session

    def fake_ingest(
        received_session: Session,
        payload: dict[str, Any],
        *,
        raw_event: dict[str, Any],
        context: object,
    ) -> PersistResult:
        calls.append((received_session, payload, raw_event, context))
        return PersistResult("inserted", measurements_created=2)

    monkeypatch.setattr(ttn_ingestion, "ingest_ttn_application_up", fake_ingest)
    service = TTNIngestionService(session_scope)

    result = service.ingest_json(
        b'{"received_at":"2026-08-05T00:00:00Z"}', context=LIVE_MQTT_CONTEXT
    )

    expected = {"received_at": "2026-08-05T00:00:00Z"}
    assert result == PersistResult("inserted", measurements_created=2)
    assert calls == [(session, expected, expected, LIVE_MQTT_CONTEXT)]


def test_shared_service_accepts_decoded_input_from_a_non_byte_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = cast(Session, object())
    calls: list[tuple[dict[str, Any], dict[str, Any]]] = []

    @contextmanager
    def session_scope() -> Generator[Session]:
        yield session

    def fake_ingest(
        received_session: Session,
        payload: dict[str, Any],
        *,
        raw_event: dict[str, Any],
        context: object,
    ) -> PersistResult:
        assert received_session is session
        assert context is LIVE_MQTT_CONTEXT
        calls.append((payload, raw_event))
        return PersistResult("duplicate")

    monkeypatch.setattr(ttn_ingestion, "ingest_ttn_application_up", fake_ingest)
    service = TTNIngestionService(session_scope)
    application_up = {"received_at": "2026-08-05T00:00:00Z"}
    transport_envelope = {"application_up": application_up, "adapter": "future"}

    result = service.ingest_application_up(
        application_up,
        raw_event=transport_envelope,
        context=LIVE_MQTT_CONTEXT,
    )

    assert result == PersistResult("duplicate")
    assert calls == [(application_up, transport_envelope)]


def test_shared_service_rejects_invalid_json_before_opening_a_transaction() -> None:
    opened = False

    @contextmanager
    def session_scope() -> Generator[Session]:
        nonlocal opened
        opened = True
        yield cast(Session, object())

    service = TTNIngestionService(session_scope)

    with pytest.raises(TTNApplicationUpPayloadError):
        service.ingest_json(b"not-json", context=LIVE_MQTT_CONTEXT)

    assert opened is False


def test_shared_service_exposes_only_sanitized_persistence_failure_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def session_scope() -> Generator[Session]:
        yield cast(Session, object())

    def fail_ingestion(*_args: object, **_kwargs: object) -> PersistResult:
        raise OperationalError("statement", {}, RuntimeError("private connection detail"))

    monkeypatch.setattr(ttn_ingestion, "ingest_ttn_application_up", fail_ingestion)
    service = TTNIngestionService(session_scope)

    with pytest.raises(TTNIngestionPersistenceError) as caught:
        service.ingest_json(b"{}", context=LIVE_MQTT_CONTEXT)

    assert caught.value.error_type == "OperationalError"
    assert str(caught.value) == "TTN ingestion persistence failed"
