import json

from bd.database import get_connection
from backend.Commun.outbox_events.outbox_repository import insert_new_event


def _serialiser_json(valeur):
    if isinstance(valeur, str):
        # Si la valeur est deja une chaine JSON, on la valide avant insertion.
        json.loads(valeur)
        return valeur

    # PostgreSQL attend du JSON texte pour la colonne jsonb.
    return json.dumps(valeur, ensure_ascii=False)


def creer_evenement_outbox(type_evenement, type_ressource, ressource_id,
                           donnees_json, cle_idempotence=None, connection=None):
    if not type_evenement:
        return None, "Le type_evenement est obligatoire"

    if not type_ressource:
        return None, "Le type_ressource est obligatoire"

    if ressource_id is None:
        return None, "Le ressource_id est obligatoire"

    if donnees_json is None:
        return None, "Les donnees_json sont obligatoires"

    if not cle_idempotence:
        return None, "La cle_idempotence est obligatoire"

    # Si une connexion est fournie, le service appelant controle commit/rollback.
    # C'est essentiel pour lier l'evenement Outbox a une transaction metier.
    connexion_locale = connection is None
    active_connection = connection or get_connection()

    try:
        donnees_serialisees = _serialiser_json(donnees_json)

        # Payload normalise: le repository recoit toujours les memes cles.
        payload = {
            "type_evenement": type_evenement,
            "type_ressource": type_ressource,
            "ressource_id": ressource_id,
            "cle_idempotence": cle_idempotence,
            "donnees_json": donnees_serialisees,
        }

        evenement_id = insert_new_event(payload, connection=active_connection)

        if connexion_locale:
            active_connection.commit()

        return {
            "id": evenement_id,
            **payload,
            "statut": "en_attente",
        }, None

    except Exception as exc:
        if connexion_locale:
            active_connection.rollback()
        return None, str(exc)

    finally:
        if connexion_locale:
            active_connection.close()


def create_a_new_event(type_evenement, type_ressource, ressource_id,
                       cle_idempotence, donnees_json, connection=None):
    return creer_evenement_outbox(
        type_evenement=type_evenement,
        type_ressource=type_ressource,
        ressource_id=ressource_id,
        cle_idempotence=cle_idempotence,
        donnees_json=donnees_json,
        connection=connection,
    )
