"""Logos de equipos y ligas servidos desde nuestra API (/api/logos/<deporte>/<tipo>/<id>).

Las respuestas para la interfaz llevan esta ruta en vez de la URL del proveedor, así la página no muestra de dónde
salen los datos. La primera vez se descarga la imagen de la URL guardada en la base y se queda en memoria; el
navegador la guarda una semana. Pide sesión (se monta con esa dependencia en app/api/main.py).
"""

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from psycopg import sql

from app.db import connect

router = APIRouter(prefix="/api/logos", tags=["Logos"])

# (deporte, tipo) -> tabla con columna `logo`. Lista cerrada: la ruta no sirve nada más.
TABLES = {
    ("nba", "teams"): ("nba", "teams"),
    ("futbol", "teams"): ("futbol", "teams"),
    ("futbol", "leagues"): ("futbol", "leagues"),
}
# Sólo imágenes de mapa de bits: un SVG o un HTML servido desde nuestro dominio podría ejecutar código.
IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
BROWSER_CACHE_SECONDS = 7 * 24 * 3600

_cache: dict[tuple[str, str, int], tuple[bytes, str]] = {}


def logo_path(sport: str, kind: str, item_id: int | None, url: str | None) -> str | None:
    """Ruta propia del logo para las respuestas (None si el proveedor no tiene logo)."""
    if not url or item_id is None:
        return None
    return f"/api/logos/{sport}/{kind}/{item_id}"


def _download(url: str) -> tuple[bytes, str]:
    try:
        resp = httpx.get(url, timeout=10.0, follow_redirects=True)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="No se pudo obtener el logo.") from exc
    media_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type not in IMAGE_TYPES:
        raise HTTPException(status_code=502, detail="No se pudo obtener el logo.")
    return resp.content, media_type


@router.get("/{sport}/{kind}/{item_id}")
def logo(sport: str, kind: str, item_id: int) -> Response:
    key = (sport, kind, item_id)
    if key not in _cache:
        table = TABLES.get((sport, kind))
        if table is None:
            raise HTTPException(status_code=404, detail="Logo desconocido.")
        with connect() as conn:
            row = conn.execute(
                sql.SQL("SELECT logo FROM {} WHERE id = %s").format(sql.Identifier(*table)), (item_id,)
            ).fetchone()
        if not row or not row["logo"]:
            raise HTTPException(status_code=404, detail="Logo desconocido.")
        _cache[key] = _download(row["logo"])
    content, media_type = _cache[key]
    return Response(
        content,
        media_type=media_type,
        headers={"Cache-Control": f"private, max-age={BROWSER_CACHE_SECONDS}", "X-Content-Type-Options": "nosniff"},
    )
