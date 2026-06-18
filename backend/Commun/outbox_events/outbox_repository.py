import datetime

from bd.database import execute_query

def insert_new_event(payload, connection=None):
    # Le repository ne decide pas du contenu metier. Il insere seulement
    # l'evenement prepare par le service Outbox.
    query = """
        INSERT INTO Evenements_Outbox (
            type_evenement,
            type_ressource,
            ressource_id,
            cle_idempotence,
            donnees_json,
            statut
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s)
    """

    params = (
        payload["type_evenement"],
        payload["type_ressource"],
        payload["ressource_id"],
        payload.get("cle_idempotence"),
        payload["donnees_json"],
        "en_attente",
    )

    return execute_query(
        query,
        params,
        connection=connection,
        commit=True,
        return_lastrowid=True,
    )


def get_pending_events(connection=None):
    query = """
        SELECT *
        FROM Evenements_Outbox e
        WHERE e.statut = %s
        ORDER BY e.cree_a ASC
    """
    return execute_query(query, ("en_attente",), connection=connection, fetch_all=True) or []


def claim_pending_events(limit=10, connection=None):
    # On "claim" les evenements avant de les traiter: ils passent de
    # en_attente a en_traitement et sont retournes au worker.
    query = """
        WITH candidats AS (
            SELECT id
            FROM Evenements_Outbox
            WHERE statut = %s
              AND disponible_a <= CURRENT_TIMESTAMP
            ORDER BY cree_a ASC, id ASC
            LIMIT %s
            -- SKIP LOCKED evite que deux workers prennent le meme evenement.
            FOR UPDATE SKIP LOCKED
        )
        UPDATE Evenements_Outbox e
        SET statut = %s,
            traitement_a = %s,
            modifie_a = %s
        FROM candidats
        WHERE e.id = candidats.id
        RETURNING e.*
    """
    now = datetime.datetime.now()
    params = ("en_attente", limit, "en_traitement", now, now)
    return execute_query(
        query,
        params,
        connection=connection,
        fetch_all=True,
        commit=True
    ) or []

def update_event_status_to_in_processing(event_id, connection=None):
    query = """
        UPDATE Evenements_Outbox
        SET statut = %s, traitement_a = %s, modifie_a = %s
        where id = %s
    """
    params = ("en_traitement", datetime.datetime.now(), datetime.datetime.now(), event_id)
    return execute_query(query, params, connection=connection, commit=True)

def update_event_status_to_completed(event_id, connection=None):
    query = """
        UPDATE Evenements_Outbox
        SET statut = %s, traite_a = %s,  modifie_a = %s
        where id = %s
    """
    params = ("traite", datetime.datetime.now(), datetime.datetime.now(), event_id)
    return execute_query(query, params, connection=connection, commit=True)

def update_event_status_to_failed(event_id, error_message, connection=None):
    query = """
        UPDATE Evenements_Outbox
        SET statut = %s, tentatives = tentatives + 1, modifie_a = %s, derniere_erreur = %s
        where id = %s
    """
    params = ("echoue", datetime.datetime.now(), error_message, event_id)
    return execute_query(query, params, connection=connection, commit=True)
