from fastapi import APIRouter

from app.api.v1.endpoints import devices, explorer, health, ingestion, overview, sites

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(sites.router)
router.include_router(devices.router)
router.include_router(overview.router)
router.include_router(explorer.router)
router.include_router(ingestion.router)
