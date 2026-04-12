from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

@jwt_required()
def get_upcoming_reservations():
    client_id = get_jwt_identity()
    return jsonify({
        "message": "Réservations à venir du client",
        "client_id": client_id,
        "data": []
    }), 200

@jwt_required()
def get_past_reservations():
    client_id = get_jwt_identity()
    return jsonify({
        "message": "Réservations passées du client",
        "client_id": client_id,
        "data": []
    }), 200

@jwt_required()
def get_client_factures():
    client_id = get_jwt_identity()
    return jsonify({
        "message": "Factures du client",
        "client_id": client_id,
        "data": []
    }), 200