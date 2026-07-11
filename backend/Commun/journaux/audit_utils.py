import logging

from flask import g, has_request_context, request

from .audit_service import enregistrer_journal_audit


LOGGER = logging.getLogger(__name__)
ROLES_AUDIT_VALIDES = {"client", "prestataire", "admin", "systeme"}


def construire_contexte_audit(acteur_id=None, role_acteur=None):
    role = role_acteur if role_acteur in ROLES_AUDIT_VALIDES else "systeme"
    contexte = {
        "acteur_id": acteur_id,
        "role_acteur": role,
        "adresse_ip": None,
        "correlation_id": None,
    }

    if not has_request_context():
        return contexte

    forwarded_for = request.headers.get("X-Forwarded-For", "")
    adresse_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.remote_addr

    contexte["adresse_ip"] = adresse_ip
    contexte["correlation_id"] = getattr(g, "correlation_id", None)
    return contexte


def enregistrer_audit(
    action,
    type_ressource,
    ressource_id=None,
    resultat="succes",
    audit_context=None,
    details=None,
    connection=None,
    strict=False,
):
    contexte = audit_context or {}
    role_acteur = contexte.get("role_acteur")
    if role_acteur not in ROLES_AUDIT_VALIDES:
        role_acteur = "systeme"

    journal, erreur = enregistrer_journal_audit(
        action=action,
        type_ressource=type_ressource,
        ressource_id=ressource_id,
        resultat=resultat,
        acteur_id=contexte.get("acteur_id"),
        role_acteur=role_acteur,
        adresse_ip=contexte.get("adresse_ip"),
        correlation_id=contexte.get("correlation_id"),
        details=details,
        connection=connection,
    )

    if erreur:
        LOGGER.warning(
            "audit_write_failed",
            extra={
                "action": action,
                "type_ressource": type_ressource,
                "ressource_id": ressource_id,
                "audit_error": erreur,
            },
        )
        if strict:
            return None, erreur

    return journal, erreur

