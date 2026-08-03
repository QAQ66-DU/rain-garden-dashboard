from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories.ttn_replay import (
    OFFLINE_REPLAY_CONTEXT,
    PersistResult,
    TTNIngestionContext,
    ensure_ttn_testbed_inventory,
    persist_ttn_uplink,
    quarantine_event,
)
from app.ingestion.ttn_console import (
    NormalisedTTNUplink,
    TTNReplayParseError,
    normalise_application_up,
)
from app.models.device import Device


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
