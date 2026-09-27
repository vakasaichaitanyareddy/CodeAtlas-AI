import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram
from .errors import create_error_response

logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "codeatlas_http_requests_total",
    "Total HTTP request count",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "codeatlas_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware managing X-Request-ID propagation, structured logging, and Prometheus metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Request ID propagation
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        # Ignore metric endpoints in metrics scraping
        is_metrics_path = path == "/metrics"

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            logger.error(f"Unhandled exception during {method} {path} (request_id={request_id}): {exc}", exc_info=True)
            response = create_error_response(
                message="An unexpected internal server error occurred.",
                code="INTERNAL_SERVER_ERROR",
                status_code=500,
                request_id=request_id,
            )
            status_code = 500
        finally:
            duration = time.perf_counter() - start_time
            response_status = status_code if "response" in locals() else 500

            if not is_metrics_path:
                REQUEST_COUNT.labels(method=method, endpoint=path, status_code=response_status).inc()
                REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)

                log_extra = {
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": response_status,
                    "duration_ms": round(duration * 1000, 2),
                }
                if response_status >= 500:
                    logger.error(f"{method} {path} -> {response_status} ({log_extra['duration_ms']}ms)", extra=log_extra)
                elif response_status >= 400:
                    logger.warning(f"{method} {path} -> {response_status} ({log_extra['duration_ms']}ms)", extra=log_extra)
                else:
                    logger.info(f"{method} {path} -> {response_status} ({log_extra['duration_ms']}ms)", extra=log_extra)

        response.headers["X-Request-ID"] = request_id
        return response
