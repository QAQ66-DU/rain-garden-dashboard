from collections.abc import Mapping
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse


def problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    error_code: str,
    errors: list[dict[str, Any]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        headers=headers,
        content={
            "type": f"https://rain-garden.example/problems/{error_code}",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": request.url.path,
            "correlation_id": correlation_id,
            "error_code": error_code,
            "errors": errors or [],
        },
    )
