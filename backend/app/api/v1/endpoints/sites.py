from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.schemas.site import SiteList, SitePublic
from app.services import sites as site_service

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=SiteList)
def list_sites(
    session: DatabaseSession,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1_000)] = None,
) -> SiteList:
    return site_service.list_sites(session, page_size=page_size, cursor=cursor)


@router.get("/{site_id}", response_model=SitePublic)
def get_site(site_id: UUID, session: DatabaseSession) -> SitePublic:
    return site_service.get_site(session, site_id)
