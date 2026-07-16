from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.dependencies import AppSettings, DatabaseSession
from app.schemas.device import DeviceDetail, DeviceList
from app.schemas.measurement import MeasurementPage
from app.services import devices as device_service
from app.services import measurements as measurement_service
from app.services.status import ConnectivityStatus

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceList)
def list_devices(
    session: DatabaseSession,
    settings: AppSettings,
    search: Annotated[str | None, Query(max_length=200)] = None,
    site_id: UUID | None = None,
    device_type: Annotated[str | None, Query(max_length=50)] = None,
    status: ConnectivityStatus | None = None,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=1_000)] = None,
) -> DeviceList:
    return device_service.list_devices(
        session,
        settings,
        page_size=page_size,
        cursor=cursor,
        search=search,
        site_id=site_id,
        device_type=device_type,
        status=status,
    )


@router.get("/{device_id}", response_model=DeviceDetail)
def get_device(device_id: UUID, session: DatabaseSession, settings: AppSettings) -> DeviceDetail:
    return device_service.get_device(session, settings, device_id)


@router.get("/{device_id}/measurements", response_model=MeasurementPage)
def list_measurements(
    device_id: UUID,
    session: DatabaseSession,
    settings: AppSettings,
    start: datetime | None = None,
    end: datetime | None = None,
    metric_code: Annotated[str | None, Query(max_length=100)] = None,
    sensor_channel_id: UUID | None = None,
    page_size: Annotated[int, Query(ge=1, le=500)] = 250,
    cursor: Annotated[str | None, Query(max_length=1_000)] = None,
) -> MeasurementPage:
    return measurement_service.list_measurements(
        session,
        settings,
        device_id,
        start=start,
        end=end,
        metric_code=metric_code,
        sensor_channel_id=sensor_channel_id,
        page_size=page_size,
        cursor=cursor,
    )
