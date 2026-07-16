from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, Field


class CanonicalMeasurement(BaseModel):
    measurement_id: UUID = Field(default_factory=uuid4)
    channel_code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")
    numeric_value: Annotated[Decimal, Field(allow_inf_nan=False)]
    measured_at: AwareDatetime


class CanonicalUplink(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    source: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    idempotency_key: str = Field(min_length=1, max_length=300)
    external_device_id: str = Field(min_length=1, max_length=200)
    external_event_identifier: str | None = Field(default=None, max_length=300)
    received_at: AwareDatetime
    measured_at: AwareDatetime | None = None
    frame_counter: int | None = Field(default=None, ge=0)
    payload_schema_version: str | None = Field(default=None, max_length=100)
    raw_payload: dict[str, Any]
    measurements: list[CanonicalMeasurement] = Field(default_factory=list, max_length=100)


def as_datetime(value: AwareDatetime) -> datetime:
    return value
