from __future__ import annotations

import os
import time
from pathlib import Path

import redis

from bd import peuplement
from bd.config import Config
from bd.database import get_connection
from bd.schema_checks import format_missing_columns, missing_public_catalog_columns


def _get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"true", "1", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _wait_for(label: str, operation, timeout_seconds: int) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            operation()
            print(f"{label}: pret.")
            return
        except Exception as exc:  # pragma: no cover - depends on external services
            last_error = exc
            time.sleep(1)

    raise RuntimeError(f"{label}: indisponible apres {timeout_seconds}s. Derniere erreur: {last_error}")


def _check_postgres() -> None:
    with get_connection() as connection:
        connection.execute("SELECT 1")


def _check_redis() -> None:
    client = redis.Redis.from_url(
        Config.REDIS_URL,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    client.ping()


def _missing_schema_columns() -> list[tuple[str, str]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            return missing_public_catalog_columns(cursor)


def _apply_schema() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "bd" / "init.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    with get_connection() as connection:
        connection.execute(schema_sql)
        connection.commit()

    print("Schema PostgreSQL applique.")


def _count_rows(table_name: str) -> int:
    if table_name not in {"Clients", "Prestataires"}:
        raise ValueError(f"Table non autorisee: {table_name}")

    with get_connection() as connection:
        row = connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
    return int(row["total"]) if row else 0


def _seed_if_needed() -> None:
    auto_seed = _get_bool_env("BOOTSTRAP_AUTO_SEED", True)
    reset_demo_data = _get_bool_env("BOOTSTRAP_RESET_DEMO_DATA", False)

    if not auto_seed and not reset_demo_data:
        print("Peuplement demo ignore.")
        return

    clients_count = _count_rows("Clients")
    prestataires_count = _count_rows("Prestataires")

    if reset_demo_data:
        print("Reinitialisation des donnees demo demandee.")
        peuplement.main()
        return

    if clients_count == 0 and prestataires_count == 0:
        print("Peuplement des donnees demo.")
        peuplement.main()
        return

    print("Donnees existantes detectees; peuplement demo ignore.")


def main() -> None:
    timeout_seconds = _get_int_env("BOOTSTRAP_TIMEOUT_SECONDS", 60)
    apply_schema = _get_bool_env("BOOTSTRAP_APPLY_SCHEMA", True)

    _wait_for("PostgreSQL", _check_postgres, timeout_seconds)
    _wait_for("Redis", _check_redis, timeout_seconds)

    missing_columns = _missing_schema_columns()
    if missing_columns:
        if not apply_schema:
            missing = format_missing_columns(missing_columns)
            raise RuntimeError(
                "Schema PostgreSQL absent ou incomplet "
                f"({missing}) et BOOTSTRAP_APPLY_SCHEMA=false."
            )
        missing = format_missing_columns(missing_columns)
        print(f"Schema PostgreSQL absent ou incomplet ({missing}).")
        _apply_schema()
    else:
        print("Schema PostgreSQL deja present et compatible.")

    _seed_if_needed()
    print("Bootstrap termine.")


if __name__ == "__main__":
    main()
