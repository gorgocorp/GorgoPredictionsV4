"""Qué ve cada plan.

Una cuenta con plan completo (admin o suscripción vigente) ve todo. Una cuenta free ve:
- los parlays gratis de cada día y deporte: los de máxima probabilidad de 2 y 3 piernas que registra el sistema
  (la configuración estándar; los mismos que mide el historial);
- los parlays destacados (el de la semana y el de fin de semana, app/core/featured.py), de todos los tamaños;
- cualquier pierna de un partido que ya empezó o ya no está programado (no se puede apostar: es evidencia, no un
  pick). Un partido con horario por definir (TBD) sigue programado.
Lo demás no sale de la API: la interfaz recibe sólo un aviso de que existe y lo muestra difuminado.

Los parlays en prueba (ADMIN_ONLY_MODES: el parlay con valor, app/core/value.py) sólo los ve admin: no le llegan a
nadie más en la página del día, el historial ni el rendimiento.
"""

from datetime import datetime

import psycopg

from app.core.featured import FEATURED_MODES
from app.core.value import MODE as VALUE_MODE

FREE_MODE = "prob"
FREE_SIZES = (2, 3)
ADMIN_ONLY_MODES = (VALUE_MODE,)


def hidden_modes(admin: bool) -> tuple[str, ...]:
    """Modos de parlay que la cuenta no ve en ningún lado."""
    return () if admin else ADMIN_ONLY_MODES


def is_free_parlay(mode: str, n_legs: int) -> bool:
    return (mode == FREE_MODE and n_legs in FREE_SIZES) or mode in FEATURED_MODES


def free_visible_picks(conn: psycopg.Connection, pick_ids: list[int], now: datetime) -> set[int]:
    """De `pick_ids`, las piernas que ve una cuenta free."""
    if not pick_ids:
        return set()
    rows = conn.execute(
        """
        SELECT k.id
        FROM core.picks k JOIN core.matches m ON m.id = k.match_id
        WHERE k.id = ANY(%(ids)s)
          AND (m.starts_at <= %(now)s OR m.state <> 'scheduled'
               OR EXISTS (SELECT 1 FROM core.parlay_legs l JOIN core.parlays p ON p.id = l.parlay_id
                          WHERE l.pick_id = k.id
                            AND ((p.mode = %(mode)s AND p.n_legs = ANY(%(sizes)s)) OR p.mode = ANY(%(featured)s))))
        """,
        {"ids": pick_ids, "now": now, "mode": FREE_MODE, "sizes": list(FREE_SIZES), "featured": list(FEATURED_MODES)},
    )
    return {r["id"] for r in rows}


def visible_legs(conn: psycopg.Connection, legs: list[dict], full: bool, now: datetime) -> list[dict]:
    """Filas de core.picks (con su `id`) que ve la cuenta."""
    if full:
        return legs
    visible = free_visible_picks(conn, [leg["id"] for leg in legs], now)
    return [leg for leg in legs if leg["id"] in visible]


def visible_parlays(parlays: list[dict], full: bool, admin: bool = False) -> list[dict]:
    """Parlays del sistema que ve la cuenta (free: sólo los gratis y los destacados; los de prueba, sólo admin)."""
    hidden = hidden_modes(admin)
    return [p for p in parlays if p["mode"] not in hidden and (full or is_free_parlay(p["mode"], p["n_legs"]))]


LOCKED_LEG_KEYS = ("position", "sport", "competition", "matchup", "starts_at")


def lock_legs(conn: psycopg.Connection, legs: dict[int, list[dict]], full: bool, now: datetime) -> dict[int, list[dict]]:
    """Piernas de parlays registrados (historial) con `locked`; a una cuenta free, las que no ve le llegan sin
    el pick: sólo partido y hora."""
    visible = None if full else free_visible_picks(conn, [leg["pick_id"] for items in legs.values() for leg in items], now)
    return {
        key: [
            {**leg, "locked": False}
            if visible is None or leg["pick_id"] in visible
            else {**{k: leg[k] for k in LOCKED_LEG_KEYS}, "locked": True}
            for leg in items
        ]
        for key, items in legs.items()
    }


def gate_projection(game: dict, full: bool, now: datetime, scheduled: tuple[str, ...]) -> dict:
    """La proyección del modelo de un partido; una cuenta free la ve sólo cuando el partido ya empezó.

    `scheduled`: estados del proveedor de un partido por jugar (SCHEDULED en app/sports/<deporte>/matches.py).
    """
    started = game["status"] not in scheduled or game["starts_at"] <= now
    locked = not full and not started and game["projection"] is not None
    return {**game, "projection": None if locked else game["projection"], "projection_locked": locked}
