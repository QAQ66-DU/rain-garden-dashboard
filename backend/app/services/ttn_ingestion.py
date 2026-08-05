from __future__ import annotations

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.repositories.ttn_replay import (
    LIVE_MQTT_CONTEXT as LIVE_MQTT_CONTEXT,
)
from app.db.repositories.ttn_replay import (
    OFFLINE_REPLAY_CONTEXT,
    ensure_ttn_testbed_inventory,
    persist_ttn_uplink,
    quarantine_event,
)
from app.db.repositories.ttn_replay import (
    PersistResult as PersistResult,
)
from app.db.repositories.ttn_replay import (
    TTNIngestionContext as TTNIngestionContext,
)
from app.ingestion.ttn_console import (
    NormalisedTTNUplink,
    TTNReplayParseError,
    normalise_application_up,
)
from app.models.device import Device

DEFAULT_TTN_PAYLOAD_LIMIT_BYTES = 262_144
SessionScope = Callable[[], AbstractContextManager[Session]]


class TTNApplicationUpPayloadError(ValueError):
    """A transport supplied an invalid bounded JSON ApplicationUp payload."""


class TTNIngestionPersistenceError(RuntimeError):
    """Persistence failed without exposing credentials or database connection details."""

    def __init__(self, error_type: str) -> None:
        self.error_type = error_type
        super().__init__("TTN ingestion persistence failed")


def decode_ttn_application_up(
    payload: bytes,
    *,
    max_payload_bytes: int = DEFAULT_TTN_PAYLOAD_LIMIT_BYTES,
) -> dict[str, Any]:
    """Decode a bounded UTF-8 JSON object independently of its input transport."""

    if len(payload) > max_payload_bytes:
        raise TTNApplicationUpPayloadError("TTN message exceeds the configured payload limit")
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TTNApplicationUpPayloadError(
            "TTN message must contain a valid UTF-8 JSON object"
        ) from exc
    if not isinstance(decoded, dict):
        raise TTNApplicationUpPayloadError("TTN message must contain a JSON object")
    return decoded


def ingest_normalised_ttn_uplink(
    session: Session,
    uplink: NormalisedTTNUplink,
    *,
    device: Device,
    context: TTNIngestionContext = OFFLINE_REPLAY_CONTEXT,
) -> PersistResult:
    """Persist one transport-independent, normalized TTN ApplicationUp."""

    return persist_ttn_uplink(session, uplink, device=device, context=context)


def ingest_ttn_application_up(
    session: Session,
    payload: dict[str, Any],
    *,
    raw_event: dict[str, Any],
    context: TTNIngestionContext,
) -> PersistResult:
    """Normalize and persist one ApplicationUp while preserving unsafe events privately."""

    from app.db.sync_catalog import sync_metric_catalog

    sync_metric_catalog(session)
    device = ensure_ttn_testbed_inventory(session, context=context)
    try:
        uplink = normalise_application_up(payload, raw_event=raw_event)
    except TTNReplayParseError as exc:
        created = quarantine_event(
            session,
            raw_event,
            failure_code=exc.failure_code,
            failure_detail=exc.detail,
            source=context.source,
        )
        return PersistResult("quarantined" if created else "duplicate_quarantine")
    return ingest_normalised_ttn_uplink(session, uplink, device=device, context=context)


class TTNIngestionService:
    """Transport-independent transaction boundary for TTN ApplicationUp ingestion."""

    def __init__(self, session_scope: SessionScope) -> None:
        self._session_scope = session_scope

    def ingest_application_up(
        self,
        payload: dict[str, Any],
        *,
        raw_event: dict[str, Any],
        context: TTNIngestionContext,
    ) -> PersistResult:
        """Map, validate, deduplicate, and persist one decoded ApplicationUp object."""

        try:
            with self._session_scope() as session:
                return ingest_ttn_application_up(
                    session,
                    payload,
                    raw_event=raw_event,
                    context=context,
                )
        except SQLAlchemyError as exc:
            raise TTNIngestionPersistenceError(type(exc).__name__) from exc

    def ingest_json(
        self,
        payload: bytes,
        *,
        context: TTNIngestionContext,
        max_payload_bytes: int = DEFAULT_TTN_PAYLOAD_LIMIT_BYTES,
    ) -> PersistResult:
        """Decode and ingest one bounded JSON message from any byte-oriented adapter."""

        application_up = decode_ttn_application_up(
            payload,
            max_payload_bytes=max_payload_bytes,
        )
        return self.ingest_application_up(
            application_up,
            raw_event=application_up,
            context=context,
        )
