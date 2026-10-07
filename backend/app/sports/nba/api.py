"""Rutas de NBA para la interfaz (montadas en /api/nba): día, piernas, recalcular, plantel y bajas.

Los días son en hora local (LOCAL_TIMEZONE); con los horarios NBA coinciden con la fecha en hora del Este
de nba.games.game_date, con la que se guardan el reporte de lesiones y las correcciones manuales.
"""

from datetime import date
from typing import Literal

import psycopg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.parlays import group_parlays
from app.api.refresh import refresh_days
from app.db import connect
from app.sports.nba.sport import SPORT

router = APIRouter(prefix="/api/nba", tags=["NBA"])


def meta(conn: psycopg.Connection) -> dict:
    """Estado de la sincronización de NBA (para el encabezado)."""
    runs = conn.execute(
        """
        SELECT DISTINCT ON (job) job, status, started_at, finished_at, error
        FROM core.ingest_runs WHERE sport = 'nba' ORDER BY job, started_at DESC
        """
    ).fetchall()
    last = conn.execute(
        """
        SELECT (SELECT max(last_seen_at) FROM nba.odds_history) AS odds_at,
               (SELECT max(evaluated_at) FROM core.picks WHERE sport = 'nba') AS picks_at,
               (SELECT max(settled_at) FROM core.picks WHERE sport = 'nba') AS settled_at,
               (SELECT max(report_at) FROM nba.injury_reports) AS injuries_at
        """
    ).fetchone()
    return {
        "key": SPORT.key,
        "label": SPORT.label,
        "model_version": SPORT.model_version,
        "sync": {r["job"]: {k: r[k] for k in ("status", "started_at", "finished_at", "error")} for r in runs},
        "last_odds_at": last["odds_at"],
        "last_picks_at": last["picks_at"],
        "last_settled_at": last["settled_at"],
        "last_injury_report_at": last["injuries_at"],
    }


@router.get("/calendar")
def calendar() -> list[dict]:
    """Días con partidos y cuántos (oficiales = sin pretemporada), para navegar entre días con juego."""
    with connect() as conn:
        return conn.execute(
            """
            SELECT m.local_date::text AS date, count(*) AS games,
                   count(*) FILTER (WHERE g.phase <> 'preseason') AS official
            FROM core.matches m JOIN nba.v_games g ON g.id = m.external_id
            WHERE m.sport = 'nba'
            GROUP BY m.local_date ORDER BY m.local_date
            """
        ).fetchall()


GAMES_SQL = """
SELECT g.id, m.id AS match_id, g.starts_at, g.status, g.phase, g.is_finished, g.home_total, g.away_total,
       g.home_team_id, ht.name AS home_name, ht.logo AS home_logo,
       g.away_team_id, at.name AS away_name, at.logo AS away_logo,
       pr.home_points::float AS proj_home, pr.away_points::float AS proj_away,
       pr.p_home_win::float AS proj_p_home, pr.evaluated_at AS proj_at,
       pr.home_missing_pts::float AS home_missing, pr.away_missing_pts::float AS away_missing,
       pr.home_roster_pts::float AS home_roster, pr.away_roster_pts::float AS away_roster, pr.roster_detail,
       EXISTS (SELECT 1 FROM nba.odds_history o WHERE o.game_id = g.id) AS has_odds,
       (SELECT count(*) FROM core.picks k WHERE k.match_id = m.id) AS picks_count
FROM core.matches m
JOIN nba.v_games g ON g.id = m.external_id
JOIN nba.teams ht ON ht.id = g.home_team_id
JOIN nba.teams at ON at.id = g.away_team_id
LEFT JOIN nba.game_projections pr ON pr.game_id = g.id
WHERE m.sport = 'nba' AND m.local_date = %s
ORDER BY g.starts_at, g.id
"""

PARLAYS_SQL = """
SELECT p.id, p.mode, p.n_legs, p.probability::float AS probability, p.odd::float AS odd,
       p.result, p.settled_odd::float AS settled_odd, p.evaluated_at,
       l.position, k.id AS pick_id, m.id AS match_id, m.external_id AS game_id, k.market, l.description,
       l.p_model::float AS p_model, l.odd::float AS leg_odd, k.result AS leg_result
FROM core.parlays p
JOIN core.parlay_legs l ON l.parlay_id = p.id
JOIN core.picks k ON k.id = l.pick_id
JOIN core.matches m ON m.id = k.match_id
WHERE p.sport = 'nba' AND p.day = %s
ORDER BY p.mode, p.n_legs, l.position
"""

LEGS_SQL = """
SELECT k.id, 'nba' AS sport, k.match_id, m.external_id AS game_id, k.market, k.side, k.line::float AS line, k.team,
       k.stat, k.player_id, pl.name AS player_name, k.description, k.p_model::float AS p_model, k.odd::float AS odd,
       k.bookmaker, k.p_market::float AS p_market, k.hits_10, k.games_10, k.hits_25, k.games_25,
       k.result, k.evaluated_at, k.player_status, k.book_odds
FROM core.picks k
JOIN core.matches m ON m.id = k.match_id
LEFT JOIN nba.players pl ON pl.id = k.player_id
WHERE k.sport = 'nba' AND m.local_date = %s
ORDER BY k.p_model DESC
"""

# Bajas del día por partido: estado efectivo (manual o reporte) de jugadores de ambos equipos.
# El equipo del jugador es el del reporte o, si no viene ahí, el de su partido más reciente.
ABSENCES_SQL = """
WITH current_team AS (
    SELECT DISTINCT ON (p.player_id) p.player_id, p.team_id
    FROM nba.player_game_stats p JOIN nba.games g ON g.id = p.game_id
    WHERE g.game_date < %(day)s
    ORDER BY p.player_id, g.game_date DESC
)
SELECT a.player_id, pl.name, COALESCE(e.team_id, ct.team_id) AS team_id, a.status, a.report_status, a.reason,
       a.manual, a.report_at
FROM nba.v_player_availability a
JOIN nba.players pl ON pl.id = a.player_id
LEFT JOIN current_team ct ON ct.player_id = a.player_id
LEFT JOIN nba.v_latest_injury_report l ON l.game_date = a.game_date
LEFT JOIN nba.injury_entries e ON e.report_id = l.report_id AND e.player_id = a.player_id AND e.game_date = a.game_date
WHERE a.game_date = %(day)s AND a.status <> 'available'
ORDER BY CASE a.status WHEN 'out' THEN 0 WHEN 'doubtful' THEN 1 WHEN 'questionable' THEN 2 ELSE 3 END, pl.name
"""

REPORT_SQL = """
SELECT l.report_at, t.team_id, t.submitted
FROM nba.v_latest_injury_report l JOIN nba.injury_report_teams t ON t.report_id = l.report_id AND t.game_date = l.game_date
WHERE l.game_date = %s
"""


def _team(row: dict, side: str) -> dict:
    return {"id": row[f"{side}_team_id"], "name": row[f"{side}_name"], "logo": row[f"{side}_logo"]}


@router.get("/days/{day}")
def day_view(day: date) -> dict:
    with connect() as conn:
        games = conn.execute(GAMES_SQL, (day,)).fetchall()
        parlay_rows = conn.execute(PARLAYS_SQL, (day,)).fetchall()
        absences = conn.execute(ABSENCES_SQL, {"day": day}).fetchall()
        report_rows = conn.execute(REPORT_SQL, (day,)).fetchall()
    report_at = report_rows[0]["report_at"] if report_rows else None
    submitted = {r["team_id"]: r["submitted"] for r in report_rows}

    return {
        "sport": "nba",
        "date": day.isoformat(),
        "games": [
            {
                "id": g["id"],
                "match_id": g["match_id"],
                "starts_at": g["starts_at"],
                "status": g["status"],
                "phase": g["phase"],
                "is_finished": g["is_finished"],
                "home": _team(g, "home"),
                "away": _team(g, "away"),
                "score": {"home": g["home_total"], "away": g["away_total"]} if g["home_total"] is not None else None,
                "projection": (
                    {
                        "home_points": g["proj_home"],
                        "away_points": g["proj_away"],
                        "p_home_win": g["proj_p_home"],
                        "evaluated_at": g["proj_at"],
                    }
                    if g["proj_home"] is not None
                    else None
                ),
                "has_odds": g["has_odds"],
                "missing_points": {"home": g["home_missing"] or 0.0, "away": g["away_missing"] or 0.0},
                # Cambios de plantel: ajuste en pts netos perdidos (negativo = ganó) y detalle por lado.
                "roster": {
                    "home": g["home_roster"] or 0.0,
                    "away": g["away_roster"] or 0.0,
                    "detail": g["roster_detail"] or {"home": None, "away": None},
                },
                "absences": [
                    {
                        "player_id": a["player_id"],
                        "name": a["name"],
                        "team": "home" if a["team_id"] == g["home_team_id"] else "away",
                        "status": a["status"],
                        "report_status": a["report_status"],
                        "reason": a["reason"],
                        "manual": a["manual"],
                    }
                    for a in absences
                    if a["team_id"] in (g["home_team_id"], g["away_team_id"])
                ],
                "injury_report": {
                    "report_at": report_at,
                    "pending": [side for side in ("home", "away") if submitted.get(g[f"{side}_team_id"]) is False],
                    "covered": g["home_team_id"] in submitted or g["away_team_id"] in submitted,
                },
                "picks_count": g["picks_count"],
            }
            for g in games
        ],
        "parlays": group_parlays(parlay_rows, "game_id"),
    }


@router.get("/days/{day}/legs")
def day_legs(day: date) -> list[dict]:
    with connect() as conn:
        return conn.execute(LEGS_SQL, (day,)).fetchall()


@router.post("/days/{day}/refresh")
def refresh_day(day: date) -> dict:
    """Recalcula y guarda los picks del día (sólo partidos que aún no empiezan)."""
    return refresh_days(SPORT, [day])


# Rotación de un partido para marcar bajas a mano: jugadores con 3+ partidos oficiales entre
# sus últimos 10 y 12+ minutos de promedio, cuyo equipo actual es uno de los dos del partido.
ROSTER_SQL = """
WITH current_team AS (
    SELECT DISTINCT ON (p.player_id) p.player_id, p.team_id, g.game_date
    FROM nba.player_game_stats p JOIN nba.games g ON g.id = p.game_id
    WHERE g.game_date < %(day)s
    ORDER BY p.player_id, g.game_date DESC
),
recent AS (
    SELECT p.player_id, p.points, p.seconds_played,
           row_number() OVER (PARTITION BY p.player_id ORDER BY g.game_date DESC) AS rn
    FROM nba.player_game_stats p JOIN nba.v_games g ON g.id = p.game_id
    WHERE g.game_date < %(day)s AND g.phase <> 'preseason' AND p.seconds_played > 0
)
SELECT ct.team_id, pl.id AS player_id, pl.name, count(*) AS games,
       round(avg(r.points), 1)::float AS points, round(avg(r.seconds_played) / 60.0, 1)::float AS minutes,
       a.status, a.report_status, a.reason, COALESCE(a.manual, false) AS manual
FROM current_team ct
JOIN recent r ON r.player_id = ct.player_id AND r.rn <= 10
JOIN nba.players pl ON pl.id = ct.player_id
LEFT JOIN nba.v_player_availability a ON a.player_id = ct.player_id AND a.game_date = %(day)s
WHERE ct.team_id IN (%(home)s, %(away)s) AND ct.game_date > %(day)s::date - 200
GROUP BY ct.team_id, pl.id, pl.name, a.status, a.report_status, a.reason, a.manual
HAVING count(*) >= 3 AND avg(r.seconds_played) >= 12 * 60  -- con menos minutos no afecta props ni proyección
ORDER BY ct.team_id, minutes DESC
"""


@router.get("/games/{game_id}/roster")
def game_roster(game_id: int) -> dict:
    with connect() as conn:
        game = conn.execute(
            "SELECT id, game_date, home_team_id, away_team_id, status FROM nba.games WHERE id = %s", (game_id,)
        ).fetchone()
        if not game:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        rows = conn.execute(
            ROSTER_SQL, {"day": game["game_date"], "home": game["home_team_id"], "away": game["away_team_id"]}
        ).fetchall()
        unmatched = conn.execute(
            """
            SELECT e.player_name, e.status, e.team_id FROM nba.injury_entries e
            JOIN nba.v_latest_injury_report l ON l.report_id = e.report_id AND l.game_date = e.game_date
            WHERE e.game_date = %s AND e.player_id IS NULL AND e.team_id IN (%s, %s)
            """,
            (game["game_date"], game["home_team_id"], game["away_team_id"]),
        ).fetchall()
    side = {game["home_team_id"]: "home", game["away_team_id"]: "away"}
    return {
        "game_id": game_id,
        "date": game["game_date"].isoformat(),
        "started": game["status"] != "NS",
        "players": [{**{k: r[k] for k in r if k != "team_id"}, "team": side[r["team_id"]]} for r in rows],
        "unmatched": [{"name": u["player_name"], "status": u["status"], "team": side[u["team_id"]]} for u in unmatched],
    }


class AvailabilityChange(BaseModel):
    date: date
    player_id: int
    # "out" / "available" = corrección manual; None = quitar la corrección (vuelve al reporte).
    status: Literal["out", "available"] | None


@router.put("/availability")
def set_availability(change: AvailabilityChange) -> dict:
    """Guarda una corrección manual y recalcula los picks del día (partidos sin empezar)."""
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM nba.players WHERE id = %s", (change.player_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Jugador no encontrado")
        with conn.transaction():
            if change.status is None:
                conn.execute(
                    "DELETE FROM nba.availability_overrides WHERE game_date = %s AND player_id = %s",
                    (change.date, change.player_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO nba.availability_overrides (game_date, player_id, status) VALUES (%s, %s, %s)
                    ON CONFLICT (game_date, player_id) DO UPDATE SET status = EXCLUDED.status, created_at = now()
                    """,
                    (change.date, change.player_id, change.status),
                )
    return refresh_day(change.date)
