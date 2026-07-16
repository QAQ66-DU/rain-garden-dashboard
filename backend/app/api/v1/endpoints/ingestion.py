import secrets
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Request
from pydantic import JsonValue, RootModel, ValidationError

from app.api.dependencies import AppSettings
from app.services.errors import ServiceError

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class UnconfirmedTTNEnvelope(RootModel[dict[str, JsonValue]]):
    """A bounded JSON object only; no unconfirmed TTN fields are modeled."""


@router.post("/ttn", status_code=501)
async def receive_ttn_webhook(request: Request, settings: AppSettings) -> None:
    configured = (
        settings.ttn_webhook_secret.get_secret_value()
        if settings.ttn_webhook_secret is not None
        else None
    )
    supplied = request.headers.get("X-Webhook-Secret")
    if configured is None:
        raise ServiceError(
            503,
            "Webhook unavailable",
            "The webhook authentication secret is not configured.",
            "webhook_not_configured",
        )
    if supplied is None or not secrets.compare_digest(supplied, configured):
        raise ServiceError(
            401,
            "Webhook authentication failed",
            "Missing or invalid webhook authentication.",
            "invalid_webhook_authentication",
        )
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise ServiceError(
            415,
            "Unsupported media type",
            "The webhook accepts application/json only.",
            "unsupported_media_type",
        )
    try:
        raw: Any = await request.json()
        UnconfirmedTTNEnvelope.model_validate(raw)
    except (JSONDecodeError, ValidationError) as exc:
        raise ServiceError(
            422,
            "Invalid webhook payload",
            "The request body must be a valid JSON object.",
            "invalid_webhook_payload",
        ) from exc
    raise ServiceError(
        501,
        "TTN adapter not implemented",
        "Authentication succeeded, but real TTN payload mapping is disabled in Phase 1.",
        "ttn_adapter_disabled",
    )
