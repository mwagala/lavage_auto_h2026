from bd.database import execute_query


def get_reservation_by_id(reservation_id):
    query = """
        SELECT r.id,
               r.client_id,
               r.prestataire_id,
               r.date,
               to_char(r.heure_debut, 'HH24:MI:SS') AS heure_debut,
               to_char(r.heure_fin, 'HH24:MI:SS')   AS heure_fin,
               r.statut,
               c.nom                                     AS client_nom,
               c.prenoms                                 AS client_prenoms,
               c.courriel                                AS client_courriel,
               c.telephone                               AS client_telephone,
               p.nom                                     AS prestataire_nom,
               p.prenoms                                 AS prestataire_prenoms,
               p.courriel                                AS prestataire_courriel,
               p.telephone                               AS prestataire_telephone
        FROM Reservations r
        INNER JOIN Clients c ON c.id = r.client_id
        INNER JOIN Prestataires p ON p.id = r.prestataire_id
        WHERE r.id = %s
    """
    return execute_query(query, (reservation_id,), fetch_one=True)


def get_reservation_services(reservation_id):
    query = """
        SELECT rs.reservation_id,
               rs.service_id,
               s.nom,
               s.description,
               rs.prix_applique,
               rs.duree_prevue,
               rs.quantite
        FROM Reservation_Services rs
        INNER JOIN Services s ON s.id = rs.service_id
        WHERE rs.reservation_id = %s
        ORDER BY s.nom ASC
    """
    return execute_query(query, (reservation_id,), fetch_all=True) or []


def get_reservation_detail(reservation_id):
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        return None

    reservation["services"] = get_reservation_services(reservation_id)
    reservation["facture"] = get_facture_by_reservation_id(reservation_id)
    return reservation


def create_reservation(client_id, prestataire_id, date_value, heure_debut, connection=None):
    query = """
        INSERT INTO Reservations (
            client_id,
            prestataire_id,
            date,
            heure_debut
        )
        VALUES (%s, %s, %s, %s)
    """
    params = (client_id, prestataire_id, date_value, heure_debut)
    return execute_query(
        query,
        params,
        connection=connection,
        commit=False,
        return_lastrowid=True
    )


def update_reservation_header(
    reservation_id,
    prestataire_id,
    date_value,
    heure_debut,
    connection=None
):
    query = """
        UPDATE Reservations
        SET prestataire_id = %s,
            date = %s,
            heure_debut = %s
        WHERE id = %s
    """
    params = (prestataire_id, date_value, heure_debut, reservation_id)
    return execute_query(
        query,
        params,
        connection=connection,
        commit=connection is None
    )


def insert_reservation_service(
    reservation_id,
    service_id,
    prix_applique,
    duree_prevue,
    quantite,
    connection=None
):
    query = """
        INSERT INTO Reservation_Services (
            reservation_id,
            service_id,
            prix_applique,
            duree_prevue,
            quantite
        )
        VALUES (%s, %s, %s, %s, %s)
    """
    params = (reservation_id, service_id, prix_applique, duree_prevue, quantite)
    execute_query(
        query,
        params,
        connection=connection,
        commit=False
    )


def delete_reservation_services(reservation_id, connection=None):
    query = "DELETE FROM Reservation_Services WHERE reservation_id = %s"
    return execute_query(
        query,
        (reservation_id,),
        connection=connection,
        commit=False
    )


def cancel_reservation(reservation_id, connection=None):
    query = """
        UPDATE Reservations
        SET statut = 'annulee'
        WHERE id = %s
    """
    return execute_query(
        query,
        (reservation_id,),
        connection=connection,
        commit=connection is None
    )


def update_reservation_status(reservation_id, statut, connection=None):
    query = """
        UPDATE Reservations
        SET statut = %s
        WHERE id = %s
    """
    params = (statut, reservation_id)
    return execute_query(
        query,
        params,
        connection=connection,
        commit=connection is None
    )


def get_services_by_ids(service_ids):
    if not service_ids:
        return []

    placeholders = ", ".join(["%s"] * len(service_ids))
    query = f"""
        SELECT id,
               prestataire_id,
               nom,
               description,
               prix,
               duree
        FROM Services
        WHERE id IN ({placeholders})
    """
    return execute_query(query, tuple(service_ids), fetch_all=True) or []


def count_active_client_reservations_same_day(client_id, date_value, exclude_reservation_id=None):
    query = """
        SELECT COUNT(*) AS total
        FROM Reservations
        WHERE client_id = %s
          AND date = %s
          AND statut <> 'annulee'
    """
    params = [client_id, date_value]

    if exclude_reservation_id is not None:
        query += " AND id <> %s"
        params.append(exclude_reservation_id)

    row = execute_query(query, tuple(params), fetch_one=True)
    if not row:
        return 0
    return int(row["total"])


def has_prestataire_conflict(
    prestataire_id,
    date_value,
    heure_debut,
    heure_fin,
    exclude_reservation_id=None
):
    query = """
        SELECT COUNT(*) AS total
        FROM Reservations
        WHERE prestataire_id = %s
          AND date = %s
          AND statut IN ('Assignee', 'En cours')
          AND heure_fin IS NOT NULL
          AND %s::time < heure_fin
          AND %s::time > heure_debut
    """
    params = [prestataire_id, date_value, heure_debut, heure_fin]

    if exclude_reservation_id is not None:
        query += " AND id <> %s"
        params.append(exclude_reservation_id)

    row = execute_query(query, tuple(params), fetch_one=True)
    if not row:
        return False
    return int(row["total"]) > 0


def get_facture_by_reservation_id(reservation_id):
    query = """
        SELECT f.id,
               f.reservation_id,
               f.sous_total,
               f.total
        FROM Factures f
        WHERE f.reservation_id = %s
    """
    return execute_query(query, (reservation_id,), fetch_one=True)


def get_facture_detail_by_id(facture_id):
    query = """
        SELECT f.id,
               f.reservation_id,
               f.sous_total,
               f.total,
               r.client_id,
               r.prestataire_id,
               r.date,
               r.heure_debut,
               r.heure_fin,
               r.statut
        FROM Factures f
        INNER JOIN Reservations r ON r.id = f.reservation_id
        WHERE f.id = %s
    """
    facture = execute_query(query, (facture_id,), fetch_one=True)
    if not facture:
        return None

    facture["services"] = get_reservation_services(facture["reservation_id"])
    return facture


def get_available_prestataires_for_service(service_id, jour, date_value, heure_debut):
    query = """
        SELECT p.id,
               p.nom,
               p.prenoms,
               p.note_moyenne,
               s.id AS service_id,
               s.nom AS service_nom,
               s.prix,
               s.duree
        FROM Services s
        INNER JOIN Prestataires p ON p.id = s.prestataire_id
        INNER JOIN Disponibilites d ON d.prestataire_id = p.id
        WHERE s.id = %s
          AND LOWER(TRIM(d.jour)) = LOWER(TRIM(%s))
          AND LOWER(TRIM(d.statut)) IN ('disponible', 'actif', 'ouverte')
          AND d.heure_debut <= %s
          AND d.heure_fin >= (%s::time + (s.duree::double precision * interval '1 hour'))
          AND NOT EXISTS (
              SELECT 1
              FROM Reservations r
              WHERE r.prestataire_id = p.id
                AND r.date = %s
                AND r.statut IN ('Assignee', 'En cours')
                AND r.heure_fin IS NOT NULL
                AND %s::time < r.heure_fin
                AND (%s::time + (s.duree::double precision * interval '1 hour')) > r.heure_debut
          )
        ORDER BY p.note_moyenne DESC, p.nom ASC, p.prenoms ASC
    """
    params = (
        service_id,
        jour,
        heure_debut,
        heure_debut,
        date_value,
        heure_debut,
        heure_debut
    )
    return execute_query(query, params, fetch_all=True) or []
