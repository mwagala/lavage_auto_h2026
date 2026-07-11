import os

from dotenv import load_dotenv


load_dotenv()


DEVELOPMENT_ENVS = {"dev", "development", "local"}
TEST_ENVS = {"test", "testing"}
WEAK_SECRET_VALUES = {
    "dev-secret-key",
    "dev-jwt-secret-key",
    "change_me",
    "change_me_secret_key_minimum_32_characters",
    "change_me_jwt_secret_key_minimum_32_characters",
}


def _get_bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"true", "1", "yes", "on"}


def _get_int_env(name, default):
    value = os.getenv(name)
    if value is None:
        return default

    return int(value)


def _get_list_env(name, default=None):
    value = os.getenv(name)
    if value is None:
        return list(default or [])

    return [item.strip() for item in value.split(",") if item.strip()]


def _is_non_production(app_env, testing=False):
    return testing or app_env in DEVELOPMENT_ENVS or app_env in TEST_ENVS


def _get_secret(name, app_env, testing, dev_default):
    value = os.getenv(name)
    if not value and _is_non_production(app_env, testing):
        return dev_default

    if not value:
        raise RuntimeError(f"{name} doit etre defini hors environnement de developpement.")

    normalized_value = value.strip()
    if not _is_non_production(app_env, testing):
        if normalized_value in WEAK_SECRET_VALUES or normalized_value.startswith("change_me"):
            raise RuntimeError(f"{name} utilise une valeur de demonstration interdite en production.")

        if len(normalized_value) < 32:
            raise RuntimeError(f"{name} doit contenir au moins 32 caracteres en production.")

    return normalized_value


def _get_cors_allowed_origins(app_env, testing):
    default_origins = []
    if _is_non_production(app_env, testing):
        default_origins = ["http://127.0.0.1:5000", "http://localhost:5000"]

    origins = _get_list_env("CORS_ALLOWED_ORIGINS", default_origins)
    if "*" in origins and not _is_non_production(app_env, testing):
        raise RuntimeError("CORS_ALLOWED_ORIGINS ne peut pas contenir '*' en production.")

    return origins


class Config:
    """
    Point central de configuration pour l'application.
    """
    APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
    TESTING = _get_bool_env("TESTING", APP_ENV in TEST_ENVS)
    IS_NON_PRODUCTION = _is_non_production(APP_ENV, TESTING)
    DEBUG = _get_bool_env(
        "FLASK_DEBUG",
        _get_bool_env("DEBUG", APP_ENV in DEVELOPMENT_ENVS and not TESTING)
    )

    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "lavage_auto")
    DB_PORT = int(os.getenv("DB_PORT", 5432))

    SECRET_KEY = _get_secret(
        "SECRET_KEY",
        APP_ENV,
        TESTING,
        "dev-secret-key-minimum-32-characters"
    )
    JWT_SECRET_KEY = _get_secret(
        "JWT_SECRET_KEY",
        APP_ENV,
        TESTING,
        "dev-jwt-secret-key-minimum-32-characters"
    )
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = _get_int_env("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 120)
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    CORS_ALLOWED_ORIGINS = _get_cors_allowed_origins(APP_ENV, TESTING)
    SECURITY_HEADERS_ENABLED = _get_bool_env("SECURITY_HEADERS_ENABLED", True)
    RATE_LIMITING_ENABLED = _get_bool_env("RATE_LIMITING_ENABLED", True)
    RATE_LIMITING_BACKEND = os.getenv("RATE_LIMITING_BACKEND", "redis").strip().lower()
    RATE_LIMITING_REDIS_TIMEOUT_SECONDS = float(os.getenv("RATE_LIMITING_REDIS_TIMEOUT_SECONDS", 0.25))
    AUTH_LOGIN_RATE_LIMIT_ATTEMPTS = _get_int_env("AUTH_LOGIN_RATE_LIMIT_ATTEMPTS", 5)
    AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS = _get_int_env("AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS", 900)
    AUTH_REGISTER_RATE_LIMIT_ATTEMPTS = _get_int_env("AUTH_REGISTER_RATE_LIMIT_ATTEMPTS", 5)
    AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS = _get_int_env("AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS", 3600)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    CELERY_TASK_ALWAYS_EAGER = _get_bool_env("CELERY_TASK_ALWAYS_EAGER", False)
    HEALTH_CHECK_TIMEOUT = float(os.getenv("HEALTH_CHECK_TIMEOUT", 0.25))
    HEALTH_CHECK_CELERY_WORKER = _get_bool_env("HEALTH_CHECK_CELERY_WORKER", False)
    OUTBOX_CONSUMER_INTERVAL_SECONDS = _get_int_env("OUTBOX_CONSUMER_INTERVAL_SECONDS", 60)
    OUTBOX_BATCH_SIZE = _get_int_env("OUTBOX_BATCH_SIZE", 10)
    OUTBOX_MAX_ATTEMPTS = _get_int_env("OUTBOX_MAX_ATTEMPTS", 5)
    OUTBOX_RETRY_BACKOFF_SECONDS = _get_int_env("OUTBOX_RETRY_BACKOFF_SECONDS", 60)
    OUTBOX_MAX_RETRY_DELAY_SECONDS = _get_int_env("OUTBOX_MAX_RETRY_DELAY_SECONDS", 3600)
    OUTBOX_STALE_PROCESSING_SECONDS = _get_int_env("OUTBOX_STALE_PROCESSING_SECONDS", 900)
    OUTBOX_STALE_RESET_LIMIT = _get_int_env("OUTBOX_STALE_RESET_LIMIT", 100)

    @classmethod
    def is_development(cls):
        return cls.APP_ENV in DEVELOPMENT_ENVS

    @classmethod
    def validate(cls):
        if cls.IS_NON_PRODUCTION:
            return

        secrets = {
            "SECRET_KEY": cls.SECRET_KEY,
            "JWT_SECRET_KEY": cls.JWT_SECRET_KEY,
        }

        for name, value in secrets.items():
            if not value or value in WEAK_SECRET_VALUES or "change_me" in value or len(value) < 32:
                raise RuntimeError(
                    f"{name} doit etre defini avec une valeur forte hors environnement de developpement."
                )

        if cls.DEBUG:
            raise RuntimeError("DEBUG doit etre desactive hors environnement de developpement.")
