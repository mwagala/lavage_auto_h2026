import datetime
import json
from types import SimpleNamespace

from bd.database import get_connection
from backend.Commun.idempotence.idempotence_repository import (
    book_new_key,
    get_key,
    update_key_status_to_completed,
    update_key_status_to_failed,
    update_key_status_to_in_processing,
)


DECISIONS_PAR_STATUT = {
    "reservee": "action_deja_vue",
    "en_traitement": "action_en_cours",
    "traitee": "action_deja_traitee",
    "echouee": "action_deja_vue",
}


def _serialiser_json(valeur):
    if valeur is None:
        return None

    if isinstance(valeur, str):
        json.loads(valeur)
        return valeur

    return json.dumps(valeur, ensure_ascii=False)


def _calculer_expiration(duree_expiration_heures):
    if duree_expiration_heures is None:
        return None

    return datetime.datetime.now() + datetime.timedelta(hours=duree_expiration_heures)


def reserver_cle_idempotence(
    cle_idempotence,
    type_ressource,
    ressource_id=None,
    empreinte_requete=None,
    expire_a=None,
    duree_expiration_heures=None,
    connection=None
):
    if not cle_idempotence:
        return None, "La cle_idempotence est obligatoire"

    if not type_ressource:
        return None, "Le type_ressource est obligatoire"

    if expire_a is None:
        expire_a = _calculer_expiration(duree_expiration_heures)

    payload = SimpleNamespace(
        cle_idempotence=cle_idempotence,
        type_ressource=type_ressource,
        ressource_id=ressource_id,
        empreinte_requete=empreinte_requete,
        expire_a=expire_a,
    )

    reponse = book_new_key(payload, connection=connection)
    cle = reponse.get("cle")

    if reponse.get("cle_creee"):
        decision = "nouvelle_action"
    else:
        decision = DECISIONS_PAR_STATUT.get(
            cle.get("statut") if cle else None,
            "action_deja_vue"
        )

    return {
        "decision": decision,
        "cle_creee": reponse.get("cle_creee"),
        "cle": cle,
        "message": reponse.get("message"),
    }, None


def trouver_cle_idempotence(cle_idempotence, connection=None):
    if not cle_idempotence:
        return None, "La cle_idempotence est obligatoire"

    return get_key(cle_idempotence, connection=connection), None


def marquer_cle_en_traitement(cle_id, connection=None):
    if not cle_id:
        return None, "Le cle_id est obligatoire"

    update_key_status_to_in_processing(cle_id, connection=connection)
    return {"id": cle_id, "statut": "en_traitement"}, None


def marquer_cle_traitee(cle_id, reponse=None, connection=None):
    if not cle_id:
        return None, "Le cle_id est obligatoire"

    update_key_status_to_completed(
        cle_id,
        _serialiser_json(reponse),
        connection=connection
    )
    return {"id": cle_id, "statut": "traitee"}, None


def marquer_cle_echouee(cle_id, connection=None):
    if not cle_id:
        return None, "Le cle_id est obligatoire"

    update_key_status_to_failed(cle_id, connection=connection)
    return {"id": cle_id, "statut": "echouee"}, None
