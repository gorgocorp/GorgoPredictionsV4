"""API HTTP para la interfaz web de los dos deportes.

- /api/nba/* y /api/futbol/*: lo propio de cada deporte (día, piernas, plantel, bajas, jornadas).
- /api/meta, /api/bets, /api/history, /api/performance: lo común (un boleto puede mezclar deportes).
Lee lo que registra el scheduler y permite recalcular un día. Si STATIC_DIR apunta a la interfaz compilada,
también la sirve (una sola app en Docker).

Local:  uvicorn app.api.main:app --reload   (desde backend/)
"""

import csv
import io
import os
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.config import BOOKMAKER, LOCAL_TZ, PRICE_BOOKMAKERS
from app.core.bets import BetError, LegInput, create_bet, delete_bet, list_bets
from app.core.evidence import summarize
from app.core.sport import Sport
from app.core.tracking import performance_data
from app.db import connect
from app.sports import all_sports
from app.sports.futbol import api as futbol_api
from app.sports.nba import api as nba_api

SPORT_APIS = {"nba": nba_api, "futbol": futbol_api}

app = FastAPI(title="GorgoPredictions V4", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(GZipMiddleware, minimum_size=1000)
for module in SPORT_APIS.values():
    app.include_router(module.router)


def _sports() -> dict[str, Sport]:
    return all_sports()


def _sport(key: str) -> Sport:
    sports = _sports()
    if key not in sports:
        raise HTTPException(status_code=404, detail=f"Deporte desconocido: {key}")
    return sports[key]


def _now() -> datetime:
    return datetime.now(LOCAL_TZ)


@app.get("/api/meta")
def meta() -> dict:
    with connect() as conn:
        sports = {key: SPORT_APIS[key].meta(conn) for key in _sports()}
    return {
        "bookmaker": BOOKMAKER,
        "bookmakers": PRICE_BOOKMAKERS,
        "today": _now().date().isoformat(),
        "timezone": str(LOCAL_TZ),
        "sports": sports,
    }


# ---------------------------------------------------------------- historial (evidencias)

RESULT_FILTERS = ("won", "lost", "void", "pending")


def _history_sql(sports: dict[str, Sport]) -> str:
    cases = " ".join(f"WHEN '{s.key}' THEN {s.preseason_sql}" for s in sports.values() if s.preseason_sql)
    preseason = f"CASE m.sport {cases} ELSE false END" if cases else "false"
    return f"""
    WITH info AS (
        SELECT p.id, p.sport, p.day, p.mode, p.n_legs, p.probability::float AS probability, p.odd::float AS odd,
               p.result, p.settled_odd::float AS settled_odd, p.evaluated_at, p.settled_at, p.bookmaker,
               p.model_version, min(m.starts_at) AS first_start, bool_or({preseason}) AS preseason
        FROM core.parlays p
        JOIN core.parlay_legs l ON l.parlay_id = p.id
        JOIN core.picks k ON k.id = l.pick_id
        JOIN core.matches m ON m.id = k.match_id
        WHERE (%(sport)s::text IS NULL OR p.sport = %(sport)s)
          AND p.day BETWEEN %(desde)s AND %(hasta)s
          AND (%(mode)s::text IS NULL OR p.mode = %(mode)s)
          AND (%(n_legs)s::int IS NULL OR p.n_legs = %(n_legs)s)
        GROUP BY p.id
    )
    SELECT * FROM info
    WHERE (%(preseason)s OR NOT preseason)
      AND (%(result)s::text IS NULL OR (%(result)s = 'pending' AND result IS NULL) OR result = %(result)s)
    ORDER BY day DESC, sport, mode, n_legs
    """


HISTORY_LEGS_SQL = """
SELECT l.parlay_id, l.position, k.id AS pick_id, k.match_id, m.external_id, m.competition, m.home_name, m.away_name,
       k.market, k.side, k.line::float AS line, k.team, k.stat,
       l.description, l.p_model::float AS p_model, l.odd::float AS odd, k.result,
{outcome_columns}
FROM core.parlay_legs l
JOIN core.picks k ON k.id = l.pick_id
{outcome_joins}
WHERE k.sport = %s AND l.parlay_id = ANY(%s)
"""


def _history_rows(conn, sport, desde, hasta, mode, n_legs, result, include_preseason) -> list[dict]:
    if sport is not None:
        _sport(sport)
    if mode not in (None, "prob", "ev"):
        raise HTTPException(status_code=422, detail="mode debe ser prob o ev")
    if result not in (None, *RESULT_FILTERS):
        raise HTTPException(status_code=422, detail=f"result debe ser uno de {RESULT_FILTERS}")
    return conn.execute(
        _history_sql(_sports()),
        {
            "sport": sport,
            "desde": desde or date(2000, 1, 1),
            "hasta": hasta or date(2100, 1, 1),
            "mode": mode,
            "n_legs": n_legs,
            "result": result,
            "preseason": include_preseason,
        },
    ).fetchall()


def _history_legs(conn, rows: list[dict]) -> dict[int, list[dict]]:
    legs: dict[int, list[dict]] = {}
    for key, sport in _sports().items():
        ids = [r["id"] for r in rows if r["sport"] == key]
        if not ids:
            continue
        query = HISTORY_LEGS_SQL.format(outcome_columns=sport.outcome_columns, outcome_joins=sport.outcome_joins)
        for r in conn.execute(query, (key, ids)):
            legs.setdefault(r["parlay_id"], []).append(
                {
                    "pick_id": r["pick_id"],
                    "position": r["position"],
                    "sport": key,
                    "match_id": r["match_id"],
                    "external_id": r["external_id"],
                    "competition": r["competition"],
                    "matchup": sport.matchup(r["home_name"], r["away_name"]),
                    "starts_at": r["starts_at"],
                    "market": r["market"],
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


def _profit(p: dict) -> float | None:
    if p["result"] not in ("won", "lost") or not p["settled_odd"]:
        return None
    return p["settled_odd"] - 1 if p["result"] == "won" else -1.0


@app.get("/api/history")
def history(
    sport: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    mode: str | None = None,
    n_legs: int | None = None,
    result: str | None = None,
    include_preseason: bool = True,
    limit: int = 20,
    offset: int = 0,
) -> dict:
    """Parlays sugeridos por el sistema: qué se predijo, cuándo y qué pasó en realidad."""
    limit = max(1, min(limit, 100))
    with connect() as conn:
        rows = _history_rows(conn, sport, desde, hasta, mode, n_legs, result, include_preseason)
        page = rows[offset : offset + limit]
        legs = _history_legs(conn, page) if page else {}
    return {
        "summary": summarize(rows),
        "total": len(rows),
        "items": [
            {
                **{k: r[k] for k in ("id", "sport", "day", "mode", "n_legs", "probability", "odd", "result",
                                     "settled_odd", "evaluated_at", "settled_at", "first_start", "preseason",
                                     "bookmaker", "model_version")},
                "profit": _profit(r),
                "recorded_before_start": r["evaluated_at"] < r["first_start"],
                "legs": legs.get(r["id"], []),
            }
            for r in page
        ],
    }


RESULT_ES = {"won": "ganado", "lost": "perdido", "void": "anulado", None: "pendiente"}
MODE_ES = {"prob": "máxima probabilidad", "ev": "máximo valor"}


@app.get("/api/history.csv")
def history_csv(
    sport: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    mode: str | None = None,
    n_legs: int | None = None,
    result: str | None = None,
    include_preseason: bool = True,
) -> Response:
    """El mismo historial en CSV, una fila por pierna (abre bien en Excel)."""
    sports = _sports()
    with connect() as conn:
        rows = _history_rows(conn, sport, desde, hasta, mode, n_legs, result, include_preseason)
        legs = _history_legs(conn, rows) if rows else {}
    out = io.StringIO()
    out.write("﻿")  # BOM: Excel reconoce los acentos
    writer = csv.writer(out)
    writer.writerow([
        "fecha", "deporte", "parlay", "modo", "piernas", "prob_parlay", "momio_parlay", "resultado_parlay",
        "momio_liquidado", "ganancia_unidades", "registrado_utc", "primer_partido_utc", "registrado_antes_del_partido",
        "pierna", "competicion", "partido", "hora_partido_utc", "mercado", "descripcion", "prob_pierna", "momio_pierna",
        "resultado_pierna", "valor_real", "detalle_real",
    ])
    for r in rows:
        profit = _profit(r)
        for leg in legs.get(r["id"], []):
            writer.writerow([
                r["day"].isoformat(), sports[r["sport"]].label, r["id"], MODE_ES[r["mode"]], r["n_legs"],
                round(r["probability"], 4), r["odd"] or "", RESULT_ES[r["result"]], r["settled_odd"] or "",
                "" if profit is None else round(profit, 3),
                r["evaluated_at"].isoformat(timespec="seconds"), r["first_start"].isoformat(timespec="seconds"),
                "sí" if r["evaluated_at"] < r["first_start"] else "no", leg["position"], leg["competition"], leg["matchup"],
                leg["starts_at"].isoformat(timespec="seconds"), leg["market"], leg["description"],
                round(leg["p_model"], 4), leg["odd"] or "", RESULT_ES[leg["result"]],
                "" if leg["outcome"]["value"] is None else leg["outcome"]["value"], leg["outcome"]["text"],
            ])
    return Response(
        out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="historial-parlays.csv"'},
    )


# ---------------------------------------------------------------- mis apuestas


class BetLegIn(BaseModel):
    pick_id: int
    odd: float  # momio de la casa en decimal


class BetIn(BaseModel):
    bookmaker: str
    stake: float
    legs: list[BetLegIn]
    total_odd: float | None = None  # momio total del boleto si la casa lo redondea distinto
    note: str | None = None


@app.get("/api/bets")
def bets() -> dict:
    with connect() as conn:
        return list_bets(conn, _now(), _sports())


@app.post("/api/bets", status_code=201)
def register_bet(bet: BetIn) -> dict:
    """Registra una apuesta real (puede mezclar NBA y fútbol). Sólo antes de que empiece el primer partido."""
    with connect() as conn:
        try:
            bet_id = create_bet(
                conn, bet.bookmaker, bet.stake, [LegInput(leg.pick_id, leg.odd) for leg in bet.legs], _now(),
                total_odd=bet.total_odd, note=bet.note,
            )
        except BetError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": bet_id}


@app.delete("/api/bets/{bet_id}")
def remove_bet(bet_id: int) -> dict:
    with connect() as conn:
        try:
            delete_bet(conn, bet_id, _now())
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except BetError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"deleted": bet_id}


# ---------------------------------------------------------------- rendimiento


@app.get("/api/performance")
def performance(sport: str, include_preseason: bool = False, league: int | None = None) -> dict:
    """Rendimiento de un deporte. NBA: sin pretemporada salvo `include_preseason`; fútbol: `league` opcional."""
    s = _sport(sport)
    filters = {"include_preseason": include_preseason} if s.key == "nba" else {"league": league}
    with connect() as conn:
        return performance_data(conn, s, **filters)


# ---------------------------------------------------------------- interfaz compilada

STATIC_DIR = Path(os.getenv("STATIC_DIR", Path(__file__).resolve().parents[3] / "frontend" / "dist"))

if STATIC_DIR.is_dir():

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        file = (STATIC_DIR / path).resolve()
        if path and file.is_file() and STATIC_DIR.resolve() in file.parents:
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")
