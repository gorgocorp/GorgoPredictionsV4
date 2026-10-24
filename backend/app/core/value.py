"""Parlay con valor, en prueba y sólo para admin: piernas en las que el momio de la casa paga más que el justo del
modelo y del mercado.

Por qué (docs/MODELOS.md, revisión del 23-oct-2026): cuando sólo el modelo ve valor, lo que pasa queda donde decía el
mercado; el valor aparece cuando la casa paga más que el precio justo del mercado (CLV positivo). Este parlay se arma
sólo con piernas así, con una regla fija desde SINCE, y se mide hacia adelante con resultados y CLV antes de mostrarlo a
nadie más.

Se publica una vez por día y deporte y ya no cambia: lo que se publicó es lo que se mide.
- Cuándo: desde PUBLISH_HOUR (hora local) del día anterior a sus partidos. Si a esa hora el scheduler no corre o no hay
  N_LEGS piernas que cumplan la regla, se reintenta en cada corrida mientras queden partidos del día.
- Cada pierna:
  - es de un partido del día que empieza al menos MIN_LEAD después de publicarse (así su cierre, a lo más CLOSE_MAX
    antes del inicio, queda al menos MIN_WINDOW después y su CLV se puede medir), a lo más una por partido;
  - es de un mercado de partido (no props: la víspera nadie conoce las alineaciones) que cotiza completo el mercado
    (probabilidad sin comisión de Pinnacle o, si no lo cotiza, la mediana de las casas);
  - tiene momio de BOOKMAKER, el que se mide, menor a MAX_ODD;
  - tiene valor para el modelo y para el mercado: momio × la menor de las dos probabilidades > 1;
  - no se aleja más de MAX_PRICE_GAP del precio justo del mercado: más lejos casi siempre es un dato malo.
- De las que cumplen, las N_LEGS que más se prometen (la menor entre modelo y mercado); a igual, la que paga más.
"""

import logging
import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import psycopg

from app.config import BOOKMAKER, LOCAL_TZ
from app.core.evidence import summarize
from app.core.sport import Sport
from app.core.tracking import CLOSE_MAX, MIN_WINDOW

log = logging.getLogger(__name__)

MODE = "value"  # core.parlays.mode
N_LEGS = 2
PUBLISH_HOUR = 20  # hora local del día anterior a los partidos
MAX_ODD = 3.0
MAX_PRICE_GAP = 0.20
MIN_LEAD = CLOSE_MAX + MIN_WINDOW
# Primer día de la prueba: la regla no cambia desde aquí (si cambiara, lo nuevo se cuenta aparte).
SINCE = date(2026, 10, 24)


def due_days(now: datetime) -> list[date]:
    """Días cuyo parlay ya toca: hoy (por si no salió la víspera) y, desde PUBLISH_HOUR, mañana."""
    local = now.astimezone(LOCAL_TZ)
    today = local.date()
    days = [today, today + timedelta(days=1)] if local.hour >= PUBLISH_HOUR else [today]
    return [d for d in days if d >= SINCE]


@dataclass(frozen=True)
class ValueLeg:
    pick_id: int
    match_id: int
    market: str
    description: str
    p_model: float
    p_market: float
    odd: float  # momio de BOOKMAKER: con el que se mide
    starts_at: datetime

    @property
    def probability(self) -> float:
        """Lo que se promete: la menor entre el modelo y el mercado."""
        return min(self.p_model, self.p_market)

    @property
    def edge(self) -> float:
        """Valor esperado por unidad con lo que se promete: momio × probabilidad − 1."""
        return self.odd * self.probability - 1


def eligible(leg: ValueLeg) -> bool:
    return leg.odd < MAX_ODD and leg.edge > 0 and abs(leg.odd * leg.p_market - 1) <= MAX_PRICE_GAP


def select_legs(legs: Iterable[ValueLeg], n: int = N_LEGS) -> list[ValueLeg]:
    """Las `n` piernas con valor que más se prometen (a igual, la que paga más), una por partido."""
    chosen: list[ValueLeg] = []
    matches: set[int] = set()
    for leg in sorted(filter(eligible, legs), key=lambda x: (-x.probability, -x.odd, x.starts_at, x.pick_id)):
        if leg.match_id in matches:
            continue
        chosen.append(leg)
        matches.add(leg.match_id)
        if len(chosen) == n:
            break
    return chosen


CANDIDATES_SQL = """
SELECT k.id, k.match_id, k.market, k.description, k.p_model::float AS p_model, k.p_market::float AS p_market,
       k.odd::float AS odd, m.starts_at
FROM core.picks k JOIN core.matches m ON m.id = k.match_id
WHERE k.sport = %(sport)s AND m.state = 'scheduled' AND m.local_date = %(day)s AND m.starts_at >= %(earliest)s
  AND k.result IS NULL AND k.market <> 'player' AND k.p_market IS NOT NULL AND k.odd IS NOT NULL
  AND k.player_status IS DISTINCT FROM 'questionable'
"""


def load_candidates(conn: psycopg.Connection, sport: Sport, day: date, now: datetime) -> list[ValueLeg]:
    rows = conn.execute(CANDIDATES_SQL, {"sport": sport.key, "day": day, "earliest": now + MIN_LEAD}).fetchall()
    return [
        ValueLeg(r["id"], r["match_id"], r["market"], r["description"], r["p_model"], r["p_market"], r["odd"], r["starts_at"])
        for r in rows
    ]


def _insert(conn: psycopg.Connection, sport: Sport, day: date, legs: list[ValueLeg], now: datetime) -> bool:
    """Guarda el parlay; False si otro proceso ya publicó el de ese día."""
    with conn.transaction():
        row = conn.execute(
            """
            INSERT INTO core.parlays (sport, day, mode, n_legs, probability, odd, bookmaker, model_version, evaluated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT parlays_slot_unique DO NOTHING
            RETURNING id
            """,
            (sport.key, day, MODE, len(legs), round(math.prod(leg.probability for leg in legs), 6),
             round(math.prod(leg.odd for leg in legs), 3), BOOKMAKER, sport.model_version, now),
        ).fetchone()
        if row is None:
            return False
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO core.parlay_legs (parlay_id, pick_id, position, description, p_model, odd, p_market)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (row["id"], leg.pick_id, i, leg.description, round(leg.p_model, 4), leg.odd, round(leg.p_market, 4))
                    for i, leg in enumerate(legs, 1)
                ],
            )
    return True


def publish_value(conn: psycopg.Connection, sport: Sport, now: datetime | None = None) -> int:
    """Publica los parlays con valor del deporte que ya tocan y aún no existen; devuelve cuántos escribió."""
    now = now or datetime.now(timezone.utc)
    written = 0
    for day in due_days(now):
        exists = conn.execute(
            "SELECT 1 FROM core.parlays WHERE sport = %s AND day = %s AND mode = %s LIMIT 1", (sport.key, day, MODE)
        ).fetchone()
        if exists:
            continue
        legs = select_legs(load_candidates(conn, sport, day, now))
        if len(legs) < N_LEGS:
            log.info("%s con valor %s: sólo %d piernas cumplen la regla; se reintenta en la siguiente corrida",
                     sport.key, day, len(legs))
            continue
        if _insert(conn, sport, day, legs, now):
            log.info("%s con valor %s: publicado (%s)", sport.key, day, " + ".join(leg.description for leg in legs))
            written += 1
    return written


# ---------------------------------------------------------------- medición

PARLAYS_SQL = """
SELECT p.id, p.n_legs, p.probability::float AS probability, p.odd::float AS odd, p.result,
       p.settled_odd::float AS settled_odd
FROM core.parlays p
WHERE p.sport = %(sport)s AND p.mode = %(mode)s AND p.day >= %(since)s
"""

LEGS_SQL = """
SELECT l.odd::float AS odd, p.evaluated_at AS published_at, k.p_sharp::float AS p_sharp, k.evaluated_at, m.starts_at
FROM core.parlays p
JOIN core.parlay_legs l ON l.parlay_id = p.id
JOIN core.picks k ON k.id = l.pick_id
JOIN core.matches m ON m.id = k.match_id
WHERE p.sport = %(sport)s AND p.mode = %(mode)s AND p.day >= %(since)s AND k.result IN ('won', 'lost')
"""


def legs_clv(legs: Iterable[dict]) -> dict:
    """CLV de las piernas publicadas ya jugadas: momio publicado × probabilidad sin comisión de Pinnacle al cierre − 1.

    Mismas reglas que tracking.clv_data: una pierna cuenta si su última evaluación fue a lo más CLOSE_MAX antes del
    inicio, Pinnacle cotizaba ahí su mercado completo y entre la publicación y esa evaluación hubo al menos MIN_WINDOW.
    """
    clv: list[float] = []
    excluded = {"no_close": 0, "no_reference": 0, "short_window": 0}
    for leg in legs:
        if leg["starts_at"] - leg["evaluated_at"] > CLOSE_MAX:
            excluded["no_close"] += 1
        elif leg["p_sharp"] is None:
            excluded["no_reference"] += 1
        elif leg["evaluated_at"] - leg["published_at"] < MIN_WINDOW:
            excluded["short_window"] += 1
        else:
            clv.append(leg["odd"] * leg["p_sharp"] - 1)
    return {
        "n": len(clv),
        "avg": statistics.mean(clv) if clv else None,
        "median": statistics.median(clv) if clv else None,
        "beat_rate": sum(c > 0 for c in clv) / len(clv) if clv else None,
        "excluded": excluded,
    }


def value_performance(conn: psycopg.Connection, sport: Sport) -> dict:
    """La prueba del parlay con valor de un deporte: su regla, sus resultados y el CLV de sus piernas."""
    params = {"sport": sport.key, "mode": MODE, "since": SINCE}
    return {
        "since": SINCE.isoformat(),
        "rules": {
            "n_legs": N_LEGS,
            "max_odd": MAX_ODD,
            "max_price_gap": MAX_PRICE_GAP,
            "publish_hour": PUBLISH_HOUR,
            "min_lead_hours": MIN_LEAD.total_seconds() / 3600,
        },
        "record": summarize(conn.execute(PARLAYS_SQL, params).fetchall()),
        "clv": legs_clv(conn.execute(LEGS_SQL, params).fetchall()),
    }


def value_report(conn: psycopg.Connection, sport: Sport) -> str:
    """La prueba en texto, para el reporte de rendimiento de la línea de comandos."""
    d = value_performance(conn, sport)
    r, c = d["record"], d["clv"]
    lines = [f"Parlay con valor (prueba, sólo admin, desde {d['since']}):"]
    if r["parlays"] == 0:
        lines.append("  Todavía no se publica ninguno.")
        return "\n".join(lines)
    roi = "" if r["roi"] is None else f"  ROI={r['roi']:+.1%}"
    lines.append(f"  Parlays: {r['parlays']} ({r['pending']} pendientes)  ganados={r['won']} de {r['settled']}  "
                 f"esperados={r['expected_wins']:.1f}{roi}")
    if c["n"]:
        lines.append(f"  CLV de sus piernas: n={c['n']}  prom.={c['avg']:+.1%}  mediana={c['median']:+.1%}  "
                     f"le ganan al cierre={c['beat_rate']:.1%}")
    else:
        lines.append("  CLV de sus piernas: todavía ninguna medible")
    skipped = c["excluded"]
    if any(skipped.values()):
        lines.append(f"  No cuentan: {skipped['no_close']} sin cierre · {skipped['no_reference']} sin Pinnacle al cierre · "
                     f"{skipped['short_window']} publicadas a menos de 2 h del cierre")
    return "\n".join(lines)
