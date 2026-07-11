import os
import uuid

import pytest


pytestmark = pytest.mark.integration


def _integration_enabled():
    return os.getenv("RUN_INTEGRATION_TESTS") == "1"


@pytest.mark.skipif(
    not _integration_enabled(),
    reason="Set RUN_INTEGRATION_TESTS=1 with PostgreSQL and Redis test services.",
)
def test_postgresql_foundation_tables_exist():
    import psycopg

    from bd.config import Config

    expected_tables = {
        "evenements_outbox",
        "cles_idempotence",
        "journaux_audit",
    }

    with psycopg.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        dbname=Config.DB_NAME,
        connect_timeout=Config.DB_CONNECT_TIMEOUT if hasattr(Config, "DB_CONNECT_TIMEOUT") else 5,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT lower(tablename)
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND lower(tablename) = ANY(%s)
                """,
                (list(expected_tables),),
            )
            found_tables = {row[0] for row in cursor.fetchall()}

    assert found_tables == expected_tables


@pytest.mark.skipif(
    not _integration_enabled(),
    reason="Set RUN_INTEGRATION_TESTS=1 with PostgreSQL and Redis test services.",
)
def test_redis_broker_accepts_ping():
    from redis import Redis

    from bd.config import Config

    client = Redis.from_url(
        Config.CELERY_BROKER_URL,
        socket_connect_timeout=Config.HEALTH_CHECK_TIMEOUT,
        socket_timeout=Config.HEALTH_CHECK_TIMEOUT,
        decode_responses=True,
    )

    assert client.ping() is True


@pytest.mark.skipif(
    not _integration_enabled(),
    reason="Set RUN_INTEGRATION_TESTS=1 with PostgreSQL and Redis test services.",
)
def test_reservation_creation_persists_audit_outbox_idempotency_and_consumer(monkeypatch):
    import psycopg
    from psycopg.rows import dict_row

    from bd.config import Config
    from backend.Reservations import service as reservation_service
    from backend.celery.tasks import outbox as outbox_task

    suffix = uuid.uuid4().hex[:12]
    correlation_id = f"it-reservation-{suffix}"
    idempotency_key = f"it-key-{suffix}"
    client_id = None
    prestataire_id = None
    service_id = None
    reservation_id = None

    monkeypatch.setattr(
        reservation_service,
        "_declencher_consumer_outbox_apres_commit",
        lambda *args, **kwargs: None,
    )

    def connect(row_factory=None):
        return psycopg.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            dbname=Config.DB_NAME,
            connect_timeout=getattr(Config, "DB_CONNECT_TIMEOUT", 5),
            row_factory=row_factory,
        )

    try:
        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO Clients (
                        nom, prenoms, date_naissance, courriel, telephone,
                        mode_paiement, adresse_numero, adresse_rue, adresse_ville,
                        adresse_province, adresse_code_postal, mot_passe_hash
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        "Integration",
                        "Client",
                        "1990-01-01",
                        f"client.integration.{suffix}@example.com",
                        f"514-700-{suffix[:4]}",
                        "Comptant",
                        "10",
                        "Rue Test",
                        "Montreal",
                        "QC",
                        "H1H 1H1",
                        "test-hash",
                    ),
                )
                client_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO Prestataires (
                        nom, prenoms, date_naissance, nas, courriel, telephone,
                        adresse_numero, adresse_rue, adresse_ville, adresse_province,
                        adresse_code_postal, mot_passe_hash
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        "Integration",
                        "Prestataire",
                        "1985-01-01",
                        str(uuid.uuid4().int % 900000000 + 100000000),
                        f"prestataire.integration.{suffix}@example.com",
                        f"514-800-{suffix[:4]}",
                        "20",
                        "Avenue Test",
                        "Montreal",
                        "QC",
                        "H2H 2H2",
                        "test-hash",
                    ),
                )
                prestataire_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO Services (
                        nom, prestataire_id, description, duree, prix
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        f"Lavage integration {suffix}",
                        prestataire_id,
                        "Service cree par test integration",
                        1.0,
                        30.0,
                    ),
                )
                service_id = cursor.fetchone()[0]
            connection.commit()

        payload = {
            "prestataire_id": prestataire_id,
            "date": "2099-03-15",
            "heure_debut": "09:00",
            "services": [{"service_id": service_id, "quantite": 1}],
        }
        result, error = reservation_service.create_reservation_client(
            client_id=client_id,
            payload=payload,
            audit_context={
                "adresse_ip": "127.0.0.1",
                "correlation_id": correlation_id,
            },
            idempotency_key=idempotency_key,
        )

        assert error is None
        assert result
        reservation_id = result["id"]

        with connect(row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM Reservations WHERE id = %s",
                    (reservation_id,),
                )
                reservation = cursor.fetchone()
                assert reservation["client_id"] == client_id
                assert reservation["prestataire_id"] == prestataire_id
                assert reservation["statut"] == "Assignee"

                cursor.execute(
                    "SELECT * FROM Factures WHERE reservation_id = %s",
                    (reservation_id,),
                )
                facture = cursor.fetchone()
                assert facture is not None
                assert float(facture["sous_total"]) == 30.0

                cursor.execute(
                    """
                    SELECT *
                    FROM Evenements_Outbox
                    WHERE type_evenement = %s
                      AND type_ressource = %s
                      AND ressource_id = %s
                    """,
                    ("reservation.created", "reservation", str(reservation_id)),
                )
                event = cursor.fetchone()
                assert event is not None
                assert event["statut"] == "en_attente"
                assert event["donnees_json"]["reservation_id"] == reservation_id

                cursor.execute(
                    """
                    SELECT type_ressource, statut, reponse_json
                    FROM Cles_Idempotence
                    WHERE cle_idempotence = %s
                    """,
                    (
                        reservation_service._build_request_idempotency_key(
                            client_id,
                            idempotency_key,
                        ),
                    ),
                )
                request_key = cursor.fetchone()
                assert request_key is not None
                assert request_key["type_ressource"] == "reservation_create_request"
                assert request_key["statut"] == "traitee"
                assert request_key["reponse_json"]["reservation_id"] == reservation_id

                cursor.execute(
                    """
                    SELECT *
                    FROM Journaux_Audit
                    WHERE action = %s
                      AND type_ressource = %s
                      AND ressource_id = %s
                      AND correlation_id = %s
                    """,
                    ("reservation.created", "reservation", str(reservation_id), correlation_id),
                )
                audit = cursor.fetchone()
                assert audit is not None
                assert audit["resultat"] == "succes"
                assert audit["acteur_id"] == client_id

        consumer_result = outbox_task._traiter_evenement_outbox(dict(event))
        assert consumer_result["statut"] == "traite"

        with connect(row_factory=dict_row) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT statut FROM Evenements_Outbox WHERE id = %s",
                    (event["id"],),
                )
                assert cursor.fetchone()["statut"] == "traite"

                cursor.execute(
                    "SELECT statut FROM Cles_Idempotence WHERE cle_idempotence = %s",
                    (event["cle_idempotence"],),
                )
                assert cursor.fetchone()["statut"] == "traitee"

    finally:
        with connect() as connection:
            with connection.cursor() as cursor:
                if reservation_id is not None:
                    cursor.execute(
                        "DELETE FROM Journaux_Audit WHERE ressource_id = %s",
                        (str(reservation_id),),
                    )
                    cursor.execute(
                        "DELETE FROM Evenements_Outbox WHERE ressource_id = %s",
                        (str(reservation_id),),
                    )
                    cursor.execute(
                        "DELETE FROM Cles_Idempotence WHERE ressource_id = %s",
                        (str(reservation_id),),
                    )
                    cursor.execute(
                        "DELETE FROM Reservations WHERE id = %s",
                        (reservation_id,),
                    )

                if client_id is not None:
                    cursor.execute(
                        """
                        DELETE FROM Cles_Idempotence
                        WHERE cle_idempotence LIKE %s
                        """,
                        (f"{reservation_service.IDEMPOTENCY_CREATE_PREFIX}:{client_id}:%",),
                    )
                    cursor.execute("DELETE FROM Clients WHERE id = %s", (client_id,))

                if service_id is not None:
                    cursor.execute("DELETE FROM Services WHERE id = %s", (service_id,))

                if prestataire_id is not None:
                    cursor.execute("DELETE FROM Prestataires WHERE id = %s", (prestataire_id,))
            connection.commit()
