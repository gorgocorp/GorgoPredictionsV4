"""Registro común de partidos (core.matches).

Cada deporte guarda sus partidos en su esquema con los IDs de su proveedor (nba.games, futbol.fixtures).
core.matches les da una identidad común para que picks, parlays y apuestas puedan referirse a partidos de
cualquier deporte. Cada deporte aporta un SELECT con las columnas de MATCH_COLUMNS y aquí se hace el
upsert por conjunto, dentro de la transacción de quien llama.
"""

import psycopg
from psycopg import sql

MATCH_COLUMNS = (
    "sport", "external_id", "competition_id", "competition", "starts_at", "local_date",
    "status", "state", "home_name", "away_name",
)
_UPDATABLE = MATCH_COLUMNS[2:]

STATES = ("scheduled", "live", "finished", "cancelled")


def upsert_matches(conn: psycopg.Connection, select: str, params: dict) -> int:
    """Inserta o actualiza en core.matches las filas de `select`. Devuelve cuántas cambiaron."""
    query = sql.SQL(
        """
        INSERT INTO core.matches AS m ({columns})
        {select}
        ON CONFLICT (sport, external_id) DO UPDATE SET {assignments}, updated_at = now()
        WHERE ({current}) IS DISTINCT FROM ({incoming})
        """
    ).format(
        columns=sql.SQL(", ").join(map(sql.Identifier, MATCH_COLUMNS)),
        select=sql.SQL(select),
        assignments=sql.SQL(", ").join(
            sql.SQL("{0} = EXCLUDED.{0}").format(sql.Identifier(c)) for c in _UPDATABLE
        ),
        current=sql.SQL(", ").join(sql.SQL("m.{}").format(sql.Identifier(c)) for c in _UPDATABLE),
        incoming=sql.SQL(", ").join(sql.SQL("EXCLUDED.{}").format(sql.Identifier(c)) for c in _UPDATABLE),
    )
    return conn.execute(query, params).rowcount
