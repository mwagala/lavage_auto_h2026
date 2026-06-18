from flask import Blueprint, render_template

client_front_bp = Blueprint("client_front", __name__)
prestataire_front_bp = Blueprint(
    "prestataire_front",
    __name__,
    template_folder="templates"
)



@client_front_bp.route("/client/reservations/new")
def new_reservation_page():
    return render_template("client/reservation.html")

@client_front_bp.route("/clients/dashboard")
def client_dashboard_page():
    return render_template("client/dashboard.html")

@client_front_bp.route("/client/profil")
def client_profile_page():
    return render_template("client/profil.html")

@client_front_bp.route("/client/reservations/<id>/edit")
def client_edit_reservation_page(id):
    return render_template("client/edit_reservation.html", reservation_id=id)

@client_front_bp.route("/client/reservations/<id>/commentaire/edit")
def client_edit_reservation_comment_page(id):
    return render_template("client/edit_comment.html", reservation_id=id)

@prestataire_front_bp.get("/prestataires/dashboard")
def prestataire_dashboard_page():
    return render_template("prestataires/dashboard.html")

@prestataire_front_bp.get("/prestataires/profil")
def prestataire_profile_page():
    return render_template("prestataires/profil.html")

