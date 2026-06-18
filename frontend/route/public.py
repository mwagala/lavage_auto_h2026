from flask import Blueprint, render_template

public_bp = Blueprint("public", __name__)

@public_bp.route("/")
def home():
    return render_template("public/accueil.html")

@public_bp.route("/services-page")
def services_page():
    return render_template("public/services.html")

@public_bp.route("/equipe")
def team_page():
    return render_template("public/equipe.html")

@public_bp.route("/prestataires/<int:prestataire_id>/profil")
def prestataire_profile_page(prestataire_id):
    return render_template("public/prestataire_profil.html", prestataire_id=prestataire_id)

@public_bp.route("/connexion")
def login_page():
    return render_template("public/connexion.html")

@public_bp.route("/inscription")
def register_page():
    return render_template("public/inscription.html")
