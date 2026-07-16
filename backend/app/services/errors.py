from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ServiceError(Exception):
    status_code: int
    title: str
    detail: str
    error_code: str
    errors: list[dict[str, Any]] = field(default_factory=list)
