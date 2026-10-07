"""Historial de parlays como evidencia: resumen de lo que se predijo frente a lo que pasó.

El valor real de cada pierna ("anotó 31", "Terminó América 2-1 Chivas") lo da cada deporte
(`Sport.leg_outcome`). Funciones puras (sin base de datos) para poder probarlas aisladas.
"""

from collections.abc import Iterable
from typing import Any


def summarize(parlays: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Resumen de parlays: aciertos reales vs. esperados por el modelo y unidades a 1 por parlay.

    Cada parlay trae: n_legs, probability, result ('won' | 'lost' | 'void' | None), settled_odd.
    """
    rows = list(parlays)
    settled = [p for p in rows if p["result"] in ("won", "lost")]
    with_odds = [p for p in settled if p["settled_odd"]]
    profit = sum((p["settled_odd"] - 1) if p["result"] == "won" else -1.0 for p in with_odds)

    by_size: dict[int, dict[str, Any]] = {}
    for p in rows:
        size = by_size.setdefault(p["n_legs"], {"n_legs": p["n_legs"], "parlays": 0, "settled": 0, "won": 0, "expected": 0.0})
        size["parlays"] += 1
        if p["result"] in ("won", "lost"):
            size["settled"] += 1
            size["won"] += p["result"] == "won"
            size["expected"] += p["probability"]

    return {
        "parlays": len(rows),
        "settled": len(settled),
        "won": sum(p["result"] == "won" for p in rows),
        "lost": sum(p["result"] == "lost" for p in rows),
        "void": sum(p["result"] == "void" for p in rows),
        "pending": sum(p["result"] is None for p in rows),
        "expected_wins": sum(p["probability"] for p in settled),
        "with_odds": len(with_odds),
        "profit_units": profit if with_odds else None,
        "roi": profit / len(with_odds) if with_odds else None,
        "by_size": [by_size[k] for k in sorted(by_size)],
    }
