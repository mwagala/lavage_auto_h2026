import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


load_dotenv()


def get_connection():
    """
    Cree une connexion PostgreSQL standard pour le projet.
    """
    database_url = os.getenv("DATABASE_URL")
    connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", 5))

    if database_url:
        return psycopg.connect(
            database_url,
            row_factory=dict_row,
            autocommit=False,
            connect_timeout=connect_timeout,
        )

    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 5432)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dbname=os.getenv("DB_NAME"),
        row_factory=dict_row,
        autocommit=False,
        connect_timeout=connect_timeout,
    )


def _query_with_returning_id(query):
    if " returning " in query.lower():
        return query

    clean_query = query.rstrip().rstrip(";")
    return f"{clean_query} RETURNING id"


def execute_query(
    query,
    params=None,
    fetch_one=False,
    fetch_all=False,
    commit=False,
    return_lastrowid=False,
    connection=None
):
    """
    Execute une requete SQL avec un comportement simple et explicite.

    - Si "connection" est fourni, on utilise cette connexion (transaction externe).
    - Sinon, on ouvre/ferme une connexion locale automatiquement.
    """
    use_local_connection = connection is None
    active_connection = connection or get_connection()
    cursor = active_connection.cursor()

    try:
        query_to_execute = _query_with_returning_id(query) if return_lastrowid else query
        cursor.execute(query_to_execute, params or ())

        if return_lastrowid:
            row = cursor.fetchone()
            result = row["id"] if row else None
        elif fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = None

        if commit and use_local_connection:
            active_connection.commit()

        return result

    except Exception:
        if use_local_connection:
            active_connection.rollback()
        raise

    finally:
        cursor.close()
        if use_local_connection:
            active_connection.close()
