"""Partes de NBA del registro de picks: proyecciones, liquidación y filtros de rendimiento.

Lo común (guardar piernas, armar y congelar parlays, liquidar parlays y apuestas, rendimiento) está en
app/core/tracking.py.
"""

from datetime import datetime, timedelta

import psycopg
from psycopg.types.json import Jsonb

from app.sports.nba.engine.evidence import CANCELLED, STAT_VALUE
from app.sports.nba.engine.legs import LegSpec, settle

# Cambiar cuando los modelos cambien de forma relevante, para separar su rendimiento.
MODEL_VERSION = "v1"

# Qué piernas se guardan: prácticamente todas las evaluadas, también las poco probables, para
# que el usuario pueda registrar en "Mis apuestas" cualquier pierna que apueste en su casa.
STORE_RANGE_PRICED = (0.01, 0.99)
STORE_RANGE_UNPRICED = (0.05, 0.97)
# Si un partido terminó y la API nunca publicó estadísticas de jugadores, sus props se anulan.
PLAYER_STATS_GRACE = timedelta(days=2)


UPSERT_PROJECTION = """
INSERT INTO nba.game_projections (game_id, home_points, away_points, p_home_win, model_version, evaluated_at,
                                  home_missing_pts, away_missing_pts, home_roster_pts, away_roster_pts, roster_detail)
VALUES (%(game_id)s, %(home)s, %(away)s, %(p_home)s, %(version)s, %(now)s, %(home_missing)s, %(away_missing)s,
        %(home_roster)s, %(away_roster)s, %(roster_detail)s)
ON CONFLICT (game_id) DO UPDATE SET
    home_roster_pts = EXCLUDED.home_roster_pts,
    away_roster_pts = EXCLUDED.away_roster_pts,
    roster_detail = EXCLUDED.roster_detail,
    home_missing_pts = EXCLUDED.home_missing_pts,
    away_missing_pts = EXCLUDED.away_missing_pts,
    home_points = EXCLUDED.home_points,
    away_points = EXCLUDED.away_points,
    p_home_win = EXCLUDED.p_home_win,
    model_version = EXCLUDED.model_version,
    evaluated_at = EXCLUDED.evaluated_at
"""


def save_projections(conn: psycopg.Connection, cards: list, now: datetime) -> None:
    """Proyección de cada partido (misma regla que picks: deja de cambiar al empezar el partido)."""
    with conn.cursor() as cur:
        cur.executemany(UPSERT_PROJECTION, [
            {
                "game_id": card.game_id,
                "home": round(card.prediction.home_points, 2),
                "away": round(card.prediction.away_points, 2),
                "p_home": round(card.p_home_win, 4),
                "home_missing": round(card.home_missing, 2),
                "away_missing": round(card.away_missing, 2),
                "home_roster": round(card.home_roster, 2),
                "away_roster": round(card.away_roster, 2),
                "roster_detail": Jsonb(card.roster_detail),
                "version": MODEL_VERSION,
                "now": now,
            }
            for card in cards
        ])


# Datos reales de cada pierna (liquidación, historial y apuestas): marcador y estadística del jugador.
OUTCOME_COLUMNS = """
       g.status, g.starts_at, g.home_total, g.away_total,
       ps.seconds_played, ps.points, ps.rebounds, ps.assists, ps.fg3_made,
       COALESCE(ps.fg2_made_derived, ps.fg2_made, 0) + COALESCE(ps.fg3_made, 0) AS fgm,
       EXISTS (SELECT 1 FROM nba.player_game_stats x WHERE x.game_id = g.id) AS game_has_stats
"""
OUTCOME_JOINS = """
JOIN core.matches m ON m.id = k.match_id
JOIN nba.games g ON g.id = m.external_id
LEFT JOIN nba.player_game_stats ps ON ps.game_id = g.id AND ps.player_id = k.player_id
"""


def pick_result(r: dict, now: datetime) -> str | None:
    """Resultado de una pierna a partir de los datos reales; None si todavía falta información."""
    if r["status"] in CANCELLED:
        return "void"
    spec = LegSpec(r["market"], r["side"], r["line"], r["team"], r["stat"], r["player_id"])
    if spec.market != "player":
        return "won" if settle(spec, r["home_total"], r["away_total"]) else "lost"
    if r["seconds_played"] is not None:
        if r["seconds_played"] == 0:
            return "void"  # no jugó: las casas anulan la apuesta
        value = STAT_VALUE[spec.stat](r)
        return "won" if settle(spec, r["home_total"], r["away_total"], value) else "lost"
    if r["game_has_stats"]:
        return "void"  # hay estadísticas del partido pero no del jugador: no jugó
    if now - r["starts_at"] > PLAYER_STATS_GRACE:
        return "void"  # la API nunca publicó estadísticas de este partido
    return None  # todavía esperando estadísticas


def performance_filters(include_preseason: bool = False, **_) -> tuple[str, str, dict]:
    """Por defecto el rendimiento no cuenta la pretemporada (el modelo se ajusta distinto en ella)."""
    if include_preseason:
        return "", "", {}
    picks = "AND NOT EXISTS (SELECT 1 FROM nba.v_games g WHERE g.id = m.external_id AND g.phase = 'preseason')"
    parlays = """
    AND NOT EXISTS (
        SELECT 1 FROM core.parlay_legs l JOIN core.picks pk ON pk.id = l.pick_id
        JOIN core.matches pm ON pm.id = pk.match_id JOIN nba.v_games g ON g.id = pm.external_id
        WHERE l.parlay_id = p.id AND g.phase = 'preseason'
    )"""
    return picks, parlays, {}
