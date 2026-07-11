from backend.celery.celery_app import celery_app
from bd.config import Config
from backend.Commun.idempotence.idempotence_service import (
    marquer_cle_echouee,
    marquer_cle_en_traitement,
    marquer_cle_traitee,
    reserver_cle_idempotence,
    trouver_cle_idempotence,
)
from backend.Commun.outbox_events.outbox_dispatcher import dispatch_evenement_outbox
from backend.Commun.outbox_events.outbox_repository import (
    claim_pending_events,
    release_stale_processing_events,
    update_event_status_after_failure,
    update_event_status_to_completed,
)


def _verifier_cle_idempotence(evenement):
    # Chaque evenement doit avoir une cle. Elle sert a savoir si le travail a
    # deja ete fait, est en cours, ou doit commencer.
    cle_idempotence = evenement.get("cle_idempotence")
    if not cle_idempotence:
        return None, "L'evenement outbox n'a pas de cle_idempotence"

    cle, error = trouver_cle_idempotence(cle_idempotence)
    if error:
        return None, error

    if cle:
        return cle, None

    # Cas de securite: si un evenement existe sans ligne dans Cles_Idempotence,
    # on recree la cle avant de traiter l'evenement.
    reponse, error = reserver_cle_idempotence(
        cle_idempotence=cle_idempotence,
        type_ressource=evenement.get("type_ressource"),
        ressource_id=str(evenement.get("ressource_id")),
        empreinte_requete=cle_idempotence,
    )
    if error:
        return None, error

    return reponse.get("cle"), None


def _enregistrer_echec_evenement(evenement, message):
    evenement_maj = update_event_status_after_failure(
        event=evenement,
        error_message=message,
        max_attempts=Config.OUTBOX_MAX_ATTEMPTS,
        retry_backoff_seconds=Config.OUTBOX_RETRY_BACKOFF_SECONDS,
        max_retry_delay_seconds=Config.OUTBOX_MAX_RETRY_DELAY_SECONDS,
    )
    statut = evenement_maj.get("statut") if evenement_maj else "echoue"
    resultat = "echoue" if statut == "echoue" else "reprogramme"

    return {
        "event_id": evenement["id"],
        "statut": resultat,
        "erreur": message,
        "tentatives": evenement_maj.get("tentatives") if evenement_maj else None,
        "prochaine_tentative": evenement_maj.get("disponible_a") if evenement_maj else None,
    }


def _traiter_evenement_outbox(evenement):
    # Cette fonction traite un seul evenement: verifier l'idempotence,
    # dispatcher, puis mettre a jour les statuts.
    cle, error = _verifier_cle_idempotence(evenement)
    if error:
        return _enregistrer_echec_evenement(evenement, error)

    statut_cle = cle.get("statut")
    if statut_cle == "traitee":
        # L'action a deja ete terminee. On marque l'Outbox comme traitee pour
        # qu'elle ne reste pas bloquee inutilement.
        update_event_status_to_completed(evenement["id"])
        return {"event_id": evenement["id"], "statut": "deja_traite"}

    if statut_cle == "en_traitement":
        error = "La cle d'idempotence est deja en traitement"
        return _enregistrer_echec_evenement(evenement, error)

    try:
        # A partir d'ici, la cle protege le traitement: si le dispatcher echoue,
        # on conserve l'erreur dans l'Outbox et la cle passe a echouee.
        marquer_cle_en_traitement(cle["id"])
        resultat_dispatch = dispatch_evenement_outbox(evenement)
        marquer_cle_traitee(cle["id"], resultat_dispatch)
        update_event_status_to_completed(evenement["id"])
        return {"event_id": evenement["id"], "statut": "traite"}
    except Exception as exc:
        message = str(exc)
        marquer_cle_echouee(cle["id"])
        return _enregistrer_echec_evenement(evenement, message)


@celery_app.task(name="outbox.process_pending_events")
def process_pending_outbox_events(limit=None):
    # La tache prend un petit lot d'evenements pour eviter de bloquer le worker
    # trop longtemps et pour faciliter les reprises.
    batch_limit = limit or Config.OUTBOX_BATCH_SIZE
    evenements_repris = release_stale_processing_events(
        stale_processing_seconds=Config.OUTBOX_STALE_PROCESSING_SECONDS,
        max_attempts=Config.OUTBOX_MAX_ATTEMPTS,
        retry_backoff_seconds=Config.OUTBOX_RETRY_BACKOFF_SECONDS,
        max_retry_delay_seconds=Config.OUTBOX_MAX_RETRY_DELAY_SECONDS,
        limit=Config.OUTBOX_STALE_RESET_LIMIT,
    )
    evenements = claim_pending_events(limit=batch_limit)
    resultats = [_traiter_evenement_outbox(evenement) for evenement in evenements]

    return {
        "nombre_evenements_repris": len(evenements_repris),
        "nombre_evenements": len(evenements),
        "resultats": resultats,
    }
