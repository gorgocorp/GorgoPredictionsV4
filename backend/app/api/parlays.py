"""Forma común de los parlays de un día en la API (una fila por pierna -> parlays con sus piernas)."""

from app.core.parlay import MODES
from app.core.value import MODE as VALUE_MODE

# Parlays de un día que registra el sistema: los de cada modo y el parlay con valor (en prueba: sólo lo ve admin,
# app/core/access.py). Los destacados tienen su propia ruta (/api/featured).
DAY_MODES = [*MODES, VALUE_MODE]


def group_parlays(rows: list[dict], match_key: str) -> list[dict]:
    """Filas de PARLAYS_SQL (una por pierna) -> parlays con sus piernas."""
    parlays: dict[int, dict] = {}
    for r in rows:
        p = parlays.setdefault(
            r["id"],
            {
                "id": r["id"],
                "mode": r["mode"],
                "n_legs": r["n_legs"],
                "probability": r["probability"],
                "odd": r["odd"],
                "ev": r["probability"] * r["odd"] - 1 if r["odd"] else None,
                "result": r["result"],
                "settled_odd": r["settled_odd"],
                "evaluated_at": r["evaluated_at"],
                "legs": [],
            },
        )
        p["legs"].append(
            {
                "pick_id": r["pick_id"],
                "match_id": r["match_id"],
                match_key: r[match_key],
                "market": r["market"],
                "description": r["description"],
                "p_model": r["p_model"],
                # Mercado al registrar; con él se promete la menor de las dos (NULL: se promete el modelo).
                "p_market": r["p_market"],
                "odd": r["leg_odd"],
                "result": r["leg_result"],
            }
        )
    return list(parlays.values())
