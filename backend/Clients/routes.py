from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from ..Auth.service import change_password
from ..Commun.decorateurs import role_required
from ..Commun.reponses import error_response, success_response
from ..Commun.serializer import serialize_reservation
from .service import (
    cancel_reservation,
    create_commentaire,
    get_client_profile,
    get_commentaire_me,
    get_facture_by_id_secure,
    get_reservation_detail,
    list_my_factures,
    list_my_past_reservations,
    list_my_reservations,
    list_my_upcoming_reservations,
    update_client_profile,
    update_my_commentaire
)


client_bp = Blueprint("client", __name__)


NOT_FOUND_ERRORS = {
    "Client introuvable.",
    "Reservation introuvable.",
    "Facture introuvable.",
    "Commentaire introuvable."
}


def _read_actor():
    actor_id = int(get_jwt_identity())
    actor_role = get_jwt().get("role")
    return actor_id, actor_role


def _read_payload():
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload
    return {}


def _error_status(error_message):
    if error_message in NOT_FOUND_ERRORS:
        return 404
    if error_message == "Acces refuse.":
        return 403
    return 400


def _ensure_client_role(role):
    if role != "client":
        return error_response("Acces refuse.", 403)
    return None


@client_bp.get("/me")
@jwt_required()
def get_my_profile():
    user_id, role = _read_actor()

    role_error = _ensure_client_role(role)
    if role_error:
        return role_error

    result, error = get_client_profile(user_id)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=200)


@client_bp.put("/me")
@jwt_required()
def update_my_profile():
    user_id, role = _read_actor()

    role_error = _ensure_client_role(role)
    if role_error:
        return role_error

    payload = _read_payload()
    result, error = update_client_profile(user_id, payload)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=200)


@client_bp.get("/me/reservations")
@jwt_required()
def get_my_reservations():
    user_id, role = _read_actor()

    role_error = _ensure_client_role(role)
    if role_error:
        return role_error

    result, error = list_my_reservations(user_id)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result)


@client_bp.get("/me/reservations/upcoming")
@jwt_required()
def get_my_upcoming_reservations():
    user_id, role = _read_actor()

    role_error = _ensure_client_role(role)
    if role_error:
        return role_error

    result, error = list_my_upcoming_reservations(user_id)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=200)


@client_bp.get("/me/reservations/past")
@jwt_required()
def get_my_past_reservations():
    user_id, role = _read_actor()

    role_error = _ensure_client_role(role)
    if role_error:
        return role_error

    result, error = list_my_past_reservations(user_id)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=200)


@client_bp.get("/me/factures")
@jwt_required()
def get_my_factures():
    user_id, role = _read_actor()

    role_error = _ensure_client_role(role)
    if role_error:
        return role_error

    result, error = list_my_factures(user_id)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=200)


@client_bp.get("/me/reservations/<int:reservation_id>")
@jwt_required()
def get_reservation(reservation_id):
    user_id, role = _read_actor()

    result, error = get_reservation_detail(reservation_id, user_id, role)
    if error:
        return error_response(error, _error_status(error))

    response_data = {
        "reservation": serialize_reservation(result.get("reservation")),
        "services": result.get("services")
    }
    return success_response(response_data, status=200)


@client_bp.delete("/me/reservations/<int:reservation_id>")
@jwt_required()
def cancel_reservation_route(reservation_id):
    user_id, role = _read_actor()

    if role not in {"client", "prestataire"}:
        return error_response("Acces refuse.", 403)

    result, error = cancel_reservation(reservation_id, user_id, role)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=200)


@client_bp.get("/me/factures/<int:facture_id>")
@jwt_required()
def get_facture_by_id_route(facture_id):
    user_id, role = _read_actor()

    result, error = get_facture_by_id_secure(facture_id, user_id, role)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=200)


@client_bp.post("/me/reservations/<int:reservation_id>/commentaire")
@jwt_required()
def create_commentaire_route(reservation_id):
    user_id, role = _read_actor()

    role_error = _ensure_client_role(role)
    if role_error:
        return role_error

    payload = _read_payload()
    result, error = create_commentaire(user_id, reservation_id, payload)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=201)


@client_bp.get("/me/reservations/<int:reservation_id>/commentaire")
@jwt_required()
def get_commentaire_route(reservation_id):
    user_id, role = _read_actor()

    role_error = _ensure_client_role(role)
    if role_error:
        return role_error

    result, error = get_commentaire_me(user_id, reservation_id)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=200)


@client_bp.put("/me/reservations/<int:reservation_id>/commentaire")
@jwt_required()
@role_required("client")
def update_my_commentaire_route(reservation_id):
    client_id, role = _read_actor()

    role_error = _ensure_client_role(role)
    if role_error:
        return role_error

    payload = _read_payload()
    result, error = update_my_commentaire(client_id, reservation_id, payload)
    if error:
        return error_response(error, _error_status(error))

    return success_response(result, status=200)


@client_bp.put("/me/change-password")
@jwt_required()
@role_required("client")
def change_password_route():
    user_id, role = _read_actor()
    payload = _read_payload()

    result, error = change_password(user_id, role, payload)
    if error:
        return error_response(error, 400)

    return success_response(result, status=200)
