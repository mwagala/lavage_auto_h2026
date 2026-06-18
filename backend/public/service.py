from .repository import (
    get_all_prestataires,
    get_prestataire_by_id,
    get_services_by_prestataire,
    get_disponibilites_open_by_prestataire,
    get_commentaires_by_prestataire,
    get_all_services
)
from ..Commun.serializer import serialize_timedelta


def _serialize_disponibilite_public(row):
    return {
        "jour": row.get("jour"),
        "heure_debut": serialize_timedelta(row.get("heure_debut")),
        "heure_fin": serialize_timedelta(row.get("heure_fin")),
        "statut": row.get("statut"),
    }


def list_prestataires_public():
    result = get_all_prestataires()
    return result, None


def get_prestataire_public(prestataire_id):
    prestataire = get_prestataire_by_id(prestataire_id)

    if not prestataire:
        return None, "Prestataire introuvable"

    prestataire["services"] = get_services_by_prestataire(prestataire_id)
    prestataire["disponibilites"] = [
        _serialize_disponibilite_public(row)
        for row in get_disponibilites_open_by_prestataire(prestataire_id)
    ]

    return prestataire, None


def list_prestataire_services_public(prestataire_id):
    prestataire = get_prestataire_by_id(prestataire_id)
    if not prestataire:
        return None, "Prestataire introuvable"

    services = get_services_by_prestataire(prestataire_id)
    return services, None


def list_prestataire_disponibilites_public(prestataire_id):
    prestataire = get_prestataire_by_id(prestataire_id)
    if not prestataire:
        return None, "Prestataire introuvable"

    disponibilites = [
        _serialize_disponibilite_public(row)
        for row in get_disponibilites_open_by_prestataire(prestataire_id)
    ]
    return disponibilites, None


def list_prestataire_commentaires_public(prestataire_id):
    prestataire = get_prestataire_by_id(prestataire_id)
    if not prestataire:
        return None, "Prestataire introuvable"

    commentaires = get_commentaires_by_prestataire(prestataire_id)
    return commentaires, None


def list_services_public():
    result = get_all_services()
    return result, None
