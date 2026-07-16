from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.status import ConnectivityStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Freshness(ApiModel):
    calculated_status: ConnectivityStatus
    reference_time: datetime
    age_seconds: int | None
    stale_after_minutes: int
    offline_after_minutes: int
    status_basis: str


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    correlation_id: str
    error_code: str
    errors: list[dict[str, Any]] = Field(default_factory=list)
