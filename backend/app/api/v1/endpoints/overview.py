from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import AppSettings, DatabaseSession
from app.schemas.overview import Overview
from app.services.overview import get_overview

router = APIRouter(tags=["overview"])


@router.get("/overview", response_model=Overview)
def overview(
    session: DatabaseSession, settings: AppSettings, site_id: UUID | None = None
) -> Overview:
    return get_overview(session, settings, site_id)
