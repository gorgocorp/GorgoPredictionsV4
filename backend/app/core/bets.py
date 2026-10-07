"""Apuestas reales del usuario ("Mis apuestas"): registro, liquidación y resumen.

El boleto guarda los momios de la casa del usuario (p. ej. Caliente, que no está en la API) y una copia
de lo que dijo el modelo. Sólo se registra antes del primer partido. Puede mezclar NBA y fútbol.
"""

import math
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

import psycopg

if TYPE_CHECKING:
    from app.core.sport import Sport

MAX_LEGS = 20  # una jornada completa de la Premier son 10 partidos; de la Champions, 18


class BetError(ValueError):
    """Error de validación con mensaje para el usuario."""


@dataclass(frozen=True)
class LegInput:
    pick_id: int
    odd: float


def settle_bet(stake: float, odd: float, legs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Resultado de un boleto a partir de sus piernas; None si aún hay piernas pendientes.

    `legs`: [{"result": "won"|"lost"|"void"|None, "odd": momio de la pierna}].
    Como en las casas: una pierna perdida pierde el boleto; las anuladas salen del cálculo (momio 1);
    si todas se anulan, se devuelve lo apostado.
    """
    results = [leg["result"] for leg in legs]
    if "lost" in results:
        return {"result": "lost", "settled_odd": odd, "payout": 0.0}
    if None in results:
        return None
    live = [leg for leg in legs if leg["result"] != "void"]
    if not live:
        return {"result": "void", "settled_odd": 1.0, "payout": round(stake, 2)}
    # Sin anuladas se respeta el momio total del boleto (la casa puede redondearlo).
    settled = odd if len(live) == len(legs) else math.prod(leg["odd"] for leg in live)
    return {"result": "won", "settled_odd": round(settled, 3), "payout": round(stake * settled, 2)}


def summarize_bets(bets: list[dict[str, Any]]) -> dict[str, Any]:
    settled = [b for b in bets if b["result"] in ("won", "lost", "void")]
    decided = [b for b in settled if b["result"] in ("won", "lost")]
    staked = sum(b["stake"] for b in settled)
    returned = sum(b["payout"] or 0.0 for b in settled)
    return {
        "bets": len(bets),
        "pending": sum(b["result"] is None for b in bets),
        "won": sum(b["result"] == "won" for b in bets),
        "lost": sum(b["result"] == "lost" for b in bets),
        "void": sum(b["result"] == "void" for b in bets),
        "expected_wins": sum(b["model_probability"] for b in decided),
        "book_expected_wins": sum(1 / b["odd"] for b in decided),
        "staked": round(staked, 2),
        "returned": round(returned, 2),
        "profit": round(returned - staked, 2),
        "roi": (returned - staked) / staked if staked else None,
        "pending_stake": round(sum(b["stake"] for b in bets if b["result"] is None), 2),
    }


def create_bet(
    conn: psycopg.Connection,
    bookmaker: str,
    stake: float,
    legs: list[LegInput],
    now: datetime,
    total_odd: float | None = None,
    note: str | None = None,
) -> int:
    if not bookmaker.strip():
        raise BetError("Escribe el nombre de tu casa de apuestas.")
    if stake <= 0:
        raise BetError("El monto apostado debe ser mayor que 0.")
    if not legs or len(legs) > MAX_LEGS:
        raise BetError(f"Un boleto lleva de 1 a {MAX_LEGS} piernas.")
    if len({leg.pick_id for leg in legs}) != len(legs):
        raise BetError("El boleto tiene la misma pierna repetida.")
    if any(leg.odd <= 1 for leg in legs) or (total_odd is not None and total_odd <= 1):
        raise BetError("Los momios en decimal deben ser mayores que 1.")

    rows = {
        r["id"]: r
        for r in conn.execute(
            """
            SELECT k.id, k.description, k.p_model::float AS p_model, m.starts_at, m.status
            FROM core.picks k JOIN core.matches m ON m.id = k.match_id
            WHERE k.id = ANY(%s)
            """,
            ([leg.pick_id for leg in legs],),
        )
    }
    if len(rows) != len(legs):
        raise BetError("Alguna pierna ya no existe; recarga la página y vuelve a armar el boleto.")
    first_start = min(r["starts_at"] for r in rows.values())
    if first_start <= now or any(r["status"] != "NS" for r in rows.values()):
        raise BetError(
            "Algún partido del boleto ya empezó. Las apuestas se registran antes del primer partido "
            "para que el historial sea honesto."
        )

    odd = total_odd if total_odd is not None else math.prod(leg.odd for leg in legs)
    probability = math.prod(rows[leg.pick_id]["p_model"] for leg in legs)
    with conn.transaction():
        bet_id = conn.execute(
            """
            INSERT INTO core.user_bets (bookmaker, stake, odd, model_probability, note, created_at, first_start)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (bookmaker.strip(), round(stake, 2), round(odd, 3), round(probability, 6), note, now, first_start),
        ).fetchone()["id"]
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO core.user_bet_legs (bet_id, position, pick_id, description, p_model, odd)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    (bet_id, i, leg.pick_id, rows[leg.pick_id]["description"], round(rows[leg.pick_id]["p_model"], 4), round(leg.odd, 3))
                    for i, leg in enumerate(legs, 1)
                ],
            )
    return bet_id


def delete_bet(conn: psycopg.Connection, bet_id: int, now: datetime) -> None:
    bet = conn.execute("SELECT first_start FROM core.user_bets WHERE id = %s", (bet_id,)).fetchone()
    if bet is None:
        raise LookupError("Apuesta no encontrada")
    if bet["first_start"] <= now:
        raise BetError("Sólo se puede borrar antes de que empiece el primer partido.")
    with conn.transaction():
        conn.execute("DELETE FROM core.user_bets WHERE id = %s", (bet_id,))


BET_LEGS_SQL = """
SELECT l.bet_id, l.position, l.pick_id, l.description, l.p_model::float AS p_model, l.odd::float AS odd,
       k.market, k.side, k.line::float AS line, k.team, k.stat, k.result,
       m.external_id, m.competition, m.home_name, m.away_name,
{outcome_columns}
FROM core.user_bet_legs l
JOIN core.picks k ON k.id = l.pick_id
{outcome_joins}
WHERE k.sport = %s AND l.bet_id = ANY(%s)
"""


def bet_legs(conn: psycopg.Connection, sports: Mapping[str, "Sport"], bet_ids: list[int]) -> dict[int, list[dict]]:
    """Piernas de cada apuesta con lo que pasó en realidad, deporte por deporte."""
    legs: dict[int, list[dict]] = defaultdict(list)
    for sport in sports.values():
        query = BET_LEGS_SQL.format(outcome_columns=sport.outcome_columns, outcome_joins=sport.outcome_joins)
        for r in conn.execute(query, (sport.key, bet_ids)):
            legs[r["bet_id"]].append(
                {
                    "position": r["position"],
                    "pick_id": r["pick_id"],
                    "sport": sport.key,
                    "competition": r["competition"],
                    "matchup": sport.matchup(r["home_name"], r["away_name"]),
                    "starts_at": r["starts_at"],
                    "description": r["description"],
                    "p_model": r["p_model"],
                    "odd": r["odd"],
                    "result": r["result"],
                    "outcome": sport.leg_outcome(r),
                }
            )
    for items in legs.values():
        items.sort(key=lambda leg: leg["position"])
    return legs


def list_bets(conn: psycopg.Connection, now: datetime, sports: Mapping[str, "Sport"]) -> dict[str, Any]:
    bets = conn.execute(
        """
        SELECT id, bookmaker, stake::float AS stake, odd::float AS odd, model_probability::float AS model_probability,
               note, created_at, first_start, result, settled_odd::float AS settled_odd, payout::float AS payout, settled_at
        FROM core.user_bets ORDER BY created_at DESC
        """
    ).fetchall()
    legs = bet_legs(conn, sports, [b["id"] for b in bets]) if bets else {}
    items = [
        {
            **b,
            "book_probability": 1 / b["odd"],
            "profit": None if b["result"] is None else round((b["payout"] or 0.0) - b["stake"], 2),
            "can_delete": b["first_start"] > now,
            "legs": legs.get(b["id"], []),
        }
        for b in bets
    ]
    return {"summary": summarize_bets(bets), "items": items}


def settle_user_bets(conn: psycopg.Connection, now: datetime) -> int:
    legs: dict[int, list[dict]] = defaultdict(list)
    meta: dict[int, dict] = {}
    for r in conn.execute(
        """
        SELECT b.id, b.stake::float AS stake, b.odd::float AS bet_odd, l.odd::float AS odd, k.result
        FROM core.user_bets b
        JOIN core.user_bet_legs l ON l.bet_id = b.id
        JOIN core.picks k ON k.id = l.pick_id
        WHERE b.result IS NULL
        """
    ):
        legs[r["id"]].append(r)
        meta[r["id"]] = r
    updates = []
    for bet_id, rows in legs.items():
        outcome = settle_bet(meta[bet_id]["stake"], meta[bet_id]["bet_odd"], rows)
        if outcome:
            updates.append({"id": bet_id, "now": now, **outcome})
    if updates:
        with conn.cursor() as cur:
            cur.executemany(
                """
                UPDATE core.user_bets SET result = %(result)s, settled_odd = %(settled_odd)s, payout = %(payout)s,
                                          settled_at = %(now)s
                WHERE id = %(id)s
                """,
                updates,
            )
    return len(updates)
