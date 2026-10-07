"""Operaciones de NBA para la CLI y el scheduler: sincronización, lesiones y carga de temporadas."""

import logging
from datetime import datetime, timedelta, timezone

import psycopg

from app.db import connect
from app.sports.nba.config import CURRENT_SEASON
from app.sports.nba.ingest import jobs

log = logging.getLogger(__name__)


def backfill(season: str) -> str:
    """Carga una temporada completa: equipos, partidos y estadísticas."""
    with connect() as conn, jobs.client() as api:
        jobs.ingest_teams(conn, api, season)
        jobs.ingest_games(conn, api, season)
        jobs.ingest_game_stats(conn, api, season)
        return f"{jobs.format_summary(jobs.summary(conn))}\nSolicitudes usadas: {api.requests_made}"


def sync(season: str = CURRENT_SEASON) -> None:
    """Temporada en curso: equipos, partidos, estadísticas de lo terminado, momios y reporte de lesiones."""
    with connect() as conn, jobs.client() as api:
        jobs.ingest_teams(conn, api, season)
        jobs.ingest_games(conn, api, season)
        jobs.ingest_game_stats(conn, api, season)
        jobs.ingest_odds(conn, api)
        log.info("nba: sync terminado; solicitudes usadas: %d", api.requests_made)
        sync_injuries(conn)


def pregame_sync(within: timedelta) -> None:
    """En NBA la corrida previa a los partidos es una sincronización completa (como en GorgoNBAParlays)."""
    sync()


def odds() -> str:
    with connect() as conn, jobs.client() as api:
        run = jobs.ingest_odds(conn, api)
    return f"Momios NBA: {run.received} recibidos, {run.written} observaciones nuevas"


def injuries() -> str:
    from app.sports.nba.ingest.injuries import ingest_injuries

    with connect() as conn:
        result = ingest_injuries(conn, datetime.now(timezone.utc))
    return "Sin reporte oficial reciente (no se publica en pretemporada)" if result is None else f"Reporte de lesiones NBA: {result}"


def sync_injuries(conn: psycopg.Connection) -> None:
    """Reporte oficial de lesiones (no usa cuota de la API). Sólo con partidos oficiales próximos."""
    from app.sports.nba.ingest.injuries import ingest_injuries

    now = datetime.now(timezone.utc)
    upcoming = conn.execute(
        "SELECT 1 FROM nba.v_games WHERE phase <> 'preseason' AND status = 'NS' AND starts_at BETWEEN %s AND %s LIMIT 1",
        (now, now + timedelta(hours=36)),
    ).fetchone()
    if not upcoming:
        log.info("lesiones: sin partidos oficiales en las próximas 36 h; no se busca reporte")
        return
    with conn.transaction():
        run_id = conn.execute(
            "INSERT INTO core.ingest_runs (sport, job) VALUES ('nba', 'injuries') RETURNING id"
        ).fetchone()["id"]
    try:
        result = ingest_injuries(conn, now) or {"entries": 0}
        status, error = "success", None
    except Exception as exc:
        log.exception("lesiones: falló la descarga o lectura del reporte")
        result, status, error = {"entries": 0}, "failed", f"{type(exc).__name__}: {exc}"
    with conn.transaction():
        conn.execute(
            "UPDATE core.ingest_runs SET status = %s, rows_written = %s, error = %s, finished_at = now() WHERE id = %s",
            (status, result["entries"], error, run_id),
        )
