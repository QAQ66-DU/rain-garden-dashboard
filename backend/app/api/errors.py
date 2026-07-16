import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.core.problem import problem_response
from app.services.errors import ServiceError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        return problem_response(
            request,
            status_code=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            error_code=exc.error_code,
            errors=exc.errors,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {"location": [str(part) for part in error["loc"]], "message": error["msg"]}
            for error in exc.errors()
        ]
        return problem_response(
            request,
            status_code=422,
            title="Request validation failed",
            detail="One or more request fields are invalid.",
            error_code="validation_error",
            errors=errors,
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return problem_response(
            request,
            status_code=exc.status_code,
            title="Request failed",
            detail=str(exc.detail),
            error_code="http_error",
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error", exc_info=exc)
        return problem_response(
            request,
            status_code=500,
            title="Internal server error",
            detail="The server could not complete the request.",
            error_code="internal_error",
        )
