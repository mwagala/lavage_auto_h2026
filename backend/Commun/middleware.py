import logging
import time
import uuid

from flask import g, request
from werkzeug.exceptions import HTTPException

from .reponses import error_response


LOGGER = logging.getLogger(__name__)
CORRELATION_HEADER = "X-Correlation-ID"


def register_request_middleware(app):
    @app.before_request
    def attach_request_context():
        g.request_started_at = time.perf_counter()
        incoming_correlation_id = request.headers.get(CORRELATION_HEADER)
        g.correlation_id = incoming_correlation_id or str(uuid.uuid4())

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
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        status_code = error.code or 500
        return error_response(error.description or "Erreur HTTP.", status=status_code)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error):
        LOGGER.exception("request_failed", extra={"path": request.path})
        return error_response("Erreur interne du serveur.", status=500)
