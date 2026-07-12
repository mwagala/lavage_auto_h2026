from flask_jwt_extended import create_access_token

from backend.Commun.middleware import CORRELATION_HEADER
from backend.Health import routes as health_routes


def test_cors_does_not_allow_unconfigured_origin(monkeypatch):
    from flask import Flask

    from app import _configure_cors
    from bd.config import Config

    cors_app = Flask(__name__)
    monkeypatch.setattr(Config, "CORS_ALLOWED_ORIGINS", ["https://allowed.example"])
    _configure_cors(cors_app)

    @cors_app.get("/ping")
    def ping():
        return {"ok": True}

    response = cors_app.test_client().get(
        "/ping",
        headers={"Origin": "https://evil.example"},
    )

    assert "Access-Control-Allow-Origin" not in response.headers


def test_health_liveness_returns_standard_payload(client):
    response = client.get("/health", headers={CORRELATION_HEADER: "corr-health"})

    assert response.status_code == 200
    assert response.headers[CORRELATION_HEADER] == "corr-health"
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"] == {"status": "ok", "service": "lavage-auto"}
    assert payload["correlation_id"] == "corr-health"


def test_health_database_check_uses_shared_connection(monkeypatch):
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, query):
            assert query == "SELECT 1"

        def fetchone(self):
            return [1]

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(health_routes, "get_connection", lambda: FakeConnection())

    result = health_routes._check_database()

    assert result == {"ok": True, "details": {"result": 1}}


def test_health_readiness_success_with_mocked_checks(client, monkeypatch):
    monkeypatch.setattr(
        health_routes,
        "_check_database",
        lambda: health_routes._ok({"result": 1}),
    )
    monkeypatch.setattr(
        health_routes,
        "_check_redis_url",
        lambda url: health_routes._ok({"url": url}),
    )

    response = client.get("/health/readiness")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "ok"
    assert set(payload["data"]["checks"]) == {
        "database",
        "redis",
        "celery_broker",
        "celery_result_backend",
    }


def test_health_readiness_reuses_same_redis_url_result(client, monkeypatch):
    calls = []

    monkeypatch.setattr(
        health_routes,
        "_check_database",
        lambda: health_routes._ok({"result": 1}),
    )
    monkeypatch.setattr(health_routes.Config, "REDIS_URL", "redis://render-internal:6379")
    monkeypatch.setattr(health_routes.Config, "CELERY_BROKER_URL", "redis://render-internal:6379")
    monkeypatch.setattr(health_routes.Config, "CELERY_RESULT_BACKEND", "redis://render-internal:6379")

    def fake_check_redis_url(url):
        calls.append(url)
        return health_routes._ok({"url": url})

    monkeypatch.setattr(health_routes, "_check_redis_url", fake_check_redis_url)

    response = client.get("/health/readiness")

    assert response.status_code == 200
    assert calls == ["redis://render-internal:6379"]


def test_health_readiness_degraded_with_mocked_failure(client, monkeypatch):
    monkeypatch.setattr(
        health_routes,
        "_check_database",
        lambda: health_routes._ok({"result": 1}),
    )
    monkeypatch.setattr(
        health_routes,
        "_check_redis_url",
        lambda url: health_routes._ko("redis down"),
    )

    response = client.get("/health/readiness")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["data"]["status"] == "degrade"
    assert payload["data"]["checks"]["redis"]["ok"] is False


def test_auth_login_route_returns_standard_success_payload(client, monkeypatch):
    from backend.Auth import routes as auth_routes

    monkeypatch.setattr(
        auth_routes,
        "login_user",
        lambda payload, **kwargs: ({"access_token": "token", "user": {"id": 1}}, None),
    )

    response = client.post(
        "/auth/login",
        json={"courriel": "client@example.com", "mot_de_passe": "secret"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["access_token"] == "token"
    assert "correlation_id" in payload


def test_reservation_create_route_returns_standard_payload(client, app, monkeypatch):
    from backend.Reservations import routes as reservation_routes

    with app.app_context():
        token = create_access_token(
            identity="7",
            additional_claims={"role": "client"},
        )

    monkeypatch.setattr(
        reservation_routes,
        "create_reservation_client",
        lambda actor_id, payload, **kwargs: (
            {"id": 99, "client_id": actor_id, "statut": "Assignee"},
            None,
        ),
    )

    response = client.post(
        "/new_reservation",
        headers={"Authorization": f"Bearer {token}"},
        json={"prestataire_id": 3},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"] == {"id": 99, "client_id": 7, "statut": "Assignee"}
    assert "correlation_id" in payload


def test_reservation_create_route_rejects_wrong_role_with_standard_payload(client, app):
    with app.app_context():
        token = create_access_token(
            identity="3",
            additional_claims={"role": "prestataire"},
        )

    response = client.post(
        "/new_reservation",
        headers={"Authorization": f"Bearer {token}"},
        json={"prestataire_id": 3},
    )

    assert response.status_code == 403
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["message"] == "Acces refuse."
    assert "correlation_id" in payload
