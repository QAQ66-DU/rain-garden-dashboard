import re
from collections.abc import Awaitable, Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.logging import request_id_context
from app.core.problem import problem_response
from app.core.rate_limit import InMemoryRateLimiter

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        correlation_id = supplied if REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid4())
        request.state.correlation_id = correlation_id
        token = request_id_context.set(correlation_id)
        try:
            response = await call_next(request)
        finally:
            request_id_context.reset(token)
        response.headers["X-Request-ID"] = correlation_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Permissions-Policy"] = "camera=(), geolocation=(), microphone=()"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self.limiter = InMemoryRateLimiter()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not request.url.path.startswith("/api/v1"):
            return await call_next(request)
        ingestion = request.url.path == "/api/v1/ingestion/ttn"
        limit = (
            self.settings.ingestion_rate_limit_requests
            if ingestion
            else self.settings.public_rate_limit_requests
        )
        window = (
            self.settings.ingestion_rate_limit_window_seconds
            if ingestion
            else self.settings.public_rate_limit_window_seconds
        )
        client = request.client.host if request.client else "unknown"
        key = f"{'ingestion' if ingestion else 'public'}:{client}"
        if not self.limiter.allow(key, limit=limit, window_seconds=window):
            return problem_response(
                request,
                status_code=429,
                title="Too many requests",
                detail="The request rate limit has been exceeded. Retry later.",
                error_code="rate_limit_exceeded",
                headers={"Retry-After": str(window)},
            )
        return await call_next(request)


class RequestBodyTooLarge(Exception):
    pass


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, *, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    await self._send_problem(scope, receive, send)
                    return
            except ValueError:
                pass

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            await self._send_problem(scope, receive, send)

    async def _send_problem(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive=receive)
        response = problem_response(
            request,
            status_code=413,
            title="Request body too large",
            detail=f"The request body exceeds the configured {self.max_bytes}-byte limit.",
            error_code="request_body_too_large",
        )
        await response(scope, receive, send)
