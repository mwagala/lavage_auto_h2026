from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint
from redis import Redis

from bd.config import Config
from bd.database import get_connection
from backend.Commun.reponses import error_response, success_response


health_bp = Blueprint("health", __name__)


def _ok(details=None):
    return {"ok": True, "details": details or {}}


def _ko(error):
    return {"ok": False, "error": str(error)}


def _check_database():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                row = cursor.fetchone()
        return _ok({"result": row[0] if row else None})
    except Exception as exc:
        return _ko(exc)


def _check_redis_url(url):
    try:
        client = Redis.from_url(
            url,
            socket_connect_timeout=Config.HEALTH_CHECK_TIMEOUT,
            socket_timeout=Config.HEALTH_CHECK_TIMEOUT,
            decode_responses=True,
        )
        client.ping()
        return _ok()
    except Exception as exc:
        return _ko(exc)


def _check_celery_worker():
    try:
        from backend.celery.celery_app import celery_app

        replies = celery_app.control.ping(timeout=Config.HEALTH_CHECK_TIMEOUT)
        if not replies:
            return _ko("Aucun worker Celery n'a repondu au ping.")
        return _ok({"workers": replies})
    except Exception as exc:
        return _ko(exc)


@health_bp.get("/health")
def liveness():
    return success_response({"status": "ok", "service": "lavage-auto"})


@health_bp.get("/health/readiness")
def readiness():
    checkers = {
        "database": _check_database,
        "redis": lambda: _check_redis_url(Config.REDIS_URL),
        "celery_broker": lambda: _check_redis_url(Config.CELERY_BROKER_URL),
        "celery_result_backend": lambda: _check_redis_url(Config.CELERY_RESULT_BACKEND),
    }

    if Config.HEALTH_CHECK_CELERY_WORKER:
        checkers["celery_worker"] = _check_celery_worker

    with ThreadPoolExecutor(max_workers=max(1, len(checkers))) as executor:
        futures = {
            name: executor.submit(checker)
            for name, checker in checkers.items()
        }
        checks = {
            name: future.result()
            for name, future in futures.items()
        }

    ready = all(check["ok"] for check in checks.values())
    payload = {
        "status": "ok" if ready else "degrade",
        "checks": checks,
    }

    if not ready:
        return error_response(
            "Certains services de fondation ne sont pas disponibles.",
            status=503,
            data=payload,
        )

    return success_response(payload)
