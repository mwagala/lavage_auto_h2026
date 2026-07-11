from redis.exceptions import RedisError

from bd.config import Config
from backend.Commun import rate_limiting


def _configure_memory_rate_limit(monkeypatch, attempts=1):
    rate_limiting.reset_rate_limit_state_for_tests()
    monkeypatch.setattr(Config, "RATE_LIMITING_ENABLED", True)
    monkeypatch.setattr(Config, "RATE_LIMITING_BACKEND", "memory")
    monkeypatch.setattr(Config, "AUTH_LOGIN_RATE_LIMIT_ATTEMPTS", attempts)
    monkeypatch.setattr(Config, "AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(Config, "AUTH_REGISTER_RATE_LIMIT_ATTEMPTS", attempts)
    monkeypatch.setattr(Config, "AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS", 60)


def test_login_rate_limit_blocks_after_threshold(client, monkeypatch):
    from backend.Auth import routes as auth_routes

    _configure_memory_rate_limit(monkeypatch, attempts=1)
    calls = []
    monkeypatch.setattr(
        auth_routes,
        "login_user",
        lambda payload, **kwargs: calls.append(payload) or ({"access_token": "token"}, None),
    )
    monkeypatch.setattr(auth_routes, "enregistrer_audit", lambda *args, **kwargs: (None, None))

    payload = {"courriel": "limited-login@example.com", "mot_de_passe": "secret"}
    first_response = client.post("/auth/login", json=payload)
    second_response = client.post("/auth/login", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.get_json()["message"] == "Trop de tentatives. Reessayez plus tard."
    assert second_response.headers["Retry-After"]
    assert len(calls) == 1


def test_login_rate_limit_allows_until_threshold_then_blocks(client, monkeypatch):
    from backend.Auth import routes as auth_routes

    _configure_memory_rate_limit(monkeypatch, attempts=2)
    calls = []
    monkeypatch.setattr(
        auth_routes,
        "login_user",
        lambda payload, **kwargs: calls.append(payload) or ({"access_token": "token"}, None),
    )
    monkeypatch.setattr(auth_routes, "enregistrer_audit", lambda *args, **kwargs: (None, None))

    payload = {"courriel": "threshold-login@example.com", "mot_de_passe": "secret"}
    first_response = client.post("/auth/login", json=payload)
    second_response = client.post("/auth/login", json=payload)
    third_response = client.post("/auth/login", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert third_response.status_code == 429
    assert third_response.get_json()["success"] is False
    assert third_response.get_json()["message"] == "Trop de tentatives. Reessayez plus tard."
    assert len(calls) == 2


def test_register_rate_limit_blocks_after_threshold(client, monkeypatch):
    from backend.Auth import routes as auth_routes

    _configure_memory_rate_limit(monkeypatch, attempts=1)
    calls = []
    monkeypatch.setattr(
        auth_routes,
        "register_user",
        lambda payload, **kwargs: calls.append(payload) or ({"id": 1, "role": "client"}, None),
    )
    monkeypatch.setattr(auth_routes, "enregistrer_audit", lambda *args, **kwargs: (None, None))

    payload = {"courriel": "limited-register@example.com"}
    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 429
    assert second_response.get_json()["message"] == "Trop de tentatives. Reessayez plus tard."
    assert second_response.headers["Retry-After"]
    assert len(calls) == 1


def test_register_rate_limit_allows_until_threshold_then_blocks(client, monkeypatch):
    from backend.Auth import routes as auth_routes

    _configure_memory_rate_limit(monkeypatch, attempts=2)
    calls = []
    monkeypatch.setattr(
        auth_routes,
        "register_user",
        lambda payload, **kwargs: calls.append(payload) or ({"id": 1, "role": "client"}, None),
    )
    monkeypatch.setattr(auth_routes, "enregistrer_audit", lambda *args, **kwargs: (None, None))

    payload = {"courriel": "threshold-register@example.com"}
    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)
    third_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert third_response.status_code == 429
    assert third_response.get_json()["success"] is False
    assert third_response.get_json()["message"] == "Trop de tentatives. Reessayez plus tard."
    assert len(calls) == 2


def test_memory_rate_limit_resets_after_window(monkeypatch):
    class FakeRequest:
        remote_addr = "203.0.113.11"

    current_time = [1000.0]
    rate_limiting.reset_rate_limit_state_for_tests()
    monkeypatch.setattr(Config, "RATE_LIMITING_ENABLED", True)
    monkeypatch.setattr(Config, "RATE_LIMITING_BACKEND", "memory")
    monkeypatch.setattr(Config, "AUTH_LOGIN_RATE_LIMIT_ATTEMPTS", 1)
    monkeypatch.setattr(Config, "AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS", 10)
    monkeypatch.setattr(rate_limiting.time, "time", lambda: current_time[0])

    payload = {"courriel": "reset-window@example.com"}
    first_decision = rate_limiting.verifier_limite_auth("login", payload, FakeRequest())
    blocked_decision = rate_limiting.verifier_limite_auth("login", payload, FakeRequest())
    current_time[0] = 1011.0
    reset_decision = rate_limiting.verifier_limite_auth("login", payload, FakeRequest())

    assert first_decision.allowed is True
    assert blocked_decision.allowed is False
    assert blocked_decision.status_code == 429
    assert reset_decision.allowed is True


def test_rate_limit_fails_closed_when_redis_unavailable_in_production(monkeypatch):
    class FakeRequest:
        remote_addr = "203.0.113.10"

    rate_limiting.reset_rate_limit_state_for_tests()
    monkeypatch.setattr(Config, "RATE_LIMITING_ENABLED", True)
    monkeypatch.setattr(Config, "RATE_LIMITING_BACKEND", "redis")
    monkeypatch.setattr(Config, "IS_NON_PRODUCTION", False)
    monkeypatch.setattr(rate_limiting, "_get_redis_client", lambda: (_ for _ in ()).throw(RedisError("down")))

    decision = rate_limiting.verifier_limite_auth(
        "login",
        {"courriel": "client@example.com"},
        FakeRequest(),
    )

    assert decision.allowed is False
    assert decision.status_code == 503
    assert decision.message == "Service temporairement indisponible."
