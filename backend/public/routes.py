from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required

from ..Commun.reponses import success_response, error_response
from .service import (
    list_prestataires_public,
    get_prestataire_public,
    list_prestataire_services_public,
    list_prestataire_disponibilites_public,
    list_prestataire_commentaires_public,
    list_services_public
)

catalogue_bp = Blueprint("catalogue", __name__)


def _optional_auth():
    try:
        jwt_required(optional=True)()
    except Exception:
        pass


@catalogue_bp.get("/prestataires")
def list_prestataires_route():
    _optional_auth()
    result, error = list_prestataires_public()

    if error:
        return error_response(error, 400)

    return success_response(result)


@catalogue_bp.get("/prestataires/<int:prestataire_id>")
def get_prestataire_route(prestataire_id):
    _optional_auth()
    result, error = get_prestataire_public(prestataire_id)

    if error:
        if error == "Prestataire introuvable":
            return error_response(error, 404)
        return error_response(error, 400)

    return success_response(result)


@catalogue_bp.get("/prestataires/<int:prestataire_id>/services")
def get_prestataire_services_route(prestataire_id):
    _optional_auth()
    result, error = list_prestataire_services_public(prestataire_id)

    if error:
        if error == "Prestataire introuvable":
            return error_response(error, 404)
        return error_response(error, 400)

    return success_response(result)


@catalogue_bp.get("/prestataires/<int:prestataire_id>/disponibilites")
def get_prestataire_disponibilites_route(prestataire_id):
    _optional_auth()
    result, error = list_prestataire_disponibilites_public(prestataire_id)

    if error:
        if error == "Prestataire introuvable":
            return error_response(error, 404)
        return error_response(error, 400)

    return success_response(result)


@catalogue_bp.get("/prestataires/<int:prestataire_id>/commentaires")
def get_prestataire_commentaires_route(prestataire_id):
    _optional_auth()
    result, error = list_prestataire_commentaires_public(prestataire_id)

    if error:
        if error == "Prestataire introuvable":
            return error_response(error, 404)
        return error_response(error, 400)

    return success_response(result)


@catalogue_bp.get("/services")
def list_services_route():
    _optional_auth()
    result, error = list_services_public()

    if error:
        return error_response(error, 400)

    return success_response(result)