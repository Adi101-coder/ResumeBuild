import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        client = request.client.host if request.client else "unknown"
        query = f"?{request.url.query}" if request.url.query else ""
        referer = request.headers.get("referer", "-")
        origin = request.headers.get("origin", "-")

        logger.info(
            "→ %s %s%s | client=%s origin=%s referer=%s",
            request.method,
            request.url.path,
            query,
            client,
            origin,
            referer,
        )

        if request.method in {"POST", "PUT", "PATCH"}:
            content_type = request.headers.get("content-type", "-")
            content_length = request.headers.get("content-length", "-")
            logger.debug("  body: type=%s length=%s", content_type, content_length)

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "✗ %s %s%s failed after %.1fms",
                request.method,
                request.url.path,
                query,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.perf_counter() - start) * 1000
        level = logging.INFO if response.status_code < 400 else logging.WARNING
        logger.log(
            level,
            "← %s %s%s → %s (%.1fms)",
            request.method,
            request.url.path,
            query,
            response.status_code,
            elapsed_ms,
        )
        return response
