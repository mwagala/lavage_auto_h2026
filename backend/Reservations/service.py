import logging
from datetime import datetime

from bd.database import get_connection
from backend.Commun.idempotence.idempotence_service import reserver_cle_idempotence
from backend.Commun.outbox_events.outbox_service import creer_evenement_outbox
from .repository import (
    cancel_reservation,
    count_active_client_reservations_same_day,
    create_reservation,
    delete_reservation_services,
    get_available_prestataires_for_service,
    get_facture_by_reservation_id,
    get_facture_detail_by_id,
    get_reservation_by_id,
    get_reservation_detail,
    get_services_by_ids,
    has_prestataire_conflict,
    insert_reservation_service,
    update_reservation_header,
    update_reservation_status
)


logger = logging.getLogger(__name__)

DAY_NAME_TO_FRENCH = {
    "monday": "Lundi",
    "tuesday": "Mardi",
    "wednesday": "Mercredi",
    "thursday": "Jeudi",
    "friday": "Vendredi",
    "saturday": "Samedi",
    "sunday": "Dimanche"
}

ALLOWED_PRESTATAIRE_STATUSES = {"Assignee", "En cours", "Terminee", "annulee"}
EDITABLE_STATUSES = {"Assignee"}
FINAL_STATUSES = {"Terminee", "annulee"}


def _parse_date(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_time(value):
    if not isinstance(value, str):
        return None

    accepted_formats = ("%H:%M", "%H:%M:%S")
    for one_format in accepted_formats:
        try:
            return datetime.strptime(value, one_format).time()
        except ValueError:
            continue
    return None


def _to_seconds(time_value):
    return (time_value.hour * 3600) + (time_value.minute * 60) + time_value.second


def _seconds_to_hms(total_seconds):
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _is_actor_allowed_on_reservation(actor_id, actor_role, reservation):
    if actor_role == "client":
        return int(reservation["client_id"]) == int(actor_id)
    if actor_role == "prestataire":
        return int(reservation["prestataire_id"]) == int(actor_id)
    return False


def _is_future_reservation(reservation):
    reservation_date = reservation["date"]
    if isinstance(reservation_date, str):
        reservation_date = _parse_date(reservation_date)

    reservation_start_time = _parse_time(reservation["heure_debut"])
    if not reservation_date or not reservation_start_time:
        return False

    reservation_start = datetime.combine(reservation_date, reservation_start_time)
    return reservation_start > datetime.now()


def _build_reservation_response(reservation_id):
    reservation_detail = get_reservation_detail(reservation_id)
    if not reservation_detail:
        return None
    return reservation_detail


def _normalize_services_payload(services_payload):
    if not isinstance(services_payload, list) or not services_payload:
        return None, "La liste des services est requise"

    normalized_items = []
    seen_service_ids = set()

    for item in services_payload:
        if not isinstance(item, dict):
            return None, "Chaque service doit etre un objet"

        service_id = item.get("service_id")
        quantite = item.get("quantite", 1)

        if not isinstance(service_id, int) or service_id <= 0:
            return None, "Chaque service doit contenir un service_id valide"

        if not isinstance(quantite, int) or quantite <= 0:
            return None, "La quantite doit etre un entier positif"

        if service_id in seen_service_ids:
            return None, "Un service ne peut apparaitre qu'une seule fois dans la reservation"

        seen_service_ids.add(service_id)
        normalized_items.append({
            "service_id": service_id,
            "quantite": quantite
        })

    return normalized_items, None


def _build_service_lines(prestataire_id, services_payload):
    normalized_items, payload_error = _normalize_services_payload(services_payload)
    if payload_error:
        return None, None, payload_error

    service_ids = [item["service_id"] for item in normalized_items]
    services_from_db = get_services_by_ids(service_ids)

    if len(services_from_db) != len(service_ids):
        return None, None, "Un ou plusieurs services sont introuvables"

    services_by_id = {}
    for one_service in services_from_db:
        services_by_id[one_service["id"]] = one_service

    service_lines = []
    total_duration_seconds = 0

    for item in normalized_items:
        service_id = item["service_id"]
        quantite = item["quantite"]
        db_service = services_by_id.get(service_id)

        if not db_service:
            return None, None, "Un ou plusieurs services sont introuvables"

        if int(db_service["prestataire_id"]) != int(prestataire_id):
            return None, None, "Tous les services doivent appartenir au meme prestataire"

        unit_price = float(db_service["prix"])
        unit_duration = float(db_service["duree"])
        total_duration_seconds += round(unit_duration * 3600 * quantite)

        service_lines.append({
            "service_id": int(db_service["id"]),
            "prix_applique": unit_price,
            "duree_prevue": unit_duration,
            "quantite": quantite
        })

    if total_duration_seconds <= 0:
        return None, None, "La duree totale de la reservation doit etre positive"

    return service_lines, total_duration_seconds, None


def _validate_common_update_access(actor_id, actor_role, reservation):
    if not _is_actor_allowed_on_reservation(actor_id, actor_role, reservation):
        return "Acces refuse"

    if reservation["statut"] not in EDITABLE_STATUSES:
        return "Cette reservation ne peut plus etre modifiee"

    if not _is_future_reservation(reservation):
        return "Une reservation deja commencee ne peut plus etre modifiee"

    return None


def _load_services_payload_from_existing_reservation(reservation_id):
    detail = get_reservation_detail(reservation_id)
    if not detail:
        return []

    current_services = detail.get("services", [])
    payload = []
    for one_service in current_services:
        payload.append({
            "service_id": int(one_service["service_id"]),
            "quantite": int(one_service["quantite"])
        })
    return payload


def _save_reservation_and_services(
    reservation_id,
    prestataire_id,
    reservation_date,
    heure_debut,
    service_lines
):
    connection = get_connection()

    try:
        update_reservation_header(
            reservation_id=reservation_id,
            prestataire_id=prestataire_id,
            date_value=reservation_date,
            heure_debut=heure_debut,
            connection=connection
        )

        delete_reservation_services(reservation_id, connection=connection)

        for line in service_lines:
            insert_reservation_service(
                reservation_id=reservation_id,
                service_id=line["service_id"],
                prix_applique=line["prix_applique"],
                duree_prevue=line["duree_prevue"],
                quantite=line["quantite"],
                connection=connection
            )

        connection.commit()
        return None
    except Exception:
        connection.rollback()
        return "Impossible de modifier la reservation"
    finally:
        connection.close()


def _declencher_consumer_outbox_apres_commit(limit=10):
    try:
        # On importe la tache ici pour eviter de charger Celery au demarrage du
        # module de reservation. Cette fonction ne doit etre appelee qu'apres
        # le commit: le worker doit lire un evenement deja visible en base.
        from backend.celery.tasks.outbox import process_pending_outbox_events

        # delay() publie la tache dans Redis. Le worker Celery la prendra
        # ensuite et traitera les evenements en_attente dans l'Outbox.
        process_pending_outbox_events.delay(limit)
    except Exception:
        # La reservation est deja committee. On ne rollback pas ici:
        # Celery Beat reste le filet de securite et retraitera l'Outbox plus tard.
        logger.exception("Impossible d'envoyer immediatement la tache Outbox.")


def create_reservation_client(client_id, payload):
    if not isinstance(payload, dict):
        return None, "Donnees invalides"

    prestataire_id = payload.get("prestataire_id")
    date_value = payload.get("date")
    heure_debut_value = payload.get("heure_debut")
    services_payload = payload.get("services")

    if not isinstance(prestataire_id, int) or prestataire_id <= 0:
        return None, "prestataire_id est requis"

    reservation_date = _parse_date(date_value)
    if not reservation_date:
        return None, "La date est invalide"

    heure_debut = _parse_time(heure_debut_value)
    if not heure_debut:
        return None, "heure_debut est invalide"

    reservation_start = datetime.combine(reservation_date, heure_debut)
    if reservation_start <= datetime.now():
        return None, "La reservation doit etre planifiee dans le futur"

    service_lines, total_duration_seconds, service_error = _build_service_lines(
        prestataire_id,
        services_payload
    )
    if service_error:
        return None, service_error

    current_count = count_active_client_reservations_same_day(client_id, reservation_date)
    if current_count >= 2:
        return None, "Limite atteinte : un client ne peut pas avoir plus de 2 reservations le meme jour"

    heure_fin = _seconds_to_hms(_to_seconds(heure_debut) + total_duration_seconds)
    has_conflict = has_prestataire_conflict(
        prestataire_id,
        reservation_date,
        heure_debut.strftime("%H:%M:%S"),
        heure_fin
    )
    if has_conflict:
        return None, "Prestataire deja occupe sur cette plage horaire"

    connection = get_connection()
    reservation_id = None
    heure_debut_serialisee = heure_debut.strftime("%H:%M:%S")

    try:
        # Cette transaction contient la reservation, ses services, la cle
        # d'idempotence et l'evenement Outbox. Tout reussit ensemble ou tout
        # est annule par rollback.
        reservation_id = create_reservation(
            client_id=client_id,
            prestataire_id=prestataire_id,
            date_value=reservation_date,
            heure_debut=heure_debut_serialisee,
            connection=connection
        )

        if not reservation_id:
            connection.rollback()
            return None, "Impossible de creer la reservation"

        for line in service_lines:
            insert_reservation_service(
                reservation_id=reservation_id,
                service_id=line["service_id"],
                prix_applique=line["prix_applique"],
                duree_prevue=line["duree_prevue"],
                quantite=line["quantite"],
                connection=connection
            )

        # La cle rend l'evenement unique. Si ce flux est rejoue, on evite de
        # traiter deux fois la meme reservation.created.
        cle_idempotence = f"reservation.created:{reservation_id}"
        reservation_key, key_error = reserver_cle_idempotence(
            cle_idempotence=cle_idempotence,
            type_ressource="reservation",
            ressource_id=str(reservation_id),
            empreinte_requete=cle_idempotence,
            connection=connection
        )
        if key_error or not reservation_key.get("cle_creee"):
            # Si la cle ne peut pas etre creee, on annule aussi la reservation.
            connection.rollback()
            return None, key_error or "Impossible de reserver la cle d'idempotence de l'evenement"

        # L'evenement est cree dans la meme transaction. Le consumer Celery le
        # lira plus tard pour declencher les traitements asynchrones.
        evenement, event_error = creer_evenement_outbox(
            type_evenement="reservation.created",
            type_ressource="reservation",
            ressource_id=str(reservation_id),
            cle_idempotence=cle_idempotence,
            donnees_json={
                "reservation_id": reservation_id,
                "client_id": client_id,
                "prestataire_id": prestataire_id,
                "date": reservation_date.isoformat(),
                "heure_debut": heure_debut_serialisee,
                "heure_fin": heure_fin,
                "services": service_lines,
            },
            connection=connection
        )
        if event_error or not evenement:
            # Sans evenement Outbox fiable, on annule la reservation pour ne
            # pas perdre le signal metier.
            connection.rollback()
            return None, event_error or "Impossible de creer l'evenement outbox de reservation"

        connection.commit()
    except Exception as exc:
        connection.rollback()
        return None, str(exc)
    finally:
        connection.close()

    _declencher_consumer_outbox_apres_commit()

    result = _build_reservation_response(reservation_id)
    if not result:
        return None, "Impossible de recuperer la reservation"

    return result, None


def get_reservation_detail_for_actor(actor_id, actor_role, reservation_id):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable"

    if not _is_actor_allowed_on_reservation(actor_id, actor_role, reservation):
        return None, "Acces refuse"

    detail = get_reservation_detail(reservation_id)
    if not detail:
        return None, "Reservation introuvable"

    return detail, None


def update_reservation_any(actor_id, actor_role, reservation_id, payload):
    if not isinstance(payload, dict):
        return None, "Donnees invalides"

    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable"

    access_error = _validate_common_update_access(actor_id, actor_role, reservation)
    if access_error:
        return None, access_error

    current_date = reservation["date"]
    if isinstance(current_date, str):
        current_date = _parse_date(current_date)

    current_start_time = _parse_time(reservation["heure_debut"])
    current_prestataire_id = int(reservation["prestataire_id"])

    new_prestataire_id = payload.get("prestataire_id", current_prestataire_id)
    new_date = current_date
    new_start_time = current_start_time

    if payload.get("date") is not None:
        new_date = _parse_date(payload.get("date"))

    if payload.get("heure_debut") is not None:
        new_start_time = _parse_time(payload.get("heure_debut"))

    if actor_role == "prestataire" and payload.get("prestataire_id") not in (None, current_prestataire_id):
        return None, "Le prestataire ne peut pas reassigner la reservation"

    if not isinstance(new_prestataire_id, int) or new_prestataire_id <= 0:
        return None, "prestataire_id est invalide"

    if not new_date:
        return None, "La date est invalide"

    if not new_start_time:
        return None, "heure_debut est invalide"

    if datetime.combine(new_date, new_start_time) <= datetime.now():
        return None, "La reservation doit rester planifiee dans le futur"

    services_payload = payload.get("services")
    if services_payload is None:
        services_payload = _load_services_payload_from_existing_reservation(reservation_id)

    service_lines, total_duration_seconds, service_error = _build_service_lines(
        new_prestataire_id,
        services_payload
    )
    if service_error:
        return None, service_error

    client_id = int(reservation["client_id"])
    active_count = count_active_client_reservations_same_day(client_id, new_date, reservation_id)
    if active_count >= 2:
        return None, "Limite atteinte : un client ne peut pas avoir plus de 2 reservations le meme jour"

    new_end_time = _seconds_to_hms(_to_seconds(new_start_time) + total_duration_seconds)
    has_conflict = has_prestataire_conflict(
        new_prestataire_id,
        new_date,
        new_start_time.strftime("%H:%M:%S"),
        new_end_time,
        reservation_id
    )
    if has_conflict:
        return None, "Prestataire deja occupe sur cette plage horaire"

    save_error = _save_reservation_and_services(
        reservation_id=reservation_id,
        prestataire_id=new_prestataire_id,
        reservation_date=new_date,
        heure_debut=new_start_time.strftime("%H:%M:%S"),
        service_lines=service_lines
    )
    if save_error:
        return None, save_error

    result = _build_reservation_response(reservation_id)
    if not result:
        return None, "Impossible de recuperer la reservation"

    return result, None


def update_reservation_status_prestataire(prestataire_id, reservation_id, payload):
    if not isinstance(payload, dict):
        return None, "Donnees invalides"

    new_status = payload.get("statut")
    if new_status not in ALLOWED_PRESTATAIRE_STATUSES:
        return None, "Statut invalide"

    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable"

    if int(reservation["prestataire_id"]) != int(prestataire_id):
        return None, "Acces refuse"

    current_status = reservation["statut"]
    if current_status in FINAL_STATUSES:
        return None, "Cette reservation ne peut plus changer de statut"

    if current_status == "Assignee" and new_status not in {"En cours", "annulee", "Assignee"}:
        return None, "Transition de statut invalide"

    if current_status == "En cours" and new_status not in {"Terminee", "annulee", "En cours"}:
        return None, "Transition de statut invalide"

    update_reservation_status(reservation_id, new_status)

    result = _build_reservation_response(reservation_id)
    if not result:
        return None, "Impossible de recuperer la reservation"

    return result, None


def cancel_reservation_any(actor_id, actor_role, reservation_id):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable"

    if not _is_actor_allowed_on_reservation(actor_id, actor_role, reservation):
        return None, "Acces refuse"

    if reservation["statut"] in FINAL_STATUSES:
        return None, "Cette reservation ne peut plus etre annulee"

    if actor_role == "client":
        if reservation["statut"] != "Assignee":
            return None, "Le client ne peut annuler qu'une reservation assignee"
        if not _is_future_reservation(reservation):
            return None, "Une reservation deja commencee ne peut plus etre annulee"

    if actor_role == "prestataire":
        if reservation["statut"] not in {"Assignee", "En cours"}:
            return None, "Cette reservation ne peut plus etre annulee"

    cancel_reservation(reservation_id)

    result = _build_reservation_response(reservation_id)
    if not result:
        return None, "Impossible de recuperer la reservation"

    return result, None


def get_reservation_facture_for_actor(actor_id, actor_role, reservation_id):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None, "Reservation introuvable"

    if not _is_actor_allowed_on_reservation(actor_id, actor_role, reservation):
        return None, "Acces refuse"

    facture = get_facture_by_reservation_id(reservation_id)
    if not facture:
        return None, "Facture introuvable"

    detail = get_facture_detail_by_id(int(facture["id"]))
    if not detail:
        return None, "Facture introuvable"

    return detail, None


def list_available_prestataires_for_service(service_id, date_value, heure_debut):
    if not service_id:
        return None, "Le service est obligatoire."

    if not date_value:
        return None, "La date est obligatoire."

    if not heure_debut:
        return None, "L'heure de debut est obligatoire."

    reservation_date = _parse_date(date_value)
    if not reservation_date:
        return None, "Format de date invalide."

    day_name_english = reservation_date.strftime("%A").lower()
    day_name_french = DAY_NAME_TO_FRENCH.get(day_name_english)
    if not day_name_french:
        return None, "Impossible de determiner le jour correspondant."

    result = get_available_prestataires_for_service(
        service_id=service_id,
        jour=day_name_french,
        date_value=date_value,
        heure_debut=heure_debut
    )
    return result, None
