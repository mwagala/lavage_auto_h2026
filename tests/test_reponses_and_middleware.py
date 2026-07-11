from flask import g

from backend.Commun.middleware import CORRELATION_HEADER, register_request_middleware
from backend.Commun.reponses import error_response, success_response


def test_success_response_contains_standard_payload(app, correlation_id):
    with app.test_request_context("/unit"):
        g.correlation_id = correlation_id
        response, status = success_response({"ok": True}, status=201)

    assert status == 201
    assert response.get_json() == {
        "success": True,
        "message": "Succes",
        "data": {"ok": True},
        "correlation_id": correlation_id,
    }


def test_success_response_accepts_legacy_status_argument(app):
    with app.test_request_context("/unit"):
        response, status = success_response({"created": True}, 201)

    assert status == 201
    assert response.get_json()["message"] == "Succes"


def test_error_response_contains_standard_payload(app, correlation_id):
    with app.test_request_context("/unit"):
        g.correlation_id = correlation_id
        response, status = error_response("Bad request", status=400, data={"field": "x"})

    assert status == 400
    assert response.get_json() == {
        "success": False,
        "message": "Bad request",
        "data": {"field": "x"},
        "correlation_id": correlation_id,
    }


def test_middleware_generates_and_returns_correlation_id():
    from flask import Flask

    app = Flask(__name__)
    register_request_middleware(app)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    response = app.test_client().get("/ping")

    assert response.status_code == 200
    assert response.headers[CORRELATION_HEADER]
    assert response.get_json() == {"ok": True}


def test_middleware_reuses_incoming_correlation_id(correlation_id):
    from flask import Flask

    app = Flask(__name__)
    register_request_middleware(app)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    response = app.test_client().get(
        "/ping",
        headers={CORRELATION_HEADER: correlation_id},
    )

    assert response.status_code == 200
    assert response.headers[CORRELATION_HEADER] == correlation_id


def test_middleware_replaces_invalid_correlation_id():
    from flask import Flask

    app = Flask(__name__)
    register_request_middleware(app)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    invalid_correlation_id = "x" * 150
    response = app.test_client().get(
        "/ping",
        headers={CORRELATION_HEADER: invalid_correlation_id},
    )

    assert response.status_code == 200
    assert response.headers[CORRELATION_HEADER]
    assert response.headers[CORRELATION_HEADER] != invalid_correlation_id


def test_middleware_adds_security_headers():
    from flask import Flask

    app = Flask(__name__)
    register_request_middleware(app)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    response = app.test_client().get("/ping")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_unexpected_exception_is_standardized(client):
    client.application.add_url_rule(
        "/raise-unexpected",
        "raise_unexpected",
        lambda: (_ for _ in ()).throw(RuntimeError("secret detail")),
    )

    response = client.get("/raise-unexpected")

    assert response.status_code == 500
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["message"] == "Erreur interne du serveur."
    assert "secret detail" not in str(payload)
    assert response.headers[CORRELATION_HEADER] == payload["correlation_id"]
