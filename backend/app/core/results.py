"""Resultados públicos (/resultados): el registro de los parlays gratis, para quien todavía no tiene cuenta.

Cuentan los parlays que ve cualquier cuenta (app/core/access.py: los de máxima probabilidad de 2 y 3 piernas de cada
día y deporte, y los destacados de la semana y de fin de semana) de SINCE en adelante que prometen en cada pierna la
menor entre el modelo y el mercado: los destacados desde que existen (19-oct-2026) y los del día desde esa misma
noche (bc392af). Los del día que ya se habían congelado con la regla anterior (prometían lo del modelo) no cuentan y
se informan aparte (`excluded`).

SINCE no se mueve: escoger desde cuándo contar según cómo salió sería hacer trampa.

Sólo salen completos los parlays ya liquidados, con lo que de ellos ve una cuenta free. Los que siguen en juego sólo
se cuentan: sus piernas son los picks gratis del día, que piden cuenta.
"""

from collections.abc import Iterable, Mapping
from datetime import date, datetime

import psycopg

from app.core.access import FREE_MODE, FREE_SIZES, lock_legs
from app.core.evidence import parlay_profit, summarize
from app.core.featured import FEATURED_MODES, LEGS_SQL
from app.core.sport import Sport

SINCE = date(2026, 10, 19)

# Tipos de parlay, en el orden en que se muestran: los del día y los destacados.
KINDS = ("daily", *FEATURED_MODES)

# Rangos de la probabilidad prometida por pierna (el último incluye el 100%).
CALIBRATION_EDGES = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)

PARLAYS_SQL = """
SELECT p.id, p.sport, p.day, p.mode, p.n_legs, p.probability::float AS probability, p.odd::float AS odd, p.result,
       p.settled_odd::float AS settled_odd, p.bookmaker, p.evaluated_at, min(m.starts_at) AS first_start,
       bool_and(l.p_market IS NOT NULL) AS market_cap
FROM core.parlays p
JOIN core.parlay_legs l ON l.parlay_id = p.id
JOIN core.picks k ON k.id = l.pick_id
JOIN core.matches m ON m.id = k.match_id
WHERE p.day >= %(since)s
  AND ((p.mode = %(free_mode)s AND p.n_legs = ANY(%(free_sizes)s)) OR p.mode = ANY(%(featured)s))
GROUP BY p.id
ORDER BY p.day DESC, p.sport, p.mode, p.n_legs
"""


def kind(mode: str) -> str:
    return "daily" if mode == FREE_MODE else mode


def promised(leg: dict) -> float:
    """Lo que prometió la pierna: la menor entre el modelo y el mercado."""
    return leg["p_model"] if leg["p_market"] is None else min(leg["p_model"], leg["p_market"])


def calibration(legs: Iterable[dict]) -> tuple[dict, list[dict]]:
    """Piernas liquidadas: total y por rango de lo prometido, prometido contra real.

    Cada pick cuenta una vez aunque esté en varios parlays (los tamaños se arman uno sobre otro).
    """
    unique: dict[int, dict] = {}
    for leg in legs:
        if leg.get("result") in ("won", "lost"):
            unique.setdefault(leg["pick_id"], leg)
    settled = [(promised(leg), leg["result"] == "won") for leg in unique.values()]
    total = {
        "settled": len(settled),
        "won": sum(won for _, won in settled),
        "promised": sum(p for p, _ in settled) / len(settled) if settled else None,
    }
    bins = []
    last = len(CALIBRATION_EDGES) - 2
    for i, (lo, hi) in enumerate(zip(CALIBRATION_EDGES, CALIBRATION_EDGES[1:])):
        grp = [(p, won) for p, won in settled if lo <= p < hi or (i == last and p == hi)]
        if grp:
            bins.append({"lo": lo, "hi": hi, "n": len(grp), "promised": sum(p for p, _ in grp) / len(grp),
                         "actual": sum(won for _, won in grp) / len(grp)})
    return total, bins


def _legs(conn: psycopg.Connection, sports: Mapping[str, Sport], parlays: list[dict], now: datetime) -> dict[int, list[dict]]:
    legs: dict[int, list[dict]] = {}
    for key, sport in sports.items():
        ids = [p["id"] for p in parlays if p["sport"] == key]
        if not ids:
            continue
        query = LEGS_SQL.format(outcome_columns=sport.outcome_columns, outcome_joins=sport.outcome_joins)
        for r in conn.execute(query, (ids,)):
            legs.setdefault(r["parlay_id"], []).append(
                {
                    "pick_id": r["pick_id"],
                    "position": r["position"],
                    "sport": key,
                    "competition": r["competition"],
                    "matchup": sport.matchup(r["home_name"], r["away_name"]),
                    "starts_at": r["starts_at"],
                    "market": r["market"],
                    "description": r["description"],
                    "p_model": r["p_model"],
                    "p_market": r["p_market"],
                    "odd": r["odd"],
                    "result": r["result"],
                    "outcome": sport.leg_outcome(r),
                }
            )
    # Lo que ve una cuenta free (de parlays liquidados, todo: sus partidos ya terminaron).
    return lock_legs(conn, legs, False, now)


def results_data(
    conn: psycopg.Connection,
    sports: Mapping[str, Sport],
    now: datetime,
    sport: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Contador, rendimiento por tipo y por mes, calibración de las piernas y una página de los parlays liquidados
    (del más reciente al más antiguo). `sport` filtra todo."""
    rows = conn.execute(
        PARLAYS_SQL,
        {"since": SINCE, "free_mode": FREE_MODE, "free_sizes": list(FREE_SIZES), "featured": list(FEATURED_MODES)},
    ).fetchall()
    if sport is not None:
        rows = [r for r in rows if r["sport"] == sport]
    counted = [r for r in rows if r["market_cap"]]
    settled = [r for r in counted if r["result"] is not None]
    legs = _legs(conn, sports, settled, now) if settled else {}
    legs_total, bins = calibration(leg for items in legs.values() for leg in items)

    groups = [
        {"sport": s, "kind": k, "summary": summarize(grp)}
        for s in sports
        for k in KINDS
        if (grp := [r for r in counted if r["sport"] == s and kind(r["mode"]) == k])
    ]
    months = sorted({r["day"].strftime("%Y-%m") for r in counted}, reverse=True)
    return {
        "since": SINCE.isoformat(),
        "summary": summarize(counted),
        "excluded": len(rows) - len(counted),
        "groups": groups,
        "months": [{"month": m, "summary": summarize(r for r in counted if r["day"].strftime("%Y-%m") == m)} for m in months],
        "legs": legs_total,
        "calibration": bins,
        "total": len(settled),
        "items": [
            {
                **{k: r[k] for k in ("id", "sport", "day", "mode", "n_legs", "probability", "odd", "result",
                                     "settled_odd", "bookmaker", "evaluated_at", "first_start")},
                "kind": kind(r["mode"]),
                "profit": parlay_profit(r),
                "legs": [{k: v for k, v in leg.items() if k != "pick_id"} for leg in legs.get(r["id"], [])],
            }
            for r in settled[offset : offset + limit]
        ],
    }
