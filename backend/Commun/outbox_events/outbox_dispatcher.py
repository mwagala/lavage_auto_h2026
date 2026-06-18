import logging


LOGGER = logging.getLogger(__name__)


def dispatch_evenement_outbox(evenement):
    type_evenement = evenement.get("type_evenement")

    if type_evenement == "reservation.created":
        # Premiere version volontairement simple: on confirme seulement que
        # l'evenement est recu. Plus tard, ce bloc pourra appeler les
        # notifications, factures, rappels, etc.
        LOGGER.info(
            "Event reservation.created received",
            extra={
                "event_id": evenement.get("id"),
                "type_ressource": evenement.get("type_ressource"),
                "ressource_id": evenement.get("ressource_id"),
            },
        )
        return {
            "type_evenement": type_evenement,
            "traite": True,
        }

    # Fallback temporaire: un evenement inconnu ne casse pas le consumer.
    # Quand chaque type d'evenement sera defini, on pourra rendre ce cas plus strict.
    LOGGER.info(
        "Event received without specific dispatcher",
        extra={
            "event_id": evenement.get("id"),
            "type_evenement": type_evenement,
        },
    )
    return {
        "type_evenement": type_evenement,
        "traite": True,
    }
