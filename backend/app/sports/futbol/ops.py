"""Operaciones de fútbol para la CLI y el scheduler: sincronización, bajas, alineaciones y carga de temporadas."""

import logging
from collections.abc import Callable
from datetime import timedelta

from app.db import connect
from app.sports.futbol.config import LEAGUES
from app.sports.futbol.ingest import jobs

log = logging.getLogger(__name__)


def _run_steps(*steps: tuple[str, Callable[[], object]]) -> list[str]:
    """Corre cada paso aunque falle uno anterior (sin detalle siguen haciendo falta bajas y momios).

    Devuelve los que fallaron para reportarlos al final.
    """
    failed = []
    for name, step in steps:
        try:
            step()
        except Exception as exc:
            log.exception("fútbol: %s falló; se sigue con lo demás", name)
            failed.append(f"{name} ({type(exc).__name__})")
    return failed


def _raise_if_failed(failed: list[str]) -> None:
    if failed:
        raise RuntimeError("fútbol: falló " + ", ".join(failed))


def backfill(seasons: list[int], leagues: list[int] | None = None, injuries: bool = True) -> str:
    """Carga temporadas completas: calendario, detalle de partidos terminados y bajas."""
    leagues = leagues or list(LEAGUES)
    with connect() as conn, jobs.client() as api:
        jobs.ensure_leagues(conn, api)
        for season in seasons:
            for league_id in leagues:
                jobs.ingest_fixtures(conn, api, league_id, season)
                if injuries:
                    jobs.ingest_season_injuries(conn, api, league_id, season)
        jobs.ingest_details(conn, api, seasons=seasons)
        return (
            f"{jobs.format_summary(jobs.summary(conn))}\n"
            f"Solicitudes usadas: {api.requests_made} (quedan {api.rate_limit.day_remaining} hoy)"
        )


def sync() -> None:
    """Calendario de la temporada en curso, detalle de lo terminado, bajas y momios."""
    with connect() as conn, jobs.client() as api:
        jobs.ensure_leagues(conn, api)
        for league_id, season in sorted(jobs.current_seasons(conn).items()):
            try:
                jobs.ingest_fixtures(conn, api, league_id, season)
            except Exception:
                log.exception("calendario de la liga %s falló; se sigue con las demás", league_id)
        failed = _run_steps(
            ("detalle", lambda: jobs.ingest_details(conn, api)),
            ("bajas", lambda: jobs.ingest_injuries(conn, api)),
            ("momios", lambda: jobs.ingest_odds(conn, api)),
        )
        log.info("fútbol: sync terminado; solicitudes usadas: %d (quedan %s hoy)", api.requests_made, api.rate_limit.day_remaining)
    _raise_if_failed(failed)


def pregame_sync(within: timedelta) -> None:
    """Corrida ligera antes de un horario de partidos: alineaciones, bajas y momios sólo de lo que empieza pronto."""
    with connect() as conn, jobs.client() as api:
        failed = _run_steps(
            ("alineaciones", lambda: jobs.ingest_lineups(conn, api, within)),
            ("bajas", lambda: jobs.ingest_injuries(conn, api, within)),
            ("momios", lambda: jobs.ingest_odds(conn, api, within)),
        )
        log.info("fútbol: previa terminada; solicitudes usadas: %d", api.requests_made)
    _raise_if_failed(failed)


def closing_sync(within: timedelta) -> None:
    """Lectura de cierre: sólo momios de lo que empieza dentro de `within`."""
    with connect() as conn, jobs.client() as api:
        jobs.ingest_odds(conn, api, within)
        log.info("fútbol: cierre terminado; solicitudes usadas: %d", api.requests_made)


def odds() -> str:
    with connect() as conn, jobs.client() as api:
        run = jobs.ingest_odds(conn, api)
    return f"Momios fútbol: {run.received} recibidos, {run.written} observaciones nuevas"


def injuries() -> str:
    with connect() as conn, jobs.client() as api:
        run = jobs.ingest_injuries(conn, api)
    return f"Bajas fútbol: {run.received} recibidas, {run.written} guardadas"


def lineups(minutes: int) -> str:
    with connect() as conn, jobs.client() as api:
        run = jobs.ingest_lineups(conn, api, timedelta(minutes=minutes))
    return "Sin partidos por empezar en esa ventana" if run is None else f"Alineaciones: {run.written} partidos revisados"
