from functools import wraps

from flask_jwt_extended import get_jwt, verify_jwt_in_request

from .reponses import error_response


def role_required(*allowed_roles):
    """
    Verifie que l'utilisateur connecte possede un role autorise.
    """
    def decorator(view_function):
        @wraps(view_function)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            jwt_claims = get_jwt()
            current_role = jwt_claims.get("role")

            if current_role not in allowed_roles:
                return error_response("Acces refuse.", 403)

            return view_function(*args, **kwargs)

        return wrapper

    return decorator
