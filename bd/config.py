import os

from dotenv import load_dotenv


load_dotenv()


def _get_bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"true", "1", "yes", "on"}


class Config:
    """
    Point central de configuration pour l'application.
    """
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "lavage_auto")
    DB_PORT = int(os.getenv("DB_PORT", 5432))

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CELERY_TASK_ALWAYS_EAGER = _get_bool_env("CELERY_TASK_ALWAYS_EAGER", False)
    HEALTH_CHECK_TIMEOUT = float(os.getenv("HEALTH_CHECK_TIMEOUT", 0.25))
    OUTBOX_CONSUMER_INTERVAL_SECONDS = int(os.getenv("OUTBOX_CONSUMER_INTERVAL_SECONDS", 60))
