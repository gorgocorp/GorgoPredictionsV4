"""Rutas de fútbol para la interfaz (montadas en /api/futbol): día, jornada o rango de fechas, piernas,
recalcular, plantel y bajas. Los días son en hora local (LOCAL_TIMEZONE), igual que futbol.fixtures.match_date.

Todas piden sesión (se montan con esa dependencia en app/api/main.py); recalcular y marcar bajas, además, admin.
Lo que ve una cuenta free: app/core/access.py.
"""

from datetime import date, datetime
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import admin_viewer, current_viewer
from app.api.parlays import group_parlays
from app.api.refresh import refresh_days
from app.config import LOCAL_TZ
from app.core.access import gate_projection, visible_legs, visible_parlays
from app.core.accounts import Viewer
from app.db import connect
from app.sports.futbol.matches import SCHEDULED
from app.sports.futbol.sport import SPORT

router = APIRouter(prefix="/api/futbol", tags=["Fútbol"])


def meta(conn: psycopg.Connection) -> dict:
    """Estado de la sincronización de fútbol (para el encabezado)."""
    runs = conn.execute(
        """
        SELECT DISTINCT ON (job) job, status, started_at, finished_at, error
        FROM core.ingest_runs WHERE sport = 'futbol' ORDER BY job, started_at DESC
        """
    ).fetchall()
    last = conn.execute(
        """
        SELECT (SELECT max(last_seen_at) FROM futbol.odds_history) AS odds_at,
               (SELECT max(evaluated_at) FROM core.picks WHERE sport = 'futbol') AS picks_at,
               (SELECT max(settled_at) FROM core.picks WHERE sport = 'futbol') AS settled_at,
               (SELECT max(fetched_at) FROM futbol.injuries) AS injuries_at
        """
    ).fetchone()
    leagues = conn.execute(
        "SELECT id, name, country, logo, current_season FROM futbol.leagues ORDER BY country = 'World', name"
    ).fetchall()
    return {
        "key": SPORT.key,
        "label": SPORT.label,
        "model_version": SPORT.model_version,
        "sync": {r["job"]: {k: r[k] for k in ("status", "started_at", "finished_at", "error")} for r in runs},
        "last_odds_at": last["odds_at"],
        "last_picks_at": last["picks_at"],
        "last_settled_at": last["settled_at"],
        "last_injuries_at": last["injuries_at"],
        "leagues": leagues,
    }


@router.get("/calendar")
def calendar() -> list[dict]:
    """Días con partidos (hora local) y cuántos, para navegar entre días con juego."""
    with connect() as conn:
        return conn.execute(
            """
            SELECT match_date::text AS date, count(*) AS games
            FROM futbol.fixtures WHERE status NOT IN ('PST', 'CANC', 'ABD', 'AWD', 'WO')
            GROUP BY match_date ORDER BY match_date
            """
        ).fetchall()


# Partidos de un día, de un rango de fechas o de una jornada (liga + ronda de la temporada en curso).
SLATE_FILTER = """
f.match_date BETWEEN %(desde)s AND %(hasta)s
AND (%(league)s::int IS NULL OR f.league_id = %(league)s)
AND (%(jornada)s::text IS NULL OR (f.round = %(jornada)s AND f.season = %(season)s))
"""

GAMES_SQL = """
SELECT f.id, m.id AS match_id, f.match_date, f.starts_at, f.status, f.elapsed, f.is_finished, f.round, f.referee,
       f.venue, f.ft_home, f.ft_away, f.goals_home, f.goals_away, f.ht_home, f.ht_away, f.pen_home, f.pen_away,
       f.league_id, l.name AS league_name, l.country AS league_country, l.logo AS league_logo,
       f.home_team_id, ht.name AS home_name, ht.logo AS home_logo,
       f.away_team_id, at.name AS away_name, at.logo AS away_logo,
       pr.home_goals::float AS proj_home, pr.away_goals::float AS proj_away,
       pr.p_home::float AS p_home, pr.p_draw::float AS p_draw, pr.p_away::float AS p_away,
       pr.p_over25::float AS p_over25, pr.p_btts::float AS p_btts, pr.top_scores,
       pr.home_cards::float AS proj_home_cards, pr.away_cards::float AS proj_away_cards,
       pr.lineups AS proj_lineups, pr.evaluated_at AS proj_at,
       EXISTS (SELECT 1 FROM futbol.odds_history o WHERE o.fixture_id = f.id) AS has_odds,
       EXISTS (SELECT 1 FROM futbol.fixture_lineups lu WHERE lu.fixture_id = f.id) AS has_lineups,
       (SELECT count(*) FROM core.picks k WHERE k.match_id = m.id) AS picks_count
FROM futbol.v_fixtures f
JOIN core.matches m ON m.sport = 'futbol' AND m.external_id = f.id
JOIN futbol.leagues l ON l.id = f.league_id
JOIN futbol.teams ht ON ht.id = f.home_team_id
JOIN futbol.teams at ON at.id = f.away_team_id
LEFT JOIN futbol.fixture_projections pr ON pr.fixture_id = f.id
WHERE """ + SLATE_FILTER + """
ORDER BY f.starts_at, l.name, f.id
"""

PARLAYS_SQL = """
SELECT p.id, p.mode, p.n_legs, p.probability::float AS probability, p.odd::float AS odd,
       p.result, p.settled_odd::float AS settled_odd, p.evaluated_at,
       l.position, k.id AS pick_id, m.id AS match_id, m.external_id AS fixture_id, k.market, l.description,
       l.p_model::float AS p_model, l.odd::float AS leg_odd, k.result AS leg_result
FROM core.parlays p
JOIN core.parlay_legs l ON l.parlay_id = p.id
JOIN core.picks k ON k.id = l.pick_id
JOIN core.matches m ON m.id = k.match_id
WHERE p.sport = 'futbol' AND p.day = %s
ORDER BY p.mode, p.n_legs, l.position
"""

LEGS_SQL = """
SELECT k.id, 'futbol' AS sport, k.match_id, f.id AS fixture_id, f.league_id, k.market, k.side, k.line::float AS line,
       k.team, k.stat, k.player_id, pl.name AS player_name, k.description, k.p_model::float AS p_model,
       k.odd::float AS odd, k.bookmaker, k.p_market::float AS p_market, k.hits_10, k.games_10, k.hits_25, k.games_25,
       k.result, k.evaluated_at, k.player_status, k.book_odds
FROM core.picks k
JOIN core.matches m ON m.id = k.match_id
JOIN futbol.fixtures f ON f.id = m.external_id
LEFT JOIN futbol.players pl ON pl.id = k.player_id
WHERE k.sport = 'futbol' AND """ + SLATE_FILTER + """
ORDER BY k.p_model DESC
"""

# Bajas de cada partido del día: estado efectivo (manual o API). Sin equipo en la API
# (corrección manual), se usa el del último partido del jugador.
ABSENCES_SQL = """
SELECT a.fixture_id, a.player_id, pl.name, a.status, a.report_status, a.reason, a.manual,
       COALESCE(a.team_id, (SELECT p.team_id FROM futbol.fixture_player_stats p JOIN futbol.fixtures x ON x.id = p.fixture_id
                            WHERE p.player_id = a.player_id ORDER BY x.starts_at DESC LIMIT 1)) AS team_id
FROM futbol.v_player_availability a
JOIN futbol.players pl ON pl.id = a.player_id
JOIN futbol.fixtures f ON f.id = a.fixture_id
WHERE """ + SLATE_FILTER + """ AND a.status <> 'available'
ORDER BY a.status, pl.name
"""


def _team(row: dict, side: str) -> dict:
    return {"id": row[f"{side}_team_id"], "name": row[f"{side}_name"], "logo": row[f"{side}_logo"]}


def _games(conn: psycopg.Connection, filt: dict, viewer: Viewer) -> list[dict]:
    """Partidos con proyección (si la cuenta la ve), bajas y conteo de piernas para un filtro de SLATE_FILTER."""
    now = datetime.now(LOCAL_TZ)
    games = conn.execute(GAMES_SQL, filt).fetchall()
    absences = conn.execute(ABSENCES_SQL, filt).fetchall()

    by_fixture: dict[int, list[dict]] = {}
    for a in absences:
        by_fixture.setdefault(a["fixture_id"], []).append(a)

    def projection(g: dict) -> dict | None:
        if g["proj_home"] is None:
            return None
        return {
            "home_goals": g["proj_home"],
            "away_goals": g["proj_away"],
            "p_home": g["p_home"],
            "p_draw": g["p_draw"],
            "p_away": g["p_away"],
            "p_over25": g["p_over25"],
            "p_btts": g["p_btts"],
            "top_scores": g["top_scores"],
            "home_cards": g["proj_home_cards"],
            "away_cards": g["proj_away_cards"],
            "lineups": g["proj_lineups"],
            "evaluated_at": g["proj_at"],
        }

    return [
        gate_projection({
            "id": g["id"],
            "match_id": g["match_id"],
            "match_date": g["match_date"],
            "starts_at": g["starts_at"],
            "status": g["status"],
            "elapsed": g["elapsed"],
            "is_finished": g["is_finished"],
            "round": g["round"],
            "referee": g["referee"],
            "venue": g["venue"],
            "league": {"id": g["league_id"], "name": g["league_name"], "country": g["league_country"], "logo": g["league_logo"]},
            "home": _team(g, "home"),
            "away": _team(g, "away"),
            # Marcador a 90' (con el que se liquida) y, si hubo tiempo extra o penales, el final.
            "score": (
                {
                    "home": g["ft_home"] if g["ft_home"] is not None else g["goals_home"],
                    "away": g["ft_away"] if g["ft_away"] is not None else g["goals_away"],
                    "final_home": g["goals_home"],
                    "final_away": g["goals_away"],
                    "pen_home": g["pen_home"],
                    "pen_away": g["pen_away"],
                    "ht_home": g["ht_home"],
                    "ht_away": g["ht_away"],
                }
                if g["goals_home"] is not None
                else None
            ),
            "projection": projection(g),
            "has_odds": g["has_odds"],
            "has_lineups": g["has_lineups"],
            "picks_count": g["picks_count"],
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
                for a in by_fixture.get(g["id"], [])
                if a["team_id"] in (g["home_team_id"], g["away_team_id"])
            ],
        }, viewer.full, now, SCHEDULED)
        for g in games
    ]


def _day_filter(day: date) -> dict:
    return {"desde": day, "hasta": day, "league": None, "jornada": None, "season": None}


@router.get("/days/{day}")
def day_view(day: date, viewer: Viewer = Depends(current_viewer)) -> dict:
    with connect() as conn:
        games = _games(conn, _day_filter(day), viewer)
        parlay_rows = conn.execute(PARLAYS_SQL, (day,)).fetchall()
    parlays = visible_parlays(group_parlays(parlay_rows, "fixture_id"), viewer.full)
    return {"sport": "futbol", "date": day.isoformat(), "games": games, "parlays": parlays}


@router.get("/days/{day}/legs")
def day_legs(day: date, viewer: Viewer = Depends(current_viewer)) -> list[dict]:
    with connect() as conn:
        return visible_legs(conn, conn.execute(LEGS_SQL, _day_filter(day)).fetchall(), viewer.full, datetime.now(LOCAL_TZ))


@router.post("/days/{day}/refresh", dependencies=[Depends(admin_viewer)])
def refresh_day(day: date) -> dict:
    """Recalcula y guarda los picks del día (sólo partidos que aún no empiezan)."""
    return refresh_days(SPORT, [day])


# ---------------------------------------------------------------- varios días (jornada o rango)

MAX_SLATE_DAYS = 14  # los momios llegan de 1 a 14 días antes


def slate_range(desde: date | None, hasta: date | None) -> tuple[date, date]:
    """Valida un rango de fechas para armar parlays de varios días."""
    if desde is None or hasta is None:
        raise HTTPException(status_code=422, detail="Indica desde y hasta, o una liga y su jornada.")
    if hasta < desde:
        raise HTTPException(status_code=422, detail="La fecha final es anterior a la inicial.")
    if (hasta - desde).days >= MAX_SLATE_DAYS:
        raise HTTPException(status_code=422, detail=f"El rango puede ser de hasta {MAX_SLATE_DAYS} días.")
    return desde, hasta


def _slate_filter(conn: psycopg.Connection, desde: date | None, hasta: date | None, league: int | None, jornada: str | None) -> dict:
    if jornada is None:
        desde, hasta = slate_range(desde, hasta)
        return {"desde": desde, "hasta": hasta, "league": league, "jornada": None, "season": None}
    if league is None:
        raise HTTPException(status_code=422, detail="Para elegir una jornada indica también la liga.")
    row = conn.execute(
        """
        SELECT l.current_season AS season, min(f.match_date) AS desde, max(f.match_date) AS hasta
        FROM futbol.leagues l JOIN futbol.fixtures f ON f.league_id = l.id AND f.season = l.current_season
        WHERE l.id = %s AND f.round = %s
        GROUP BY l.current_season
        """,
        (league, jornada),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Esa jornada no existe en la temporada en curso.")
    return {"desde": row["desde"], "hasta": row["hasta"], "league": league, "jornada": jornada, "season": row["season"]}


@router.get("/rounds")
def rounds(league: int) -> dict:
    """Jornadas de la temporada en curso de una liga, con sus fechas y cuántos partidos faltan."""
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT f.round, min(f.match_date) AS desde, max(f.match_date) AS hasta, count(*) AS games,
                   count(*) FILTER (WHERE f.status = 'NS' AND f.starts_at > now()) AS open,
                   count(*) FILTER (WHERE f.status IN ('FT', 'AET', 'PEN')) AS finished
            FROM futbol.fixtures f JOIN futbol.leagues l ON l.id = f.league_id AND f.season = l.current_season
            WHERE f.league_id = %s AND f.round IS NOT NULL
              AND f.status NOT IN ('PST', 'CANC', 'ABD', 'AWD', 'WO')
            GROUP BY f.round
            ORDER BY min(f.starts_at)
            """,
            (league,),
        ).fetchall()
    # Jornada en curso: la primera con al menos la mitad de sus partidos por jugar (una jornada vieja
    # con un partido reprogramado no cuenta); si no hay, la primera con alguno por jugar.
    current = next(
        (r["round"] for r in rows if r["open"] * 2 >= r["games"]),
        next((r["round"] for r in rows if r["open"] > 0), rows[-1]["round"] if rows else None),
    )
    return {"league": league, "current": current, "rounds": rows}


@router.get("/slate")
def slate(
    desde: date | None = None,
    hasta: date | None = None,
    league: int | None = None,
    jornada: str | None = None,
    viewer: Viewer = Depends(current_viewer),
) -> dict:
    """Partidos de varios días: un rango de fechas o una jornada completa de una liga."""
    with connect() as conn:
        filt = _slate_filter(conn, desde, hasta, league, jornada)
        games = _games(conn, filt, viewer)
    return {"desde": filt["desde"], "hasta": filt["hasta"], "league": league, "jornada": jornada, "games": games}


@router.get("/slate/legs")
def slate_legs(
    desde: date | None = None,
    hasta: date | None = None,
    league: int | None = None,
    jornada: str | None = None,
    viewer: Viewer = Depends(current_viewer),
) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(LEGS_SQL, _slate_filter(conn, desde, hasta, league, jornada)).fetchall()
        return visible_legs(conn, rows, viewer.full, datetime.now(LOCAL_TZ))


@router.post("/slate/refresh", dependencies=[Depends(admin_viewer)])
def slate_refresh(desde: date | None = None, hasta: date | None = None, league: int | None = None, jornada: str | None = None) -> dict:
    """Recalcula los días de la jornada o del rango que tienen partidos por empezar."""
    with connect() as conn:
        filt = _slate_filter(conn, desde, hasta, league, jornada)
        days = [
            r["match_date"]
            for r in conn.execute(
                "SELECT DISTINCT f.match_date FROM futbol.fixtures f WHERE "
                + SLATE_FILTER
                + " AND f.status = 'NS' AND f.starts_at > now() ORDER BY 1",
                filt,
            )
        ]
    return refresh_days(SPORT, days)


# ---------------------------------------------------------------- plantel y bajas

# Jugadores de los dos equipos para marcar bajas a mano: los que jugaron al menos 2 de los
# últimos 6 partidos de su equipo, con su estado (API o manual) y si están en la alineación.
ROSTER_SQL = """
WITH team_fx AS (
    SELECT t.team_id, f.id AS fixture_id,
           row_number() OVER (PARTITION BY t.team_id ORDER BY f.starts_at DESC) AS rn
    FROM futbol.fixtures f
    CROSS JOIN LATERAL (VALUES (f.home_team_id), (f.away_team_id)) AS t (team_id)
    WHERE t.team_id IN (%(home)s, %(away)s) AND f.status IN ('FT', 'AET', 'PEN') AND f.starts_at < %(starts)s
),
recent AS (
    SELECT p.player_id, p.team_id, p.minutes, p.goals, p.assists, p.is_substitute, p.position
    FROM futbol.fixture_player_stats p
    JOIN team_fx x ON x.fixture_id = p.fixture_id AND x.team_id = p.team_id AND x.rn <= 6
)
SELECT r.team_id, pl.id AS player_id, pl.name,
       mode() WITHIN GROUP (ORDER BY r.position) AS position,
       count(*) FILTER (WHERE r.minutes > 0) AS games,
       count(*) FILTER (WHERE r.minutes > 0 AND NOT r.is_substitute) AS starts,
       COALESCE(round(avg(r.minutes) FILTER (WHERE r.minutes > 0)), 0)::int AS minutes,
       COALESCE(sum(r.goals), 0)::int AS goals, COALESCE(sum(r.assists), 0)::int AS assists,
       a.status, a.report_status, a.reason, COALESCE(a.manual, false) AS manual, lu.is_starter
FROM recent r
JOIN futbol.players pl ON pl.id = r.player_id
LEFT JOIN futbol.v_player_availability a ON a.fixture_id = %(fixture)s AND a.player_id = r.player_id
LEFT JOIN futbol.fixture_lineups lu ON lu.fixture_id = %(fixture)s AND lu.player_id = r.player_id
GROUP BY r.team_id, pl.id, pl.name, a.status, a.report_status, a.reason, a.manual, lu.is_starter
HAVING count(*) FILTER (WHERE r.minutes > 0) >= 2
ORDER BY r.team_id, starts DESC, minutes DESC
"""


@router.get("/fixtures/{fixture_id}/roster")
def fixture_roster(fixture_id: int) -> dict:
    with connect() as conn:
        f = conn.execute(
            "SELECT id, match_date, starts_at, home_team_id, away_team_id, status FROM futbol.fixtures WHERE id = %s",
            (fixture_id,),
        ).fetchone()
        if not f:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        rows = conn.execute(
            ROSTER_SQL,
            {"fixture": fixture_id, "home": f["home_team_id"], "away": f["away_team_id"], "starts": f["starts_at"]},
        ).fetchall()
        listed = {r["player_id"] for r in rows}
        others = conn.execute(
            """
            SELECT i.player_id, pl.name, i.team_id, i.status, i.reason
            FROM futbol.injuries i JOIN futbol.players pl ON pl.id = i.player_id
            WHERE i.fixture_id = %s ORDER BY pl.name
            """,
            (fixture_id,),
        ).fetchall()
        has_lineups = conn.execute("SELECT 1 FROM futbol.fixture_lineups WHERE fixture_id = %s LIMIT 1", (fixture_id,)).fetchone()
    side = {f["home_team_id"]: "home", f["away_team_id"]: "away"}
    return {
        "fixture_id": fixture_id,
        "date": f["match_date"].isoformat(),
        "started": f["status"] != "NS",
        "lineups": bool(has_lineups),
        "players": [{**{k: r[k] for k in r if k != "team_id"}, "team": side[r["team_id"]]} for r in rows],
        # Bajas de la API de jugadores que no aparecen entre los recientes (lesiones largas).
        "others": [
            {"player_id": o["player_id"], "name": o["name"], "status": o["status"], "reason": o["reason"], "team": side[o["team_id"]]}
            for o in others
            if o["player_id"] not in listed and o["team_id"] in side
        ],
    }


class AvailabilityChange(BaseModel):
    fixture_id: int
    player_id: int
    # "out" / "available" = corrección manual; None = quitar la corrección (vuelve a la API).
    status: Literal["out", "available"] | None


@router.put("/availability", dependencies=[Depends(admin_viewer)])
def set_availability(change: AvailabilityChange) -> dict:
    """Guarda una corrección manual y recalcula los picks del día (partidos sin empezar)."""
    with connect() as conn:
        if not conn.execute("SELECT 1 FROM futbol.players WHERE id = %s", (change.player_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Jugador no encontrado")
        fixture = conn.execute("SELECT match_date FROM futbol.fixtures WHERE id = %s", (change.fixture_id,)).fetchone()
        if not fixture:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        with conn.transaction():
            if change.status is None:
                conn.execute(
                    "DELETE FROM futbol.availability_overrides WHERE fixture_id = %s AND player_id = %s",
                    (change.fixture_id, change.player_id),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO futbol.availability_overrides (fixture_id, player_id, status) VALUES (%s, %s, %s)
                    ON CONFLICT (fixture_id, player_id) DO UPDATE SET status = EXCLUDED.status, created_at = now()
                    """,
                    (change.fixture_id, change.player_id, change.status),
                )
    return refresh_day(fixture["match_date"])
