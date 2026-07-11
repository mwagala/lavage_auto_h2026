import datetime

from bd.database import execute_query, get_connection


def _calculer_delai_retry(tentatives, retry_backoff_seconds, max_retry_delay_seconds):
    delay = retry_backoff_seconds * (2 ** max(tentatives - 1, 0))
    return min(delay, max_retry_delay_seconds)

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


def release_stale_processing_events(
    stale_processing_seconds,
    max_attempts,
    retry_backoff_seconds,
    max_retry_delay_seconds,
    limit=100,
    connection=None
):
    # Si un worker tombe apres avoir claim un evenement, celui-ci peut rester
    # bloque en_traitement. On le remet en attente avec le meme chemin de retry
    # qu'un echec applicatif, puis on libere sa cle d'idempotence.
    cutoff = datetime.datetime.now() - datetime.timedelta(seconds=stale_processing_seconds)
    use_local_connection = connection is None
    active_connection = connection or get_connection()

    query = """
        WITH candidats AS (
            SELECT id, cle_idempotence, tentatives
            FROM Evenements_Outbox
            WHERE statut = %s
              AND traitement_a IS NOT NULL
              AND traitement_a <= %s
            ORDER BY traitement_a ASC, id ASC
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        )
        UPDATE Evenements_Outbox e
        SET statut = CASE
                WHEN e.tentatives + 1 >= %s THEN %s
                ELSE %s
            END,
            tentatives = e.tentatives + 1,
            derniere_erreur = %s,
            disponible_a = CASE
                WHEN e.tentatives + 1 >= %s THEN %s
                ELSE %s + (
                    LEAST(%s * POWER(2, GREATEST(e.tentatives, 0)), %s)
                    * interval '1 second'
                )
            END,
            traitement_a = NULL,
            modifie_a = %s
        FROM candidats
        WHERE e.id = candidats.id
        RETURNING e.*
    """
    now = datetime.datetime.now()
    stale_message = "Traitement Outbox expire; evenement remis en reprise."

    try:
        stale_events = execute_query(
            query,
            (
                "en_traitement",
                cutoff,
                limit,
                max_attempts,
                "echoue",
                "en_attente",
                stale_message,
                max_attempts,
                now,
                now,
                retry_backoff_seconds,
                max_retry_delay_seconds,
                now,
            ),
            connection=active_connection,
            fetch_all=True,
        ) or []

        for event in stale_events:
            if not event.get("cle_idempotence"):
                continue

            execute_query(
                """
                    UPDATE Cles_Idempotence
                    SET statut = %s,
                        modifie_a = %s
                    WHERE cle_idempotence = %s
                      AND statut = %s
                """,
                ("echouee", now, event["cle_idempotence"], "en_traitement"),
                connection=active_connection,
            )

        if use_local_connection:
            active_connection.commit()

        return stale_events
    except Exception:
        if use_local_connection:
            active_connection.rollback()
        raise
    finally:
        if use_local_connection:
            active_connection.close()

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


def update_event_status_after_failure(
    event,
    error_message,
    max_attempts,
    retry_backoff_seconds,
    max_retry_delay_seconds,
    connection=None
):
    next_attempts = int(event.get("tentatives") or 0) + 1
    final_failure = next_attempts >= max_attempts
    next_status = "echoue" if final_failure else "en_attente"
    now = datetime.datetime.now()
    next_available_at = now

    if not final_failure:
        delay_seconds = _calculer_delai_retry(
            next_attempts,
            retry_backoff_seconds,
            max_retry_delay_seconds,
        )
        next_available_at = now + datetime.timedelta(seconds=delay_seconds)

    query = """
        UPDATE Evenements_Outbox
        SET statut = %s,
            tentatives = %s,
            disponible_a = %s,
            traitement_a = NULL,
            modifie_a = %s,
            derniere_erreur = %s
        where id = %s
        RETURNING *
    """
    params = (
        next_status,
        next_attempts,
        next_available_at,
        now,
        error_message,
        event["id"],
    )
    return execute_query(
        query,
        params,
        connection=connection,
        commit=True,
        fetch_one=True,
    )


def update_event_status_to_failed(event_id, error_message, connection=None):
    event = {
        "id": event_id,
        "tentatives": 0,
    }
    return update_event_status_after_failure(
        event=event,
        error_message=error_message,
        max_attempts=1,
        retry_backoff_seconds=0,
        max_retry_delay_seconds=0,
        connection=connection,
    )
