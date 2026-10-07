"""Trabajos de ingesta: API-Football -> PostgreSQL (esquema futbol).

Cada trabajo registra una fila en core.ingest_runs. Las descargas ocurren fuera de las
transacciones; cada lote se guarda en una transacción corta.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

import psycopg
from psycopg import sql

from app.apisports import ApiSportsClient
from app.core.ingest import RunStats, ingest_run, now_utc, store_odds, upsert
from app.sports.futbol.config import API_BASE_URL, LEAGUES
from app.sports.futbol.engine.odds import USED_BET_IDS
from app.sports.futbol.ingest import normalize
from app.sports.futbol.matches import sync_matches

log = logging.getLogger(__name__)

SPORT = "futbol"
IDS_BATCH_SIZE = 20  # máximo de `ids` por llamada según la documentación
# Las estadísticas se completan después del partido; se vuelven a pedir hasta tener una
# descarga hecha al menos este tiempo después del inicio.
DETAILS_FINAL_AFTER = timedelta(hours=6)
# Partidos sin livescore pueden quedarse en NS hasta 48 h; se revisan los de los últimos días.
STALE_LOOKBACK = timedelta(days=3)
ODDS_WINDOW = timedelta(days=7)
INJURIES_WINDOW = timedelta(days=3)
FINISHED = ("FT", "AET", "PEN")


def client() -> ApiSportsClient:
    return ApiSportsClient(API_BASE_URL, timeout=30.0)


# ---------------------------------------------------------------- ligas y partidos


def ingest_leagues(conn: psycopg.Connection, api: ApiSportsClient) -> RunStats:
    """Competiciones del proyecto con su temporada en curso (una sola llamada)."""
    with ingest_run(conn, api, SPORT, "leagues") as run:
        fetched_at = now_utc()
        raw = api.get("/leagues", current="true")
        run.received = len(raw)
        rows = [normalize.league_row(item, fetched_at) for item in raw if item["league"]["id"] in LEAGUES]
        run.skipped = run.received - len(rows)
        with conn.transaction():
            run.written = upsert(conn, ("futbol", "leagues"), rows, ["id"])
    return run


def ensure_leagues(conn: psycopg.Connection, api: ApiSportsClient, max_age: timedelta = timedelta(hours=20)) -> None:
    row = conn.execute("SELECT count(*) AS n, min(fetched_at) AS oldest FROM futbol.leagues").fetchone()
    if row["n"] < len(LEAGUES) or row["oldest"] < now_utc() - max_age:
        ingest_leagues(conn, api)


def current_seasons(conn: psycopg.Connection) -> dict[int, int]:
    return {
        r["id"]: r["current_season"]
        for r in conn.execute("SELECT id, current_season FROM futbol.leagues WHERE current_season IS NOT NULL")
        if r["id"] in LEAGUES
    }


def ingest_fixtures(conn: psycopg.Connection, api: ApiSportsClient, league_id: int, season: int) -> RunStats:
    """Calendario completo de una competición y temporada (una llamada)."""
    with ingest_run(conn, api, SPORT, "fixtures", league=league_id, season=season) as run:
        fetched_at = now_utc()
        raw = api.get("/fixtures", league=league_id, season=season)
        run.received = len(raw)
        teams, fixtures = {}, []
        for item in raw:
            try:
                for t in normalize.team_rows(item, fetched_at):
                    teams[t["id"]] = t
                fixtures.append(normalize.fixture_row(item, fetched_at))
            except (normalize.InvalidRecord, KeyError) as exc:
                log.warning("partido descartado: %s", exc)
                run.skipped += 1
        with conn.transaction():
            upsert(conn, ("futbol", "teams"), list(teams.values()), ["id"])
            run.written = upsert(conn, ("futbol", "fixtures"), fixtures, ["id"])
            sync_matches(conn, [f["id"] for f in fixtures])
    return run


# ---------------------------------------------------------------- detalle de partidos


def _store_details(conn: psycopg.Connection, raw_items: list[dict], fetched_at: datetime) -> int:
    """Guarda partido, estadísticas, jugadores, eventos y alineaciones de /fixtures?ids=."""
    teams, fixtures, team_stats, players, player_stats, events, lineup_players, lineups = {}, [], [], {}, [], [], {}, []
    for item in raw_items:
        try:
            for t in normalize.team_rows(item, fetched_at):
                teams[t["id"]] = t
            fixture = normalize.fixture_row(item, fetched_at)
        except (normalize.InvalidRecord, KeyError) as exc:
            log.warning("detalle descartado: %s", exc)
            continue
        finished = fixture["status"] in FINISHED
        # Sólo un partido terminado queda con detalle "completo"; los demás se vuelven a pedir.
        fixture["details_fetched_at"] = fetched_at if finished else None
        fixtures.append(fixture)
        team_stats += normalize.team_stats_rows(item, fetched_at)
        ps, stats = normalize.player_stats_rows(item, fetched_at)
        players.update({p["id"]: p for p in ps})
        player_stats += stats
        events += normalize.event_rows(item)
        lp, lr = normalize.lineup_rows(item, fetched_at)
        lineup_players.update({p["id"]: p for p in lp})
        lineups += lr

    ids = [f["id"] for f in fixtures]
    with conn.transaction():
        upsert(conn, ("futbol", "teams"), list(teams.values()), ["id"])
        upsert(conn, ("futbol", "fixtures"), fixtures, ["id"])
        sync_matches(conn, ids)
        upsert(conn, ("futbol", "players"), list(players.values()), ["id"])
        upsert(conn, ("futbol", "players"), [p for pid, p in lineup_players.items() if pid not in players], ["id"], do_nothing=True)
        upsert(conn, ("futbol", "fixture_team_stats"), team_stats, ["fixture_id", "team_id"])
        upsert(conn, ("futbol", "fixture_player_stats"), player_stats, ["fixture_id", "player_id"])
        with_events = sorted({e["fixture_id"] for e in events})
        if with_events:
            conn.execute("DELETE FROM futbol.fixture_events WHERE fixture_id = ANY(%s)", (with_events,))
            upsert(conn, ("futbol", "fixture_events"), events, ["fixture_id", "seq"])
        with_lineups = sorted({r["fixture_id"] for r in lineups})
        if with_lineups:
            conn.execute("DELETE FROM futbol.fixture_lineups WHERE fixture_id = ANY(%s)", (with_lineups,))
            upsert(conn, ("futbol", "fixture_lineups"), lineups, ["fixture_id", "player_id"])
    return len(ids)


def fetch_details(conn: psycopg.Connection, api: ApiSportsClient, fixture_ids: list[int], job: str = "details") -> RunStats:
    with ingest_run(conn, api, SPORT, job, fixtures=len(fixture_ids)) as run:
        for start in range(0, len(fixture_ids), IDS_BATCH_SIZE):
            batch = fixture_ids[start : start + IDS_BATCH_SIZE]
            fetched_at = now_utc()
            raw = api.get("/fixtures", ids="-".join(map(str, batch)))
            run.received += len(raw)
            run.written += _store_details(conn, raw, fetched_at)
            if (start // IDS_BATCH_SIZE) % 10 == 9:
                log.info("detalle: %d/%d partidos", min(start + IDS_BATCH_SIZE, len(fixture_ids)), len(fixture_ids))
        run.skipped = run.received - run.written
    return run


def fixtures_needing_details(conn: psycopg.Connection, now: datetime, seasons: list[int] | None = None) -> list[int]:
    """Terminados sin detalle definitivo, y partidos recientes que siguen sin marcador final."""
    return [
        r["id"]
        for r in conn.execute(
            """
            SELECT id FROM futbol.fixtures
            WHERE (%(seasons)s::int[] IS NULL OR season = ANY(%(seasons)s))
              AND (
                (status = ANY(%(finished)s)
                 AND (details_fetched_at IS NULL OR details_fetched_at < starts_at + %(final_after)s))
                OR (status NOT IN ('FT', 'AET', 'PEN', 'PST', 'CANC', 'ABD', 'AWD', 'WO', 'TBD')
                    AND starts_at BETWEEN %(lookback)s AND %(now)s - interval '2 hours')
              )
            ORDER BY starts_at
            """,
            {
                "seasons": seasons,
                "finished": list(FINISHED),
                "final_after": DETAILS_FINAL_AFTER,
                "lookback": now - STALE_LOOKBACK,
                "now": now,
            },
        )
    ]


def ingest_details(conn: psycopg.Connection, api: ApiSportsClient, seasons: list[int] | None = None) -> RunStats:
    return fetch_details(conn, api, fixtures_needing_details(conn, now_utc(), seasons))


def ingest_lineups(conn: psycopg.Connection, api: ApiSportsClient, within: timedelta) -> RunStats | None:
    """Alineaciones de los partidos que empiezan pronto (la API las publica 20–40 min antes)."""
    now = now_utc()
    ids = [
        r["id"]
        for r in conn.execute(
            "SELECT id FROM futbol.fixtures WHERE status = 'NS' AND starts_at BETWEEN %s AND %s ORDER BY starts_at",
            (now, now + within),
        )
    ]
    if not ids:
        return None
    return fetch_details(conn, api, ids, job="lineups")


# ---------------------------------------------------------------- bajas


def _store_injuries(conn: psycopg.Connection, raw: list[dict], fixture_ids: list[int] | None, fetched_at: datetime) -> int:
    players, rows = {}, []
    known = {
        r["id"]
        for r in conn.execute("SELECT id FROM futbol.fixtures WHERE id = ANY(%s)", ([x["fixture"]["id"] for x in raw],))
    }
    for item in raw:
        parsed = normalize.injury_rows(item, fetched_at)
        if parsed is None or item["fixture"]["id"] not in known:
            continue
        player, row = parsed
        players[player["id"]] = player
        rows.append(row)
    with conn.transaction():
        upsert(conn, ("futbol", "players"), list(players.values()), ["id"], do_nothing=True)
        if fixture_ids:
            conn.execute("DELETE FROM futbol.injuries WHERE fixture_id = ANY(%s)", (fixture_ids,))
        return upsert(conn, ("futbol", "injuries"), rows, ["fixture_id", "player_id"])


def ingest_injuries(conn: psycopg.Connection, api: ApiSportsClient, window: timedelta = INJURIES_WINDOW) -> RunStats:
    """Bajas de los partidos que empiezan dentro de `window` (por defecto, los próximos 3 días)."""
    now = now_utc()
    ids = [
        r["id"]
        for r in conn.execute(
            "SELECT id FROM futbol.fixtures WHERE status = 'NS' AND starts_at BETWEEN %s AND %s ORDER BY starts_at",
            (now - timedelta(hours=1), now + window),
        )
    ]
    with ingest_run(conn, api, SPORT, "injuries", fixtures=len(ids)) as run:
        for start in range(0, len(ids), IDS_BATCH_SIZE):
            batch = ids[start : start + IDS_BATCH_SIZE]
            fetched_at = now_utc()
            raw = api.get("/injuries", ids="-".join(map(str, batch)))
            run.received += len(raw)
            run.written += _store_injuries(conn, raw, batch, fetched_at)
        run.skipped = run.received - run.written
    return run


def ingest_season_injuries(conn: psycopg.Connection, api: ApiSportsClient, league_id: int, season: int) -> RunStats:
    """Bajas de una temporada completa (backfill; una llamada por competición y temporada)."""
    with ingest_run(conn, api, SPORT, "season_injuries", league=league_id, season=season) as run:
        fetched_at = now_utc()
        raw = api.get("/injuries", league=league_id, season=season)
        run.received = len(raw)
        run.written = _store_injuries(conn, raw, None, fetched_at)
        run.skipped = run.received - run.written
    return run


# ---------------------------------------------------------------- momios


def ingest_odds(conn: psycopg.Connection, api: ApiSportsClient, window: timedelta = ODDS_WINDOW) -> RunStats:
    """Momios de las competiciones con partidos dentro de `window` (10 partidos por página).

    Se guardan los de todos sus partidos de los próximos 7 días que vengan en la respuesta.
    """
    now = now_utc()
    targets = conn.execute(
        """
        SELECT league_id, season, array_agg(id) AS ids FROM futbol.fixtures
        WHERE status = 'NS' AND starts_at BETWEEN %(now)s AND %(until)s
        GROUP BY league_id, season
        HAVING min(starts_at) <= %(soon)s
        ORDER BY league_id
        """,
        {"now": now, "until": now + ODDS_WINDOW, "soon": now + window},
    ).fetchall()
    with ingest_run(conn, api, SPORT, "odds", leagues=len(targets)) as run:
        for t in targets:
            open_ids = set(t["ids"])
            seen_at = now_utc()
            raw = api.get_all("/odds", league=t["league_id"], season=t["season"])
            # Sólo partidos por empezar (la API conserva momios de partidos ya jugados) y mercados que se usan.
            rows = [
                row
                for item in raw
                if item["fixture"]["id"] in open_ids
                for row in normalize.odds_rows(item)
                if row["bet_id"] in USED_BET_IDS
            ]
            run.received += len(rows)
            with conn.transaction():
                run.written += store_odds(conn, "futbol", "fixture_id", run.id, rows, seen_at)
        run.skipped = run.received - run.written
    return run


# ---------------------------------------------------------------- resumen


def summary(conn: psycopg.Connection) -> dict[str, Any]:
    counts = {}
    for table in (
        "leagues", "teams", "players", "fixtures", "fixture_team_stats", "fixture_player_stats",
        "fixture_events", "fixture_lineups", "injuries", "odds_history",
    ):
        counts[table] = conn.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier("futbol", table))).fetchone()["n"]
    counts["fixtures_by_season"] = {
        str(r["season"]): {"total": r["n"], "finished": r["finished"], "with_details": r["details"]}
        for r in conn.execute(
            """
            SELECT season, count(*) AS n, count(*) FILTER (WHERE status IN ('FT', 'AET', 'PEN')) AS finished,
                   count(*) FILTER (WHERE details_fetched_at IS NOT NULL) AS details
            FROM futbol.fixtures GROUP BY season ORDER BY season
            """
        )
    }
    return counts


def format_summary(counts: dict[str, Any]) -> str:
    return json.dumps(counts, indent=2, ensure_ascii=False)
