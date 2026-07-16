import base64
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from app.services.errors import ServiceError


def encode_cursor(payload: dict[str, str]) -> str:
    raw = json.dumps({"v": 1, **payload}, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        padding = "=" * (-len(cursor) % 4)
        decoded = base64.urlsafe_b64decode(cursor + padding)
        payload = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        raise _invalid_cursor() from exc
    if not isinstance(payload, dict) or payload.get("v") != 1:
        raise _invalid_cursor()
    return payload


def decode_measurement_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = decode_cursor(cursor)
    try:
        timestamp = datetime.fromisoformat(str(payload["measured_at"]))
        identifier = UUID(str(payload["id"]))
    except (KeyError, ValueError) as exc:
        raise _invalid_cursor() from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise _invalid_cursor()
    return timestamp, identifier


def decode_name_cursor(cursor: str) -> tuple[str, UUID]:
    payload = decode_cursor(cursor)
    try:
        name = str(payload["name"])
        identifier = UUID(str(payload["id"]))
    except (KeyError, ValueError) as exc:
        raise _invalid_cursor() from exc
    if not name:
        raise _invalid_cursor()
    return name, identifier


def _invalid_cursor() -> ServiceError:
    return ServiceError(
        status_code=422,
        title="Invalid pagination cursor",
        detail="The pagination cursor is malformed or incompatible with this endpoint.",
        error_code="invalid_cursor",
    )
