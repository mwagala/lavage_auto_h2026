from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ..Commun.journaux.audit_utils import construire_contexte_audit, enregistrer_audit
from ..Commun.rate_limiting import verifier_limite_auth
from ..Commun.reponses import error_response, success_response
from .service import login_user, logout_user, register_user


auth_bp = Blueprint("auth", __name__)


def _read_json_payload():
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload
    return {}


def _rate_limit_response(decision):
    response, status = error_response(decision.message, status=decision.status_code)
    if decision.retry_after_seconds:
        response.headers["Retry-After"] = str(decision.retry_after_seconds)
    return response, status


def _audit_rate_limited(action, audit_context):
    enregistrer_audit(
        action=f"auth.{action}.rate_limited",
        type_ressource="auth",
        resultat="echec",
        audit_context=audit_context,
        details={"raison": "rate_limited"},
    )


@auth_bp.post("/register")
def register_route():
    payload = _read_json_payload()
    audit_context = construire_contexte_audit()
    rate_limit = verifier_limite_auth("register", payload, request)
    if not rate_limit.allowed:
        _audit_rate_limited("register", audit_context)
        return _rate_limit_response(rate_limit)

    result, error = register_user(payload, audit_context=audit_context)

    if error:
        return error_response(error, 400)

    return success_response(result, status=201)


@auth_bp.post("/login")
def login_route():
    payload = _read_json_payload()
    audit_context = construire_contexte_audit()
    rate_limit = verifier_limite_auth("login", payload, request)
    if not rate_limit.allowed:
        _audit_rate_limited("login", audit_context)
        return _rate_limit_response(rate_limit)

    result, error = login_user(payload, audit_context=audit_context)

    if error:
        # On ne dit pas si email ou mot de passe est faux pour limiter
        # la fuite d'information.
        return error_response(error, 401)

    return success_response(result, status=200)


@auth_bp.post("/logout")
@jwt_required()
def logout_route():
    result, error = logout_user()

    if error:
        return error_response(error, 400)

    return success_response(result, status=200)
