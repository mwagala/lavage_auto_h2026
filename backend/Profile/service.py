import logging

from ..Commun.journaux.audit_utils import enregistrer_audit
from ..Commun.validators import normalize_code_postal
from .repository import (
    get_client_profile_by_id,
    get_prestataire_profile_by_id,
    update_client_profile,
    update_prestataire_profile,
    deactivate_client,
    deactivate_prestataire
)


LOGGER = logging.getLogger(__name__)
SENSITIVE_PROFILE_FIELDS = {"mot_de_passe", "ancien_mot_de_passe", "nouveau_mot_de_passe", "nas"}


def _champs_audites(data):
    if not isinstance(data, dict):
        return []
    return sorted(set(data.keys()) - SENSITIVE_PROFILE_FIELDS)


def _audit_update_profile(user_id, role, resultat, audit_context=None, details=None):
    contexte = dict(audit_context or {})
    contexte["acteur_id"] = user_id
    contexte["role_acteur"] = role
    _, erreur = enregistrer_audit(
        action="profile.updated",
        type_ressource=role if role in {"client", "prestataire"} else "profile",
        ressource_id=str(user_id) if user_id is not None else None,
        resultat=resultat,
        audit_context=contexte,
        details=details,
    )
    if erreur:
        LOGGER.warning("profile_audit_failed", extra={"audit_error": erreur})


def _validate_role(role):
    return role in ["client", "prestataire"]


def get_profile(user_id, role):
    if not _validate_role(role):
        return None, "Rôle invalide."

    if role == "client":
        user = get_client_profile_by_id(user_id)
    else:
        user = get_prestataire_profile_by_id(user_id)

    if not user:
        return None, "Utilisateur introuvable."

    return user, None


def _update_profile_impl(user_id, role, data):
    if not _validate_role(role):
        return None, "Rôle invalide."

    if not isinstance(data, dict):
        return None, "Donnees invalides."

    data = dict(data)

    required_fields = [
        "nom",
        "prenoms",
        "date_naissance",
        "courriel",
        "telephone",
        "adresse_numero",
        "adresse_rue",
        "adresse_ville",
        "adresse_province",
        "adresse_code_postal"
    ]

    for field in required_fields:
        if not data.get(field):
            return None, f"Champ obligatoire manquant : {field}"

    code_postal = normalize_code_postal(data.get("adresse_code_postal"))
    if not code_postal:
        return None, "Le code postal doit respecter le format A1A 1A1."
    data["adresse_code_postal"] = code_postal

    if role == "client":
        if not data.get("mode_paiement"):
            return None, "Champ obligatoire manquant : mode_paiement"
        update_client_profile(user_id, data)
        user = get_client_profile_by_id(user_id)
    else:
        update_prestataire_profile(user_id, data)
        user = get_prestataire_profile_by_id(user_id)

    return user, None


def update_profile(user_id, role, data, audit_context=None):
    result, error = _update_profile_impl(user_id, role, data)
    details = {"champs": _champs_audites(data)}
    if error:
        details["raison"] = error

    _audit_update_profile(
        user_id=user_id,
        role=role,
        resultat="echec" if error else "succes",
        audit_context=audit_context,
        details=details,
    )
    return result, error


def delete_profile(user_id, role):
    if not _validate_role(role):
        return None, "Rôle invalide."

    if role == "client":
        deactivate_client(user_id)
        user = get_client_profile_by_id(user_id)
    else:
        deactivate_prestataire(user_id)
        user = get_prestataire_profile_by_id(user_id)

    if not user:
        return None, "Utilisateur introuvable."

    return {"message": "Compte désactivé avec succès."}, None
