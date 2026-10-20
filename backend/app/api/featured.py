"""Parlays destacados (/api/featured): el de la semana y el de fin de semana, con su contador de aciertos.

Los arma y publica el scheduler (app/core/featured.py). Pide sesión (se monta con esa dependencia en app/api/main.py);
lo que ve cada plan lo decide app/core/access.py (hoy los destacados los ve cualquier cuenta).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import current_viewer
from app.config import LOCAL_TZ
from app.core.access import visible_parlays
from app.core.accounts import Viewer
from app.core.featured import featured_data
from app.db import connect
from app.sports import all_sports

router = APIRouter(tags=["Destacados"])


def _now() -> datetime:
    return datetime.now(LOCAL_TZ)


@router.get("/api/featured")
def featured(sport: str, viewer: Viewer = Depends(current_viewer)) -> dict:
    s = all_sports().get(sport)
    if s is None:
        raise HTTPException(status_code=404, detail=f"Deporte desconocido: {sport}")
    if s.featured_excluded_markets is None:
        raise HTTPException(status_code=404, detail=f"{s.label} todavía no tiene parlays de la semana.")
    with connect() as conn:
        data = featured_data(conn, s, _now())
    for window in (*data["current"], *data["past"]):
        window["parlays"] = visible_parlays(window["parlays"], viewer.full)
    return data
