"""Registro de picks, liquidación automática y reporte de rendimiento, para cualquier deporte.

Lo propio de cada deporte (modelos, proyecciones, datos reales de cada pierna, filtros) llega por su
contrato (`app.core.sport.Sport`).
"""

import logging
import math
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import psycopg
from psycopg.types.json import Jsonb

from app.core.bets import settle_user_bets
from app.core.parlay import MODES, PARLAY_SIZES, Candidate, ParlayFilters, build_parlay
from app.core.sport import Sport

log = logging.getLogger(__name__)


def should_store(c: Candidate, sport: Sport) -> bool:
    lo, hi = sport.store_range_priced if (c.odd or c.book_odds) else sport.store_range_unpriced
    return lo <= c.p_model <= hi


def _spec_key(spec) -> tuple:
    line = None if spec.line is None else round(spec.line, 1)
    return (spec.market, spec.side, line, spec.team, spec.stat, spec.player_id)


# El momio de publicación (first_*) se toma la primera vez que la pierna llega con momio y ya no cambia;
# el resto se actualiza en cada corrida hasta que empieza el partido.
UPSERT_PICK = """
INSERT INTO core.picks (sport, match_id, market, side, line, team, stat, player_id, description, p_model, odd,
                        bookmaker, p_market, p_sharp, model_version, first_evaluated_at, evaluated_at,
                        hits_10, games_10, hits_25, games_25, player_status, book_odds,
                        first_odd, first_p_model, first_p_market, first_p_sharp, first_priced_at)
VALUES (%(sport)s, %(match_id)s, %(market)s, %(side)s, %(line)s, %(team)s, %(stat)s, %(player_id)s, %(description)s,
        %(p_model)s, %(odd)s, %(bookmaker)s, %(p_market)s, %(p_sharp)s, %(model_version)s, %(now)s, %(now)s,
        %(hits_10)s, %(games_10)s, %(hits_25)s, %(games_25)s, %(player_status)s, %(book_odds)s,
        %(first_odd)s, %(first_p_model)s, %(first_p_market)s, %(first_p_sharp)s, %(first_priced_at)s)
ON CONFLICT ON CONSTRAINT picks_leg_unique DO UPDATE SET
    first_odd = COALESCE(core.picks.first_odd, EXCLUDED.first_odd),
    first_p_model = CASE WHEN core.picks.first_odd IS NULL THEN EXCLUDED.first_p_model ELSE core.picks.first_p_model END,
    first_p_market = CASE WHEN core.picks.first_odd IS NULL THEN EXCLUDED.first_p_market ELSE core.picks.first_p_market END,
    first_p_sharp = CASE WHEN core.picks.first_odd IS NULL THEN EXCLUDED.first_p_sharp ELSE core.picks.first_p_sharp END,
    first_priced_at = COALESCE(core.picks.first_priced_at, EXCLUDED.first_priced_at),
    description = EXCLUDED.description,
    p_model = EXCLUDED.p_model,
    odd = EXCLUDED.odd,
    bookmaker = EXCLUDED.bookmaker,
    p_market = EXCLUDED.p_market,
    p_sharp = EXCLUDED.p_sharp,
    model_version = EXCLUDED.model_version,
    evaluated_at = EXCLUDED.evaluated_at,
    hits_10 = EXCLUDED.hits_10,
    games_10 = EXCLUDED.games_10,
    hits_25 = EXCLUDED.hits_25,
    games_25 = EXCLUDED.games_25,
    player_status = EXCLUDED.player_status,
    book_odds = EXCLUDED.book_odds,
    result = NULL,
    settled_at = NULL
RETURNING id
"""


def _hit_columns(c: Candidate) -> dict[str, int | None]:
    (h10, n10), (h25, n25) = c.hits if len(c.hits) == 2 else ((None, None), (None, None))
    return {"hits_10": h10, "games_10": n10, "hits_25": h25, "games_25": n25}


def _first_price_columns(row: dict) -> dict:
    """Momio de publicación de la fila: sólo si esta corrida trae momio de la casa (si no, queda NULL)."""
    priced = row["odd"] is not None
    return {
        "first_odd": row["odd"],
        "first_p_model": row["p_model"] if priced else None,
        "first_p_market": row["p_market"] if priced else None,
        "first_p_sharp": row["p_sharp"] if priced else None,
        "first_priced_at": row["now"] if priced else None,
    }


def _match_ids(conn: psycopg.Connection, sport: Sport, external_ids: list[int]) -> dict[int, int]:
    """IDs de core.matches de los partidos del deporte (los registra si faltaran)."""
    sport.sync_matches(conn, external_ids)
    return {
        r["external_id"]: r["id"]
        for r in conn.execute(
            "SELECT id, external_id FROM core.matches WHERE sport = %s AND external_id = ANY(%s)", (sport.key, external_ids)
        )
    }


def record_picks(
    conn: psycopg.Connection,
    sport: Sport,
    hist,
    day: date,
    bookmaker: str,
    now: datetime | None = None,
    models=None,
) -> dict[str, int]:
    """Evalúa el día y guarda piernas y parlays de los partidos que aún no empiezan."""
    now = now or datetime.now(timezone.utc)
    cards = [c for c in sport.generate_day(conn, hist, day, bookmaker, models) if c.starts_at > pd.Timestamp(now)]
    candidates = [c for card in cards for c in card.candidates]
    stored = [c for c in candidates if should_store(c, sport)]

    pick_ids: dict[tuple, int] = {}
    parlays_written = stale = 0
    with conn.transaction():
        match_ids = _match_ids(conn, sport, [card.external_id for card in cards]) if cards else {}
        rows = [
            {
                "sport": sport.key,
                "match_id": match_ids[c.external_id],
                "market": c.spec.market,
                "side": c.spec.side,
                "line": None if c.spec.line is None else round(c.spec.line, 1),
                "team": c.spec.team,
                "stat": c.spec.stat,
                "player_id": c.spec.player_id,
                "description": c.description,
                "p_model": round(c.p_model, 4),
                "odd": c.odd,
                "bookmaker": c.bookmaker,
                "p_market": None if c.p_market is None else round(c.p_market, 4),
                "p_sharp": None if c.p_sharp is None else round(c.p_sharp, 4),
                "model_version": sport.model_version,
                "now": now,
                **_hit_columns(c),
                "player_status": c.player_status,
                "book_odds": Jsonb(c.book_odds) if c.book_odds else None,
            }
            for c in stored
        ]
        rows = [{**r, **_first_price_columns(r)} for r in rows]
        if rows:
            with conn.cursor() as cur:
                cur.executemany(UPSERT_PICK, rows, returning=True)
                for c in stored:
                    pick_ids[(c.external_id, _spec_key(c.spec))] = cur.fetchone()["id"]
                    cur.nextset()

        if cards:
            sport.save_projections(conn, cards, now)

        for mode, (_, filters) in MODES.items():
            for n in PARLAY_SIZES:
                parlays_written += _replace_parlay(conn, sport, day, mode, n, candidates, filters, pick_ids, bookmaker, now)

        # Piernas de partidos abiertos que esta corrida ya no generó (p. ej. su probabilidad salió
        # del rango guardado o el jugador quedó fuera): se borran para no mostrar ni medir datos
        # viejos. Se conservan las que forman parte de un parlay o de una apuesta registrada.
        stale = conn.execute(
            """
            DELETE FROM core.picks k
            WHERE k.match_id = ANY(%s) AND NOT (k.id = ANY(%s))
              AND NOT EXISTS (SELECT 1 FROM core.parlay_legs l WHERE l.pick_id = k.id)
              AND NOT EXISTS (SELECT 1 FROM core.user_bet_legs u WHERE u.pick_id = k.id)
            """,
            (list(match_ids.values()), list(pick_ids.values())),
        ).rowcount
    log.info(
        "%s picks %s: %d partidos abiertos, %d piernas guardadas, %d obsoletas borradas, %d parlays",
        sport.key, day, len(cards), len(rows), stale, parlays_written,
    )
    return {"games": len(cards), "picks": len(rows), "parlays": parlays_written}


def record_upcoming(
    conn: psycopg.Connection, sport: Sport, hist, today: date, days: int, bookmaker: str
) -> dict[str, int]:
    """Registra picks de `today` y los `days - 1` días siguientes; los modelos se ajustan una vez por fecha de corte."""
    totals = {"games": 0, "picks": 0, "parlays": 0}
    fitted: dict[date, object] = {}
    for i in range(days):
        day = today + timedelta(days=i)
        if not sport.has_matches(hist, day):
            continue
        cutoff = sport.models_cutoff(today, day)
        if cutoff not in fitted:
            fitted[cutoff] = sport.fit_models(hist, cutoff)
        for k, v in record_picks(conn, sport, hist, day, bookmaker, models=fitted[cutoff]).items():
            totals[k] += v
    return totals


def _replace_parlay(
    conn: psycopg.Connection,
    sport: Sport,
    day: date,
    mode: str,
    n: int,
    candidates: list[Candidate],
    filters: ParlayFilters,
    pick_ids: dict[tuple, int],
    bookmaker: str,
    now: datetime,
) -> int:
    existing = conn.execute(
        """
        SELECT p.id, bool_or(m.starts_at <= %s) AS frozen
        FROM core.parlays p
        JOIN core.parlay_legs l ON l.parlay_id = p.id
        JOIN core.picks k ON k.id = l.pick_id
        JOIN core.matches m ON m.id = k.match_id
        WHERE p.sport = %s AND p.day = %s AND p.mode = %s AND p.n_legs = %s
        GROUP BY p.id
        """,
        (now, sport.key, day, mode, n),
    ).fetchone()
    if existing and existing["frozen"]:
        return 0
    parlay = build_parlay(candidates, n, mode, filters)
    if existing:
        conn.execute("DELETE FROM core.parlays WHERE id = %s", (existing["id"],))
    if parlay is None:
        return 0
    parlay_id = conn.execute(
        """
        INSERT INTO core.parlays (sport, day, mode, n_legs, probability, odd, bookmaker, model_version, evaluated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """,
        (sport.key, day, mode, n, round(parlay.probability, 6), parlay.odd, bookmaker, sport.model_version, now),
    ).fetchone()["id"]
    with conn.cursor() as cur:
        # Copia de la pierna tal como se predijo (las de partidos posteriores siguen cambiando en picks).
        cur.executemany(
            """
            INSERT INTO core.parlay_legs (parlay_id, pick_id, position, description, p_model, odd)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                (parlay_id, pick_ids[(c.external_id, _spec_key(c.spec))], i, c.description, round(c.p_model, 4), c.odd)
                for i, c in enumerate(parlay.legs, 1)
            ],
        )
    return 1


# ---------------------------------------------------------------- liquidación

SETTLE_SQL = """
SELECT k.id, k.market, k.side, k.line::float AS line, k.team, k.stat, k.player_id,
{outcome_columns}
FROM core.picks k
{outcome_joins}
WHERE k.sport = %(sport)s
  AND k.result IS NULL
  AND m.status = ANY(%(statuses)s)
"""


def settle_all(conn: psycopg.Connection, sports: Iterable[Sport], now: datetime | None = None) -> dict[str, int]:
    """Liquida las piernas de partidos terminados o anulados de cada deporte, y luego parlays y tus apuestas."""
    now = now or datetime.now(timezone.utc)
    updates = []
    for sport in sports:
        query = SETTLE_SQL.format(outcome_columns=sport.outcome_columns, outcome_joins=sport.outcome_joins)
        statuses = list(sport.finished_statuses + sport.cancelled_statuses)
        for r in conn.execute(query, {"sport": sport.key, "statuses": statuses}):
            result = sport.pick_result(r, now)
            if result:
                updates.append({"id": r["id"], "result": result, "now": now})
    with conn.transaction():
        if updates:
            with conn.cursor() as cur:
                cur.executemany("UPDATE core.picks SET result = %(result)s, settled_at = %(now)s WHERE id = %(id)s", updates)
        parlays = _settle_parlays(conn, now)
        bets = settle_user_bets(conn, now)
    log.info("liquidación: %d piernas, %d parlays, %d apuestas tuyas", len(updates), parlays, bets)
    return {"picks": len(updates), "parlays": parlays, "bets": bets}


def _settle_parlays(conn: psycopg.Connection, now: datetime) -> int:
    legs = defaultdict(list)
    for r in conn.execute(
        """
        SELECT p.id, k.result, l.odd::float AS odd
        FROM core.parlays p
        JOIN core.parlay_legs l ON l.parlay_id = p.id
        JOIN core.picks k ON k.id = l.pick_id
        WHERE p.result IS NULL
        """
    ):
        legs[r["id"]].append(r)

    updates = []
    for parlay_id, rows in legs.items():
        results = [r["result"] for r in rows]
        if "lost" in results:
            result = "lost"
        elif None in results:
            continue
        else:
            live = [r for r in rows if r["result"] != "void"]
            result = "won" if live else "void"
        live = [r for r in rows if r["result"] != "void"]
        odd = math.prod(r["odd"] for r in live) if live and all(r["odd"] for r in live) else None
        updates.append({"id": parlay_id, "result": result, "odd": odd, "now": now})
    if updates:
        with conn.cursor() as cur:
            cur.executemany(
                "UPDATE core.parlays SET result = %(result)s, settled_odd = %(odd)s, settled_at = %(now)s WHERE id = %(id)s",
                updates,
            )
    return len(updates)


# ---------------------------------------------------------------- rendimiento

CALIBRATION_BINS = np.round(np.arange(0.5, 1.0001, 0.05), 2)
# El cierre de una pierna es su última evaluación antes del partido (momio y probabilidades de esa corrida). Sólo
# cuenta si esa corrida fue a lo más CLOSE_MAX antes del inicio.
CLOSE_MAX = timedelta(minutes=90)
# Entre la publicación y el cierre debe haber al menos MIN_WINDOW: si no, son la misma foto de los momios y no hay
# movimiento que medir (p. ej. la NBA en pretemporada, con momios sólo una hora antes del partido).
MIN_WINDOW = timedelta(hours=2)
# Precio dudoso: el momio de publicación × la probabilidad justa de ese momento se aleja de 1 más que esto. Una
# diferencia así casi siempre es un dato malo (línea retirada, precio de relleno), no una oportunidad.
MAX_PRICE_GAP = 0.20
# Momios desde aquí (10% de probabilidad o menos): su precio justo es poco confiable y se reportan aparte.
LONG_SHOT_ODD = 10.0
# Por qué no cuenta una pierna, en el orden en que se revisa.
CLV_EXCLUSIONS = ("no_close", "no_reference", "short_window", "doubtful")


def _clv_summary(rows: pd.DataFrame) -> dict | None:
    """CLV de un conjunto de piernas medibles: promedio, mediana, % que le ganó al cierre y movimiento de Pinnacle."""
    if rows.empty:
        return None
    moved = rows[rows["first_p_sharp"].notna()]
    return {
        "n": len(rows),
        "avg": float(rows["clv"].mean()),
        "median": float(rows["clv"].median()),
        "beat_rate": float((rows["clv"] > 0).mean()),
        "n_move": len(moved),
        "avg_move": float((moved["p_sharp"] - moved["first_p_sharp"]).mean()) if len(moved) else None,
    }


def clv_data(picks: pd.DataFrame) -> tuple[dict | None, dict[str, dict]]:
    """CLV: el momio de publicación (el primero registrado) contra la probabilidad sin comisión de Pinnacle al cierre.

    CLV = momio de publicación × probabilidad de Pinnacle al cierre − 1: lo que valía la apuesta con los precios
    finales del mercado más preciso. Positivo = se publicó a mejor precio que el cierre.

    Una pierna cuenta si su última evaluación fue a lo más CLOSE_MAX antes del inicio, Pinnacle cotizaba ahí su
    mercado completo, se publicó al menos MIN_WINDOW antes de esa evaluación y su momio de publicación no estaba a
    más de MAX_PRICE_GAP del precio justo de ese momento (el de Pinnacle; si no lo había, el del mercado).

    Lo que mide al modelo son las piernas con valor al publicarse (probabilidad del modelo × momio > 1) de momio
    menor a LONG_SHOT_ODD; las de momio mayor van aparte. Todas las piernas (los dos lados de cada mercado) rondan
    menos la comisión de la casa: son la referencia.

    Devuelve el resumen (None si ninguna pierna tiene momio de publicación) y el CLV por mercado de las piernas
    con valor que cuentan.
    """
    legs = picks[picks["first_odd"].notna()].copy()
    if legs.empty:
        return None, {}
    for col in ("first_odd", "first_p_model", "first_p_market", "first_p_sharp", "p_sharp"):
        legs[col] = pd.to_numeric(legs[col])  # una columna toda NULL llega como object
    legs["clv"] = legs["first_odd"] * legs["p_sharp"] - 1
    reference = legs["first_p_sharp"].fillna(legs["first_p_market"])
    fresh = (legs["starts_at"] - legs["evaluated_at"]) <= CLOSE_MAX
    legs["reason"] = np.select(
        [
            ~fresh,
            legs["p_sharp"].isna(),
            (legs["evaluated_at"] - legs["first_priced_at"]) < MIN_WINDOW,
            (legs["first_odd"] * reference - 1).abs() > MAX_PRICE_GAP,  # sin precio justo al publicar: no se descarta
        ],
        list(CLV_EXCLUSIONS),
        default="ok",
    )
    value = legs["first_p_model"] * legs["first_odd"] > 1
    long_shot = legs["first_odd"] >= LONG_SHOT_ODD
    counts = legs["reason"] == "ok"
    headline = legs[counts & value & ~long_shot]
    hours = (legs.loc[fresh, "starts_at"] - legs.loc[fresh, "first_priced_at"]).dt.total_seconds() / 3600
    excluded = legs.loc[value, "reason"].value_counts()
    summary = {
        "value": _clv_summary(headline),
        "long_shots": _clv_summary(legs[counts & value & long_shot]),
        "all": _clv_summary(legs[counts & ~long_shot]),
        "hours_before": float(hours.median()) if len(hours) else None,
        # Piernas con valor que no cuentan, por motivo.
        "excluded": {reason: int(excluded.get(reason, 0)) for reason in CLV_EXCLUSIONS},
        "close_max_minutes": int(CLOSE_MAX.total_seconds() // 60),
        "min_window_hours": MIN_WINDOW.total_seconds() / 3600,
        "max_price_gap": MAX_PRICE_GAP,
        "long_shot_odd": LONG_SHOT_ODD,
    }
    by_market = {market: {"n": len(grp), "avg": float(grp["clv"].mean())} for market, grp in headline.groupby("market")}
    return summary, by_market


def performance_data(conn: psycopg.Connection, sport: Sport, **filters) -> dict:
    """Métricas de rendimiento de los picks liquidados de un deporte (para la API y el reporte de texto).

    `filters` son los del deporte (NBA: include_preseason; fútbol: league).
    """
    pick_filter, parlay_filter, extra = sport.performance_filters(**filters)
    params = {"sport": sport.key, **extra}
    picks = pd.DataFrame(
        conn.execute(
            f"""
            SELECT k.market, k.p_model::float AS p, k.odd::float AS odd, k.p_market::float AS p_market,
                   k.result = 'won' AS won, k.first_odd::float AS first_odd, k.first_p_model::float AS first_p_model,
                   k.first_p_market::float AS first_p_market, k.p_sharp::float AS p_sharp,
                   k.first_p_sharp::float AS first_p_sharp, k.first_priced_at, k.evaluated_at, m.starts_at
            FROM core.picks k JOIN core.matches m ON m.id = k.match_id
            WHERE k.sport = %(sport)s AND k.result IN ('won', 'lost') {pick_filter}
            """,
            params,
        ).fetchall(),
        columns=[
            "market", "p", "odd", "p_market", "won", "first_odd", "first_p_model", "first_p_market", "p_sharp",
            "first_p_sharp", "first_priced_at", "evaluated_at", "starts_at",
        ],
    )
    for col in ("first_priced_at", "evaluated_at", "starts_at"):
        picks[col] = pd.to_datetime(picks[col], utc=True)
    voids = conn.execute(
        f"""
        SELECT count(*) AS n FROM core.picks k JOIN core.matches m ON m.id = k.match_id
        WHERE k.sport = %(sport)s AND k.result = 'void' {pick_filter}
        """,
        params,
    ).fetchone()["n"]
    parlays = pd.DataFrame(
        conn.execute(
            f"""
            SELECT p.mode, p.n_legs, p.probability::float AS p, p.settled_odd::float AS odd, p.result = 'won' AS won
            FROM core.parlays p
            WHERE p.sport = %(sport)s AND p.result IN ('won', 'lost') {parlay_filter}
            """,
            params,
        ).fetchall(),
        columns=["mode", "n_legs", "p", "odd", "won"],
    )

    data: dict = {
        "sport": sport.key,
        "filters": {k: v for k, v in filters.items() if v is not None},
        "legs": {"settled": len(picks), "void": voids, "won": int(picks["won"].sum()) if len(picks) else 0},
        "by_market": [],
        "calibration": [],
        "model_vs_market": None,
        "positive_ev": None,
        "clv": None,
        "parlays": [],
    }
    if picks.empty:
        return data

    # Piernas con p < 50% sólo existen como el lado contrario de otra; se pliegan al lado favorito.
    fav = picks.copy()
    flip = fav["p"] < 0.5
    fav.loc[flip, "p"] = 1 - fav.loc[flip, "p"]
    fav.loc[flip, "won"] = ~fav.loc[flip, "won"].astype(bool)
    fav["bin"] = pd.cut(fav["p"], CALIBRATION_BINS, include_lowest=True)
    for interval, grp in fav.groupby("bin", observed=True):
        data["calibration"].append(
            {"lo": float(interval.left), "hi": float(interval.right), "n": len(grp),
             "predicted": float(grp["p"].mean()), "actual": float(grp["won"].astype(float).mean())}
        )
    data["clv"], clv_by_market = clv_data(picks)
    for market, grp in picks.groupby("market"):
        clv = clv_by_market.get(market)
        data["by_market"].append(
            {
                "market": market,
                "n": len(grp),
                "predicted": float(grp["p"].mean()),
                "actual": float(grp["won"].astype(float).mean()),
                "clv_n": clv["n"] if clv else 0,
                "clv": clv["avg"] if clv else None,
            }
        )

    priced = picks[picks["odd"].notna()]
    with_market = priced[priced["p_market"].notna()]
    if not with_market.empty:
        y = with_market["won"].astype(float)
        data["model_vs_market"] = {
            "n": len(with_market),
            "brier_model": float(((with_market["p"] - y) ** 2).mean()),
            "brier_market": float(((with_market["p_market"] - y) ** 2).mean()),
        }
    positive = priced[priced["p"] * priced["odd"] > 1]
    if not positive.empty:
        profit = float((positive["won"] * positive["odd"] - 1).sum())
        data["positive_ev"] = {
            "n": len(positive),
            "hit_rate": float(positive["won"].mean()),
            "avg_odd": float(positive["odd"].mean()),
            "profit": profit,
            "roi": profit / len(positive),
        }

    for (mode, n), grp in parlays.groupby(["mode", "n_legs"]):
        with_odds = grp[grp["odd"].notna()]
        data["parlays"].append(
            {
                "mode": mode,
                "n_legs": int(n),
                "count": len(grp),
                "predicted": float(grp["p"].mean()),
                "actual": float(grp["won"].astype(float).mean()),
                "count_with_odds": len(with_odds),
                "roi": float((with_odds["won"] * with_odds["odd"] - 1).sum() / len(with_odds)) if len(with_odds) else None,
            }
        )
    return data


def _clv_exclusion_texts(c: dict) -> list[str]:
    """Cuántas piernas con valor no cuentan en el CLV y por qué ("3 sin Pinnacle al cierre")."""
    late = c["excluded"]["short_window"]
    texts = {
        "no_close": f"sin lectura a ≤{c['close_max_minutes']} min del inicio",
        "no_reference": "sin Pinnacle al cierre",
        "short_window": f"publicada{'' if late == 1 else 's'} a menos de {c['min_window_hours']:g} h del cierre",
        "doubtful": f"con precio dudoso (a más de {c['max_price_gap']:.0%} del precio justo al publicarse)",
    }
    return [f"{n} {texts[reason]}" for reason, n in c["excluded"].items() if n]


def performance_report(conn: psycopg.Connection, sport: Sport, **filters) -> str:
    d = performance_data(conn, sport, **filters)
    scope = ", ".join(f"{k}={v}" for k, v in d["filters"].items())
    lines = [f"{sport.label} — rendimiento de picks registrados{f' ({scope})' if scope else ''}", ""]
    if not d["legs"]["settled"]:
        return "\n".join(lines + ["Todavía no hay piernas liquidadas."])

    lines.append(f"Anuladas (jugador no jugó o partido cancelado): {d['legs']['void']}")
    lines.append(f"Piernas liquidadas: {d['legs']['settled']}")
    for m in d["by_market"]:
        clv = f"  CLV con valor={m['clv']:+.1%} (n={m['clv_n']})" if m["clv"] is not None else ""
        lines.append(f"  {m['market']:<11} n={m['n']:<6} predicho={m['predicted']:6.1%}  real={m['actual']:6.1%}{clv}")
    lines.append("")
    lines.append("Calibración (lado favorito; predicho vs real):")
    for b in d["calibration"]:
        lines.append(f"  {b['lo']:.0%}-{b['hi']:.0%}  n={b['n']:<6} predicho={b['predicted']:6.1%}  real={b['actual']:6.1%}")
    lines.append("")
    if d["model_vs_market"]:
        m = d["model_vs_market"]
        lines.append(f"Modelo vs mercado (Brier, menor es mejor; n={m['n']}): modelo {m['brier_model']:.4f} | mercado {m['brier_market']:.4f}")
    if d["positive_ev"]:
        e = d["positive_ev"]
        lines.append(
            f"Piernas con EV positivo a 1 unidad: n={e['n']}  acierto={e['hit_rate']:.1%}  "
            f"momio prom.={e['avg_odd']:.2f}  ganancia={e['profit']:+.1f} u  ROI={e['roi']:+.1%}"
        )
    if d["clv"]:
        c = d["clv"]
        odd = f"{c['long_shot_odd']:g}"
        lines.append("")
        lines.append(
            "CLV contra el cierre de Pinnacle (momio de publicación × probabilidad sin comisión de Pinnacle − 1; "
            f"última lectura a ≤{c['close_max_minutes']} min del inicio):"
        )
        groups = (
            (f"Con valor al publicarse (momio < {odd})", c["value"]),
            (f"Con valor, momio ≥ {odd} (poco confiable)", c["long_shots"]),
            (f"Todas con momio < {odd} (referencia)", c["all"]),
        )
        for label, s in groups:
            if s is None:
                lines.append(f"  {label}: sin piernas que cuenten")
                continue
            move = f"  mercado a favor={s['avg_move'] * 100:+.1f} pts" if s["avg_move"] is not None else ""
            lines.append(
                f"  {label}: n={s['n']}  CLV prom.={s['avg']:+.1%}  mediana={s['median']:+.1%}  "
                f"le ganan al cierre={s['beat_rate']:.1%}{move}"
            )
        if c["hours_before"] is not None:
            lines.append(f"  Publicadas {c['hours_before']:.1f} h antes del partido (mediana)")
        reasons = _clv_exclusion_texts(c)
        if reasons:
            lines.append("  Piernas con valor que no cuentan: " + " · ".join(reasons))
    if d["parlays"]:
        lines.append("")
        lines.append("Parlays sugeridos:")
        lines.append(f"  {'Modo':<6}{'Piernas':>8}{'n':>6}{'Predicho':>10}{'Real':>8}{'ROI (con momio)':>18}")
        for r in d["parlays"]:
            roi = f"{r['roi']:+.1%}" if r["roi"] is not None else "—"
            lines.append(f"  {r['mode']:<6}{r['n_legs']:>8}{r['count']:>6}{r['predicted']:>10.1%}{r['actual']:>8.1%}{roi:>18}")
    return "\n".join(lines)
