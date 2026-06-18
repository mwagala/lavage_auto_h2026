from datetime import date, datetime

from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash, generate_password_hash

from ..Commun.validators import normalize_code_postal, normalize_nas, validate_password
from .repository import (
    get_client_by_email,
    get_client_by_id,
    get_client_by_telephone,
    get_prestataire_by_email,
    get_prestataire_by_id,
    get_prestataire_by_nas,
    get_prestataire_by_telephone,
    insert_client,
    insert_prestataire,
    update_client_password,
    update_prestataire_password
)


VALID_ROLES = {"client", "prestataire"}
VALID_PAYMENT_METHODS = {"Comptant", "Carte Credit", "Carte debit"}

COMMON_REQUIRED_FIELDS = [
    "nom",
    "prenoms",
    "date_naissance",
    "courriel",
    "telephone",
    "adresse_numero",
    "adresse_rue",
    "adresse_ville",
    "adresse_province",
    "adresse_code_postal",
    "mot_de_passe"
]


def _validate_role(role):
    if role not in VALID_ROLES:
        return "Role invalide. Valeurs permises : client, prestataire."
    return None


def _sanitize_user_response(user, role):
    if not user:
        return None

    return {
        "id": user["id"],
        "role": role,
        "nom": user["nom"],
        "prenoms": user["prenoms"],
        "courriel": user["courriel"],
        "telephone": user["telephone"],
        "est_actif": user["est_actif"],
        "cree_a": user["cree_a"],
        "modifier_a": user["modifier_a"]
    }


def _parse_birth_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    return None


def _is_at_least_age(birth_date_value, minimum_age):
    birth_date = _parse_birth_date(birth_date_value)
    if not birth_date:
        return False

    today = date.today()
    age = today.year - birth_date.year
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)

    if not had_birthday:
        age -= 1

    return age >= minimum_age


def _require_fields(data, required_fields):
    for field in required_fields:
        value = data.get(field)
        if value is None:
            return f"Champ obligatoire manquant : {field}"
        if isinstance(value, str) and not value.strip():
            return f"Champ obligatoire manquant : {field}"
    return None


def _get_user_by_role_and_email(role, email):
    if role == "client":
        return get_client_by_email(email)
    return get_prestataire_by_email(email)


def _get_user_by_role_and_id(role, user_id):
    if role == "client":
        return get_client_by_id(user_id)
    return get_prestataire_by_id(user_id)


def _get_login_candidates(email):
    candidates = []

    client = get_client_by_email(email)
    if client:
        candidates.append(("client", client))

    prestataire = get_prestataire_by_email(email)
    if prestataire:
        candidates.append(("prestataire", prestataire))

    return candidates


def _register_client(data, password_hash):
    mode_paiement = data.get("mode_paiement")
    if not mode_paiement:
        return None, "Champ obligatoire manquant : mode_paiement"

    if mode_paiement not in VALID_PAYMENT_METHODS:
        return None, "Le mode paiement doit etre Comptant, Carte Credit ou Carte debit"

    if get_client_by_email(data["courriel"]) or get_prestataire_by_email(data["courriel"]):
        return None, "Un compte avec ce courriel existe deja."

    if get_client_by_telephone(data["telephone"]):
        return None, "Un client avec ce numero de telephone existe deja."

    if not _is_at_least_age(data["date_naissance"], 16):
        return None, "Le client doit avoir au moins 16 ans"

    new_user_id = insert_client(data, password_hash)
    created_user = get_client_by_id(new_user_id)
    return _sanitize_user_response(created_user, "client"), None


def _register_prestataire(data, password_hash):
    if not data.get("nas"):
        return None, "Champ obligatoire manquant : nas"

    nas = normalize_nas(data.get("nas"))
    if not nas:
        return None, "Le NAS doit contenir exactement 9 chiffres."
    data["nas"] = nas

    if get_client_by_email(data["courriel"]) or get_prestataire_by_email(data["courriel"]):
        return None, "Un compte avec ce courriel existe deja."

    if get_prestataire_by_telephone(data["telephone"]):
        return None, "Un prestataire avec ce numero de telephone existe deja."

    if get_prestataire_by_nas(data["nas"]):
        return None, "Un prestataire avec ce numero de nas existe deja."

    if not _is_at_least_age(data["date_naissance"], 18):
        return None, "Le prestataire doit avoir au moins 18 ans"

    new_user_id = insert_prestataire(data, password_hash)
    created_user = get_prestataire_by_id(new_user_id)
    return _sanitize_user_response(created_user, "prestataire"), None


def register_user(data):
    if not isinstance(data, dict):
        return None, "Donnees invalides."

    data = dict(data)

    role = data.get("role")
    role_error = _validate_role(role)
    if role_error:
        return None, role_error

    missing_field_error = _require_fields(data, COMMON_REQUIRED_FIELDS)
    if missing_field_error:
        return None, missing_field_error

    code_postal = normalize_code_postal(data.get("adresse_code_postal"))
    if not code_postal:
        return None, "Le code postal doit respecter le format A1A 1A1."
    data["adresse_code_postal"] = code_postal

    password, password_error = validate_password(data["mot_de_passe"])
    if password_error:
        return None, password_error

    password_hash = generate_password_hash(password)

    if role == "client":
        return _register_client(data, password_hash)

    return _register_prestataire(data, password_hash)


def login_user(data):
    if not isinstance(data, dict):
        return None, "Donnees invalides."

    email = data.get("courriel")
    password = data.get("mot_de_passe")

    if not email or not password:
        return None, "Champs obligatoires manquants: courriel, mot_de_passe"

    matching_users = []
    inactive_match_found = False

    for role, user in _get_login_candidates(email):
        if not check_password_hash(user["mot_passe_hash"], password):
            continue

        if not user["est_actif"]:
            inactive_match_found = True
            continue

        matching_users.append((role, user))

    if len(matching_users) > 1:
        return None, "Ce courriel correspond a plusieurs comptes. Contactez le support."

    if inactive_match_found and not matching_users:
        return None, "Compte inactif."

    if not matching_users:
        return None, "Identifiants invalides."

    role, user = matching_users[0]

    access_token = create_access_token(
        identity=str(user["id"]),
        additional_claims={"role": role}
    )

    response = {
        "access_token": access_token,
        "user": _sanitize_user_response(user, role)
    }
    return response, None


def logout_user():
    return {"message": "Deconnexion reussie."}, None


def get_current_user(user_id, role):
    role_error = _validate_role(role)
    if role_error:
        return None, role_error

    user = _get_user_by_role_and_id(role, user_id)
    if not user:
        return None, "Utilisateur introuvable."

    return _sanitize_user_response(user, role), None


def change_password(user_id, role, data):
    if not isinstance(data, dict):
        return None, "Donnees invalides."

    current_password = data.get("ancien_mot_de_passe")
    new_password = data.get("nouveau_mot_de_passe")

    if not current_password or not new_password:
        return None, "Champs obligatoires manquants."

    new_password, password_error = validate_password(new_password)
    if password_error:
        return None, password_error

    role_error = _validate_role(role)
    if role_error:
        return None, role_error

    user = _get_user_by_role_and_id(role, user_id)
    if not user:
        return None, "Utilisateur introuvable."

    user_with_hash = _get_user_by_role_and_email(role, user["courriel"])
    if not user_with_hash:
        return None, "Utilisateur introuvable."

    if not check_password_hash(user_with_hash["mot_passe_hash"], current_password):
        return None, "Ancien mot de passe incorrect."

    if check_password_hash(user_with_hash["mot_passe_hash"], new_password):
        return None, "Le nouveau mot de passe doit etre different de l'ancien."

    new_password_hash = generate_password_hash(new_password)

    if role == "client":
        update_client_password(user_id, new_password_hash)
    else:
        update_prestataire_password(user_id, new_password_hash)

    return {"message": "Mot de passe modifie avec succes."}, None
