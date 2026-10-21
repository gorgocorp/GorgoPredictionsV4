"""Resultados públicos (/api/public/results): el registro de los parlays gratis, sin sesión.

Apagados salvo PUBLIC_RESULTS en el .env (responden 404). Qué cuenta y qué se muestra: app/core/results.py. Como no
piden sesión, cada respuesta se guarda CACHE_SECONDS: la liquidación corre cada pocas horas, así que nadie ve algo
viejo y una visita repetida no llega a la base.
"""

import threading
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app import config
from app.core.results import results_data
from app.db import connect
from app.sports import all_sports

router = APIRouter(prefix="/api/public/results", tags=["Público"])

CACHE_SECONDS = 300
CACHE_MAX = 256
_cache: dict[tuple, tuple[float, dict]] = {}
_lock = threading.Lock()


def _now() -> datetime:
    return datetime.now(config.LOCAL_TZ)


@router.get("/status")
def status() -> dict:
    """Si la página pública está prendida (la pantalla de entrar muestra el enlace)."""
    return {"enabled": config.PUBLIC_RESULTS}


@router.get("")
def results(sport: str | None = None, limit: int = 20, offset: int = 0) -> dict:
    if not config.PUBLIC_RESULTS:
        raise HTTPException(status_code=404, detail="Los resultados públicos todavía no están disponibles.")
    sports = all_sports()
    if sport is not None and sport not in sports:
        raise HTTPException(status_code=404, detail=f"Deporte desconocido: {sport}")
    key = (sport, max(1, min(limit, 50)), max(0, offset))
    with _lock:
        hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]
    with connect() as conn:
        data = results_data(conn, sports, _now(), sport=key[0], limit=key[1], offset=key[2])
    with _lock:
        if len(_cache) >= CACHE_MAX:
            _cache.clear()
        _cache[key] = (time.monotonic(), data)
    return data
