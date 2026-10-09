"""API HTTP contra una base de prueba con datos sintéticos (rutas por deporte y comunes, cuentas y planes)."""

import os
from datetime import date, datetime, timedelta, timezone

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from app.config import LOCAL_TZ
from app.core.accounts import create_user, find_user, set_password
from app.core.tracking import record_picks
from app.db import migrate
from app.sports.futbol.api import slate_range
from app.sports.futbol.engine.legs import LegSpec as FutbolLeg
from app.sports.nba.engine.legs import LegSpec as NbaLeg
from tests.integration.helpers import add_futbol_fixture, add_nba_game
from tests.integration.test_core_tracking import card, nba_legs, with_engine
from tests.pg import recreate_database

FUTURE = (datetime.now(timezone.utc) + timedelta(days=3)).replace(hour=23, minute=30, second=0, microsecond=0)
DAY = FUTURE.date()
PASSWORD = "contraseña-de-prueba"
TODAY = datetime.now(LOCAL_TZ).date()


@pytest.fixture(scope="module")
def app_db():
    """La app contra una base con dos partidos NBA y uno de fútbol, y cuentas de cada plan.

    NBA 2001: el local es la pierna más probable y la de valor. NBA 2002: la más probable es el over (sin momio de
    Bet365, sólo de 1xBet) y la de valor, el local. Así el parlay de máxima probabilidad (gratis) y el de máximo valor (con suscripción)
    comparten "Gana local 2001" y difieren en la segunda pierna.
    """
    url = recreate_database("gorgo_v4_test_api")
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        migrate(conn)
        with conn.transaction():
            add_nba_game(conn, 2001, starts=FUTURE.isoformat(), game_date=DAY.isoformat())
            add_nba_game(conn, 2002, starts=FUTURE.isoformat(), game_date=DAY.isoformat(), home=134, away=135)
            add_futbol_fixture(conn, 2001, starts=FUTURE.isoformat(), match_date=DAY.isoformat())
            conn.execute("UPDATE futbol.fixtures SET round = 'Apertura - 11' WHERE id = 2001")
            conn.execute("UPDATE futbol.leagues SET current_season = 2026 WHERE id = 262")
            conn.execute(
                """
                INSERT INTO nba.game_projections (game_id, home_points, away_points, p_home_win, model_version, evaluated_at)
                VALUES (2001, 112.5, 106.0, 0.68, 'v1', now())
                """
            )
        now = datetime.now(timezone.utc)
        nba_2002 = card("nba", 2002, FUTURE.isoformat(), [
            (NbaLeg("ml", "home"), "Gana local 2002", 0.66, 1.6),
            (NbaLeg("ml", "away"), "Gana visitante 2002", 0.34, 2.4),
            (NbaLeg("total", "over", 220.5), "Más de 220.5 (2002)", 0.7, None, {"1xBet": 1.3}),
        ])
        record_picks(conn, with_engine("nba", [nba_legs(2001, FUTURE.isoformat()), nba_2002]), None, DAY, "Bet365", now=now)
        record_picks(
            conn,
            with_engine("futbol", [card("futbol", 2001, FUTURE.isoformat(), [
                (FutbolLeg("1x2", "home"), "Gana local", 0.62, 1.7),
                (FutbolLeg("btts", "yes"), "Ambos anotan", 0.55, 1.8),
            ])]),
            None, DAY, "Bet365", now=now,
        )
        set_password(conn, find_user(conn, "GorgoAdmin")["id"], PASSWORD)
        create_user(conn, "suscriptor", PASSWORD, "subscriber", TODAY)  # vigente hasta hoy inclusive
        create_user(conn, "vencido", PASSWORD, "subscriber", TODAY - timedelta(days=1))
        create_user(conn, "gratis", PASSWORD, "free")
        create_user(conn, "gratis2", PASSWORD, "free")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", url)
        from app.api.main import app

        yield app


def db_conn() -> psycopg.Connection:
    """Conexión a la base de la app de prueba (DATABASE_URL la pone `app_db`)."""
    return psycopg.connect(os.environ["DATABASE_URL"], autocommit=True, row_factory=dict_row)


def login(app, username: str, password: str = PASSWORD) -> TestClient:
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture(scope="module")
def client(app_db):
    """El administrador: ve todo."""
    return login(app_db, "GorgoAdmin")


@pytest.fixture(scope="module")
def free(app_db):
    return login(app_db, "gratis")


# ---------------------------------------------------------------- sesión


def test_everything_but_login_requires_a_session(app_db):
    anon = TestClient(app_db)
    for url in ("/api/meta", f"/api/nba/days/{DAY}", f"/api/futbol/days/{DAY}/legs", "/api/bets", "/api/history",
                "/api/auth/me", "/api/admin/users"):
        r = anon.get(url)
        assert r.status_code == 401 and r.json()["detail"] == "Inicia sesión para continuar.", url
    anon.cookies.set("gorgo_session", "inventada")
    assert anon.get("/api/meta").status_code == 401


def test_login_me_and_logout(app_db):
    c = TestClient(app_db)
    wrong = c.post("/api/auth/login", json={"username": "suscriptor", "password": "otra"})
    assert wrong.status_code == 401 and wrong.json()["detail"] == "Usuario o contraseña incorrectos."
    # Mismo mensaje si el usuario no existe: no se revela qué cuentas hay.
    assert c.post("/api/auth/login", json={"username": "nadie", "password": "x"}).json() == wrong.json()

    me = c.post("/api/auth/login", json={"username": "SUSCRIPTOR", "password": PASSWORD})
    assert me.status_code == 200
    assert me.json() | {"id": 0} == {
        "id": 0, "username": "suscriptor", "role": "subscriber", "plan": "subscriber", "full": True,
        "subscription_until": TODAY.isoformat(),
    }
    cookie = me.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert c.get("/api/auth/me").json()["username"] == "suscriptor"

    assert c.post("/api/auth/logout").json() == {"ok": True}
    assert c.get("/api/auth/me").status_code == 401


def test_repeated_failures_block_login_for_that_user(app_db):
    c = TestClient(app_db)
    for _ in range(5):
        assert c.post("/api/auth/login", json={"username": "gratis2", "password": "mal"}).status_code == 401
    blocked = c.post("/api/auth/login", json={"username": "gratis2", "password": PASSWORD})
    assert blocked.status_code == 429 and "15 minutos" in blocked.json()["detail"]


def test_expired_subscription_sees_the_free_plan(app_db):
    me = login(app_db, "vencido").get("/api/auth/me").json()
    assert (me["role"], me["plan"], me["full"]) == ("subscriber", "free", False)


def test_changing_the_password_closes_other_sessions(app_db):
    with db_conn() as conn:
        create_user(conn, "cambia", PASSWORD, "free")
    here, elsewhere = login(app_db, "cambia"), login(app_db, "cambia")
    wrong = here.post("/api/auth/password", json={"current": "mal", "new": "nueva-contraseña"})
    assert wrong.status_code == 422
    short = here.post("/api/auth/password", json={"current": PASSWORD, "new": "corta"})
    assert short.status_code == 422 and "8 caracteres" in short.json()["detail"]
    assert here.post("/api/auth/password", json={"current": PASSWORD, "new": "nueva-contraseña"}).json() == {"ok": True}
    assert here.get("/api/auth/me").status_code == 200
    assert elsewhere.get("/api/auth/me").status_code == 401
    login(app_db, "cambia", "nueva-contraseña")


# ---------------------------------------------------------------- con plan completo (admin)


def test_meta_lists_both_sports(client):
    body = client.get("/api/meta").json()
    assert list(body["sports"]) == ["nba", "futbol"]
    assert body["sports"]["futbol"]["leagues"][0]["name"] == "Liga MX"
    assert body["sharp_bookmaker"] == "Pinnacle"


def test_day_views_by_sport(client):
    nba = client.get(f"/api/nba/days/{DAY}").json()
    assert [(g["id"], g["home"]["name"], g["picks_count"]) for g in nba["games"]] == [(2001, "NBA 132", 3), (2002, "NBA 134", 3)]
    assert {(p["mode"], p["n_legs"]) for p in nba["parlays"]} == {("prob", 2), ("ev", 2)}
    assert nba["games"][0]["projection"]["p_home_win"] == 0.68 and nba["games"][0]["projection_locked"] is False
    futbol = client.get(f"/api/futbol/days/{DAY}").json()
    assert [(g["id"], g["league"]["name"], g["picks_count"]) for g in futbol["games"]] == [(2001, "Liga MX", 2)]
    # Mismo ID de proveedor (2001) en los dos deportes: partidos distintos en core.
    assert nba["games"][0]["match_id"] != futbol["games"][0]["match_id"]

    legs = client.get(f"/api/futbol/days/{DAY}/legs").json()
    assert {leg["sport"] for leg in legs} == {"futbol"} and {leg["fixture_id"] for leg in legs} == {2001}
    assert len(client.get(f"/api/nba/days/{DAY}/legs").json()) == 6


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


def _pick(client, sport: str, description: str) -> int:
    return next(leg["id"] for leg in client.get(f"/api/{sport}/days/{DAY}/legs").json() if leg["description"] == description)


def test_a_bet_can_mix_sports_and_be_deleted_before_start(client):
    legs = [
        {"pick_id": _pick(client, "nba", "Gana local 2001"), "odd": 1.5},
        {"pick_id": _pick(client, "futbol", "Gana local"), "odd": 1.7},
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
    assert all(item["recorded_before_start"] and not item["locked"] for item in everything["items"])
    nba = client.get("/api/history", params={"sport": "nba"}).json()
    assert nba["total"] == everything["total"]
    assert client.get("/api/history", params={"sport": "futbol"}).json()["total"] == 0
    csv = client.get("/api/history.csv").text
    assert csv.splitlines()[0].lstrip("﻿").startswith("fecha,deporte,parlay")


def test_performance_requires_a_known_sport(client):
    assert client.get("/api/performance", params={"sport": "nba"}).json()["legs"] == {"settled": 0, "void": 0, "won": 0}
    assert client.get("/api/performance", params={"sport": "futbol", "league": 262}).json()["filters"] == {"league": 262}
    assert client.get("/api/performance", params={"sport": "tenis"}).status_code == 404


# ---------------------------------------------------------------- plan free


def test_free_sees_only_the_free_parlays_and_their_legs(free, client):
    nba = free.get(f"/api/nba/days/{DAY}").json()
    assert [(p["mode"], p["n_legs"]) for p in nba["parlays"]] == [("prob", 2)]
    free_legs = [leg["description"] for leg in nba["parlays"][0]["legs"]]
    assert sorted(free_legs) == ["Gana local 2001", "Más de 220.5 (2002)"]
    # Los partidos sí; la proyección del modelo, no (sólo el aviso de que existe).
    assert [g["picks_count"] for g in nba["games"]] == [3, 3]
    assert (nba["games"][0]["projection"], nba["games"][0]["projection_locked"]) == (None, True)
    assert nba["games"][1]["projection_locked"] is False  # 2002 no tiene proyección

    assert sorted(leg["description"] for leg in free.get(f"/api/nba/days/{DAY}/legs").json()) == sorted(free_legs)
    # Fútbol tiene un solo partido: no hay parlay gratis, ni piernas.
    assert free.get(f"/api/futbol/days/{DAY}").json()["parlays"] == []
    assert free.get(f"/api/futbol/days/{DAY}/legs").json() == []
    assert free.get("/api/futbol/slate/legs", params={"league": 262, "jornada": "Apertura - 11"}).json() == []
    assert free.get("/api/futbol/slate", params={"league": 262, "jornada": "Apertura - 11"}).json()["games"][0]["id"] == 2001


def test_free_history_locks_the_picks_it_does_not_include(free):
    items = {item["mode"]: item for item in free.get("/api/history", params={"sport": "nba"}).json()["items"]}
    assert items["prob"]["locked"] is False and all(not leg["locked"] for leg in items["prob"]["legs"])
    ev = items["ev"]
    assert ev["locked"] is True
    shown = {leg["description"] for leg in ev["legs"] if not leg["locked"]}
    hidden = [leg for leg in ev["legs"] if leg["locked"]]
    assert shown == {"Gana local 2001"}  # también está en el parlay gratis
    assert hidden == [{"position": hidden[0]["position"], "sport": "nba", "competition": "NBA", "matchup": "135 @ 134",
                       "starts_at": hidden[0]["starts_at"], "locked": True}]
    assert free.get("/api/history.csv").status_code == 403


def test_free_once_the_game_starts_sees_everything_of_it(free):
    def nba_2002(status: str, state: str) -> None:
        with db_conn() as conn:
            conn.execute("UPDATE core.matches SET status = %s, state = %s WHERE sport = 'nba' AND external_id = 2002", (status, state))

    def legs() -> set[str]:
        return {leg["description"] for leg in free.get(f"/api/nba/days/{DAY}/legs").json()}

    try:
        nba_2002("TBD", "scheduled")  # horario por definir: sigue por jugar
        assert "Gana local 2002" not in legs()
        nba_2002("Q1", "live")
        assert {"Gana local 2002", "Gana visitante 2002", "Más de 220.5 (2002)"} <= legs()
        assert "Gana visitante 2001" not in legs()
    finally:
        nba_2002("NS", "scheduled")


def test_free_bets_only_with_free_legs_and_each_account_sees_its_own(free, client):
    locked = {"pick_id": _pick(client, "nba", "Gana local 2002"), "odd": 1.6}
    rejected = free.post("/api/bets", json={"bookmaker": "Caliente", "stake": 50, "legs": [locked]})
    assert rejected.status_code == 403 and "plan" in rejected.json()["detail"]

    legs = [{"pick_id": leg["id"], "odd": 1.5} for leg in free.get(f"/api/nba/days/{DAY}/legs").json()]
    mine = free.post("/api/bets", json={"bookmaker": "Caliente", "stake": 50, "legs": legs})
    assert mine.status_code == 201
    theirs = client.post("/api/bets", json={"bookmaker": "Codere", "stake": 10, "legs": [locked]}).json()["id"]

    assert [b["id"] for b in free.get("/api/bets").json()["items"]] == [mine.json()["id"]]
    assert theirs in [b["id"] for b in client.get("/api/bets").json()["items"]]
    assert mine.json()["id"] not in [b["id"] for b in client.get("/api/bets").json()["items"]]
    # Borrar la de otra cuenta: "no existe".
    assert free.delete(f"/api/bets/{theirs}").status_code == 404
    assert client.delete(f"/api/bets/{theirs}").status_code == 200


def test_only_the_admin_recalculates_and_marks_absences(free, app_db):
    subscriber = login(app_db, "suscriptor")
    for c in (free, subscriber):
        assert c.post(f"/api/nba/days/{DAY}/refresh").status_code == 403
        assert c.post(f"/api/futbol/days/{DAY}/refresh").status_code == 403
        assert c.post("/api/futbol/slate/refresh", params={"league": 262, "jornada": "Apertura - 11"}).status_code == 403
        assert c.put("/api/nba/availability", json={"date": str(DAY), "player_id": 1, "status": "out"}).status_code == 403
        assert c.put("/api/futbol/availability", json={"fixture_id": 2001, "player_id": 1, "status": "out"}).status_code == 403
        assert c.get("/api/admin/users").status_code == 403
    # El suscriptor sí ve todo lo demás.
    assert len(subscriber.get(f"/api/nba/days/{DAY}/legs").json()) == 6
    assert subscriber.get("/api/history.csv").status_code == 200


# ---------------------------------------------------------------- administración de cuentas


def test_admin_creates_accounts_and_changes_plans(client, app_db):
    users = {u["username"]: u for u in client.get("/api/admin/users").json()}
    assert users["GorgoAdmin"]["role"] == "admin" and users["vencido"]["full"] is False
    assert "password_hash" not in users["GorgoAdmin"]

    short = client.post("/api/admin/users", json={"username": "cliente1", "password": "corta"})
    assert short.status_code == 422
    bad = client.post("/api/admin/users", json={"username": "con espacio", "password": PASSWORD})
    assert bad.status_code == 422
    new_id = client.post("/api/admin/users", json={"username": "cliente1", "password": PASSWORD}).json()["id"]
    again = client.post("/api/admin/users", json={"username": "CLIENTE1", "password": PASSWORD})
    assert again.status_code == 422 and "Ya existe" in again.json()["detail"]
    free_until = client.put(f"/api/admin/users/{new_id}", json={"role": "free", "subscription_until": str(TODAY), "active": True})
    assert free_until.status_code == 422

    customer = login(app_db, "cliente1")
    assert customer.get("/api/auth/me").json()["plan"] == "free"
    month = TODAY + timedelta(days=30)
    client.put(f"/api/admin/users/{new_id}", json={"role": "subscriber", "subscription_until": str(month), "active": True})
    assert customer.get("/api/auth/me").json() | {"id": 0} == {
        "id": 0, "username": "cliente1", "role": "subscriber", "plan": "subscriber", "full": True,
        "subscription_until": month.isoformat(),
    }

    # Contraseña nueva (la olvidó): se cierran sus sesiones y entra con la nueva.
    assert client.put(f"/api/admin/users/{new_id}/password", json={"password": "otra-contraseña"}).status_code == 200
    assert customer.get("/api/auth/me").status_code == 401
    customer = login(app_db, "cliente1", "otra-contraseña")

    # Desactivar: no entra y su sesión se cierra.
    client.put(f"/api/admin/users/{new_id}", json={"role": "subscriber", "active": False})
    assert customer.get("/api/auth/me").status_code == 401
    assert TestClient(app_db).post("/api/auth/login", json={"username": "cliente1", "password": "otra-contraseña"}).status_code == 401

    me = client.get("/api/auth/me").json()["id"]
    assert client.put(f"/api/admin/users/{me}", json={"role": "free", "active": True}).status_code == 409
    assert client.put(f"/api/admin/users/{me}", json={"role": "admin", "active": False}).status_code == 409
    assert client.put("/api/admin/users/999999", json={"role": "free", "active": True}).status_code == 404
