from uuid import UUID

from sqlalchemy.orm import Session

from app.db.repositories import sites as site_repository
from app.schemas.site import SiteList, SitePublic
from app.services.errors import ServiceError
from app.utils.cursors import decode_name_cursor, encode_cursor


def list_sites(session: Session, *, page_size: int, cursor: str | None) -> SiteList:
    after = decode_name_cursor(cursor) if cursor else None
    rows = site_repository.list_sites(session, page_size=page_size, after=after)
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = encode_cursor({"name": last.name.lower(), "id": str(last.id)})
    return SiteList(items=[SitePublic.model_validate(row) for row in rows], next_cursor=next_cursor)


def get_site(session: Session, site_id: UUID) -> SitePublic:
    site = site_repository.get_site(session, site_id)
    if site is None:
        raise ServiceError(404, "Site not found", "The requested site does not exist.", "not_found")
    return SitePublic.model_validate(site)
