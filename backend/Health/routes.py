from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint
import psycopg
from redis import Redis

from bd.config import Config
from backend.Commun.reponses import error_response, success_response


health_bp = Blueprint("health", __name__)


def _ok(details=None):
    return {"ok": True, "details": details or {}}


def _ko(error):
    return {"ok": False, "error": str(error)}


def _check_database():
    try:
        health_host = "127.0.0.1" if Config.DB_HOST == "localhost" else Config.DB_HOST
        with psycopg.connect(
            host=health_host,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            dbname=Config.DB_NAME,
            connect_timeout=max(1, int(Config.HEALTH_CHECK_TIMEOUT)),
        ) as connection:
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

    with ThreadPoolExecutor(max_workers=len(checkers)) as executor:
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
