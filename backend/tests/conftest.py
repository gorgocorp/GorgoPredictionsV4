"""Fixtures comunes.

Las pruebas de integración usan bases aisladas (prefijo gorgo_v4_test) en el mismo servidor de V4, que se
recrean con las migraciones en cada sesión de pytest.
"""

from collections.abc import Iterator

import psycopg
import pytest
from psycopg.rows import dict_row

from app.core import accounts
from app.db import migrate
from tests.pg import TEST_DB, recreate_database


@pytest.fixture(autouse=True, scope="session")
def fast_password_hashing() -> Iterator[None]:
    """scrypt barato en pruebas: el costo real (~0.5 s por contraseña) no cambia lo que se prueba."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(accounts, "SCRYPT_N", 2**10)
        yield


@pytest.fixture(scope="session")
def test_db_url() -> str:
    url = recreate_database(TEST_DB)
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        migrate(conn)
    return url


@pytest.fixture
def db(test_db_url: str) -> Iterator[psycopg.Connection]:
    """Conexión a la base de pruebas migrada; todo lo que haga la prueba se revierte al final."""
    with psycopg.connect(test_db_url, row_factory=dict_row) as conn:
        yield conn
        conn.rollback()
