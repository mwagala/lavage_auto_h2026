from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..Commun.reponses import error_response, success_response
from .service import login_user, logout_user, register_user


auth_bp = Blueprint("auth", __name__)


def _read_json_payload():
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload
    return {}


@auth_bp.post("/register")
def register_route():
    payload = _read_json_payload()
    result, error = register_user(payload)

    if error:
        return error_response(error, 400)

    return success_response(result, status=201)


@auth_bp.post("/login")
def login_route():
    payload = _read_json_payload()
    result, error = login_user(payload)

    if error:
        # On ne dit pas si email ou mot de passe est faux pour limiter
        # la fuite d'information.
        return error_response(error, 401)

    return success_response(result, status=200)


@auth_bp.post("/logout")
@jwt_required()
def logout_route():
    result, error = logout_user()

    if error:
        return error_response(error, 400)

    return success_response(result, status=200)
