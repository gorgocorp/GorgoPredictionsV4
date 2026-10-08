"""Trabajos de ingesta: API-Basketball -> PostgreSQL (esquema nba).

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
from app.sports.nba.config import API_BASE_URL, NBA_LEAGUE_ID
from app.sports.nba.ingest import normalize
from app.sports.nba.matches import sync_matches

log = logging.getLogger(__name__)

SPORT = "nba"
STATS_BATCH_SIZE = 20  # máximo de `ids` por llamada según la documentación
# Las estadísticas se actualizan 30–120 s después; se vuelven a pedir hasta tener
# una descarga hecha al menos este tiempo después del inicio del partido.
STATS_FINAL_AFTER = timedelta(hours=6)
ODDS_WINDOW = timedelta(days=7)


def client() -> ApiSportsClient:
    return ApiSportsClient(API_BASE_URL, timeout=20.0)


def ingest_teams(conn: psycopg.Connection, api: ApiSportsClient, season: str) -> RunStats:
    with ingest_run(conn, api, SPORT, "teams", season=season) as run:
        fetched_at = now_utc()
        raw = api.get("/teams", league=NBA_LEAGUE_ID, season=season)
        run.received = len(raw)
        rows = [normalize.team_row(t, fetched_at) for t in raw if t["id"] in normalize.NBA_FRANCHISE_IDS]
        run.skipped = run.received - len(rows)
        with conn.transaction():
            run.written = upsert(conn, ("nba", "teams"), rows, ["id"])
    return run


def ingest_games(conn: psycopg.Connection, api: ApiSportsClient, season: str) -> RunStats:
    with ingest_run(conn, api, SPORT, "games", season=season) as run:
        fetched_at = now_utc()
        raw = api.get("/games", league=NBA_LEAGUE_ID, season=season)
        run.received = len(raw)
        rows = [normalize.game_row(g, fetched_at) for g in raw if normalize.is_franchise_game(g)]
        run.skipped = run.received - len(rows)
        with conn.transaction():
            run.written = upsert(conn, ("nba", "games"), rows, ["id"])
            sync_matches(conn, [r["id"] for r in rows])
    return run


def _games_needing_stats(conn: psycopg.Connection, season: str | None) -> list[int]:
    return [
        r["id"]
        for r in conn.execute(
            """
            SELECT g.id
            FROM nba.games g
            LEFT JOIN LATERAL (
                SELECT max(fetched_at) AS fetched_at FROM nba.player_game_stats p WHERE p.game_id = g.id
            ) p ON true
            WHERE g.status IN ('FT', 'AOT')
              AND (%(season)s::text IS NULL OR g.season = %(season)s)
              AND (p.fetched_at IS NULL OR p.fetched_at < g.starts_at + %(final_after)s)
            ORDER BY g.starts_at
            """,
            {"season": season, "final_after": STATS_FINAL_AFTER},
        )
    ]


def ingest_game_stats(conn: psycopg.Connection, api: ApiSportsClient, season: str | None = None) -> RunStats:
    """Descarga estadísticas de jugadores y equipos de partidos terminados que no las tienen."""
    with ingest_run(conn, api, SPORT, "game_stats", season=season) as run:
        game_ids = _games_needing_stats(conn, season)
        for start in range(0, len(game_ids), STATS_BATCH_SIZE):
            batch = game_ids[start : start + STATS_BATCH_SIZE]
            ids = "-".join(map(str, batch))
            fetched_at = now_utc()
            raw_players = api.get("/games/statistics/players", ids=ids)
            raw_teams = api.get("/games/statistics/teams", ids=ids)
            run.received += len(raw_players) + len(raw_teams)

            players: dict[int, dict] = {}
            player_stats = []
            for raw in raw_players:
                try:
                    player, stats = normalize.player_rows(raw, fetched_at)
                except normalize.InvalidRecord as exc:
                    log.warning("fila de jugador descartada: %s", exc)
                    run.skipped += 1
                    continue
                if stats["team_id"] not in normalize.NBA_FRANCHISE_IDS:
                    run.skipped += 1
                    continue
                players[player["id"]] = player
                player_stats.append(stats)
            team_stats = [
                normalize.team_stats_row(t, fetched_at)
                for t in raw_teams
                if t["team"]["id"] in normalize.NBA_FRANCHISE_IDS
            ]

            with conn.transaction():
                upsert(conn, ("nba", "players"), list(players.values()), ["id"])
                run.written += upsert(conn, ("nba", "player_game_stats"), player_stats, ["game_id", "player_id"])
                run.written += upsert(conn, ("nba", "team_game_stats"), team_stats, ["game_id", "team_id"])
            log.info("estadísticas: %d/%d partidos", min(start + STATS_BATCH_SIZE, len(game_ids)), len(game_ids))
    return run


def _upcoming_games(conn: psycopg.Connection, now: datetime, window: timedelta) -> list[int]:
    return [
        r["id"]
        for r in conn.execute(
            "SELECT id FROM nba.games WHERE status = 'NS' AND starts_at BETWEEN %s AND %s ORDER BY starts_at",
            (now, now + window),
        )
    ]


def ingest_odds(conn: psycopg.Connection, api: ApiSportsClient, window: timedelta = ODDS_WINDOW) -> RunStats:
    """Momios de los partidos programados dentro de `window` (por defecto, los próximos 7 días), uno por consulta."""
    params = {} if window == ODDS_WINDOW else {"window_minutes": int(window.total_seconds() // 60)}
    with ingest_run(conn, api, SPORT, "odds", **params) as run:
        for game_id in _upcoming_games(conn, now_utc(), window):
            seen_at = now_utc()
            raw = api.get("/odds", game=game_id)
            rows = [row for item in raw for row in normalize.odds_rows(item)]
            run.received += len(rows)
            with conn.transaction():
                run.written += store_odds(conn, "nba", "game_id", run.id, rows, seen_at)
            run.skipped = run.received - run.written
    return run


def summary(conn: psycopg.Connection) -> dict[str, Any]:
    counts = {}
    for table in ("teams", "players", "games", "player_game_stats", "team_game_stats", "odds_history"):
        counts[table] = conn.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(sql.Identifier("nba", table))).fetchone()["n"]
    return counts


def format_summary(counts: dict[str, Any]) -> str:
    return json.dumps(counts, indent=2)
