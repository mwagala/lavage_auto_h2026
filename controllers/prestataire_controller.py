from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

@jwt_required()
def get_prestataire_profile():
    prestataire_id = get_jwt_identity()
    return jsonify({
        "message": "Profil prestataire",
        "prestataire_id": prestataire_id,
        "data": {}
    }), 200

@jwt_required()
def update_prestataire_profile():
    prestataire_id = get_jwt_identity()
    data = request.get_json()
    return jsonify({
        "message": "Profil prestataire mis à jour",
        "prestataire_id": prestataire_id,
        "data": data
    }), 200

@jwt_required()
def get_prestataire_reservations():
    prestataire_id = get_jwt_identity()
    return jsonify({
        "message": "Toutes les réservations du prestataire",
        "prestataire_id": prestataire_id,
        "data": []
    }), 200

@jwt_required()
def get_prestataire_upcoming_reservations():
    prestataire_id = get_jwt_identity()
    return jsonify({
        "message": "Réservations à venir du prestataire",
        "prestataire_id": prestataire_id,
        "data": []
    }), 200

@jwt_required()
def get_prestataire_past_reservations():
    prestataire_id = get_jwt_identity()
    return jsonify({
        "message": "Réservations passées du prestataire",
        "prestataire_id": prestataire_id,
        "data": []
    }), 200

@jwt_required()
def update_reservation_statut(id):
    prestataire_id = get_jwt_identity()
    data = request.get_json()
    return jsonify({
        "message": "Statut mis à jour",
        "prestataire_id": prestataire_id,
        "reservation_id": id,
        "data": data
    }), 200

@jwt_required()
def get_prestataire_disponibilites():
    prestataire_id = get_jwt_identity()
    return jsonify({
        "message": "Disponibilités du prestataire",
        "prestataire_id": prestataire_id,
        "data": []
    }), 200