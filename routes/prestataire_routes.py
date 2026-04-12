from flask import Blueprint
from controllers.prestataire_controller import (
    get_prestataire_profile,
    update_prestataire_profile,
    get_prestataire_reservations,
    get_prestataire_upcoming_reservations,
    get_prestataire_past_reservations,
    update_reservation_statut,
    get_prestataire_disponibilites,
)

prestataire_bp = Blueprint("prestataire", __name__)

prestataire_bp.route("/prestataires/me", methods=["GET"])(get_prestataire_profile)
prestataire_bp.route("/prestataires/me", methods=["PUT"])(update_prestataire_profile)
prestataire_bp.route("/prestataires/me/reservations", methods=["GET"])(get_prestataire_reservations)
prestataire_bp.route("/prestataires/me/reservations/upcoming", methods=["GET"])(get_prestataire_upcoming_reservations)
prestataire_bp.route("/prestataires/me/reservations/past", methods=["GET"])(get_prestataire_past_reservations)
prestataire_bp.route("/prestataires/me/reservations/<int:id>/statut", methods=["PATCH"])(update_reservation_statut)
prestataire_bp.route("/prestataires/me/disponibilites", methods=["GET"])(get_prestataire_disponibilites)