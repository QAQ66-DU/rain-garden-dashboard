from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import AppSettings, DatabaseSession
from app.models.enums import MetricGroup
from app.schemas.explorer import ExploreResponse
from app.services.explorer import get_explorer

router = APIRouter(tags=["explore"])


@router.get("/explore", response_model=ExploreResponse)
def explore(
    session: DatabaseSession,
    settings: AppSettings,
    start: datetime,
    end: datetime,
    site_id: UUID | None = None,
    feature: Annotated[str | None, Query(max_length=100)] = None,
    metric_group: MetricGroup = MetricGroup.HYDROLOGY,
    channels: Annotated[str | None, Query(max_length=5_000)] = None,
) -> ExploreResponse:
    return get_explorer(
        session,
        settings,
        start=start,
        end=end,
        site_id=site_id,
        feature=feature,
        metric_group=metric_group,
        channels=channels,
    )
