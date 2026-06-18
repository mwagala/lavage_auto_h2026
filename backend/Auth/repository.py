from bd.database import execute_query


def _get_client_by_field(field_name, value):
    query = f"""
        SELECT id,
               nom,
               prenoms,
               courriel,
               telephone,
               mode_paiement,
               mot_passe_hash,
               est_actif,
               cree_a,
               modifier_a
        FROM Clients
        WHERE {field_name} = %s
    """
    return execute_query(query, (value,), fetch_one=True)


def _get_prestataire_by_field(field_name, value):
    query = f"""
        SELECT id,
               nom,
               prenoms,
               courriel,
               telephone,
               nas,
               note_moyenne,
               mot_passe_hash,
               est_actif,
               cree_a,
               modifier_a
        FROM Prestataires
        WHERE {field_name} = %s
    """
    return execute_query(query, (value,), fetch_one=True)


def get_client_by_email(courriel):
    return _get_client_by_field("courriel", courriel)


def get_client_by_telephone(telephone):
    return _get_client_by_field("telephone", telephone)


def get_prestataire_by_email(courriel):
    return _get_prestataire_by_field("courriel", courriel)


def get_prestataire_by_telephone(telephone):
    return _get_prestataire_by_field("telephone", telephone)


def get_prestataire_by_nas(nas):
    return _get_prestataire_by_field("nas", nas)


def get_client_by_id(user_id):
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
        WHERE id = %s
    """
    return execute_query(query, (user_id,), fetch_one=True)


def get_prestataire_by_id(user_id):
    query = """
        SELECT id,
               nom,
               prenoms,
               date_naissance,
               courriel,
               telephone,
               nas,
               note_moyenne,
               adresse_numero,
               adresse_rue,
               adresse_ville,
               adresse_province,
               adresse_code_postal,
               est_actif,
               cree_a,
               modifier_a
        FROM Prestataires
        WHERE id = %s
    """
    return execute_query(query, (user_id,), fetch_one=True)


def insert_client(data, password_hash):
    query = """
        INSERT INTO Clients (
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
            mot_passe_hash
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    params = (
        data["nom"],
        data["prenoms"],
        data["date_naissance"],
        data["courriel"],
        data["telephone"],
        data["mode_paiement"],
        data["adresse_numero"],
        data["adresse_rue"],
        data["adresse_ville"],
        data["adresse_province"],
        data["adresse_code_postal"],
        password_hash
    )

    return execute_query(query, params, commit=True, return_lastrowid=True)


def insert_prestataire(data, password_hash):
    query = """
        INSERT INTO Prestataires (
            nom,
            prenoms,
            date_naissance,
            nas,
            courriel,
            telephone,
            adresse_numero,
            adresse_rue,
            adresse_ville,
            adresse_province,
            adresse_code_postal,
            mot_passe_hash
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    params = (
        data["nom"],
        data["prenoms"],
        data["date_naissance"],
        data["nas"],
        data["courriel"],
        data["telephone"],
        data["adresse_numero"],
        data["adresse_rue"],
        data["adresse_ville"],
        data["adresse_province"],
        data["adresse_code_postal"],
        password_hash
    )

    return execute_query(query, params, commit=True, return_lastrowid=True)


def update_client_password(user_id, new_password_hash):
    query = """
        UPDATE Clients
        SET mot_passe_hash = %s
        WHERE id = %s
    """
    return execute_query(query, (new_password_hash, user_id), commit=True)


def update_prestataire_password(user_id, new_password_hash):
    query = """
        UPDATE Prestataires
        SET mot_passe_hash = %s
        WHERE id = %s
    """
    return execute_query(query, (new_password_hash, user_id), commit=True)
