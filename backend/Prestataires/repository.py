from bd.database import execute_query


PROFILE_COLUMNS = """
    p.id,
    p.nom,
    p.prenoms,
    p.date_naissance,
    p.nas,
    p.note_moyenne,
    p.courriel,
    p.telephone,
    p.adresse_numero,
    p.adresse_rue,
    p.adresse_ville,
    p.adresse_province,
    p.adresse_code_postal,
    p.est_actif,
    p.cree_a,
    p.modifier_a
"""

SERVICE_COLUMNS = """
    s.id,
    s.nom,
    s.prestataire_id,
    s.description,
    s.duree,
    s.prix
"""

DISPO_COLUMNS = """
    d.prestataire_id,
    d.jour,
    d.statut,
    d.heure_debut,
    d.heure_fin
"""

RESERVATION_COLUMNS = """
    r.id,
    r.client_id,
    r.prestataire_id,
    r.date,
    r.heure_debut,
    r.heure_fin,
    r.statut,
    c.nom AS client_nom,
    c.prenoms AS client_prenoms,
    c.courriel AS client_courriel,
    c.telephone AS client_telephone,
    COALESCE(f.sous_total, 0) AS sous_total,
    COALESCE(f.total, 0) AS total
"""

COMMENTAIRE_COLUMNS = """
    cm.id,
    cm.client_id,
    cm.reservation_id,
    cm.texte,
    cm.note,
    r.date AS reservation_date,
    r.heure_debut AS reservation_heure_debut,
    r.heure_fin AS reservation_heure_fin,
    c.nom AS client_nom,
    c.prenoms AS client_prenoms
"""


def get_prestataire_by_id(prestataire_id: int):
    query = f"""
        SELECT p.id,
               p.nom,
               p.prenoms,
               p.date_naissance,
               p.courriel,
               p.telephone,
               p.nas,
               p.adresse_numero,
               p.adresse_rue,
               p.adresse_ville,
               p.adresse_province,
               p.adresse_code_postal,
               p.est_actif,
               p.cree_a,
               p.modifier_a,
               p.note_moyenne,
               COUNT(cm.id) AS nombre_notes
        FROM Prestataires p
        LEFT JOIN Reservations r
            ON r.prestataire_id = p.id
        LEFT JOIN Commentaires cm
            ON cm.reservation_id = r.id
        WHERE p.id = %s
        GROUP BY p.id,
                 p.nom,
                 p.prenoms,
                 p.date_naissance,
                 p.courriel,
                 p.telephone,
                 p.nas,
                 p.adresse_numero,
                 p.adresse_rue,
                 p.adresse_ville,
                 p.adresse_province,
                 p.adresse_code_postal,
                 p.est_actif,
                 p.cree_a,
                 p.modifier_a,
                 p.note_moyenne
    """
    return execute_query(query, (prestataire_id,), fetch_one=True)


def update_prestataire_profile(prestataire_id: int, fields: dict):
    if not fields:
        return get_prestataire_by_id(prestataire_id)

    query = f"""
        UPDATE Prestataires
        SET nom = %s, 
        prenoms = %s, 
        date_naissance = %s, 
        courriel = %s, 
        telephone = %s, 
        nas = %s,
        adresse_numero = %s, adresse_rue = %s, adresse_ville = %s, adresse_province = %s, adresse_code_postal = %s
        WHERE id = %s
    """
    execute_query(query, (fields.get("nom"), fields.get("prenoms"), fields.get("date_naissance"),fields.get("courriel"),
                          fields.get("telephone"), fields.get("nas"), fields.get("adresse_numero"), fields.get("adresse_rue"), fields.get("adresse_ville"),
                          fields.get("adresse_province"), fields.get("adresse_code_postal"), prestataire_id), commit=True)
    return get_prestataire_by_id(prestataire_id)


def get_prestataire_all_reservations(prestataire_id: int):
    query = f"""
        SELECT {RESERVATION_COLUMNS}
        FROM Reservations r
        INNER JOIN Clients c ON c.id = r.client_id
        LEFT JOIN Factures f ON f.reservation_id = r.id
        WHERE r.prestataire_id = %s
        ORDER BY r.date DESC, r.heure_debut DESC
    """
    return execute_query(query, (prestataire_id,), fetch_all=True)


def get_prestataire_upcoming_reservations(prestataire_id: int):
    query = f"""
        SELECT *
        FROM Reservations r
        INNER JOIN Clients c ON c.id = r.client_id
        LEFT JOIN Factures f ON f.reservation_id = r.id
        WHERE r.prestataire_id = %s
          AND r.statut IN ('Assignee', 'En cours')
          AND (
                r.date > CURRENT_DATE
                OR (r.date = CURRENT_DATE AND COALESCE(r.heure_fin, r.heure_debut) >= CURRENT_TIME)
          )
        ORDER BY r.date ASC, r.heure_debut ASC
    """
    return execute_query(query, (prestataire_id,), fetch_all=True)


def get_prestataire_past_reservations(prestataire_id: int):
    query = f"""
        SELECT *
        FROM Reservations r
        INNER JOIN Clients c ON c.id = r.client_id
        LEFT JOIN Factures f ON f.reservation_id = r.id
        WHERE r.prestataire_id = %s
          AND (
                r.statut IN ('Terminee', 'annulee')
                OR r.date < CURRENT_DATE
                OR (r.date = CURRENT_DATE AND COALESCE(r.heure_fin, r.heure_debut) < CURRENT_TIME)
          )
        ORDER BY r.date DESC, r.heure_debut DESC
    """
    return execute_query(query, (prestataire_id,), fetch_all=True)


def get_reservation_for_prestataire(prestataire_id: int, reservation_id: int):
    query = f"""
        SELECT *
        FROM Reservations r
        INNER JOIN Clients c ON c.id = r.client_id
        LEFT JOIN Factures f ON f.reservation_id = r.id
        WHERE r.prestataire_id = %s
          AND r.id = %s
    """
    rows = execute_query(query, (prestataire_id, reservation_id), fetch_one=True)
    return rows if rows else None


def update_reservation_status(prestataire_id: int, reservation_id: int, new_status: str):
    query = """
        UPDATE Reservations
        SET statut = %s
        WHERE id = %s
          AND prestataire_id = %s
    """
    execute_query(query, (new_status, reservation_id, prestataire_id), commit=True)
    return get_reservation_for_prestataire(prestataire_id, reservation_id)


def get_prestataire_disponibilites(prestataire_id: int):
    query = f"""
        SELECT *
        FROM Disponibilites d
        WHERE d.prestataire_id = %s
        ORDER BY
            CASE LOWER(d.jour)
                WHEN 'lundi' THEN 1
                WHEN 'mardi' THEN 2
                WHEN 'mercredi' THEN 3
                WHEN 'jeudi' THEN 4
                WHEN 'vendredi' THEN 5
                WHEN 'samedi' THEN 6
                WHEN 'dimanche' THEN 7
                ELSE 8
            END,
            d.heure_debut ASC
    """
    return execute_query(query, (prestataire_id,), fetch_all=True)


def get_disponibilite(prestataire_id: int, jour: str, heure_debut: str, heure_fin: str):
    query = f"""
        SELECT *
        FROM Disponibilites d
        WHERE d.prestataire_id = %s
          AND d.jour = %s
          AND d.heure_debut = %s
          AND d.heure_fin = %s
    """
    rows = execute_query(query, (prestataire_id, jour, heure_debut, heure_fin), fetch_one=True)
    return rows if rows else None


def create_disponibilite(prestataire_id: int, jour: str, statut: str, heure_debut: str, heure_fin: str):
    query = """
        INSERT INTO Disponibilites (prestataire_id, jour, statut, heure_debut, heure_fin)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(query, (prestataire_id, jour, statut, heure_debut, heure_fin), commit=True)
    return get_disponibilite(prestataire_id, jour, heure_debut, heure_fin)


def update_disponibilite(
    prestataire_id: int,
    old_jour: str,
    old_heure_debut: str,
    old_heure_fin: str,
    new_jour: str,
    new_statut: str,
    new_heure_debut: str,
    new_heure_fin: str
):
    query = """
        UPDATE Disponibilites
        SET jour = %s,
            statut = %s,
            heure_debut = %s,
            heure_fin = %s
        WHERE prestataire_id = %s
          AND jour = %s
          AND heure_debut = %s
          AND heure_fin = %s
    """
    execute_query(
        query,
        (
            new_jour,
            new_statut,
            new_heure_debut,
            new_heure_fin,
            prestataire_id,
            old_jour,
            old_heure_debut,
            old_heure_fin
        ),
        commit=True
    )
    return get_disponibilite(prestataire_id, new_jour, new_heure_debut, new_heure_fin)


def delete_disponibilite(prestataire_id: int, jour: str, heure_debut: str, heure_fin: str):
    existing = get_disponibilite(prestataire_id, jour, heure_debut, heure_fin)
    if not existing:
        return None

    query = """
        DELETE FROM Disponibilites
        WHERE prestataire_id = %s
          AND jour = %s
          AND heure_debut = %s
          AND heure_fin = %s
    """
    execute_query(query, (prestataire_id, jour, heure_debut, heure_fin), commit=True)
    return existing


def get_prestataire_services(prestataire_id: int):
    query = f"""
        SELECT {SERVICE_COLUMNS}
        FROM Services s
        WHERE s.prestataire_id = %s
        ORDER BY s.nom ASC
    """
    return execute_query(query, (prestataire_id,), fetch_all=True)

def is_service_exist(prestataire_id: int, nom_service: str):
    query = f"""
        SELECT * 
        FROM Services s
        WHERE s.prestataire_id = %s and s.nom = %s
    """
    return execute_query(query, (prestataire_id, nom_service), fetch_one=True)


def get_service_by_id_for_prestataire(prestataire_id: int, service_id: int):
    query = f"""
        SELECT *
        FROM Services s
        WHERE s.prestataire_id = %s
          AND s.id = %s
    """
    rows = execute_query(query, (prestataire_id, service_id), fetch_one=True)
    return rows if rows else None


def get_service_by_name_for_prestataire(prestataire_id: int, nom: str):
    query = f"""
        SELECT {SERVICE_COLUMNS}
        FROM Services s
        WHERE s.prestataire_id = %s
          AND s.nom = %s
        LIMIT 1
    """
    rows = execute_query(query, (prestataire_id, nom), fetch_all=True)
    return rows if rows else None


def create_service(prestataire_id: int, nom: str, description: str, duree: float, prix: float):
    query = """
        INSERT INTO Services (nom, prestataire_id, description, duree, prix)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_query(query, (nom, prestataire_id, description, duree, prix), commit=True)
    return get_service_by_name_for_prestataire(prestataire_id, nom)


def update_service(prestataire_id: int, service_id: int, fields: dict):
    if not fields:
        return get_service_by_id_for_prestataire(prestataire_id, service_id)

    set_clause = ", ".join([f"{column} = %s" for column in fields.keys()])
    params = tuple(fields.values()) + (prestataire_id, service_id)

    query = f"""
        UPDATE Services
        SET {set_clause}
        WHERE prestataire_id = %s
          AND id = %s
    """
    execute_query(query, params, commit=True)
    return get_service_by_id_for_prestataire(prestataire_id, service_id)


def delete_service(prestataire_id: int, service_id: int):
    existing = get_service_by_id_for_prestataire(prestataire_id, service_id)
    if not existing:
        return None

    query = """
        DELETE FROM Services
        WHERE prestataire_id = %s
          AND id = %s
    """
    execute_query(query, (prestataire_id, service_id), commit=True)
    return existing


def get_prestataire_commentaires(prestataire_id: int):
    query = f"""
        SELECT r.id, c.nom, c.prenoms, r.date, r.heure_debut, r.heure_fin, cm.texte, cm.note
        FROM Commentaires cm
        JOIN Reservations r ON r.id = cm.reservation_id
        JOIN Clients c ON c.id = cm.client_id
        WHERE r.prestataire_id = %s
        ORDER BY r.date DESC, r.heure_debut DESC
    """
    return execute_query(query, (prestataire_id,), fetch_all=True)


def service_name_exists_for_other_service(prestataire_id: int, nom: str, service_id: int):
    query = """
        SELECT id
        FROM Services
        WHERE prestataire_id = %s
          AND nom = %s
          AND id <> %s
        LIMIT 1
    """
    row = execute_query(query, (prestataire_id, nom, service_id), fetch_one=True)
    return bool(row)


def overlapping_disponibilite_exists(
    prestataire_id: int,
    jour: str,
    heure_debut: str,
    heure_fin: str,
    exclude_old: tuple | None = None
):
    params = [prestataire_id, jour, heure_debut, heure_fin]
    exclude_sql = ""

    if exclude_old:
        exclude_sql = """
          AND NOT (
                jour = %s
            AND heure_debut = %s
            AND heure_fin = %s
          )
        """
        params.extend([exclude_old[0], exclude_old[1], exclude_old[2]])

    query = f"""
        SELECT 1
        FROM Disponibilites
        WHERE prestataire_id = %s
          AND jour = %s
          AND %s < heure_fin
          AND %s > heure_debut
          {exclude_sql}
        LIMIT 1
    """
    rows = execute_query(query, tuple(params), fetch_one=True)
    return bool(rows)

