import pytest

from app import create_app


@pytest.fixture
def app():
    flask_app = create_app()
    flask_app.config.update(
        TESTING=True,
        PROPAGATE_EXCEPTIONS=False,
        CELERY_TASK_ALWAYS_EAGER=True,
        SECRET_KEY="test-secret-key-minimum-32-characters",
        JWT_SECRET_KEY="test-jwt-secret-key-minimum-32-characters",
    )
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def correlation_id():
    return "test-correlation-id"
