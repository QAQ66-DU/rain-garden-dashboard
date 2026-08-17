from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import AppSettings, DatabaseSession
from app.schemas.device import DeviceDetail, DeviceList
from app.schemas.measurement import MeasurementChartSeries, MeasurementPage
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
    feature: Annotated[str | None, Query(max_length=100)] = None,
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
        feature_slug=feature,
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


@router.get("/{device_id}/measurements/chart", response_model=MeasurementChartSeries)
def chart_measurements(
    device_id: UUID,
    session: DatabaseSession,
    settings: AppSettings,
    sensor_channel_id: UUID,
    start: datetime | None = None,
    end: datetime | None = None,
) -> MeasurementChartSeries:
    return measurement_service.chart_measurements(
        session,
        settings,
        device_id,
        start=start,
        end=end,
        sensor_channel_id=sensor_channel_id,
    )


@router.get(
    "/{device_id}/measurements/export.csv",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/csv": {"schema": {"type": "string"}}},
            "description": "Privacy-reviewed normalized measurements as CSV.",
        }
    },
)
def export_measurements_csv(
    device_id: UUID,
    session: DatabaseSession,
    settings: AppSettings,
    start: datetime,
    end: datetime,
    sensor_channel_id: UUID,
) -> StreamingResponse:
    exported = measurement_service.export_measurements_csv(
        session,
        settings,
        device_id,
        start=start,
        end=end,
        sensor_channel_id=sensor_channel_id,
    )
    return StreamingResponse(
        content=exported.content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{exported.filename}"',
            "Cache-Control": "private, no-store",
        },
    )
