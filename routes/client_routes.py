from flask import Blueprint
from controllers.client_controller import (
    get_upcoming_reservations,
    get_past_reservations,
    get_client_factures,
)

client_bp = Blueprint("client", __name__)

client_bp.route("/clients/me/reservations/upcoming", methods=["GET"])(get_upcoming_reservations)
client_bp.route("/clients/me/reservations/past", methods=["GET"])(get_past_reservations)
client_bp.route("/clients/me/factures", methods=["GET"])(get_client_factures)