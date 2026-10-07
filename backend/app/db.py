"""Conexión a PostgreSQL y migraciones versionadas."""

from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app.config import get_database_url

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def connect() -> psycopg.Connection:
    # autocommit: cada `with conn.transaction()` es una transacción real y las lecturas
    # sueltas no dejan transacciones implícitas abiertas.
    return psycopg.connect(get_database_url(), row_factory=dict_row, autocommit=True)


def migrate(conn: psycopg.Connection) -> list[str]:
    """Aplica en orden los archivos de migrations/ que aún no se han aplicado."""
    with conn.transaction():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    applied = {r["version"] for r in conn.execute("SELECT version FROM schema_migrations")}

    newly_applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.stem in applied:
            continue
        with conn.transaction():
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
        newly_applied.append(path.stem)
    return newly_applied
