from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from common.responses import success_response, error_response
from auth.service import register_user, login_user, get_current_user, change_password

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/register")
def register():
    data = request.get_json()
    result, error = register_user(data)

    if error:
        return error_response(error[0], error[1])

    return success_response(result, "Compte créé avec succès", 201)

@auth_bp.post("/login")
def login():
    data = request.get_json()
    result, error = login_user(data)

    if error:
        return error_response(error[0], error[1])

    return success_response(result, "Connexion réussie")

@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")

    result, error = get_current_user(user_id, role)

    if error:
        return error_response(error[0], error[1])

    return success_response(result)

@auth_bp.put("/change-password")
@jwt_required()
def change_password_route():
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")
    data = request.get_json()

    result, error = change_password(user_id, role, data)

    if error:
        return error_response(error[0], error[1])

    return success_response(result, result["message"])