from uuid import UUID

from app.schemas.common import ApiModel


class SitePublic(ApiModel):
    id: UUID
    name: str
    description: str | None
    public_location_label: str
    location_disclosure: str
    display_timezone: str
    active: bool


class SiteList(ApiModel):
    items: list[SitePublic]
    next_cursor: str | None
