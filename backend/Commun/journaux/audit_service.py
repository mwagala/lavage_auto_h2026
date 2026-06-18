import json
from types import SimpleNamespace

from bd.database import get_connection
from backend.Commun.journaux.audit_repository import insert_new_audit_log


ROLES_ACTEUR_VALIDES = {"client", "prestataire", "admin", "systeme"}
RESULTATS_VALIDES = {"succes", "echec"}


def _serialiser_json(valeur):
    if valeur is None:
        return None

    if isinstance(valeur, str):
        json.loads(valeur)
        return valeur

    return json.dumps(valeur, ensure_ascii=False)


def enregistrer_journal_audit(
    action,
    type_ressource,
    ressource_id=None,
    resultat="succes",
    acteur_id=None,
    role_acteur="systeme",
    adresse_ip=None,
    correlation_id=None,
    details=None,
    connection=None
):
    if not action:
        return None, "L'action est obligatoire"

    if not type_ressource:
        return None, "Le type_ressource est obligatoire"

    if role_acteur not in ROLES_ACTEUR_VALIDES:
        return None, "Le role_acteur est invalide"

    if resultat not in RESULTATS_VALIDES:
        return None, "Le resultat est invalide"

    connexion_locale = connection is None
    active_connection = connection or get_connection()

    try:
        payload = SimpleNamespace(
            acteur_id=acteur_id,
            role_acteur=role_acteur,
            action=action,
            type_ressource=type_ressource,
            ressource_id=ressource_id,
            resultat=resultat,
            adresse_ip=adresse_ip,
            correlation_id=correlation_id,
            details_json=_serialiser_json(details),
        )

        journal_id = insert_new_audit_log(payload, connection=active_connection)

        if connexion_locale:
            active_connection.commit()

        return {
            "id": journal_id,
            "acteur_id": acteur_id,
            "role_acteur": role_acteur,
            "action": action,
            "type_ressource": type_ressource,
            "ressource_id": ressource_id,
            "resultat": resultat,
            "adresse_ip": adresse_ip,
            "correlation_id": correlation_id,
            "details_json": payload.details_json,
        }, None

    except Exception as exc:
        if connexion_locale:
            active_connection.rollback()
        return None, str(exc)

    finally:
        if connexion_locale:
            active_connection.close()
