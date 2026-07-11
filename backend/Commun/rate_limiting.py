import hashlib
import hmac
import logging
import math
import threading
import time
from dataclasses import dataclass

from flask import current_app, has_app_context
from redis import Redis
from redis.exceptions import RedisError

from bd.config import Config


LOGGER = logging.getLogger(__name__)
_MEMORY_LOCK = threading.Lock()
_MEMORY_COUNTERS = {}
_REDIS_CLIENT = None


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    status_code: int = 200
    message: str = "OK"
    retry_after_seconds: int = 0


def _is_testing_request():
    return has_app_context() and bool(current_app.config.get("TESTING"))


def _memory_backend_allowed():
    return (
        Config.RATE_LIMITING_BACKEND == "memory"
        or _is_testing_request()
        or Config.IS_NON_PRODUCTION
    )


def _get_redis_client():
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        _REDIS_CLIENT = Redis.from_url(
            Config.REDIS_URL,
            socket_connect_timeout=Config.RATE_LIMITING_REDIS_TIMEOUT_SECONDS,
            socket_timeout=Config.RATE_LIMITING_REDIS_TIMEOUT_SECONDS,
            decode_responses=True,
        )
    return _REDIS_CLIENT


def _hash_value(value):
    normalized = str(value or "unknown").strip().lower()
    secret = Config.SECRET_KEY.encode("utf-8")
    return hmac.new(secret, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def _rate_limit_keys(action, payload, request_obj):
    remote_addr = getattr(request_obj, "remote_addr", None) or "unknown"
    keys = [f"rate_limit:auth:{action}:ip:{_hash_value(remote_addr)}"]

    identifier = None
    if isinstance(payload, dict):
        identifier = payload.get("courriel")

    if identifier:
        keys.append(f"rate_limit:auth:{action}:identifier:{_hash_value(identifier)}")

    return keys


def _increment_memory_counter(key, window_seconds):
    now = time.time()
    with _MEMORY_LOCK:
        count, expires_at = _MEMORY_COUNTERS.get(key, (0, now + window_seconds))
        if expires_at <= now:
            count = 0
            expires_at = now + window_seconds

        count += 1
        _MEMORY_COUNTERS[key] = (count, expires_at)
        retry_after = max(1, math.ceil(expires_at - now))

    return count, retry_after


def _increment_redis_counter(key, window_seconds):
    client = _get_redis_client()
    count = int(client.incr(key))
    if count == 1:
        client.expire(key, window_seconds)

    ttl = client.ttl(key)
    retry_after = ttl if ttl and ttl > 0 else window_seconds
    return count, retry_after


def _increment_counter(key, window_seconds):
    if Config.RATE_LIMITING_BACKEND == "memory" or _is_testing_request():
        return _increment_memory_counter(key, window_seconds)

    try:
        return _increment_redis_counter(key, window_seconds)
    except RedisError as exc:
        if not _memory_backend_allowed():
            LOGGER.warning("rate_limit_backend_unavailable", extra={"backend_error": str(exc)})
            raise

        LOGGER.info("rate_limit_memory_fallback", extra={"backend_error": str(exc)})
        return _increment_memory_counter(key, window_seconds)


def _limit_for_action(action):
    if action == "login":
        return (
            Config.AUTH_LOGIN_RATE_LIMIT_ATTEMPTS,
            Config.AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )

    if action == "register":
        return (
            Config.AUTH_REGISTER_RATE_LIMIT_ATTEMPTS,
            Config.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
        )

    raise ValueError(f"Action rate limit inconnue: {action}")


def verifier_limite_auth(action, payload, request_obj):
    if not Config.RATE_LIMITING_ENABLED:
        return RateLimitDecision(allowed=True)

    max_attempts, window_seconds = _limit_for_action(action)
    keys = _rate_limit_keys(action, payload, request_obj)

    try:
        for key in keys:
            count, retry_after = _increment_counter(key, window_seconds)
            if count > max_attempts:
                return RateLimitDecision(
                    allowed=False,
                    status_code=429,
                    message="Trop de tentatives. Reessayez plus tard.",
                    retry_after_seconds=retry_after,
                )
    except RedisError:
        return RateLimitDecision(
            allowed=False,
            status_code=503,
            message="Service temporairement indisponible.",
            retry_after_seconds=60,
        )

    return RateLimitDecision(allowed=True)


def reset_rate_limit_state_for_tests():
    global _REDIS_CLIENT
    _REDIS_CLIENT = None
    with _MEMORY_LOCK:
        _MEMORY_COUNTERS.clear()

