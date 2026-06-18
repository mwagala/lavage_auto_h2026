import datetime

from psycopg.errors import UniqueViolation

from bd.database import execute_query


def get_key(key, connection=None):
    query = """
            SELECT *
            FROM Cles_Idempotence
            WHERE cle_idempotence = %s
            """
    return execute_query(query, (key,), fetch_one=True, connection=connection)


def book_new_key(payload, connection=None):
    existing_key = get_key(payload.cle_idempotence, connection=connection)
    if existing_key:
        return {
            "cle_creee": False,
            "cle": existing_key,
            "message": "La cle existe deja"
        }

    query = """
            INSERT INTO Cles_Idempotence (
                cle_idempotence,
                type_ressource,
                ressource_id,
                empreinte_requete,
                statut,
                expire_a
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """
    params = (
        payload.cle_idempotence,
        payload.type_ressource,
        payload.ressource_id,
        getattr(payload, "empreinte_requete", None),
        "reservee",
        getattr(payload, "expire_a", None)
    )

    try:
        execute_query(query, params, connection=connection, commit=True)
    except UniqueViolation:
        return {
            "cle_creee": False,
            "cle": get_key(payload.cle_idempotence, connection=connection),
            "message": "La cle existe deja"
        }

    return {
        "cle_creee": True,
        "cle": get_key(payload.cle_idempotence, connection=connection),
        "message": None
    }


def update_key_status_to_in_processing(key_id, connection=None):
    query = """
        UPDATE Cles_Idempotence
        SET statut = %s, traitement_a = %s, modifie_a = %s
        where id = %s
    """
    params = ("en_traitement", datetime.datetime.now(), datetime.datetime.now(), key_id)
    return execute_query(query, params, connection=connection, commit=True)

def update_key_status_to_completed(key_id, reponse_json, connection=None):
    query = """
        UPDATE Cles_Idempotence
        SET statut = %s, traite_a = %s, reponse_json = %s::jsonb, modifie_a = %s
        where id = %s
    """
    params = ("traitee", datetime.datetime.now(), reponse_json, datetime.datetime.now() , key_id)
    return execute_query(query, params, connection=connection, commit=True)

def update_key_status_to_failed(key_id, connection=None):
    query = """
        UPDATE Cles_Idempotence
        SET statut = %s, modifie_a = %s
        where id = %s
    """
    params = ("echouee", datetime.datetime.now(), key_id)
    return execute_query(query, params, connection=connection, commit=True)
