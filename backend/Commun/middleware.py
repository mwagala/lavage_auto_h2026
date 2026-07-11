import logging
import re
import time
import uuid

from flask import g, request
from werkzeug.exceptions import HTTPException

from .reponses import error_response


LOGGER = logging.getLogger(__name__)
CORRELATION_HEADER = "X-Correlation-ID"
CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")


def _sanitize_correlation_id(value):
    if not value:
        return str(uuid.uuid4())

    clean_value = value.strip()
    if CORRELATION_ID_PATTERN.fullmatch(clean_value):
        return clean_value

    return str(uuid.uuid4())


def _apply_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "img-src 'self' data:; "
        "font-src 'self' https://fonts.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "script-src 'self' 'unsafe-inline' https://unpkg.com; "
        "connect-src 'self'"
    )
    return response


def register_request_middleware(app):
    @app.before_request
    def attach_request_context():
        g.request_started_at = time.perf_counter()
        incoming_correlation_id = request.headers.get(CORRELATION_HEADER)
        g.correlation_id = _sanitize_correlation_id(incoming_correlation_id)

    @app.after_request
    def log_request(response):
        correlation_id = getattr(g, "correlation_id", None)
        if correlation_id:
            response.headers[CORRELATION_HEADER] = correlation_id

        started_at = getattr(g, "request_started_at", None)
        duration_ms = None
        if started_at is not None:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

        LOGGER.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        if app.config.get("SECURITY_HEADERS_ENABLED", True):
            response = _apply_security_headers(response)
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        status_code = error.code or 500
        return error_response(error.description or "Erreur HTTP.", status=status_code)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        LOGGER.exception("request_failed", extra={"path": request.path})
        return error_response("Erreur interne du serveur.", status=500)
