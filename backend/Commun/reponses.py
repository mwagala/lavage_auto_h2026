from flask import g, has_request_context, jsonify


def _get_correlation_id():
    if not has_request_context():
        return None

    return getattr(g, "correlation_id", None)


def success_response(data=None, message="Succes", status=200):
    """
    Construit une reponse JSON de succes.

    Note:
        Plusieurs routes existantes utilisent success_response(result, 201)
        (sans nommer le parametre status). Pour rester compatible avec ce style,
        si "message" est un entier et que "status" est encore 200,
        on interprete cet entier comme le code HTTP.
    """
    if isinstance(message, int) and status == 200:
        status = message
        message = "Succes"

    payload = {
        "success": True,
        "message": message,
        "data": data
    }

    correlation_id = _get_correlation_id()
    if correlation_id:
        payload["correlation_id"] = correlation_id

    return jsonify(payload), status


def error_response(message="Erreur", status=400, data=None):
    """
    Construit une reponse JSON d'erreur.
    """
    payload = {
        "success": False,
        "message": message
    }

    if data is not None:
        payload["data"] = data

    correlation_id = _get_correlation_id()
    if correlation_id:
        payload["correlation_id"] = correlation_id

    return jsonify(payload), status
