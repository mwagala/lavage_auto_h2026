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
        timeout = max(1, float(Config.HEALTH_CHECK_TIMEOUT))
        client = Redis.from_url(
            url,
            socket_connect_timeout=timeout,
            socket_timeout=timeout,
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
    checks = {
        "database": _check_database(),
    }

    redis_urls_by_check = {
        "redis": Config.REDIS_URL,
        "celery_broker": Config.CELERY_BROKER_URL,
        "celery_result_backend": Config.CELERY_RESULT_BACKEND,
    }
    redis_results_by_url = {}

    for check_name, redis_url in redis_urls_by_check.items():
        if redis_url not in redis_results_by_url:
            redis_results_by_url[redis_url] = _check_redis_url(redis_url)
        checks[check_name] = redis_results_by_url[redis_url]

    if Config.HEALTH_CHECK_CELERY_WORKER:
        with ThreadPoolExecutor(max_workers=1) as executor:
            checks["celery_worker"] = executor.submit(_check_celery_worker).result()

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
