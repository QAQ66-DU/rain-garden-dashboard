from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import __version__
from app.api.dependencies import DatabaseSession
from app.services.errors import ServiceError

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
def health(session: DatabaseSession) -> HealthResponse:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise ServiceError(
            503,
            "Service unavailable",
            "The database health check failed.",
            "database_unavailable",
        ) from exc
    return HealthResponse(
        status="ok", database="ok", version=__version__, timestamp=datetime.now(UTC)
    )
