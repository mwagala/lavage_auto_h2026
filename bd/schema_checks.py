REQUIRED_PUBLIC_DATABASE_COLUMNS = frozenset(
    {
        ("prestataires", "id"),
        ("prestataires", "nom"),
        ("prestataires", "prenoms"),
        ("prestataires", "note_moyenne"),
        ("prestataires", "courriel"),
        ("prestataires", "telephone"),
        ("prestataires", "adresse_ville"),
        ("prestataires", "adresse_province"),
        ("prestataires", "est_actif"),
        ("services", "id"),
        ("services", "nom"),
        ("services", "description"),
        ("services", "prix"),
        ("services", "duree"),
        ("services", "prestataire_id"),
    }
)


def fetch_public_catalog_columns(cursor):
    cursor.execute(
        """
        SELECT lower(table_name) AS table_name, lower(column_name) AS column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND lower(table_name) IN ('prestataires', 'services')
        """
    )
    return {
        (column["table_name"], column["column_name"])
        for column in cursor.fetchall()
    }


def missing_public_catalog_columns(cursor):
    found_columns = fetch_public_catalog_columns(cursor)
    return sorted(REQUIRED_PUBLIC_DATABASE_COLUMNS - found_columns)


def format_missing_columns(missing_columns):
    return ", ".join(f"{table}.{column}" for table, column in missing_columns)
