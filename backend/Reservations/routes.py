from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from ..Commun.decorateurs import role_required
from ..Commun.journaux.audit_utils import construire_contexte_audit
from ..Commun.reponses import error_response, success_response
from ..Commun.serializer import serialize_timedelta
from .service import (
    cancel_reservation_any,
    create_reservation_client,
    get_reservation_detail_for_actor,
    get_reservation_facture_for_actor,
    list_available_prestataires_for_service,
    update_reservation_any,
    update_reservation_status_prestataire
)


reservations_bp = Blueprint("reservations", __name__)


def _read_payload():
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload
    return {}


def _read_current_actor():
    claims = get_jwt()
    actor_id = int(get_jwt_identity())
    actor_role = claims.get("role")

    if actor_role not in {"client", "prestataire"}:
        return None, None, ("Acces refuse", 403)

    return actor_id, actor_role, None


def _map_reservation_error_to_http_status(error_message):
    if error_message == "Reservation introuvable":
        return 404
    if error_message == "Facture introuvable":
        return 404
    if error_message == "Acces refuse":
        return 403
    if error_message == "Impossible d'ecrire le journal d'audit de la reservation":
        return 500
    if error_message in {
        "La cle d'idempotence existe deja avec une requete differente",
        "Cette creation de reservation est deja en cours",
        "Cette creation de reservation est deja traitee",
        "Cette cle d'idempotence est associee a une tentative echouee",
    }:
        return 409
    return 400


@reservations_bp.post("/new_reservation")
@jwt_required()
@role_required("client")
def create_reservation_route():
    actor_id, actor_role, actor_error = _read_current_actor()
    if actor_error:
        return error_response(actor_error[0], actor_error[1])

    if actor_role != "client":
        return error_response("Acces reserve au client", 403)

    payload = _read_payload()
    result, error = create_reservation_client(
        actor_id,
        payload,
        audit_context=construire_contexte_audit(actor_id, actor_role),
        idempotency_key=request.headers.get("Idempotency-Key"),
    )
    if error:
        return error_response(error, _map_reservation_error_to_http_status(error))

    return success_response(result, status=201)


@reservations_bp.get("/reservations/<int:reservation_id>")
@jwt_required()
def get_reservation_detail_route(reservation_id):
    actor_id, actor_role, actor_error = _read_current_actor()
    if actor_error:
        return error_response(actor_error[0], actor_error[1])

    result, error = get_reservation_detail_for_actor(actor_id, actor_role, reservation_id)
    if error:
        return error_response(error, _map_reservation_error_to_http_status(error))

    return success_response(result)


@reservations_bp.put("/reservations/<int:reservation_id>")
@jwt_required()
def update_reservation_route(reservation_id):
    actor_id, actor_role, actor_error = _read_current_actor()
    if actor_error:
        return error_response(actor_error[0], actor_error[1])

    payload = _read_payload()
    result, error = update_reservation_any(
        actor_id,
        actor_role,
        reservation_id,
        payload,
        audit_context=construire_contexte_audit(actor_id, actor_role),
    )
    if error:
        return error_response(error, _map_reservation_error_to_http_status(error))

    return success_response(result)


@reservations_bp.patch("/reservations/<int:reservation_id>/statut")
@jwt_required()
def update_reservation_status_route(reservation_id):
    actor_id, actor_role, actor_error = _read_current_actor()
    if actor_error:
        return error_response(actor_error[0], actor_error[1])

    if actor_role != "prestataire":
        return error_response("Acces reserve au prestataire", 403)

    payload = _read_payload()
    result, error = update_reservation_status_prestataire(
        actor_id,
        reservation_id,
        payload,
        audit_context=construire_contexte_audit(actor_id, actor_role),
    )
    if error:
        return error_response(error, _map_reservation_error_to_http_status(error))

    return success_response(result)


@reservations_bp.delete("/reservations/<int:reservation_id>")
@jwt_required()
def cancel_reservation_route(reservation_id):
    actor_id, actor_role, actor_error = _read_current_actor()
    if actor_error:
        return error_response(actor_error[0], actor_error[1])

    result, error = cancel_reservation_any(
        actor_id,
        actor_role,
        reservation_id,
        audit_context=construire_contexte_audit(actor_id, actor_role),
    )
    if error:
        return error_response(error, _map_reservation_error_to_http_status(error))

    return success_response(result)


@reservations_bp.get("/reservations/<int:reservation_id>/facture")
@jwt_required()
def get_reservation_facture_route(reservation_id):
    actor_id, actor_role, actor_error = _read_current_actor()
    if actor_error:
        return error_response(actor_error[0], actor_error[1])

    result, error = get_reservation_facture_for_actor(actor_id, actor_role, reservation_id)
    if error:
        return error_response(error, _map_reservation_error_to_http_status(error))

    response_data = {
        "facture_id": result.get("id"),
        "reservation_id": result.get("reservation_id"),
        "prestataire_id": result.get("prestataire_id"),
        "date": result.get("date").isoformat() if result.get("date") else None,
        "heure_debut": serialize_timedelta(result.get("heure_debut")),
        "heure_fin": serialize_timedelta(result.get("heure_fin")),
        "sous_total": result.get("sous_total"),
        "total": result.get("total"),
        "services": result.get("services")
    }
    return success_response(response_data)


@reservations_bp.get("/prestataires/disponibles")
def get_available_prestataires_route():
    service_id = request.args.get("service_id", type=int)
    date_value = request.args.get("date")
    heure_debut = request.args.get("heure_debut")

    result, error = list_available_prestataires_for_service(service_id, date_value, heure_debut)
    if error:
        return error_response(error, 400)

    return success_response(result, message="Succes")
