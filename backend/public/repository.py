from bd.database import execute_query


def get_all_prestataires():
    query = """
        SELECT
            id,
            nom,
            prenoms,
            note_moyenne,
            courriel,
            telephone,
            adresse_ville,
            adresse_province
        FROM Prestataires
        WHERE est_actif = TRUE
        ORDER BY note_moyenne DESC
    """
    return execute_query(query, fetch_all=True) or []


def get_prestataire_by_id(prestataire_id):
    query = """
        SELECT
            id,
            nom,
            prenoms,
            note_moyenne,
            courriel,
            telephone,
            adresse_numero,
            adresse_rue,
            adresse_ville,
            adresse_province,
            adresse_code_postal
        FROM Prestataires
        WHERE id = %s AND est_actif = TRUE
    """
    rows = execute_query(query, (prestataire_id,), fetch_one=True)
    return rows if rows else None


def get_services_by_prestataire(prestataire_id):
    query = """
        SELECT
            id,
            nom,
            description,
            prix,
            duree
        FROM Services
        WHERE prestataire_id = %s
        ORDER BY nom ASC
    """
    return execute_query(query, (prestataire_id,), fetch_all=True) or []


def get_disponibilites_open_by_prestataire(prestataire_id):
    query = """
        SELECT
            jour,
            statut,
            heure_debut,
            heure_fin
        FROM Disponibilites
        WHERE prestataire_id = %s
          AND LOWER(statut) IN ('ouvert', 'ouverte', 'disponible')
        ORDER BY jour, heure_debut
    """
    return execute_query(query, (prestataire_id,), fetch_all=True) or []


def get_commentaires_by_prestataire(prestataire_id):
    query = """
        SELECT
            c.id,
            c.texte,
            c.note,
            cl.nom,
            cl.prenoms,
            r.date
        FROM Commentaires c
        INNER JOIN Reservations r ON r.id = c.reservation_id
        INNER JOIN Clients cl ON cl.id = c.client_id
        WHERE r.prestataire_id = %s
        ORDER BY r.date DESC
    """
    return execute_query(query, (prestataire_id,), fetch_all=True) or []


def get_all_services():
    query = """
        SELECT
            s.id,
            s.nom,
            s.description,
            s.prix,
            s.duree,
            p.id AS prestataire_id,
            p.nom AS prestataire_nom,
            p.prenoms AS prestataire_prenoms,
            p.note_moyenne
        FROM Services s
        INNER JOIN Prestataires p ON p.id = s.prestataire_id
        WHERE p.est_actif = TRUE
        ORDER BY p.note_moyenne DESC, s.nom ASC
    """
    return execute_query(query, fetch_all=True) or []
