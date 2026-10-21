"""/api/public/results: la página pública de resultados, sin sesión y apagada salvo PUBLIC_RESULTS.

La semana sintética es la de tests/integration/test_featured.py (enero de 2030), con su parlay de la semana publicado
y liquidado, más parlays del día: uno con la regla actual, uno con la anterior (sin mercado), uno de máximo valor (con
suscripción) y uno que sigue en juego.
"""

from datetime import date, datetime, timezone

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app import config
from app.api import results as results_api
from app.core.featured import publish_featured
from app.core.tracking import settle_all
from app.db import migrate
from app.sports.futbol.matches import sync_matches as sync_futbol
from tests.integration.test_featured import FIXTURES, FUTBOL, MONDAY_9, add_week, local
from tests.pg import recreate_database

# 3007 (14 de enero) no termina: el parlay del día 14 sigue en juego.
SCORES = {3001: (0, 0), 3002: (1, 1), 3003: (2, 1), 3004: (1, 0), 3005: (2, 2), 3006: (2, 2), 3008: (0, 0)}


def add_parlay(conn, day: date, mode: str, legs: list[int], with_market: bool = True) -> int:
    parlay_id = conn.execute(
        """
        INSERT INTO core.parlays (sport, day, mode, n_legs, probability, odd, bookmaker, model_version, evaluated_at)
        VALUES ('futbol', %s, %s, %s, 0.5, 1.8, 'Bet365', 'v3', %s) RETURNING id
        """,
        (day, mode, len(legs), local(6, 12)),
    ).fetchone()["id"]
    for position, pick_id in enumerate(legs, 1):
        conn.execute(
            """
            INSERT INTO core.parlay_legs (parlay_id, pick_id, position, description, p_model, odd, p_market)
            SELECT %s, id, %s, description, p_model, odd, CASE WHEN %s THEN p_market END FROM core.picks WHERE id = %s
            """,
            (parlay_id, position, with_market, pick_id),
        )
    return parlay_id


@pytest.fixture(scope="module")
def app_db():
    url = recreate_database("gorgo_v4_test_results")
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        migrate(conn)
        with conn.transaction():
            picks = add_week(conn)
        publish_featured(conn, FUTBOL, now=MONDAY_9)
        monday, tuesday = date(2030, 1, 7), date(2030, 1, 14)
        ids = {
            "daily": add_parlay(conn, monday, "prob", [picks["Menos de 4.5 goles (ya empezó)"], picks["Menos de 4.5 goles (martes)"]]),
            "old_rule": add_parlay(conn, monday, "prob", [picks["Menos de 4.5 goles (ya empezó)"], picks["Menos de 4.5 goles"],
                                                          picks["Menos de 4.5 goles (martes)"]], with_market=False),
            "ev": add_parlay(conn, monday, "ev", [picks["Gana local"], picks["Menos de 4.5 goles (martes)"]]),
            "pending": add_parlay(conn, tuesday, "prob", [picks["Menos de 4.5 goles (otra semana)"], picks["Menos de 2.5 goles (viernes)"]]),
        }
        for fixture, (home, away) in SCORES.items():
            conn.execute("UPDATE futbol.fixtures SET status = 'FT', ft_home = %s, ft_away = %s WHERE id = %s", (home, away, fixture))
        sync_futbol(conn, list(FIXTURES))
        settle_all(conn, [FUTBOL], now=datetime(2030, 1, 15, tzinfo=timezone.utc))
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", url)
        mp.setattr(results_api, "_now", lambda: local(15, 10))
        from app.api.main import app

        yield TestClient(app), ids


@pytest.fixture
def anon(app_db, monkeypatch):
    """Quien no tiene cuenta, con la página prendida."""
    monkeypatch.setattr(config, "PUBLIC_RESULTS", True)
    results_api._cache.clear()
    return app_db[0]


def test_off_unless_enabled(app_db, monkeypatch):
    client = app_db[0]
    monkeypatch.setattr(config, "PUBLIC_RESULTS", False)
    assert client.get("/api/public/results/status").json() == {"enabled": False}
    r = client.get("/api/public/results")
    assert r.status_code == 404 and r.json()["detail"] == "Los resultados públicos todavía no están disponibles."


def test_without_a_session_only_settled_free_parlays_with_the_current_rule(anon, app_db):
    ids = app_db[1]
    assert anon.get("/api/public/results/status").json() == {"enabled": True}
    data = anon.get("/api/public/results").json()
    assert data["since"] == "2026-10-19"
    # Cuentan los 4 de la semana, el del día con la regla actual y el que sigue en juego; el de máximo valor no es
    # gratis y el de la regla anterior se informa aparte.
    s = data["summary"]
    assert (s["parlays"], s["settled"], s["won"], s["lost"], s["pending"]) == (6, 5, 4, 1, 1)
    assert data["excluded"] == 1
    assert data["total"] == 5
    listed = [(p["id"], p["kind"], p["n_legs"], p["result"]) for p in data["items"]]
    assert listed[0] == (ids["daily"], "daily", 2, "won")
    assert [(k, n, r) for _, k, n, r in listed[1:]] == [("week", 2, "won"), ("week", 3, "won"), ("week", 4, "won"), ("week", 5, "lost")]
    assert not {ids["old_rule"], ids["ev"], ids["pending"]} & {p["id"] for p in data["items"]}

    daily = data["items"][0]
    assert daily["profit"] == pytest.approx(1.30 * 1.31 - 1)  # con los momios de sus piernas
    assert datetime.fromisoformat(daily["evaluated_at"]) < datetime.fromisoformat(daily["first_start"])
    leg = daily["legs"][0]
    assert (leg["description"], leg["p_model"], leg["p_market"], leg["result"], leg["locked"]) == (
        "Menos de 4.5 goles (ya empezó)", 0.8, 0.78, "won", False
    )
    assert leg["outcome"]["text"] and "pick_id" not in leg

    assert [(g["sport"], g["kind"], g["summary"]["settled"], g["summary"]["won"]) for g in data["groups"]] == [
        ("futbol", "daily", 1, 1), ("futbol", "week", 4, 3)
    ]
    assert [(m["month"], m["summary"]["parlays"]) for m in data["months"]] == [("2030-01", 6)]
    # Seis picks distintos en los parlays liquidados (el del martes está en dos): sólo "No anotan ambos" falla.
    assert (data["legs"]["settled"], data["legs"]["won"]) == (6, 5)
    assert [(b["lo"], b["hi"], b["n"]) for b in data["calibration"]] == [(0.7, 0.8, 6)]


def test_pages_and_sport_filter(anon):
    page = anon.get("/api/public/results?limit=2&offset=4").json()
    assert page["total"] == 5 and [p["n_legs"] for p in page["items"]] == [5]
    nba = anon.get("/api/public/results?sport=nba").json()
    assert (nba["summary"]["parlays"], nba["total"], nba["items"], nba["groups"]) == (0, 0, [], [])
    assert anon.get("/api/public/results?sport=tenis").status_code == 404


def test_answers_are_cached(anon, app_db, monkeypatch):
    first = anon.get("/api/public/results?limit=1").json()
    monkeypatch.setattr(results_api, "connect", lambda: pytest.fail("no debió consultar la base"))
    assert anon.get("/api/public/results?limit=1").json() == first
