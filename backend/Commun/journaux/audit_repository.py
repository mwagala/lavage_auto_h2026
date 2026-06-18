from bd.database import execute_query

def insert_new_audit_log(payload, connection=None):
    query = """
        INSERT INTO Journaux_Audit (
            acteur_id,
            role_acteur,
            action,
            type_ressource,
            ressource_id,
            resultat,
            adresse_ip,
            correlation_id,
            details_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
    """
    params = (payload.acteur_id, payload.role_acteur, payload.action,
              payload.type_ressource, payload.ressource_id,
              payload.resultat, getattr(payload, "adresse_ip", None),
              payload.correlation_id, getattr(payload, "details_json", None))
    return execute_query(
        query,
        params,
        connection=connection,
        commit=True,
        return_lastrowid=True
    )

def get_audit_logs_by_ressource(ressource_id, ressource_type, connection=None):
    query = """
    select * from Journaux_Audit where ressource_id = %s and type_ressource = %s"""

    params = (ressource_id, ressource_type)
    return execute_query(query, params, connection=connection, fetch_all=True) or []

def get_audit_logs_by_actor(actor_id, connection=None):
    query = """
            select *
            from Journaux_Audit
            where acteur_id = %s"""

    params = (actor_id,)
    return execute_query(query, params, connection=connection, fetch_all=True) or []

def get_audit_logs_by_correlation(correlation_id, connection=None):
    query = """
            select *
            from Journaux_Audit
            where correlation_id = %s"""

    params = (correlation_id,)
    return execute_query(query, params, connection=connection, fetch_all=True) or []
