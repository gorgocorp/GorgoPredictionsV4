"""Partidos de fútbol en el registro común core.matches."""

import psycopg

from app.core.matches import upsert_matches
from app.sports.futbol.engine.evidence import CANCELLED, FINISHED

# Estados de /fixtures (docs/apis/API_Football_campos_verificados.md), terminados y anulados como los
# liquida el motor (AET y PEN también terminaron: las apuestas van a 90 minutos). El resto (1H, HT, 2H,
# ET, BT, P, SUSP, INT, LIVE) es partido en juego.
SCHEDULED = ("NS", "TBD")

# match_date ya es el día en LOCAL_TIMEZONE (lo calcula la ingesta desde fixture.date).
MATCHES_SELECT = """
SELECT 'futbol', f.id, f.league_id, l.name, f.starts_at, f.match_date, f.status,
       CASE WHEN f.status = ANY(%(finished)s) THEN 'finished'
            WHEN f.status = ANY(%(cancelled)s) THEN 'cancelled'
            WHEN f.status = ANY(%(scheduled)s) THEN 'scheduled'
            ELSE 'live' END,
       ht.name, at.name
FROM futbol.fixtures f
JOIN futbol.leagues l ON l.id = f.league_id
JOIN futbol.teams ht ON ht.id = f.home_team_id
JOIN futbol.teams at ON at.id = f.away_team_id
WHERE %(ids)s::int[] IS NULL OR f.id = ANY(%(ids)s::int[])
"""


def sync_matches(conn: psycopg.Connection, fixture_ids: list[int] | None = None) -> int:
    """Registra en core.matches los partidos de futbol.fixtures (todos, o sólo `fixture_ids`)."""
    return upsert_matches(
        conn,
        MATCHES_SELECT,
        {
            "finished": list(FINISHED),
            "cancelled": list(CANCELLED),
            "scheduled": list(SCHEDULED),
            "ids": fixture_ids,
        },
    )
