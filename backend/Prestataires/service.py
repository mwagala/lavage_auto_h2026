from datetime import datetime

from ..Clients.repository import get_commentaire_by_reservation
from ..Clients.repository import get_reservation_by_id
from ..Commun.serializer import serialize_comments, serialize_timedelta, serialize_reservation, \
    serialize_reservation_prestataire
from ..Commun.validators import normalize_code_postal, normalize_nas

from .repository import (
    create_disponibilite,
    create_service,
    delete_disponibilite,
    delete_service,
    get_disponibilite,
    get_prestataire_all_reservations,
    get_prestataire_by_id,
    get_prestataire_commentaires,
    get_prestataire_disponibilites,
    get_prestataire_past_reservations,
    get_prestataire_services,
    get_prestataire_upcoming_reservations,
    get_reservation_for_prestataire,
    get_service_by_id_for_prestataire,
    overlapping_disponibilite_exists,
    service_name_exists_for_other_service,
    update_disponibilite,
    update_prestataire_profile,
    update_reservation_status,
    update_service,
)

ALLOWED_RESERVATION_STATUSES = {"Assignee", "En cours", "Annulee", "Terminee"}
ALLOWED_DISPO_STATUSES = {"disponible", "indisponible", "actif", "inactif"}
ALLOWED_PROFILE_FIELDS = {
    "nom",
    "prenoms",
    "date_naissance",
    "nas",
    "courriel",
    "telephone",
    "adresse_numero",
    "adresse_rue",
    "adresse_ville",
    "adresse_province",
    "adresse_code_postal",
}
REQUIRED_SERVICE_FIELDS = {"nom", "description", "duree", "prix"}
REQUIRED_DISPO_FIELDS = {"jour", "statut", "heure_debut", "heure_fin"}


def _clean_str(value):
    if value is None:
        return None
    return str(value).strip()


def _parse_time(value):
    try:
        return datetime.strptime(_clean_str(value), "%H:%M").time()
    except Exception:
        try:
            return datetime.strptime(_clean_str(value), "%H:%M:%S").time()
        except Exception:
            return None


def _normalize_time(value):
    parsed = _parse_time(value)
    return parsed.strftime("%H:%M:%S") if parsed else None


def _parse_date(value):
    try:
        return datetime.strptime(_clean_str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def _to_positive_decimal(value):
    try:
        number = round(float(value), 2)
        return number if number > 0 else None
    except Exception:
        return None


def _validate_email(value):
    value = _clean_str(value)
    return bool(value and "@" in value and "." in value.split("@")[-1])


def _validate_phone(value):
    value = _clean_str(value)
    digits = "".join(ch for ch in value if ch.isdigit())
    return len(digits) >= 7


def _normalize_jour(value):
    value = _clean_str(value)
    if not value:
        return None

    mapping = {
        "lundi": "lundi",
        "mardi": "mardi",
        "mercredi": "mercredi",
        "jeudi": "jeudi",
        "vendredi": "vendredi",
        "samedi": "samedi",
        "dimanche": "dimanche",
    }
    return mapping.get(value.lower())


def _validate_profile_payload(payload: dict):
    if not isinstance(payload, dict) or not payload:
        return None, "Aucune donnée fournie."

    unknown = set(payload.keys()) - ALLOWED_PROFILE_FIELDS
    if unknown:
        return None, f"Champs non autorisés: {', '.join(sorted(unknown))}."

    cleaned = {}

    for field, value in payload.items():
        if field == "date_naissance":
            parsed = _parse_date(value)
            if not parsed:
                return None, "date_naissance doit être au format YYYY-MM-DD."
            cleaned[field] = parsed.isoformat()
            continue

        value = _clean_str(value)
        if not value:
            return None, f"Le champ {field} est obligatoire."

        cleaned[field] = value

    if "courriel" in cleaned and not _validate_email(cleaned["courriel"]):
        return None, "Adresse courriel invalide."

    if "telephone" in cleaned and not _validate_phone(cleaned["telephone"]):
        return None, "Numéro de téléphone invalide."

    if "nas" in cleaned:
        nas = normalize_nas(cleaned["nas"])
        if not nas:
            return None, "Le NAS doit contenir exactement 9 chiffres."
        cleaned["nas"] = nas

    if "adresse_code_postal" in cleaned:
        code_postal = normalize_code_postal(cleaned["adresse_code_postal"])
        if not code_postal:
            return None, "Le code postal doit respecter le format A1A 1A1."
        cleaned["adresse_code_postal"] = code_postal

    return cleaned, None


def _validate_service_payload(payload: dict, partial: bool = False):
    if not isinstance(payload, dict) or not payload:
        return None, "Aucune donnée fournie."

    allowed_fields = REQUIRED_SERVICE_FIELDS
    unknown = set(payload.keys()) - allowed_fields
    if unknown:
        return None, f"Champs non autorisés: {', '.join(sorted(unknown))}."

    if not partial:
        missing = REQUIRED_SERVICE_FIELDS - set(payload.keys())
        if missing:
            return None, f"Champs manquants: {', '.join(sorted(missing))}."

    cleaned = {}

    if "nom" in payload:
        nom = _clean_str(payload.get("nom"))
        if not nom:
            return None, "Le nom du service est obligatoire."
        cleaned["nom"] = nom

    if "description" in payload:
        description = _clean_str(payload.get("description"))
        if not description:
            return None, "La description est obligatoire."
        cleaned["description"] = description

    if "duree" in payload:
        duree = _to_positive_decimal(payload.get("duree"))
        if duree is None:
            return None, "La durée doit être un nombre positif."
        cleaned["duree"] = duree

    if "prix" in payload:
        prix = _to_positive_decimal(payload.get("prix"))
        if prix is None:
            return None, "Le prix doit être un nombre positif."
        cleaned["prix"] = prix

    return cleaned, None


def _validate_dispo_payload(payload: dict, partial: bool = False):
    if not isinstance(payload, dict) or not payload:
        return None, "Aucune donnée fournie."

    unknown = set(payload.keys()) - REQUIRED_DISPO_FIELDS
    if unknown:
        return None, f"Champs non autorisés: {', '.join(sorted(unknown))}."

    if not partial:
        missing = REQUIRED_DISPO_FIELDS - set(payload.keys())
        if missing:
            return None, f"Champs manquants: {', '.join(sorted(missing))}."

    cleaned = {}

    if "jour" in payload:
        jour = _normalize_jour(payload.get("jour"))
        if not jour:
            return None, "Jour invalide."
        cleaned["jour"] = jour

    if "statut" in payload:
        statut = _clean_str(payload.get("statut"))
        if not statut:
            return None, "Le statut est obligatoire."
        statut_lower = statut.lower()
        if statut_lower not in ALLOWED_DISPO_STATUSES:
            return None, "Statut de disponibilité invalide."
        cleaned["statut"] = statut_lower

    if "heure_debut" in payload:
        heure_debut = _normalize_time(payload.get("heure_debut"))
        if not heure_debut:
            return None, "heure_debut invalide. Format attendu HH:MM ou HH:MM:SS."
        cleaned["heure_debut"] = heure_debut

    if "heure_fin" in payload:
        heure_fin = _normalize_time(payload.get("heure_fin"))
        if not heure_fin:
            return None, "heure_fin invalide. Format attendu HH:MM ou HH:MM:SS."
        cleaned["heure_fin"] = heure_fin

    if "heure_debut" in cleaned and "heure_fin" in cleaned:
        if cleaned["heure_debut"] >= cleaned["heure_fin"]:
            return None, "heure_debut doit être antérieure à heure_fin."

    return cleaned, None


def get_my_profile(prestataire_id: int):
    prestataire = get_prestataire_by_id(prestataire_id)
    if not prestataire:
        return None, "Prestataire introuvable."
    return prestataire, None


def update_my_profile(prestataire_id: int, payload: dict):
    prestataire = get_prestataire_by_id(prestataire_id)
    if not prestataire:
        return None, "Prestataire introuvable."

    fields, error = _validate_profile_payload(payload)
    if error:
        return None, error

    updated = update_prestataire_profile(prestataire_id, fields)
    return updated, None


def list_my_reservations(prestataire_id: int):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."

    rows = get_prestataire_all_reservations(prestataire_id) or []
    return [serialize_reservation(row) for row in rows], None


def list_my_upcoming_reservations(prestataire_id: int):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."
    rows = get_prestataire_upcoming_reservations(prestataire_id) or []
    return [serialize_reservation_prestataire(row) for row in rows], None


def list_my_past_reservations(prestataire_id: int):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."
    rows = get_prestataire_past_reservations(prestataire_id) or []
    return [serialize_reservation_prestataire(row) for row in rows], None


def update_my_reservation_status(prestataire_id: int, reservation_id: int, payload: dict):
    if not isinstance(payload, dict):
        return None, "Payload invalide."

    new_status = _clean_str(payload.get("statut"))
    if not new_status:
        return None, "Le champ statut est obligatoire."

    if new_status not in ALLOWED_RESERVATION_STATUSES:
        return None, "Statut invalide."

    reservation = get_reservation_for_prestataire(prestataire_id, reservation_id)
    if not reservation:
        return None, "Réservation introuvable."

    current_status = reservation["statut"]
    if current_status == new_status:
        return reservation, None

    allowed_transitions = {
        "Assignee": {"En cours", "annulee"},
        "En cours": {"Terminee", "annulee"},
        "annulee": set(),
        "Terminee": set(),
    }

    if new_status not in allowed_transitions.get(current_status, set()):
        return None, f"Transition invalide: {current_status} -> {new_status}."

    updated = update_reservation_status(prestataire_id, reservation_id, new_status)
    updated = serialize_reservation_prestataire(updated)
    return updated, None



def serialize_disponibilite(row):
    return {
        "jour": row.get("jour"),
            "heure_debut": serialize_timedelta(row.get("heure_debut")),
            "heure_fin": serialize_timedelta(row.get("heure_fin"))
    }

def list_my_disponibilites(prestataire_id: int):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."
    results = get_prestataire_disponibilites(prestataire_id)
    return [serialize_disponibilite(result) for result in results], None


def create_my_disponibilite(prestataire_id: int, payload: dict):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."

    cleaned, error = _validate_dispo_payload(payload, partial=False)
    if error:
        return None, error

    existing = get_disponibilite(
        prestataire_id,
        cleaned["jour"],
        cleaned["heure_debut"],
        cleaned["heure_fin"]
    )
    if existing:
        return None, "Cette disponibilité existe déjà."

    if overlapping_disponibilite_exists(
            prestataire_id,
            cleaned["jour"],
            cleaned["heure_debut"],
            cleaned["heure_fin"]
    ):
        return None, "Une autre disponibilité chevauche déjà cette plage horaire."

    created = create_disponibilite(
        prestataire_id,
        cleaned["jour"],
        cleaned["statut"],
        cleaned["heure_debut"],
        cleaned["heure_fin"]
    )
    return {"jour": created.get("jour"),
            "heure_debut": serialize_timedelta(created.get("heure_debut")),
            "heure_fin": serialize_timedelta(created.get("heure_fin"))}, None


def update_my_disponibilite(prestataire_id: int, jour: str, heure_debut: str, heure_fin: str, payload: dict):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."

    old_jour = _normalize_jour(jour)
    old_heure_debut = _normalize_time(heure_debut)
    old_heure_fin = _normalize_time(heure_fin)

    if not old_jour or not old_heure_debut or not old_heure_fin:
        return None, "Identifiant de disponibilité invalide."

    existing = get_disponibilite(prestataire_id, old_jour, old_heure_debut, old_heure_fin)
    if not existing:
        return None, "Disponibilité introuvable."

    clean_payload = {
        "jour": payload.get("jour"),
        "heure_debut": payload.get("heure_debut"),
        "heure_fin": payload.get("heure_fin")
    }

    cleaned, error = _validate_dispo_payload(clean_payload, partial=True)
    if error:
        return None, error

    final_jour = cleaned.get("jour", existing["jour"])
    final_statut = cleaned.get("statut", existing["statut"])
    final_heure_debut = cleaned.get("heure_debut", existing["heure_debut"])
    final_heure_fin = cleaned.get("heure_fin", existing["heure_fin"])

    final_heure_debut = _normalize_time(final_heure_debut)
    final_heure_fin = _normalize_time(final_heure_fin)

    if final_heure_debut >= final_heure_fin:
        return None, "heure_debut doit être antérieure à heure_fin."

    if overlapping_disponibilite_exists(
            prestataire_id,
            final_jour,
            final_heure_debut,
            final_heure_fin,
            exclude_old=(old_jour, old_heure_debut, old_heure_fin)
    ):
        return None, "Une autre disponibilité chevauche déjà cette plage horaire."

    updated = update_disponibilite(
        prestataire_id,
        old_jour,
        old_heure_debut,
        old_heure_fin,
        final_jour,
        final_statut,
        final_heure_debut,
        final_heure_fin
    )
    return updated, None


def delete_my_disponibilite(prestataire_id: int, jour: str, heure_debut: str, heure_fin: str):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."

    jour = _normalize_jour(jour)
    heure_debut = _normalize_time(heure_debut)
    heure_fin = _normalize_time(heure_fin)

    if not jour or not heure_debut or not heure_fin:
        return None, "Identifiant de disponibilité invalide."

    deleted = delete_disponibilite(prestataire_id, jour, heure_debut, heure_fin)
    if not deleted:
        return None, "Disponibilité introuvable."

    return deleted, None


def list_my_services(prestataire_id: int):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."
    return get_prestataire_services(prestataire_id), None


def create_my_service(prestataire_id: int, payload: dict):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."

    cleaned, error = _validate_service_payload(payload, partial=False)
    if error:
        return None, error

    if get_service_by_id_for_prestataire(prestataire_id, payload.get("id", -1)):
        return None, "Service invalide."

    created = create_service(
        prestataire_id,
        cleaned["nom"],
        cleaned["description"],
        cleaned["duree"],
        cleaned["prix"]
    )
    return created, None


def update_my_service(prestataire_id: int, service_id: int, payload: dict):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."

    existing = get_service_by_id_for_prestataire(prestataire_id, service_id)
    if not existing:
        return None, "Service introuvable."

    cleaned, error = _validate_service_payload(payload, partial=True)
    if error:
        return None, error

    if "nom" in cleaned and service_name_exists_for_other_service(prestataire_id, cleaned["nom"], service_id):
        return None, "Un autre service avec ce nom existe déjà."

    updated = update_service(prestataire_id, service_id, cleaned)
    return updated, None


def delete_my_service(prestataire_id: int, service_id: int):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."

    deleted = delete_service(prestataire_id, service_id)
    if not deleted:
        return None, "Service introuvable."

    return deleted, None


def list_my_commentaires(prestataire_id: int):
    if not get_prestataire_by_id(prestataire_id):
        return None, "Prestataire introuvable."

    rows = get_prestataire_commentaires(prestataire_id) or []
    return [serialize_comments(row) for row in rows], None

def get_commentaire_on_me(prestataire_id, reservation_id):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Réservation introuvable."

    if reservation["prestataire_id"] != prestataire_id:
        return None, "Accès refusé."

    rows = get_commentaire_by_reservation(reservation_id) or []
    if not rows:
        return None, "Commentaire introuvable."

    return serialize_comments(rows), None
