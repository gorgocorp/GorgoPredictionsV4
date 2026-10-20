"""Parlays destacados: el de la semana y el de fin de semana, de 2 a 5 piernas.

Cada uno se arma una sola vez, al llegar su hora de publicación, con las piernas que el scheduler ya registró en
core.picks para los partidos de su ventana, y ya no cambia: lo que se publicó es lo que se mide. Viven en core.parlays
con su propio modo y `day` = primer día de su ventana, así que se liquidan y salen en el historial y en el rendimiento
como los demás.

| Destacado | Se publica            | Partidos           |
|-----------|-----------------------|--------------------|
| week      | lunes, PUBLISH_HOUR   | lunes a domingo    |
| weekend   | jueves, PUBLISH_HOUR  | viernes a domingo  |

Si el scheduler no corre a esa hora, se publica en su siguiente corrida mientras dure la ventana, sólo con los
partidos que aún no empiezan.

Cada pierna:
- es de un partido de la ventana que aún no empieza, a lo más una por partido, y de un mercado de partido (el deporte
  excluye los suyos en `featured_excluded_markets`: al publicarse nadie conoce las alineaciones de días después);
- la cotiza alguna casa a MIN_ODD o más (el momio de BOOKMAKER si la cotiza; si no, el mejor de las otras casas de
  PRICE_BOOKMAKERS): así es una apuesta real y no "menos de 10.5 goles", que nadie publica o pagan a 1.01. Si ese
  momio se aleja más de MAX_PRICE_GAP del precio justo del mercado, casi siempre es un dato malo y no entra;
- el modelo y el mercado sin comisión le dan al menos MIN_PROB, y se promete la menor de las dos. Escoger lo que el
  modelo ve más seguro escoge justo donde es más optimista que el mercado: en las piernas de los parlays de máxima
  probabilidad del 9 al 19-oct-2026 el modelo decía 87%, el mercado 78% y acertaron 79%;
- a lo más MAX_PER_MARKET piernas del mismo mercado, para que no sean cinco "menos de 4.5 goles".

Los tamaños se arman uno sobre otro: el de 3 piernas es el de 2 más la siguiente mejor.
"""

import logging
import math
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

import psycopg

from app.config import BOOKMAKER, LOCAL_TZ
from app.core.evidence import summarize
from app.core.sport import Sport

log = logging.getLogger(__name__)

SIZES = (2, 3, 4, 5)
PUBLISH_HOUR = 8  # hora local
MIN_ODD = 1.30
MIN_PROB = 0.60
MAX_PER_MARKET = 2
MAX_PRICE_GAP = 0.20
# Semanas anteriores que muestra la página (el contador de aciertos cuenta todas).
PAST_WEEKS = 8


@dataclass(frozen=True)
class Window:
    mode: str  # core.parlays.mode
    label: str
    publish_weekday: int  # 0 = lunes
    first_day: int  # primer día de partidos, en días desde el lunes
    days: int

    def dates(self, monday: date) -> tuple[date, date]:
        start = monday + timedelta(days=self.first_day)
        return start, start + timedelta(days=self.days - 1)

    def publish_at(self, monday: date) -> datetime:
        return datetime.combine(monday + timedelta(days=self.publish_weekday), time(PUBLISH_HOUR), LOCAL_TZ)


WINDOWS = (
    Window("week", "Parlay de la semana", publish_weekday=0, first_day=0, days=7),
    Window("weekend", "Parlay de fin de semana", publish_weekday=3, first_day=4, days=3),
)
FEATURED_MODES = tuple(w.mode for w in WINDOWS)
_BY_MODE = {w.mode: w for w in WINDOWS}


def week_monday(moment: datetime) -> date:
    """Lunes (hora local) de la semana de `moment`."""
    day = moment.astimezone(LOCAL_TZ).date()
    return day - timedelta(days=day.weekday())


def due_windows(now: datetime) -> list[tuple[Window, date, date]]:
    """Destacados cuya hora de publicación ya llegó y cuya ventana sigue abierta: (destacado, primer día, último)."""
    monday = week_monday(now)
    today = now.astimezone(LOCAL_TZ).date()
    due = []
    for w in WINDOWS:
        start, end = w.dates(monday)
        if w.publish_at(monday) <= now and today <= end:
            due.append((w, start, end))
    return due


@dataclass(frozen=True)
class FeaturedLeg:
    pick_id: int
    match_id: int
    market: str
    description: str
    p_model: float
    p_market: float
    odd: float | None  # momio de BOOKMAKER: con el que se mide el parlay
    price: float  # el que cuenta para MIN_ODD: el de BOOKMAKER o, si no la cotiza, el mejor de las otras casas
    starts_at: datetime

    @property
    def probability(self) -> float:
        """Lo que se promete: la menor entre el modelo y el mercado."""
        return min(self.p_model, self.p_market)


def eligible(leg: FeaturedLeg) -> bool:
    return leg.price >= MIN_ODD and leg.probability >= MIN_PROB and abs(leg.price * leg.p_market - 1) <= MAX_PRICE_GAP


def select_legs(legs: Iterable[FeaturedLeg], n: int = max(SIZES)) -> list[FeaturedLeg]:
    """Las `n` mejores piernas, en orden: de la que más se promete a la que menos (a igual probabilidad, la que paga
    más), una por partido y a lo más MAX_PER_MARKET por mercado."""
    chosen: list[FeaturedLeg] = []
    matches: set[int] = set()
    markets: Counter[str] = Counter()
    for leg in sorted(filter(eligible, legs), key=lambda x: (-x.probability, -x.price, x.starts_at, x.pick_id)):
        if leg.match_id in matches or markets[leg.market] >= MAX_PER_MARKET:
            continue
        chosen.append(leg)
        matches.add(leg.match_id)
        markets[leg.market] += 1
        if len(chosen) == n:
            break
    return chosen


CANDIDATES_SQL = """
SELECT k.id, k.match_id, k.market, k.description, k.p_model::float AS p_model, k.p_market::float AS p_market,
       k.odd::float AS odd, k.book_odds, m.starts_at
FROM core.picks k JOIN core.matches m ON m.id = k.match_id
WHERE k.sport = %(sport)s AND m.state = 'scheduled' AND m.starts_at > %(now)s
  AND m.local_date BETWEEN %(start)s AND %(end)s
  AND k.result IS NULL AND k.p_market IS NOT NULL AND NOT (k.market = ANY(%(excluded)s))
  AND k.player_status IS DISTINCT FROM 'questionable'
  AND (k.odd IS NOT NULL OR k.book_odds IS NOT NULL)
"""


def load_candidates(conn: psycopg.Connection, sport: Sport, start: date, end: date, now: datetime) -> list[FeaturedLeg]:
    rows = conn.execute(
        CANDIDATES_SQL,
        {"sport": sport.key, "now": now, "start": start, "end": end, "excluded": list(sport.featured_excluded_markets or ())},
    ).fetchall()
    legs = []
    for r in rows:
        price = r["odd"] or max((float(v) for v in (r["book_odds"] or {}).values()), default=None)
        if price is None:
            continue
        legs.append(
            FeaturedLeg(r["id"], r["match_id"], r["market"], r["description"], r["p_model"], r["p_market"], r["odd"], price,
                        r["starts_at"])
        )
    return legs


class _SlotTaken(Exception):
    """Otro proceso publicó el mismo destacado mientras se armaba este."""


def _insert(conn: psycopg.Connection, sport: Sport, window: Window, start: date, legs: list[FeaturedLeg], now: datetime) -> int:
    written = 0
    with conn.transaction():
        for n in SIZES:
            if len(legs) < n:
                break
            chosen = legs[:n]
            odd = math.prod(leg.odd for leg in chosen) if all(leg.odd for leg in chosen) else None
            row = conn.execute(
                """
                INSERT INTO core.parlays (sport, day, mode, n_legs, probability, odd, bookmaker, model_version, evaluated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT ON CONSTRAINT parlays_slot_unique DO NOTHING
                RETURNING id
                """,
                (sport.key, start, window.mode, n, round(math.prod(leg.probability for leg in chosen), 6),
                 None if odd is None else round(odd, 3), BOOKMAKER, sport.model_version, now),
            ).fetchone()
            if row is None:
                raise _SlotTaken
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO core.parlay_legs (parlay_id, pick_id, position, description, p_model, odd, p_market)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (row["id"], leg.pick_id, i, leg.description, round(leg.p_model, 4), leg.odd, round(leg.p_market, 4))
                        for i, leg in enumerate(chosen, 1)
                    ],
                )
            written += 1
    return written


def publish_featured(conn: psycopg.Connection, sport: Sport, now: datetime | None = None) -> int:
    """Publica los destacados del deporte que ya tocan y aún no existen; devuelve cuántos parlays escribió.

    Un destacado se publica completo (todos los tamaños que alcancen) o no se publica: si no hay al menos dos piernas
    que cumplan las reglas, se vuelve a intentar en la siguiente corrida.
    """
    if sport.featured_excluded_markets is None:
        return 0
    now = now or datetime.now(timezone.utc)
    written = 0
    for window, start, end in due_windows(now):
        exists = conn.execute(
            "SELECT 1 FROM core.parlays WHERE sport = %s AND day = %s AND mode = %s LIMIT 1", (sport.key, start, window.mode)
        ).fetchone()
        if exists:
            continue
        legs = select_legs(load_candidates(conn, sport, start, end, now))
        if len(legs) < min(SIZES):
            log.info("%s %s %s: sólo %d piernas cumplen las reglas; se reintenta en la siguiente corrida",
                     sport.key, window.mode, start, len(legs))
            continue
        try:
            n = _insert(conn, sport, window, start, legs, now)
        except _SlotTaken:
            continue
        log.info("%s %s %s: publicados %d parlays (%d piernas)", sport.key, window.mode, start, n, len(legs))
        written += n
    return written


# ---------------------------------------------------------------- vista

PARLAYS_SQL = """
SELECT p.id, p.day, p.mode, p.n_legs, p.probability::float AS probability, p.odd::float AS odd, p.result,
       p.settled_odd::float AS settled_odd, p.evaluated_at
FROM core.parlays p
WHERE p.sport = %(sport)s AND p.mode = ANY(%(modes)s)
ORDER BY p.day DESC, p.mode, p.n_legs
"""

LEGS_SQL = """
SELECT l.parlay_id, l.position, k.id AS pick_id, k.match_id, m.competition, m.home_name, m.away_name, m.local_date,
       k.market, k.side, k.line::float AS line, k.team, k.stat, l.description, l.p_model::float AS p_model,
       l.p_market::float AS p_market, l.odd::float AS odd, k.book_odds, k.result,
{outcome_columns}
FROM core.parlay_legs l
JOIN core.picks k ON k.id = l.pick_id
{outcome_joins}
WHERE l.parlay_id = ANY(%s)
ORDER BY l.parlay_id, l.position
"""


def _leg(sport: Sport, r: dict) -> dict:
    return {
        "pick_id": r["pick_id"],
        "position": r["position"],
        "sport": sport.key,
        "match_id": r["match_id"],
        "competition": r["competition"],
        "matchup": sport.matchup(r["home_name"], r["away_name"]),
        "starts_at": r["starts_at"],
        "date": r["local_date"].isoformat(),
        "market": r["market"],
        "description": r["description"],
        "p_model": r["p_model"],
        "p_market": r["p_market"],
        "odd": r["odd"],
        "book_odds": r["book_odds"],
        "result": r["result"],
        "outcome": sport.leg_outcome(r),
    }


def _window(w: Window, start: date, parlays: list[dict]) -> dict:
    monday = start - timedelta(days=w.first_day)
    return {
        "mode": w.mode,
        "label": w.label,
        "start": start.isoformat(),
        "end": w.dates(monday)[1].isoformat(),
        "publish_at": w.publish_at(monday).isoformat(),
        "parlays": parlays,
    }


def featured_data(conn: psycopg.Connection, sport: Sport, now: datetime) -> dict:
    """Destacados del deporte: los de esta semana (publicados o por publicar), los de semanas anteriores y el
    contador de aciertos por destacado y tamaño (todas las semanas)."""
    rows = conn.execute(PARLAYS_SQL, {"sport": sport.key, "modes": list(FEATURED_MODES)}).fetchall()
    monday = week_monday(now)
    since = monday - timedelta(weeks=PAST_WEEKS)
    shown = [r for r in rows if r["day"] >= since]
    legs: dict[int, list[dict]] = {}
    if shown:
        query = LEGS_SQL.format(outcome_columns=sport.outcome_columns, outcome_joins=sport.outcome_joins)
        for r in conn.execute(query, ([r["id"] for r in shown],)):
            legs.setdefault(r["parlay_id"], []).append(_leg(sport, r))

    groups: dict[tuple[str, date], list[dict]] = {}
    for r in shown:
        groups.setdefault((r["mode"], r["day"]), []).append(
            {**{k: r[k] for k in ("id", "mode", "n_legs", "probability", "odd", "result", "settled_odd", "evaluated_at")},
             "legs": legs.get(r["id"], [])}
        )
    current = [_window(w, w.dates(monday)[0], groups.pop((w.mode, w.dates(monday)[0]), [])) for w in WINDOWS]
    past = [_window(_BY_MODE[mode], day, parlays) for (mode, day), parlays in groups.items() if day < monday]
    past.sort(key=lambda x: (x["start"], x["mode"]), reverse=True)
    return {
        "sport": sport.key,
        "rules": {"sizes": list(SIZES), "min_odd": MIN_ODD, "min_prob": MIN_PROB, "max_per_market": MAX_PER_MARKET,
                  "publish_hour": PUBLISH_HOUR},
        "current": current,
        "past": past,
        "record": {w.mode: summarize(r for r in rows if r["mode"] == w.mode) for w in WINDOWS},
    }
