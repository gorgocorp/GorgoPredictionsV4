"""Bases de prueba en el servidor PostgreSQL de V4 (nunca la de trabajo ni las de los proyectos anteriores)."""

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.config import get_database_url

TEST_DB = "gorgo_v4_test"


def recreate_database(name: str) -> str:
    """Borra y crea una base vacía de prueba y devuelve su cadena de conexión."""
    if not name.startswith(TEST_DB):
        raise ValueError(f"sólo se recrean bases de prueba ({TEST_DB}*), no {name}")
    params = conninfo_to_dict(get_database_url())
    with psycopg.connect(make_conninfo(**{**params, "dbname": "postgres"}), autocommit=True) as admin:
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    return make_conninfo(**{**params, "dbname": name})
