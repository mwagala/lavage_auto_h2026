from datetime import time, timedelta


def serialize_comments(row):
    return {
        "id": row.get("id"),
        "reservation_id": row.get("reservation_id"),
        "client_nom": row.get("client_nom"),
        "client_prenoms": row.get("client_prenoms"),
        "prestataire_nom": row.get("prestataire_nom"),
        "prestataire_prenoms": row.get("prestataire_prenoms"),
        "date": row.get("date").isoformat() if row.get("date") else None,
        "heure_debut": serialize_timedelta(row.get("heure_debut")),
        "heure_fin": serialize_timedelta(row.get("heure_fin")),
        "texte": row.get("texte"),
        "note": row.get("note")
    }

def serialize_timedelta(value):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    if isinstance(value, time):
        return value.strftime("%H:%M:%S")

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    total_seconds = int(value.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def serialize_reservation(row):
    return {
        "id": row.get("id"),
        "prestataire_nom": row.get("nom"),
        "prestataire_prenoms": row.get("prenoms"),
        "date": row.get("date").isoformat() if row.get("date") else None,
        "heure_debut": serialize_timedelta(row.get("heure_debut")),
        "heure_fin": serialize_timedelta(row.get("heure_fin")),
        "statut": row.get("statut")
    }

def serialize_reservation_prestataire(row):
    return {
        "id": row.get("id"),
        "client_nom": row.get("nom"),
        "client_prenoms": row.get("prenoms"),
        "date": row.get("date").isoformat() if row.get("date") else None,
        "heure_debut": serialize_timedelta(row.get("heure_debut")),
        "heure_fin": serialize_timedelta(row.get("heure_fin")),
        "statut": row.get("statut")
    }

def serialize_facture(row):
    return {
        "id": row.get("id"),
        "facture_id": row.get("id"),
        "reservation_id": row.get("reservation_id"),
        "prestataire_id": row.get("prestataire_id"),
        "date": row.get("date").isoformat() if row.get("date") else None,
        "heure_debut": serialize_timedelta(row.get("heure_debut")),
        "heure_fin": serialize_timedelta(row.get("heure_fin")),
        "sous_total": row.get("sous_total"),
        "total" : row.get("total")
    }
