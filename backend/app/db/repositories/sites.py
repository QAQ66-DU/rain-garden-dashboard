from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.site import Site


def list_sites(
    session: Session,
    *,
    page_size: int,
    after: tuple[str, UUID] | None,
) -> list[Site]:
    normalized_name = func.lower(Site.name)
    statement = select(Site)
    if after is not None:
        name, identifier = after
        statement = statement.where(
            or_(
                normalized_name > name,
                and_(normalized_name == name, Site.id > identifier),
            )
        )
    return list(session.scalars(statement.order_by(normalized_name, Site.id).limit(page_size + 1)))


def get_site(session: Session, site_id: UUID) -> Site | None:
    return session.get(Site, site_id)


def get_default_site(session: Session) -> Site | None:
    return session.scalar(select(Site).where(Site.active.is_(True)).order_by(Site.name, Site.id))
