"""Partidos NBA en el registro común core.matches."""

import psycopg

from app.config import LOCAL_TZ
from app.core.matches import upsert_matches
from app.sports.nba.config import NBA_LEAGUE_ID
from app.sports.nba.engine.evidence import CANCELLED, FINISHED

# Estados de /games (docs/apis/API_Basketball_1_5_endpoints.md, "Estados de partido"): terminados y
# anulados como los liquida el motor; el resto (Q1–Q4, OT, BT, HT, SUSP) es partido en juego.
SCHEDULED = ("NS",)

# El día es el de LOCAL_TIMEZONE, igual que en fútbol. nba.games.game_date sigue en hora del Este
# para las fases de nba.seasons; con los horarios NBA (12:00–23:00 ET) las dos fechas coinciden.
MATCHES_SELECT = """
SELECT 'nba', g.id, %(league_id)s, 'NBA', g.starts_at, (g.starts_at AT TIME ZONE %(tz)s)::date, g.status,
       CASE WHEN g.status = ANY(%(finished)s) THEN 'finished'
            WHEN g.status = ANY(%(cancelled)s) THEN 'cancelled'
            WHEN g.status = ANY(%(scheduled)s) THEN 'scheduled'
            ELSE 'live' END,
       ht.name, at.name
FROM nba.games g
JOIN nba.teams ht ON ht.id = g.home_team_id
JOIN nba.teams at ON at.id = g.away_team_id
WHERE %(ids)s::int[] IS NULL OR g.id = ANY(%(ids)s::int[])
"""


def sync_matches(conn: psycopg.Connection, game_ids: list[int] | None = None) -> int:
    """Registra en core.matches los partidos de nba.games (todos, o sólo `game_ids`)."""
    return upsert_matches(
        conn,
        MATCHES_SELECT,
        {
            "league_id": NBA_LEAGUE_ID,
            "tz": str(LOCAL_TZ),
            "finished": list(FINISHED),
            "cancelled": list(CANCELLED),
            "scheduled": list(SCHEDULED),
            "ids": game_ids,
        },
    )
