from __future__ import annotations

from werkzeug.security import generate_password_hash
from bd.database import execute_query


# Mot de passe commun des comptes de test.
# Il respecte la regle actuelle: au moins 15 caracteres et pas de mot de passe
# trop facile a deviner.
PASSWORD_PLAIN = "TestPassword2026!"


class SeedError(Exception):
    pass


def q(query, params=None, fetch_one=False, fetch_all=False, commit=False):
    return execute_query(
        query,
        params or (),
        fetch_one=fetch_one,
        fetch_all=fetch_all,
        commit=commit
    )


def ensure_row_found(row, message: str):
    if not row:
        raise SeedError(message)
    return row


def reset_database():
    q(
        """
        TRUNCATE TABLE
            Journaux_Audit,
            Cles_Idempotence,
            Evenements_Outbox,
            Factures,
            Commentaires,
            Reservation_Services,
            Reservations,
            Disponibilites,
            Services,
            Clients,
            Prestataires
        RESTART IDENTITY CASCADE
        """,
        commit=True
    )


def get_inserted_id_by_unique_field(table: str, where_clause: str, params: tuple):
    row = q(
        f"""
        SELECT id
        FROM {table}
        WHERE {where_clause}
        LIMIT 1
        """,
        params,
        fetch_one=True
    )
    return ensure_row_found(row, f"Impossible de récupérer l'id dans {table}.")["id"]


def seed_prestataires():
    ids = []

    prestataires = [
        {
            "nom": "Prestataire",
            "prenoms": "Postman1",
            "date_naissance": "1990-06-10",
            "nas": "123456781",
            "note_moyenne": 4.60,
            "courriel": "prestataire1.postman@example.com",
            "telephone": "5810002001",
            "adresse_numero": "200",
            "adresse_rue": "Rue Service 1",
            "adresse_ville": "Lévis",
            "adresse_province": "QC",
            "adresse_code_postal": "G2G2G2",
        },
        {
            "nom": "Prestataire",
            "prenoms": "Postman2",
            "date_naissance": "1989-07-11",
            "nas": "123456782",
            "note_moyenne": 4.30,
            "courriel": "prestataire2.postman@example.com",
            "telephone": "5810002002",
            "adresse_numero": "201",
            "adresse_rue": "Rue Service 2",
            "adresse_ville": "Québec",
            "adresse_province": "QC",
            "adresse_code_postal": "G1G2G2",
        },
        {
            "nom": "Prestataire",
            "prenoms": "Postman3",
            "date_naissance": "1988-08-12",
            "nas": "123456783",
            "note_moyenne": 4.80,
            "courriel": "prestataire3.postman@example.com",
            "telephone": "5810002003",
            "adresse_numero": "202",
            "adresse_rue": "Rue Service 3",
            "adresse_ville": "Montréal",
            "adresse_province": "QC",
            "adresse_code_postal": "H2B2B2",
        },
        {
            "nom": "Prestataire",
            "prenoms": "Postman4",
            "date_naissance": "1987-09-13",
            "nas": "123456784",
            "note_moyenne": 4.10,
            "courriel": "prestataire4.postman@example.com",
            "telephone": "5810002004",
            "adresse_numero": "203",
            "adresse_rue": "Rue Service 4",
            "adresse_ville": "Sherbrooke",
            "adresse_province": "QC",
            "adresse_code_postal": "J1K1K1",
        },
        {
            "nom": "Prestataire",
            "prenoms": "Postman5",
            "date_naissance": "1986-10-14",
            "nas": "123456785",
            "note_moyenne": 3.90,
            "courriel": "prestataire5.postman@example.com",
            "telephone": "5810002005",
            "adresse_numero": "204",
            "adresse_rue": "Rue Service 5",
            "adresse_ville": "Gatineau",
            "adresse_province": "QC",
            "adresse_code_postal": "J8Y8Y8",
        },
        {
            "nom": "Prestataire",
            "prenoms": "Postman6",
            "date_naissance": "1985-11-15",
            "nas": "123456786",
            "note_moyenne": 4.50,
            "courriel": "prestataire6.postman@example.com",
            "telephone": "5810002006",
            "adresse_numero": "205",
            "adresse_rue": "Rue Service 6",
            "adresse_ville": "Trois-Rivières",
            "adresse_province": "QC",
            "adresse_code_postal": "G9A9A9",
        },
    ]

    query = """
        INSERT INTO Prestataires (
            nom, prenoms, date_naissance, nas, note_moyenne, courriel, telephone,
            adresse_numero, adresse_rue, adresse_ville, adresse_province, adresse_code_postal,
            mot_passe_hash, est_actif
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for p in prestataires:
        password_hash = generate_password_hash(PASSWORD_PLAIN)

        q(
            query,
            (
                p["nom"],
                p["prenoms"],
                p["date_naissance"],
                p["nas"],
                p["note_moyenne"],
                p["courriel"],
                p["telephone"],
                p["adresse_numero"],
                p["adresse_rue"],
                p["adresse_ville"],
                p["adresse_province"],
                p["adresse_code_postal"],
                password_hash,
                True,
            ),
            commit=True
        )

        inserted_id = get_inserted_id_by_unique_field(
            "Prestataires",
            "courriel = %s",
            (p["courriel"],)
        )
        ids.append(inserted_id)

    return ids


def seed_clients():
    ids = []

    clients = [
        {
            "nom": "Client",
            "prenoms": "Postman1",
            "date_naissance": "1995-01-15",
            "courriel": "client1.postman@example.com",
            "telephone": "5810001001",
            "mode_paiement": "Carte Credit",
            "adresse_numero": "100",
            "adresse_rue": "Rue Test 1",
            "adresse_ville": "Québec",
            "adresse_province": "QC",
            "adresse_code_postal": "G1G1G1",
        },
        {
            "nom": "Client",
            "prenoms": "Postman2",
            "date_naissance": "1994-02-10",
            "courriel": "client2.postman@example.com",
            "telephone": "5810001002",
            "mode_paiement": "Comptant",
            "adresse_numero": "101",
            "adresse_rue": "Rue Test 2",
            "adresse_ville": "Lévis",
            "adresse_province": "QC",
            "adresse_code_postal": "G2G2G2",
        },
        {
            "nom": "Client",
            "prenoms": "Postman3",
            "date_naissance": "1993-03-12",
            "courriel": "client3.postman@example.com",
            "telephone": "5810001003",
            "mode_paiement": "Carte debit",
            "adresse_numero": "102",
            "adresse_rue": "Rue Test 3",
            "adresse_ville": "Montréal",
            "adresse_province": "QC",
            "adresse_code_postal": "H1A1A1",
        },
        {
            "nom": "Client",
            "prenoms": "Postman4",
            "date_naissance": "1992-04-08",
            "courriel": "client4.postman@example.com",
            "telephone": "5810001004",
            "mode_paiement": "Carte Credit",
            "adresse_numero": "103",
            "adresse_rue": "Rue Test 4",
            "adresse_ville": "Sherbrooke",
            "adresse_province": "QC",
            "adresse_code_postal": "J1J1J1",
        },
        {
            "nom": "Client",
            "prenoms": "Postman5",
            "date_naissance": "1991-05-20",
            "courriel": "client5.postman@example.com",
            "telephone": "5810001005",
            "mode_paiement": "Comptant",
            "adresse_numero": "104",
            "adresse_rue": "Rue Test 5",
            "adresse_ville": "Trois-Rivières",
            "adresse_province": "QC",
            "adresse_code_postal": "G8Z8Z8",
        },
        {
            "nom": "Client",
            "prenoms": "Postman6",
            "date_naissance": "1990-06-25",
            "courriel": "client6.postman@example.com",
            "telephone": "5810001006",
            "mode_paiement": "Carte Credit",
            "adresse_numero": "105",
            "adresse_rue": "Rue Test 6",
            "adresse_ville": "Gatineau",
            "adresse_province": "QC",
            "adresse_code_postal": "J8X8X8",
        },
    ]

    query = """
        INSERT INTO Clients (
            nom, prenoms, date_naissance, courriel, telephone, mode_paiement,
            adresse_numero, adresse_rue, adresse_ville, adresse_province, adresse_code_postal,
            mot_passe_hash, est_actif
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for c in clients:
        password_hash = generate_password_hash(PASSWORD_PLAIN)

        q(
            query,
            (
                c["nom"],
                c["prenoms"],
                c["date_naissance"],
                c["courriel"],
                c["telephone"],
                c["mode_paiement"],
                c["adresse_numero"],
                c["adresse_rue"],
                c["adresse_ville"],
                c["adresse_province"],
                c["adresse_code_postal"],
                password_hash,
                True,
            ),
            commit=True
        )

        inserted_id = get_inserted_id_by_unique_field(
            "Clients",
            "courriel = %s",
            (c["courriel"],)
        )
        ids.append(inserted_id)

    return ids


def seed_services(prestataire_ids):
    service_ids = []

    data = [
        (prestataire_ids[0], "Lavage intérieur premium 1", "Nettoyage intérieur complet 1", 1.50, 79.99),
        (prestataire_ids[1], "Lavage extérieur premium 2", "Nettoyage extérieur complet 2", 1.00, 59.99),
        (prestataire_ids[2], "Lavage complet 3", "Intérieur et extérieur 3", 2.00, 99.99),
        (prestataire_ids[3], "Shampoing sièges 4", "Nettoyage sièges et tapis 4", 1.25, 69.99),
        (prestataire_ids[4], "Polissage express 5", "Polissage carrosserie 5", 2.50, 129.99),
        (prestataire_ids[5], "Traitement complet 6", "Traitement premium 6", 3.00, 149.99),
    ]

    query = """
        INSERT INTO Services (nom, prestataire_id, description, duree, prix)
        VALUES (%s, %s, %s, %s, %s)
    """

    for prestataire_id, nom, description, duree, prix in data:
        q(query, (nom, prestataire_id, description, duree, prix), commit=True)

        inserted_id = get_inserted_id_by_unique_field(
            "Services",
            "prestataire_id = %s AND nom = %s",
            (prestataire_id, nom)
        )
        service_ids.append(inserted_id)

    return service_ids


def seed_disponibilites(prestataire_ids):
    data = [
        (prestataire_ids[0], "Lundi", "disponible", "08:00:00", "17:00:00"),
        (prestataire_ids[1], "Mardi", "disponible", "08:00:00", "17:00:00"),
        (prestataire_ids[2], "Mercredi", "disponible", "09:00:00", "18:00:00"),
        (prestataire_ids[3], "Jeudi", "disponible", "09:00:00", "17:00:00"),
        (prestataire_ids[4], "Vendredi", "disponible", "08:30:00", "16:30:00"),
        (prestataire_ids[5], "Samedi", "disponible", "10:00:00", "15:00:00"),
    ]

    query = """
        INSERT INTO Disponibilites (prestataire_id, jour, statut, heure_debut, heure_fin)
        VALUES (%s, %s, %s, %s, %s)
    """

    for row in data:
        q(query, row, commit=True)


def create_reservation(client_id, prestataire_id, date_value, heure_debut, statut):
    query = """
        INSERT INTO Reservations (
            client_id,
            prestataire_id,
            heure_debut,
            date,
            statut
        )
        VALUES (%s, %s, %s, %s, %s)
    """
    q(query, (client_id, prestataire_id, heure_debut, date_value, statut), commit=True)

    return get_inserted_id_by_unique_field(
        "Reservations",
        "client_id = %s AND prestataire_id = %s AND date = %s AND heure_debut = %s",
        (client_id, prestataire_id, date_value, heure_debut)
    )


def add_reservation_service(reservation_id, service_id, prix_applique, duree_prevue, quantite=1):
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
    q(query, (reservation_id, service_id, prix_applique, duree_prevue, quantite), commit=True)


def seed_reservations(clients, prestataires, services):
    reservation_ids = []

    reservations = [
        (clients[0], prestataires[0], "2026-04-20", "09:00:00", "Assignee", services[0], 79.99, 1.50, 1),
        (clients[1], prestataires[1], "2026-04-08", "09:00:00", "Terminee", services[1], 59.99, 1.00, 1),
        (clients[1], prestataires[2], "2026-04-10", "13:00:00", "Terminee", services[2], 99.99, 2.00, 1),
        (clients[2], prestataires[1], "2026-04-09", "10:30:00", "Terminee", services[1], 59.99, 1.00, 1),
        (clients[2], prestataires[2], "2026-04-11", "14:00:00", "Terminee", services[2], 99.99, 2.00, 1),
        (clients[3], prestataires[3], "2026-04-23", "09:30:00", "Assignee", services[3], 69.99, 1.25, 1),
        (clients[4], prestataires[4], "2026-04-24", "13:00:00", "Assignee", services[4], 129.99, 2.50, 1),
        (clients[5], prestataires[5], "2026-04-25", "10:30:00", "Assignee", services[5], 149.99, 3.00, 1),
    ]

    for r in reservations:
        reservation_id = create_reservation(
            client_id=r[0],
            prestataire_id=r[1],
            date_value=r[2],
            heure_debut=r[3],
            statut=r[4],
        )
        add_reservation_service(
            reservation_id=reservation_id,
            service_id=r[5],
            prix_applique=r[6],
            duree_prevue=r[7],
            quantite=r[8],
        )
        reservation_ids.append(reservation_id)

    return reservation_ids


def seed_commentaires():
    rows = q(
        """
        SELECT r.id, r.client_id
        FROM Reservations r
        WHERE r.statut = 'Terminee'
        ORDER BY r.id ASC
        """,
        fetch_all=True
    ) or []

    commentaires = [
        ("Excellent service", 5),
        ("Très bon service", 4),
        ("Service correct", 3),
        ("Bonne expérience", 4),
    ]

    query = """
        INSERT INTO Commentaires (client_id, reservation_id, texte, note)
        VALUES (%s, %s, %s, %s)
    """

    for row, commentaire in zip(rows, commentaires):
        q(
            query,
            (row["client_id"], row["id"], commentaire[0], commentaire[1]),
            commit=True
        )


def recalculate_prestataire_notes():
    q(
        """
        UPDATE Prestataires p
        SET note_moyenne = COALESCE((
            SELECT ROUND(AVG(c.note), 2)
            FROM Reservations r
            INNER JOIN Commentaires c
                ON c.reservation_id = r.id
            WHERE r.prestataire_id = p.id
        ), 0)
        """,
        commit=True
    )


def print_summary():
    print("Repopulation terminée.")
    print(f"Mot de passe de test: {PASSWORD_PLAIN}")

    for table in [
        "Prestataires",
        "Clients",
        "Services",
        "Disponibilites",
        "Reservations",
        "Reservation_Services",
        "Commentaires",
        "Factures",
        "Evenements_Outbox",
        "Cles_Idempotence",
        "Journaux_Audit",
    ]:
        row = q(f"SELECT COUNT(*) AS total FROM {table}", fetch_one=True)
        total = row["total"] if row else 0
        print(f"{table}: {total}")


def main():
    reset_database()
    prestataire_ids = seed_prestataires()
    client_ids = seed_clients()
    service_ids = seed_services(prestataire_ids)
    seed_disponibilites(prestataire_ids)
    seed_reservations(client_ids, prestataire_ids, service_ids)
    seed_commentaires()
    recalculate_prestataire_notes()
    print_summary()


if __name__ == "__main__":
    main()
