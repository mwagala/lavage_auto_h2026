from bd.database import execute_query


def get_client_by_id(client_id):
    query = """
            SELECT id,
                   nom,
                   prenoms,
                   date_naissance,
                   courriel,
                   telephone,
                   mode_paiement,
                   adresse_numero,
                   adresse_rue,
                   adresse_ville,
                   adresse_province,
                   adresse_code_postal,
                   est_actif,
                   cree_a,
                   modifier_a
            FROM Clients
            WHERE id = %s \
            """
    return execute_query(query, (client_id,), fetch_one=True)


def update_client(client_id, data, date_naissance):
    query = """
            UPDATE Clients
            SET nom                 = %s,
                prenoms             = %s,
                date_naissance      = %s,
                courriel            = %s,
                telephone           = %s,
                mode_paiement       = %s,
                adresse_numero      = %s,
                adresse_rue         = %s,
                adresse_ville       = %s,
                adresse_province    = %s,
                adresse_code_postal = %s
            WHERE id = %s """
    return execute_query(query, (data.get("nom"), data.get("prenoms"), date_naissance, data.get("courriel"),
                                 data.get("telephone"), data.get("mode_paiement"), data.get("adresse_numero"),
                                 data.get("adresse_rue"), data.get("adresse_ville"), data.get("adresse_province"),
                                 data.get("adresse_code_postal"), client_id), commit=True)


def get_client_reservations(client_id):
    query = """
            SELECT p.nom, p.prenoms, r.id, r.date, r.heure_debut, r.heure_fin, r.statut
            FROM Reservations r
                     join Prestataires p on r.prestataire_id = p.id
            WHERE r.client_id = %s
            ORDER BY date DESC, heure_debut DESC
            LIMIT 10 \
            """
    return execute_query(query, (client_id,), fetch_all=True)


def get_reservation_by_id(reservation_id, client_id=None):
    query = """
            SELECT r.id, r.client_id, r.prestataire_id,   p.nom, p.prenoms, r.date, r.heure_debut, r.heure_fin, statut
            FROM Reservations r join Prestataires p on r.prestataire_id = p.id
            WHERE r.id = %s \
            """
    params = [reservation_id]
    if client_id is not None:
        query += " AND r.client_id = %s"
        params.append(client_id)

    return execute_query(query, tuple(params), fetch_one=True)


def get_reservation_services(reservation_id):
    query = """
            SELECT rs.service_id, s.nom, rs.prix_applique, rs.duree_prevue, rs.quantite
            FROM Reservation_Services rs
                     JOIN Services s ON s.id = rs.service_id
            WHERE rs.reservation_id = %s \
            """
    return execute_query(query, (reservation_id,), fetch_one=True)


def get_facture_by_reservation(reservation_id):
    query = """
            SELECT id, reservation_id, sous_total, total
            FROM Factures
            WHERE reservation_id = %s \
            """
    return execute_query(query, (reservation_id,), fetch_one=True)


def get_facture_by_id(facture_id):
    query = """
            SELECT id, reservation_id, sous_total, total
            FROM Factures
            WHERE id = %s \
            """
    return execute_query(query, (facture_id,), fetch_one=True)


def update_reservation_status(reservation_id, statut):
    query = """
            UPDATE Reservations
            SET statut = %s
            WHERE id = %s \
            """
    return execute_query(query, (statut, reservation_id), commit=True)


def mark_client_past_reservations_completed(client_id):
    query = """
            UPDATE Reservations
            SET statut = 'Terminee'
            WHERE client_id = %s
              AND statut NOT IN ('Terminee', 'annulee')
              AND (date + COALESCE(heure_fin, heure_debut)) < NOW()
            """
    return execute_query(query, (client_id,), commit=True)


def get_client_factures(client_id):
    query = """
            SELECT f.id,
                   f.reservation_id,
                   f.sous_total,
                   f.total,
                   r.prestataire_id,
                   r.date,
                   r.heure_debut,
                   r.heure_fin,
                   r.statut
            FROM Factures f
                     JOIN Reservations r ON r.id = f.reservation_id
            WHERE r.client_id = %s
            ORDER BY r.date DESC, r.heure_debut DESC \
            """
    return execute_query(query, (client_id,), fetch_all=True)


def get_client_comments(client_id):
    query = """
            SELECT c.id             as comment_id,
                   c.note,
                   c.texte,
                   c.reservation_id as reservation_id,
                   r.prestataire_id as prestataire_id
            FROM Commentaires c
                     JOIN Reservations r ON r.id = c.reservation_id
            WHERE r.client_id = %s
            ORDER BY r.date DESC, r.heure_debut DESC \
            """
    return execute_query(query, (client_id,), fetch_all=True)


def get_commentaire_by_reservation(reservation_id):
    query = """
            SELECT cm.id,
                   r.id as reservation_id,
                   p.nom as prestataire_nom,
                   p.prenoms as prestataire_prenoms,
                   c.nom as client_nom,
                   c.prenoms as client_prenoms,
                   r.date,
                   r.heure_debut,
                   r.heure_fin,
                   cm.texte,
                   cm.note
            FROM Commentaires cm
                     JOIN Reservations r ON r.id = cm.reservation_id
                     Join Clients c ON c.id = cm.client_id
                     JOIN Prestataires p ON p.id = r.prestataire_id
            WHERE cm.reservation_id = %s
            """
    return execute_query(query, (reservation_id,), fetch_one=True)


def insert_commentaire(client_id, reservation_id, texte, note):
    query = """
            INSERT INTO Commentaires (client_id, reservation_id, texte, note)
            VALUES (%s, %s, %s, %s) \
            """
    return execute_query(
        query,
        (client_id, reservation_id, texte, note),
        commit=True,
        return_lastrowid=True
    )


def get_commentaire_by_id(commentaire_id):
    query = """
            SELECT id, client_id, reservation_id, texte, note
            FROM Commentaires
            WHERE id = %s \
            """
    return execute_query(query, (commentaire_id,), fetch_one=True)


def get_client_upcoming_reservations(client_id):
    query = """
            SELECT p.nom, p.prenoms, r.id, r.date, r.heure_debut, r.heure_fin, r.statut
            FROM Reservations r
                     join Prestataires p on r.prestataire_id = p.id
            WHERE r.client_id = %s
              AND r.statut NOT IN ('annulee', 'Terminee')
              AND (r.date + COALESCE(r.heure_fin, r.heure_debut)) >= NOW()
            ORDER BY date ASC, heure_debut ASC \
            """
    return execute_query(query, (client_id,), fetch_all=True)


def get_client_past_reservations(client_id):
    query = """
            SELECT p.nom, p.prenoms, r.id, r.date, r.heure_debut, r.heure_fin, r.statut
            FROM Reservations r
                     join Prestataires p on r.prestataire_id = p.id
            WHERE r.client_id = %s
              AND (
                r.statut IN ('Terminee', 'annulee')
                OR (r.date + COALESCE(r.heure_fin, r.heure_debut)) < NOW()
                )
            ORDER BY date DESC, heure_debut DESC \
            """
    return execute_query(query, (client_id,), fetch_all=True)

def get_commentaire_by_client_reservation(client_id, reservation_id):
    query = """
        SELECT
            c.id,
            c.client_id,
            c.reservation_id,
            c.texte,
            c.note
        FROM Commentaires c
        JOIN Reservations r
            ON r.id = c.reservation_id
        WHERE c.client_id = %s
          AND c.reservation_id = %s
          AND r.client_id = %s
        LIMIT 1
    """
    return execute_query(
        query,
        (client_id, reservation_id, client_id),
        fetch_one=True
    )


def update_commentaire_by_id(commentaire_id, texte, note):
    query = """
        UPDATE Commentaires
        SET texte = %s,
            note = %s
        WHERE id = %s
    """
    execute_query(
        query,
        (texte, note, commentaire_id),
        commit=True
    )
    return get_commentaire_by_id(commentaire_id)


def update_prestataire_note_moyenne_by_reservation(reservation_id):
    query = """
        UPDATE Prestataires p
        SET note_moyenne = notes.note_moyenne
        FROM (
            SELECT
                r.prestataire_id,
                COALESCE(ROUND(AVG(cm.note), 2), 0) AS note_moyenne
            FROM Reservations r
            LEFT JOIN Commentaires cm
                ON cm.reservation_id = r.id
            WHERE r.prestataire_id = (
                SELECT reservation_prestataire.prestataire_id
                FROM Reservations reservation_prestataire
                WHERE reservation_prestataire.id = %s
                LIMIT 1
            )
            GROUP BY r.prestataire_id
        ) notes
        WHERE notes.prestataire_id = p.id
    """
    return execute_query(query, (reservation_id,), commit=True)
