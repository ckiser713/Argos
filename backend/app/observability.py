from __future__ import annotations

import contextvars
import logging
import time
import uuid
from typing import Any, Dict, Iterable, Optional

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

try:  # Opentelemetry is optional and can be disabled via settings
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
except Exception:  # pragma: no cover - handled gracefully when OTEL is unavailable
    trace = None  # type: ignore[assignment]
    OTLPSpanExporter = None  # type: ignore[assignment]
    FastAPIInstrumentor = None  # type: ignore[assignment]
    RequestsInstrumentor = None  # type: ignore[assignment]
    TracerProvider = None  # type: ignore[assignment]
    BatchSpanProcessor = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment]
    TraceIdRatioBased = None  # type: ignore[assignment]

# -----------------------------------------------------------------------------
# Context fields for structured logging
# -----------------------------------------------------------------------------

_request_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
_user_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user", default=None
)
_path_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "path", default=None
)
_status_ctx: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "status_code", default=None
)
_trace_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)

# -----------------------------------------------------------------------------
# Prometheus metrics
# -----------------------------------------------------------------------------

REQUEST_COUNTER = Counter(
    "argos_http_requests_total",
    "Count of HTTP requests by method, path, and status.",
    labelnames=("method", "path", "status_code"),
)
REQUEST_LATENCY = Histogram(
    "argos_http_request_duration_seconds",
    "Latency of HTTP requests.",
    labelnames=("method", "path", "status_code"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

INGEST_STATUS_COUNTER = Counter(
    "argos_ingest_jobs_total",
    "Total ingest job transitions by status.",
    labelnames=("status",),
)
INGEST_STATUS_GAUGE = Gauge(
    "argos_ingest_jobs_current",
    "Current ingest jobs by status.",
    labelnames=("status",),
)

EMBEDDING_CALL_COUNTER = Counter(
    "argos_embedding_calls_total",
    "Embedding model invocations.",
    labelnames=("model", "status"),
)

MODEL_CALL_COUNTER = Counter(
    "argos_model_calls_total",
    "LLM/model invocations.",
    labelnames=("backend", "model", "status"),
)

_KNOWN_INGEST_STATUSES = ("queued", "running", "completed", "failed", "cancelled")
_SKIP_METRIC_PATHS = {"/metrics"}


# -----------------------------------------------------------------------------
# Logging helpers
# -----------------------------------------------------------------------------

class _ContextFilter(logging.Filter):
    """Inject request-scoped context variables into log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        record.request_id = getattr(record, "request_id", None) or _request_id_ctx.get()
        record.trace_id = getattr(record, "trace_id", None) or _trace_ctx.get()
        record.user = getattr(record, "user", None) or _user_ctx.get()
        record.path = getattr(record, "path", None) or _path_ctx.get()
        record.status_code = getattr(record, "status_code", None) or _status_ctx.get()
        return True


def configure_logging(settings: Any) -> None:
    """
    Configure JSON structured logging for the backend.

    Safe for production: no request/response bodies are logged; only metadata and
    optional per-request identifiers are emitted.
    """
    level = getattr(logging, str(getattr(settings, "log_level", "INFO")).upper(), logging.INFO)

    handler = logging.StreamHandler()
    use_json = bool(getattr(settings, "log_json", True))
    formatter: logging.Formatter
    if use_json:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(trace_id)s %(user)s %(path)s %(status_code)s"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    handler.setFormatter(formatter)
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
    root.propagate = False

    # Align uvicorn/fastapi loggers to use the same handler
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.setLevel(level)
        logger.propagate = False


# -----------------------------------------------------------------------------
# Tracing helpers
# -----------------------------------------------------------------------------

def setup_tracing(app: FastAPI, settings: Any) -> None:
    """
    Configure optional OpenTelemetry tracing with an OTLP exporter.

    Tracing is disabled unless `settings.enable_tracing` is truthy.
    """
    if not getattr(settings, "enable_tracing", False):
        return
    if trace is None or TracerProvider is None or OTLPSpanExporter is None:
        logging.getLogger(__name__).warning(
            "Tracing enabled but OpenTelemetry dependencies are unavailable; skipping setup."
        )
        return
    if getattr(app.state, "tracing_enabled", False):
        return

    resource = Resource.create({"service.name": getattr(settings, "otel_service_name", "argos-backend")})
    sample_ratio = float(getattr(settings, "otel_sample_ratio", 1.0) or 1.0)
    sample_ratio = max(0.0, min(1.0, sample_ratio))
    if TraceIdRatioBased:
        sampler = TraceIdRatioBased(sample_ratio)
        provider = TracerProvider(resource=resource, sampler=sampler)
    else:
        provider = TracerProvider(resource=resource)

    exporter_endpoint = getattr(settings, "otel_exporter_endpoint", None)
    exporter = OTLPSpanExporter(endpoint=exporter_endpoint) if exporter_endpoint else OTLPSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="|".join(_SKIP_METRIC_PATHS),
    )
    RequestsInstrumentor().instrument()
    app.state.tracing_enabled = True


def _current_trace_id() -> Optional[str]:
    if trace is None:
        return None
    span = trace.get_current_span()
    if not span:
        return None
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        return format(ctx.trace_id, "032x")
    return None


# -----------------------------------------------------------------------------
# Metrics helpers for services
# -----------------------------------------------------------------------------

def record_ingest_transition(status: str) -> None:
    """Increment ingest job transition counters."""
    status = status.lower()
    INGEST_STATUS_COUNTER.labels(status=status).inc()


def set_ingest_gauge(counts: Dict[str, int]) -> None:
    """Update ingest job gauges from a status->count mapping."""
    for status in _KNOWN_INGEST_STATUSES:
        INGEST_STATUS_GAUGE.labels(status=status).set(0)
    for status, count in counts.items():
        INGEST_STATUS_GAUGE.labels(status=status.lower()).set(count)


def record_embedding_call(model: str, success: bool) -> None:
    EMBEDDING_CALL_COUNTER.labels(model=model, status="success" if success else "error").inc()


def record_model_call(backend: str, model: str, success: bool) -> None:
    MODEL_CALL_COUNTER.labels(backend=backend or "unknown", model=model or "unknown", status="success" if success else "error").inc()


# -----------------------------------------------------------------------------
# Metrics endpoint & middleware
# -----------------------------------------------------------------------------

def setup_metrics_endpoint(app: FastAPI) -> None:
    """Expose Prometheus metrics at /metrics."""

    @app.get("/metrics")
    def metrics() -> StarletteResponse:  # pragma: no cover - exercised in integration tests
        return StarletteResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware that injects request IDs, trace IDs, structured logging, and
    Prometheus HTTP metrics.
    """

    def __init__(self, app: FastAPI, *, skip_paths: Iterable[str] | None = None) -> None:
        super().__init__(app)
        self._logger = logging.getLogger("app.http")
        self._skip_paths = set(skip_paths or _SKIP_METRIC_PATHS)

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        path_template = _path_from_request(request)
        user = _user_from_request(request)
        trace_id = _current_trace_id()

        request_token = _request_id_ctx.set(request_id)
        path_token = _path_ctx.set(path_template)
        user_token = _user_ctx.set(user)
        trace_token = _trace_ctx.set(trace_id)
        status_token = _status_ctx.set(None)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            duration = time.perf_counter() - start
            _status_ctx.set(status_code)

            if path_template not in self._skip_paths:
                REQUEST_COUNTER.labels(
                    method=request.method, path=path_template, status_code=str(status_code)
                ).inc()
                REQUEST_LATENCY.labels(
                    method=request.method, path=path_template, status_code=str(status_code)
                ).observe(duration)

            response.headers["X-Request-ID"] = request_id
            self._logger.info(
                "http.request",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "user": user,
                    "path": path_template,
                    "status_code": status_code,
                    "method": request.method,
                    "duration_ms": round(duration * 1000, 2),
                },
            )
            return response
        except Exception:
            duration = time.perf_counter() - start
            if path_template not in self._skip_paths:
                REQUEST_COUNTER.labels(
                    method=request.method, path=path_template, status_code="500"
                ).inc()
                REQUEST_LATENCY.labels(
                    method=request.method, path=path_template, status_code="500"
                ).observe(duration)
            self._logger.exception(
                "http.request.failed",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "user": user,
                    "path": path_template,
                    "status_code": 500,
                    "method": request.method,
                    "duration_ms": round(duration * 1000, 2),
                },
            )
            raise
        finally:
            _request_id_ctx.reset(request_token)
            _path_ctx.reset(path_token)
            _user_ctx.reset(user_token)
            _trace_ctx.reset(trace_token)
            _status_ctx.reset(status_token)


def _path_from_request(request: Request) -> str:
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return getattr(route, "path", "/") or "/"
    return request.url.path


def _user_from_request(request: Request) -> Optional[str]:
    state_user = getattr(request.state, "user", None)
    if state_user is None:
        return None
    for attr in ("username", "email", "id"):
        if hasattr(state_user, attr):
            value = getattr(state_user, attr)
            if value:
                return str(value)
    return None


