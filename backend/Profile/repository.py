from bd.database import execute_query


def get_client_profile_by_id(user_id):
    query = """
        SELECT id, nom, prenoms, date_naissance, courriel, telephone,
               mode_paiement, adresse_numero, adresse_rue, adresse_ville,
               adresse_province, adresse_code_postal, est_actif, cree_a, modifier_a
        FROM Clients
        WHERE id = %s
    """
    return execute_query(query, (user_id,), fetch_one=True)


def get_prestataire_profile_by_id(user_id):
    query = """
        SELECT id, nom, prenoms, date_naissance, courriel, telephone,
               nas, note_moyenne, adresse_numero, adresse_rue, adresse_ville,
               adresse_province, adresse_code_postal, est_actif, cree_a, modifier_a
        FROM Prestataires
        WHERE id = %s
    """
    return execute_query(query, (user_id,), fetch_one=True)


def update_client_profile(user_id, data):
    query = """
        UPDATE Clients
        SET nom = %s,
            prenoms = %s,
            date_naissance = %s,
            courriel = %s,
            telephone = %s,
            mode_paiement = %s,
            adresse_numero = %s,
            adresse_rue = %s,
            adresse_ville = %s,
            adresse_province = %s,
            adresse_code_postal = %s
        WHERE id = %s
    """
    return execute_query(
        query,
        (
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
            user_id
        ),
        commit=True
    )


def update_prestataire_profile(user_id, data):
    query = """
        UPDATE Prestataires
        SET nom = %s,
            prenoms = %s,
            date_naissance = %s,
            courriel = %s,
            telephone = %s,
            adresse_numero = %s,
            adresse_rue = %s,
            adresse_ville = %s,
            adresse_province = %s,
            adresse_code_postal = %s
        WHERE id = %s
    """
    return execute_query(
        query,
        (
            data["nom"],
            data["prenoms"],
            data["date_naissance"],
            data["courriel"],
            data["telephone"],
            data["adresse_numero"],
            data["adresse_rue"],
            data["adresse_ville"],
            data["adresse_province"],
            data["adresse_code_postal"],
            user_id
        ),
        commit=True
    )


def deactivate_client(user_id):
    query = """
        UPDATE Clients
        SET est_actif = FALSE
        WHERE id = %s
    """
    return execute_query(query, (user_id,), commit=True)


def deactivate_prestataire(user_id):
    query = """
        UPDATE Prestataires
        SET est_actif = FALSE
        WHERE id = %s
    """
    return execute_query(query, (user_id,), commit=True)