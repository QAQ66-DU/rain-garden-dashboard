from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import register_exception_handlers
from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    application = FastAPI(
        title="Rain Garden Monitoring Dashboard API",
        version=__version__,
        description=(
            "Read-only API for deterministic synthetic urban green infrastructure monitoring "
            "data, including half-open UTC period exploration."
        ),
    )
    application.state.settings = resolved_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID", "X-Webhook-Secret"],
    )
    application.add_middleware(
        RequestBodyLimitMiddleware, max_bytes=resolved_settings.webhook_body_limit_bytes
    )
    application.add_middleware(RateLimitMiddleware, settings=resolved_settings)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(api_v1_router)
    return application


app = create_app()
