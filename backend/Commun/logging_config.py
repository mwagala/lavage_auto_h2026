import logging

from flask import g, has_request_context
from pythonjsonlogger import jsonlogger


class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = None
        if has_request_context():
            record.correlation_id = getattr(g, "correlation_id", None)
        return True


def configure_logging(app):
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.addFilter(CorrelationIdFilter())
    handler.setFormatter(jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(correlation_id)s "
        "%(method)s %(path)s %(status_code)s %(duration_ms)s"
    ))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    app.logger.handlers = []
    app.logger.setLevel(level)
