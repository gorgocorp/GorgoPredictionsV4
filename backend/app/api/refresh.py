"""Recalcular picks desde la interfaz (tras marcar una baja o al pedirlo), por deporte.

El historial y los modelos se guardan en memoria por deporte: recalcular no vuelve a cargar cientos de
miles de filas ni a ajustar los modelos si no llegaron datos nuevos. Un cálculo a la vez por deporte.
"""

import threading
from collections.abc import Iterable
from datetime import date, datetime

import psycopg
from fastapi import HTTPException

from app.config import BOOKMAKER, LOCAL_TZ
from app.core.sport import Sport
from app.core.tracking import record_picks
from app.db import connect

_locks: dict[str, threading.Lock] = {}
_caches: dict[str, dict] = {}


def _models_for(conn: psycopg.Connection, sport: Sport, day: date):
    """(historial, modelos) del deporte para `day`; se recargan sólo si hubo una ingesta nueva."""
    cache = _caches.setdefault(sport.key, {})
    stamp = conn.execute(
        "SELECT max(finished_at) AS t FROM core.ingest_runs WHERE sport = %s AND status = 'success'", (sport.key,)
    ).fetchone()["t"]
    if cache.get("stamp") != stamp or "hist" not in cache:
        cache.clear()
        cache["stamp"] = stamp
        cache["hist"] = sport.load_history(conn)
    hist = cache["hist"]
    # Misma fecha de corte que el scheduler (NBA: el propio día; fútbol: de mañana en adelante, mañana).
    cutoff = sport.models_cutoff(datetime.now(LOCAL_TZ).date(), day)
    key = ("models", cutoff)
    if key not in cache:
        cache[key] = sport.fit_models(hist, cutoff)
    return hist, cache[key]


def record_day(conn: psycopg.Connection, sport: Sport, day: date) -> dict[str, int]:
    hist, models = _models_for(conn, sport, day)
    if not sport.has_matches(hist, day):
        return {"games": 0, "picks": 0, "parlays": 0}
    return record_picks(conn, sport, hist, day, BOOKMAKER, models=models)


def refresh_days(sport: Sport, days: Iterable[date]) -> dict[str, int]:
    """Recalcula y guarda los picks de esos días (sólo partidos que aún no empiezan)."""
    lock = _locks.setdefault(sport.key, threading.Lock())
    if not lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail=f"Ya hay un cálculo de {sport.label} en curso; intenta en unos segundos.")
    totals = {"games": 0, "picks": 0, "parlays": 0, "days": 0}
    try:
        with connect() as conn:
            for day in days:
                totals["days"] += 1
                for k, v in record_day(conn, sport, day).items():
                    totals[k] += v
    finally:
        lock.release()
    return totals
