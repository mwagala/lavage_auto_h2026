from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

@jwt_required()
def add_commentaire(id):
    client_id = get_jwt_identity()
    data = request.get_json()

    note = data.get("note")
    texte = data.get("texte")

    if note is None or texte is None:
        return jsonify({
            "error": "Les champs note et texte sont obligatoires"
        }), 400

    return jsonify({
        "message": "Commentaire ajouté",
        "client_id": client_id,
        "reservation_id": id,
        "data": {
            "note": note,
            "texte": texte
        }
    }), 201