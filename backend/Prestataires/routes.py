from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from .repository import is_service_exist
from ..Auth.service import change_password
from ..Commun.journaux.audit_utils import construire_contexte_audit
from ..Commun.serializer import serialize_timedelta
from ..Commun.decorateurs import role_required
from ..Commun.reponses import success_response, error_response
from ..Reservations.service import update_reservation_status_prestataire
from .service import (
    get_my_profile,
    update_my_profile,
    list_my_reservations,
    list_my_upcoming_reservations,
    list_my_past_reservations,
    list_my_disponibilites,
    update_my_disponibilite,
    delete_my_disponibilite,
    update_my_service,
    delete_my_service,
    create_my_service, create_my_disponibilite, get_commentaire_on_me
)
from ..public.service import list_prestataire_services_public

prestataires_bp = Blueprint("prestataires", __name__, url_prefix="/prestataires")


def _get_json_payload():
    data = request.get_json(silent=True)
    if data is None:
        return {}
    return data


@prestataires_bp.get("/me")
@jwt_required()
@role_required("prestataire")
def get_my_profile_route():
    prestataire_id = int(get_jwt_identity())
    result, error = get_my_profile(prestataire_id)
    if error:
        return error_response(error, 404)

    return success_response(result, 200)


@prestataires_bp.put("/me")
@jwt_required()
@role_required("prestataire")
def update_my_profile_route():
    prestataire_id = int(get_jwt_identity())
    payload = _get_json_payload()

    result, error = update_my_profile(
        prestataire_id,
        payload,
        audit_context=construire_contexte_audit(prestataire_id, "prestataire"),
    )

    if error:
        status_code = 404 if error == "Prestataire introuvable" else 400
        return error_response(error, status_code)

    return success_response(result, 200)


@prestataires_bp.get("/me/reservations")
@jwt_required()
@role_required("prestataire")
def list_my_reservations_route():
    prestataire_id = int(get_jwt_identity())
    result, error = list_my_reservations(prestataire_id)

    if error:
        return error_response(error, 400)

    return success_response(result, 200)


@prestataires_bp.get("/me/reservations/upcoming")
@jwt_required()
@role_required("prestataire")
def list_my_upcoming_reservations_route():
    prestataire_id = int(get_jwt_identity())
    result, error = list_my_upcoming_reservations(prestataire_id)

    if error:
        return error_response(error, 400)

    return success_response(result, 200)


@prestataires_bp.get("/me/reservations/past")
@jwt_required()
@role_required("prestataire")
def list_my_past_reservations_route():
    prestataire_id = int(get_jwt_identity())
    result, error = list_my_past_reservations(prestataire_id)

    if error:
        return error_response(error, 400)

    return success_response(result, 200)


@prestataires_bp.patch("/me/reservations/<int:reservation_id>/statut")
@jwt_required()
@role_required("prestataire")
def update_my_reservation_status_route(reservation_id):
    prestataire_id = int(get_jwt_identity())
    payload = _get_json_payload()

    result, error = update_reservation_status_prestataire(
        prestataire_id,
        reservation_id,
        payload,
        audit_context=construire_contexte_audit(prestataire_id, "prestataire"),
    )

    if error:
        if error == "Impossible d'ecrire le journal d'audit de la reservation":
            return error_response(error, 500)
        if error in {"Reservation introuvable", "Acces refuse"}:
            return error_response(error, 404 if error == "Reservation introuvable" else 403)
        return error_response(error, 400)

    return success_response(result, 200)


@prestataires_bp.get("/me/disponibilites")
@jwt_required()
@role_required("prestataire")
def get_my_disponibilites_route():
    prestataire_id = int(get_jwt_identity())
    result, error = list_my_disponibilites(prestataire_id)

    if error:
        return error_response(error, 400)

    return success_response(result, 200)


@prestataires_bp.post("/me/disponibilites")
@jwt_required()
@role_required("prestataire")
def create_disponibilite_route():
    prestataire_id = int(get_jwt_identity())
    payload = _get_json_payload()

    result, error = create_my_disponibilite(prestataire_id, payload)

    if error:
        return error_response(error, 400)

    return success_response(result, 201)


@prestataires_bp.put("/me/disponibilites")
@jwt_required()
@role_required("prestataire")
def update_my_disponibilite_route():
    prestataire_id = int(get_jwt_identity())
    payload = _get_json_payload()

    result, error = update_my_disponibilite(
        prestataire_id,
        payload.get("original_jour"),
        payload.get("original_heure_debut"),
        payload.get("original_heure_fin"),
        payload
    )

    if error:
        if error == "Disponibilite introuvable":
            return error_response(error, 404)
        return error_response(error, 400)

    data = {
        "jour": result.get("jour"),
        "heure_debut": serialize_timedelta(result.get("heure_debut")),
        "heure_fin": serialize_timedelta(result.get("heure_fin")),
        "statut": result.get("statut")
    }

    return success_response(data, 200)


@prestataires_bp.delete("/me/disponibilites/<string:jour>/<string:heure_debut>/<string:heure_fin>")
@jwt_required()
@role_required("prestataire")
def delete_my_disponibilite_route(jour, heure_debut, heure_fin):
    prestataire_id = int(get_jwt_identity())

    result, error = delete_my_disponibilite(
        prestataire_id,
        jour,
        heure_debut,
        heure_fin
    )

    if error:
        if error == "Disponibilite introuvable":
            return error_response(error, 404)
        return error_response(error, 400)

    data = {
        "jour": result.get("jour"),
        "heure_debut": serialize_timedelta(result.get("heure_debut")),
        "heure_fin": serialize_timedelta(result.get("heure_fin")),
        "statut": result.get("statut")
    }

    return success_response(data, 200)


@prestataires_bp.get("/me/services")
@jwt_required()
@role_required("prestataire")
def get_my_services_route():
    prestataire_id = int(get_jwt_identity())
    result, error = list_prestataire_services_public(prestataire_id)

    if error:
        return error_response(error, 400)

    return success_response(result, 200)


@prestataires_bp.post("/me/services")
@jwt_required()
@role_required("prestataire")
def create_service_route():
    prestataire_id = int(get_jwt_identity())
    payload = _get_json_payload()

    if is_service_exist(prestataire_id, payload.get("nom")):
        return error_response("Ce service existe deja", 400)

    result, error = create_my_service(prestataire_id, payload)

    if error:
        return error_response(error, 400)

    return success_response(result, 201)


@prestataires_bp.put("/me/services/<int:service_id>")
@jwt_required()
@role_required("prestataire")
def update_my_service_route(service_id):
    prestataire_id = int(get_jwt_identity())
    payload = _get_json_payload()

    result, error = update_my_service(prestataire_id, service_id, payload)

    if error:
        if error in {"Service introuvable", "Acces refuse"}:
            return error_response(error, 404 if error == "Service introuvable" else 403)
        return error_response(error, 400)

    return success_response(result)


@prestataires_bp.delete("/me/services/<int:service_id>")
@jwt_required()
@role_required("prestataire")
def delete_my_service_route(service_id):
    prestataire_id = int(get_jwt_identity())

    result, error = delete_my_service(prestataire_id, service_id)

    if error:
        if error in {"Service introuvable", "Acces refuse"}:
            return error_response(error, 404 if error == "Service introuvable" else 403)
        return error_response(error, 400)

    return success_response(result, 200)


@prestataires_bp.get("/me/reservations/<int:reservation_id>/commentaire")
@jwt_required()
def get_commentaire_route(reservation_id):
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")

    if role != "prestataire":
        return error_response("Accès refusé.", 403)

    result, error = get_commentaire_on_me(user_id, reservation_id)
    if error:
        status_code = 404 if error in {"Réservation introuvable.", "Commentaire introuvable."} else 403
        return error_response(error, status_code)

    return success_response(result, status=200)

@prestataires_bp.put("/me/change-password")
@jwt_required()
def change_password_route():
    user_id = int(get_jwt_identity())
    role = get_jwt().get("role")
    data = request.get_json() or {}

    result, error = change_password(
        user_id,
        role,
        data,
        audit_context=construire_contexte_audit(user_id, role),
    )
    if error:
        return error_response(error, 400)

    return success_response(result, 200)
