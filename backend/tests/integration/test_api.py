"""API HTTP contra una base de prueba con datos sintéticos (rutas por deporte y comunes)."""

from datetime import date, datetime, timedelta, timezone

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.core.tracking import record_picks
from app.db import migrate
from app.sports.futbol.api import slate_range
from app.sports.futbol.engine.legs import LegSpec as FutbolLeg
from tests.integration.helpers import add_futbol_fixture, add_nba_game
from tests.integration.test_core_tracking import card, nba_legs, with_engine
from tests.pg import recreate_database

FUTURE = (datetime.now(timezone.utc) + timedelta(days=3)).replace(hour=23, minute=30, second=0, microsecond=0)
DAY = FUTURE.date()


@pytest.fixture(scope="module")
def client():
    url = recreate_database("gorgo_v4_test_api")
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        migrate(conn)
        with conn.transaction():
            add_nba_game(conn, 2001, starts=FUTURE.isoformat(), game_date=DAY.isoformat())
            add_nba_game(conn, 2002, starts=FUTURE.isoformat(), game_date=DAY.isoformat(), home=134, away=135)
            add_futbol_fixture(conn, 2001, starts=FUTURE.isoformat(), match_date=DAY.isoformat())
            conn.execute("UPDATE futbol.fixtures SET round = 'Apertura - 11' WHERE id = 2001")
            conn.execute("UPDATE futbol.leagues SET current_season = 2026 WHERE id = 262")
        now = datetime.now(timezone.utc)
        record_picks(conn, with_engine("nba", [nba_legs(2001, FUTURE.isoformat()), nba_legs(2002, FUTURE.isoformat())]), None, DAY, "Bet365", now=now)
        record_picks(
            conn,
            with_engine("futbol", [card("futbol", 2001, FUTURE.isoformat(), [
                (FutbolLeg("1x2", "home"), "Gana local", 0.62, 1.7),
                (FutbolLeg("btts", "yes"), "Ambos anotan", 0.55, 1.8),
            ])]),
            None, DAY, "Bet365", now=now,
        )
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", url)
        from app.api.main import app

        yield TestClient(app)


def test_meta_lists_both_sports(client):
    body = client.get("/api/meta").json()
    assert list(body["sports"]) == ["nba", "futbol"]
    assert body["sports"]["futbol"]["leagues"][0]["name"] == "Liga MX"
    assert body["sharp_bookmaker"] == "Pinnacle"


def test_day_views_by_sport(client):
    nba = client.get(f"/api/nba/days/{DAY}").json()
    assert [(g["id"], g["home"]["name"], g["picks_count"]) for g in nba["games"]] == [(2001, "NBA 132", 3), (2002, "NBA 134", 3)]
    assert {p["mode"] for p in nba["parlays"]} == {"prob", "ev"}
    futbol = client.get(f"/api/futbol/days/{DAY}").json()
    assert [(g["id"], g["league"]["name"], g["picks_count"]) for g in futbol["games"]] == [(2001, "Liga MX", 2)]
    # Mismo ID de proveedor (2001) en los dos deportes: partidos distintos en core.
    assert nba["games"][0]["match_id"] != futbol["games"][0]["match_id"]

    legs = client.get(f"/api/futbol/days/{DAY}/legs").json()
    assert {leg["sport"] for leg in legs} == {"futbol"} and {leg["fixture_id"] for leg in legs} == {2001}


def test_rounds_and_slate(client):
    rounds = client.get("/api/futbol/rounds?league=262").json()
    assert rounds["current"] == "Apertura - 11"
    slate = client.get("/api/futbol/slate", params={"league": 262, "jornada": "Apertura - 11"}).json()
    assert [g["id"] for g in slate["games"]] == [2001]
    assert client.get("/api/futbol/slate", params={"desde": "2026-10-01", "hasta": "2026-10-20"}).status_code == 422


def test_slate_range_validation():
    assert slate_range(date(2026, 10, 9), date(2026, 10, 11)) == (date(2026, 10, 9), date(2026, 10, 11))
    for desde, hasta in ((None, date(2026, 10, 11)), (date(2026, 10, 11), date(2026, 10, 9)), (date(2026, 10, 1), date(2026, 10, 20))):
        with pytest.raises(HTTPException):
            slate_range(desde, hasta)


def test_a_bet_can_mix_sports_and_be_deleted_before_start(client):
    nba = client.get(f"/api/nba/days/{DAY}/legs").json()
    futbol = client.get(f"/api/futbol/days/{DAY}/legs").json()
    legs = [
        {"pick_id": next(leg["id"] for leg in nba if leg["description"] == "Gana local 2001"), "odd": 1.5},
        {"pick_id": next(leg["id"] for leg in futbol if leg["description"] == "Gana local"), "odd": 1.7},
    ]
    created = client.post("/api/bets", json={"bookmaker": "Caliente", "stake": 100, "legs": legs})
    assert created.status_code == 201
    bet_id = created.json()["id"]

    item = next(b for b in client.get("/api/bets").json()["items"] if b["id"] == bet_id)
    assert [(leg["sport"], leg["outcome"]["text"]) for leg in item["legs"]] == [("nba", "Programado"), ("futbol", "Programado")]
    assert item["can_delete"] is True

    repeated = client.post("/api/bets", json={"bookmaker": "Caliente", "stake": 100, "legs": [legs[0], legs[0]]})
    assert repeated.status_code == 422 and "repetida" in repeated.json()["detail"]
    assert client.delete(f"/api/bets/{bet_id}").json() == {"deleted": bet_id}
    assert client.delete(f"/api/bets/{bet_id}").status_code == 404


def test_history_by_sport_and_csv(client):
    everything = client.get("/api/history").json()
    # Sólo NBA tiene dos partidos (un parlay lleva una pierna por partido).
    assert {item["sport"] for item in everything["items"]} == {"nba"} and everything["total"] == 2
    assert all(item["recorded_before_start"] for item in everything["items"])
    nba = client.get("/api/history", params={"sport": "nba"}).json()
    assert nba["total"] == everything["total"]
    assert client.get("/api/history", params={"sport": "futbol"}).json()["total"] == 0
    csv = client.get("/api/history.csv").text
    assert csv.splitlines()[0].lstrip("﻿").startswith("fecha,deporte,parlay")


def test_performance_requires_a_known_sport(client):
    assert client.get("/api/performance", params={"sport": "nba"}).json()["legs"] == {"settled": 0, "void": 0, "won": 0}
    assert client.get("/api/performance", params={"sport": "futbol", "league": 262}).json()["filters"] == {"league": 262}
    assert client.get("/api/performance", params={"sport": "tenis"}).status_code == 404
