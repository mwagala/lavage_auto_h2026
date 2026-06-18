from datetime import datetime

from ..Commun.serializer import (
    serialize_comments,
    serialize_facture,
    serialize_reservation
)
from ..Commun.validators import normalize_code_postal
from .repository import (
    get_client_by_id,
    update_client,
    get_client_reservations,
    get_client_upcoming_reservations,
    get_client_past_reservations,
    get_reservation_by_id,
    get_reservation_services,
    get_facture_by_reservation,
    get_facture_by_id,
    get_client_factures,
    mark_client_past_reservations_completed,
    update_reservation_status,
    get_commentaire_by_reservation,
    insert_commentaire,
    get_commentaire_by_id,
    get_client_comments,
    get_commentaire_by_client_reservation,
    update_commentaire_by_id,
    update_prestataire_note_moyenne_by_reservation
)


VALID_UPDATE_FIELDS = [
    "nom",
    "prenoms",
    "date_naissance",
    "courriel",
    "telephone",
    "mode_paiement",
    "adresse_numero",
    "adresse_rue",
    "adresse_ville",
    "adresse_province",
    "adresse_code_postal"
]


def _parse_iso_date(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _can_access_reservation(user_id, role, reservation):
    if role == "client":
        return int(reservation["client_id"]) == int(user_id)
    if role == "prestataire":
        return int(reservation["prestataire_id"]) == int(user_id)
    return False


def _validate_comment_payload(payload):
    texte = (payload.get("texte") or "").strip()
    note = payload.get("note")

    if not texte:
        return None, None, "Le texte du commentaire est obligatoire."

    if note is None:
        return None, None, "La note est obligatoire."

    try:
        note = int(note)
    except (TypeError, ValueError):
        return None, None, "La note doit etre un entier."

    if note < 1 or note > 5:
        return None, None, "La note doit etre comprise entre 1 et 5."

    return texte, note, None


def get_client_profile(client_id):
    client = get_client_by_id(client_id)
    if not client:
        return None, "Client introuvable."
    return client, None


def update_client_profile(client_id, data):
    if not isinstance(data, dict):
        return None, "Donnees invalides."

    data = dict(data)

    for field in VALID_UPDATE_FIELDS:
        if field not in data:
            return None, f"Champ obligatoire manquant : {field}"

    code_postal = normalize_code_postal(data.get("adresse_code_postal"))
    if not code_postal:
        return None, "Le code postal doit respecter le format A1A 1A1."
    data["adresse_code_postal"] = code_postal

    parsed_birth_date = _parse_iso_date(data.get("date_naissance"))
    if not parsed_birth_date:
        return None, "Date invalide, utilisez le format yyyy-mm-dd"

    try:
        update_client(client_id, data, parsed_birth_date.isoformat())
    except Exception:
        return None, "Impossible de modifier le profil"

    updated_client = get_client_by_id(client_id)
    return updated_client, None


def _synchroniser_reservations_passees(client_id):
    # Au chargement du tableau de bord, une reservation dont la plage horaire
    # est passee devient Terminee. Elle quitte ainsi "a venir" et apparait dans
    # l'historique avec un statut coherent.
    mark_client_past_reservations_completed(client_id)


def list_my_reservations(client_id):
    _synchroniser_reservations_passees(client_id)
    rows = get_client_reservations(client_id) or []
    return [serialize_reservation(row) for row in rows], None


def list_my_upcoming_reservations(client_id):
    client = get_client_by_id(client_id)
    if not client:
        return None, "Client introuvable."

    _synchroniser_reservations_passees(client_id)
    rows = get_client_upcoming_reservations(client_id) or []
    return [serialize_reservation(row) for row in rows], None


def list_my_past_reservations(client_id):
    client = get_client_by_id(client_id)
    if not client:
        return None, "Client introuvable."

    _synchroniser_reservations_passees(client_id)
    rows = get_client_past_reservations(client_id) or []
    return [serialize_reservation(row) for row in rows], None


def get_reservation_detail(reservation_id, user_id, role):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable."

    if not _can_access_reservation(user_id, role, reservation):
        return None, "Acces refuse."

    services = get_reservation_services(reservation_id) or []
    return {
        "reservation": reservation,
        "services": services
    }, None


def cancel_reservation(reservation_id, user_id, role):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable."

    if not _can_access_reservation(user_id, role, reservation):
        return None, "Acces refuse."

    if reservation["statut"] in {"annulee", "Terminee"}:
        return None, "Impossible d'annuler cette reservation."

    update_reservation_status(reservation_id, "annulee")
    return {"message": "Reservation annulee."}, None


def get_facture(reservation_id, user_id, role):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable."

    if not _can_access_reservation(user_id, role, reservation):
        return None, "Acces refuse."

    facture = get_facture_by_reservation(reservation_id)
    return facture, None


def get_facture_by_id_secure(facture_id, user_id, role):
    facture = get_facture_by_id(facture_id)
    if not facture:
        return None, "Facture introuvable."

    reservation = get_reservation_by_id(facture["reservation_id"])
    if not reservation:
        return None, "Reservation introuvable."

    if not _can_access_reservation(user_id, role, reservation):
        return None, "Acces refuse."

    return facture, None


def list_my_factures(client_id):
    client = get_client_by_id(client_id)
    if not client:
        return None, "Client introuvable."

    _synchroniser_reservations_passees(client_id)
    rows = get_client_factures(client_id) or []
    return [serialize_facture(row) for row in rows], None


def create_commentaire(client_id, reservation_id, data):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable."

    if int(reservation["client_id"]) != int(client_id):
        return None, "Acces refuse."

    if reservation["statut"] == "annulee":
        return None, "Impossible de commenter une reservation annulee."

    existing_comment = get_commentaire_by_reservation(reservation_id)
    if existing_comment:
        return None, "Un commentaire existe deja pour cette reservation."

    texte, note, payload_error = _validate_comment_payload(data or {})
    if payload_error:
        return None, payload_error

    commentaire_id = insert_commentaire(client_id, reservation_id, texte, note)
    commentaire = get_commentaire_by_id(commentaire_id)
    if not commentaire:
        return None, "Erreur lors de la creation du commentaire."

    update_prestataire_note_moyenne_by_reservation(reservation_id)

    return commentaire, None


def get_commentaire_me(client_id, reservation_id):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable."

    if int(reservation["client_id"]) != int(client_id):
        return None, "Acces refuse."

    commentaire = get_commentaire_by_reservation(reservation_id)
    if not commentaire:
        return None, "Commentaire introuvable."

    return serialize_comments(commentaire), None


def list_my_comments(client_id):
    client = get_client_by_id(client_id)
    if not client:
        return None, "Client introuvable."

    rows = get_client_comments(client_id) or []
    return rows, None


def update_my_commentaire(client_id, reservation_id, payload):
    if not reservation_id:
        return None, "Reservation introuvable."

    texte, note, payload_error = _validate_comment_payload(payload or {})
    if payload_error:
        return None, payload_error

    commentaire = get_commentaire_by_client_reservation(client_id, reservation_id)
    if not commentaire:
        return None, "Commentaire introuvable."

    updated = update_commentaire_by_id(commentaire["id"], texte, note)
    if not updated:
        return None, "Impossible de modifier le commentaire."

    update_prestataire_note_moyenne_by_reservation(reservation_id)

    return {
        "id": commentaire["id"],
        "client_id": client_id,
        "reservation_id": reservation_id,
        "texte": texte,
        "note": note
    }, None
