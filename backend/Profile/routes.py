from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from ..Commun.reponses import success_response, error_response
from .service import (
    get_profile,
    update_profile,
    delete_profile
)

profile_bp = Blueprint("profile", __name__)


@profile_bp.get("/")
@jwt_required()
def get_profile_route():
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")

    result, error = get_profile(user_id, role)
    if error:
        return error_response(error, 404)

    return success_response(result, 200)


@profile_bp.put("/")
@jwt_required()
def update_profile_route():
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")
    data = request.get_json() or {}

    result, error = update_profile(user_id, role, data)
    if error:
        return error_response(error, 400)

    return success_response(result, 200)


@profile_bp.delete("/")
@jwt_required()
def delete_profile_route():
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")

    result, error = delete_profile(user_id, role)
    if error:
        return error_response(error, 400)

    return success_response(result, 200)