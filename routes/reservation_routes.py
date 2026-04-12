from flask import Blueprint
from controllers.reservation_controller import add_commentaire

reservation_bp = Blueprint("reservation", __name__)

reservation_bp.route("/reservations/<int:id>/commentaire", methods=["POST"])(add_commentaire)