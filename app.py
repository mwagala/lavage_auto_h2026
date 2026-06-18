from flask import Flask
from flask_cors import CORS

from bd.config import Config
from extensions import bcrypt, jwt

from backend.Auth.routes import auth_bp
from backend.Clients.routes import client_bp
from backend.Commun.logging_config import configure_logging
from backend.Commun.middleware import register_request_middleware
from backend.Health.routes import health_bp
from backend.Prestataires.routes import prestataires_bp
from backend.Profile.routes import profile_bp
from backend.Reservations.routes import reservations_bp
from backend.public.routes import catalogue_bp
from frontend.route.privee import client_front_bp, prestataire_front_bp
from frontend.route.public import public_bp


def _configure_app_settings(app):
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["JWT_SECRET_KEY"] = Config.JWT_SECRET_KEY
    app.config["LOG_LEVEL"] = Config.LOG_LEVEL


def _register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(profile_bp, url_prefix="/profile")
    app.register_blueprint(client_bp, url_prefix="/clients")
    app.register_blueprint(prestataires_bp, url_prefix="/prestataires")
    app.register_blueprint(health_bp)
    app.register_blueprint(catalogue_bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(client_front_bp)
    app.register_blueprint(prestataire_front_bp)


def create_app():
    app = Flask(
        __name__,
        template_folder="frontend/templates",
        static_folder="frontend/static"
    )

    _configure_app_settings(app)
    configure_logging(app)

    CORS(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    register_request_middleware(app)
    _register_blueprints(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
