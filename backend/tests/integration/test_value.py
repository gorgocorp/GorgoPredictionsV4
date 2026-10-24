"""Parlay con valor contra PostgreSQL real: publicación única, reintento del día, liquidación, CLV y que sólo lo vea admin.

Día sintético: martes 8 de enero de 2030 (hora del centro de México, UTC−6); se publica desde las 20:00 del lunes 7.
"""

from datetime import datetime, timedelta

import psycopg
import pytest
from psycopg.rows import dict_row

from app.config import LOCAL_TZ
from app.core.accounts import create_user, find_user, set_password
from app.core.tracking import settle_all
from app.core.value import publish_value, value_performance
from app.db import migrate
from app.sports import all_sports
from app.sports.futbol.matches import sync_matches as sync_futbol
from tests.integration.helpers import add_futbol_fixture, match_id
from tests.integration.test_api import PASSWORD, login
from tests.pg import recreate_database

FUTBOL = all_sports()["futbol"]


def local(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2030, 1, day, hour, minute, tzinfo=LOCAL_TZ)


# fixture: (inicio local, [(mercado, lado, línea, descripción, p_modelo, p_mercado, momio Bet365, estado del jugador)])
FIXTURES = {
    4001: (local(8, 13), [
        ("total", "under", 2.5, "Menos de 2.5 goles", 0.66, 0.63, 1.62, None),  # 1.62 × 63% = 1.02: valor
        ("player", "over", 0.5, "Anota", 0.70, 0.66, 1.60, None),  # prop de jugador: no entra
    ]),
    4002: (local(8, 15), [("btts", "no", None, "No anotan ambos", 0.68, 0.61, 1.70, None)]),  # 1.70 × 61% = 1.04
    4003: (local(8, 17), [("1x2", "home", None, "Gana local", 0.70, 0.52, 1.85, None)]),  # sólo el modelo ve valor
    4004: (local(8, 19), [("dc", "1x", None, "Local o empate", 0.80, 0.70, 1.48, None)]),  # 1.48 × 70% = 1.04
    4005: (local(9, 13), [("total", "over", 1.5, "Más de 1.5 goles (miércoles)", 0.80, 0.75, 1.40, None)]),
}


def add_day(db) -> dict[str, int]:
    """Partidos y piernas ya registradas por el scheduler; devuelve {descripción: pick_id}."""
    picks = {}
    for i, (fixture, (starts, _)) in enumerate(FIXTURES.items()):
        add_futbol_fixture(db, fixture, starts=starts.isoformat(), match_date=starts.date().isoformat(),
                           home=200 + 2 * i, away=201 + 2 * i)
    sync_futbol(db, list(FIXTURES))
    for fixture, (_, legs) in FIXTURES.items():
        for market, side, line, desc, p, pm, odd, status in legs:
            picks[desc] = db.execute(
                """
                INSERT INTO core.picks (sport, match_id, market, side, line, stat, player_id, description, p_model, odd,
                                        bookmaker, p_market, player_status, model_version, first_evaluated_at, evaluated_at)
                VALUES ('futbol', %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Bet365', %s, %s, 'v3', %s, %s)
                RETURNING id
                """,
                (match_id(db, "futbol", fixture), market, side, line, "goals" if market == "player" else None,
                 10 if market == "player" else None, desc, p, odd, pm, status, local(7, 12), local(7, 12)),
            ).fetchone()["id"]
    return picks


def value_parlays(db) -> list[dict]:
    return db.execute(
        """
        SELECT p.id, p.day, p.n_legs, p.probability::float AS probability, p.odd::float AS odd, p.evaluated_at,
               array_agg(l.description ORDER BY l.position) AS legs, array_agg(l.p_market::float ORDER BY l.position) AS markets
        FROM core.parlays p JOIN core.parlay_legs l ON l.parlay_id = p.id
        WHERE p.mode = 'value' GROUP BY p.id ORDER BY p.day
        """
    ).fetchall()


def test_published_once_from_the_evening_before_and_never_replaced(db):
    picks = add_day(db)
    assert publish_value(db, FUTBOL, now=local(7, 19)) == 0  # antes de las 20 sólo toca el lunes, que no tiene partidos
    assert publish_value(db, FUTBOL, now=local(7, 20)) == 1

    [parlay] = value_parlays(db)
    assert parlay["day"].isoformat() == "2030-01-08"
    assert parlay["legs"] == ["Local o empate", "Menos de 2.5 goles"]  # las dos con valor que más se prometen
    assert parlay["markets"] == [0.70, 0.63]
    assert parlay["probability"] == pytest.approx(0.70 * 0.63)  # la menor entre modelo y mercado
    assert parlay["odd"] == pytest.approx(1.48 * 1.62, abs=1e-3)
    assert parlay["evaluated_at"] == local(7, 20)

    # Ya publicado no cambia aunque las piernas cambien.
    db.execute("UPDATE core.picks SET p_model = 0.90, p_market = 0.80 WHERE id = %s", (picks["No anotan ambos"],))
    assert publish_value(db, FUTBOL, now=local(7, 22)) == 0
    assert [p["id"] for p in value_parlays(db)] == [parlay["id"]]


def test_if_nothing_was_published_the_day_before_it_retries_with_matches_far_enough(db):
    add_day(db)
    # 10:00 del martes: "Menos de 2.5 goles" empieza a las 13:00, a menos de 3.5 h: su CLV no se podría medir.
    assert publish_value(db, FUTBOL, now=local(8, 10)) == 1
    assert value_parlays(db)[0]["legs"] == ["Local o empate", "No anotan ambos"]


def test_settles_and_measures_results_and_clv(db):
    picks = add_day(db)
    publish_value(db, FUTBOL, now=local(7, 20))
    # Cierre: última evaluación 15 min antes de cada partido, con la probabilidad sin comisión de Pinnacle.
    for desc, p_sharp, result, starts in (("Local o empate", 0.72, "won", local(8, 19)),
                                          ("Menos de 2.5 goles", 0.60, "won", local(8, 13))):
        db.execute(
            "UPDATE core.picks SET p_sharp = %s, evaluated_at = %s, result = %s WHERE id = %s",
            (p_sharp, starts - timedelta(minutes=15), result, picks[desc]),
        )
    settle_all(db, [FUTBOL], now=local(8, 22))

    data = value_performance(db, FUTBOL)
    assert (data["record"]["parlays"], data["record"]["won"]) == (1, 1)
    assert data["record"]["roi"] == pytest.approx(1.48 * 1.62 - 1, abs=1e-3)
    assert data["clv"]["n"] == 2
    assert data["clv"]["avg"] == pytest.approx((1.48 * 0.72 - 1 + 1.62 * 0.60 - 1) / 2)
    assert data["clv"]["beat_rate"] == 0.5  # 1.62 × 60% = 0.97: la segunda se cerró en contra
    assert data["rules"]["max_odd"] == 3.0 and data["rules"]["min_lead_hours"] == 3.5


# ---------------------------------------------------------------- sólo admin


@pytest.fixture(scope="module")
def app_db():
    url = recreate_database("gorgo_v4_test_value")
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        migrate(conn)
        with conn.transaction():
            add_day(conn)
        publish_value(conn, FUTBOL, now=local(7, 20))
        set_password(conn, find_user(conn, "GorgoAdmin")["id"], PASSWORD)
        create_user(conn, "suscriptor", PASSWORD, "subscriber")
        create_user(conn, "gratis", PASSWORD, "free")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", url)
        from app.api.main import app

        yield app


@pytest.mark.parametrize("username, sees", [("GorgoAdmin", True), ("suscriptor", False), ("gratis", False)])
def test_only_admin_sees_the_value_parlay(app_db, username, sees):
    c = login(app_db, username)
    day = c.get("/api/futbol/days/2030-01-08").json()
    assert [p["mode"] for p in day["parlays"]] == (["value"] if sees else [])
    if sees:
        legs = day["parlays"][0]["legs"]
        assert [(leg["description"], leg["p_market"], leg["odd"]) for leg in legs] == [
            ("Local o empate", 0.7, 1.48), ("Menos de 2.5 goles", 0.63, 1.62)
        ]

    assert c.get("/api/history?mode=value").json()["total"] == (1 if sees else 0)
    assert [p["mode"] for p in c.get("/api/history").json()["items"]] == (["value"] if sees else [])

    perf = c.get("/api/performance?sport=futbol").json()
    assert (perf["value"] is not None) == sees
    if sees:
        assert (perf["value"]["since"], perf["value"]["record"]["parlays"], perf["value"]["record"]["pending"]) == (
            "2026-10-24", 1, 1
        )


def test_the_csv_only_lists_it_for_admin(app_db):
    assert "con valor (prueba)" in login(app_db, "GorgoAdmin").get("/api/history.csv").text
    assert "con valor (prueba)" not in login(app_db, "suscriptor").get("/api/history.csv").text
