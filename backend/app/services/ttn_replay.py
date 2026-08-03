from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.repositories.ttn_replay import (
    ensure_ttn_testbed_inventory,
    persist_ttn_uplink,
    quarantine_event,
)
from app.db.sync_catalog import sync_metric_catalog
from app.ingestion.ttn_console import (
    FORWARD_EVENT_NAME,
    TTNReplayParseError,
    parse_console_export_event,
)


@dataclass(frozen=True, slots=True)
class ReplaySummary:
    total_events: int
    selected_uplinks: int
    raw_inserted: int
    duplicates_skipped: int
    measurements_created: int
    invalid_preserved: int
    status_processed: int
    quarantined: int
    failed: int


def _load_events(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fixture_file:
        value = json.load(fixture_file)
    if isinstance(value, dict) and isinstance(value.get("events"), list):
        value = value["events"]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("TTN replay input must be a JSON array of console event objects")
    return value


def replay_ttn_export(session: Session, path: Path) -> ReplaySummary:
    events = _load_events(path)
    selected = [event for event in events if event.get("name") == FORWARD_EVENT_NAME]
    sync_metric_catalog(session)
    device = ensure_ttn_testbed_inventory(session)

    parsed = []
    quarantined = 0
    duplicate_quarantine = 0
    for event in selected:
        try:
            uplink = parse_console_export_event(event)
        except TTNReplayParseError as exc:
            created = quarantine_event(
                session,
                event,
                failure_code=exc.failure_code,
                failure_detail=exc.detail,
            )
            quarantined += int(created)
            duplicate_quarantine += int(not created)
            continue
        if uplink is not None:
            parsed.append(uplink)

    raw_inserted = 0
    duplicates_skipped = duplicate_quarantine
    measurements_created = 0
    invalid_preserved = 0
    status_processed = 0
    for uplink in sorted(parsed, key=lambda item: (item.received_at, item.f_cnt)):
        result = persist_ttn_uplink(session, uplink, device=device)
        if result.outcome in {"inserted", "inserted_invalid"}:
            raw_inserted += 1
            measurements_created += result.measurements_created
            status_processed += int(result.status_processed)
            invalid_preserved += int(result.outcome == "inserted_invalid")
        elif result.outcome in {"duplicate", "duplicate_quarantine"}:
            duplicates_skipped += 1
        elif result.outcome == "quarantined":
            quarantined += 1

    return ReplaySummary(
        total_events=len(events),
        selected_uplinks=len(selected),
        raw_inserted=raw_inserted,
        duplicates_skipped=duplicates_skipped,
        measurements_created=measurements_created,
        invalid_preserved=invalid_preserved,
        status_processed=status_processed,
        quarantined=quarantined,
        failed=0,
    )
