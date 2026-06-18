from .repository import (
    get_client_profile_by_id,
    get_prestataire_profile_by_id,
    update_client_profile,
    update_prestataire_profile,
    deactivate_client,
    deactivate_prestataire
)
from ..Commun.validators import normalize_code_postal


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


def update_profile(user_id, role, data):
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
