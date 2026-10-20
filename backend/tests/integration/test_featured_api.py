"""/api/featured y cómo conviven los destacados con el resto de la API (día, historial, apuestas de una cuenta free).

La semana sintética es la de tests/integration/test_featured.py (enero de 2030): sus partidos no han empezado, así que
una cuenta free sólo ve sus piernas por estar en un parlay destacado.
"""

import psycopg
import pytest
from psycopg.rows import dict_row

from app.api import featured as featured_api
from app.core.accounts import create_user
from app.core.featured import publish_featured
from app.db import migrate
from tests.integration.test_api import PASSWORD, login
from tests.integration.test_featured import FUTBOL, MONDAY_9, add_week, local
from tests.pg import recreate_database


@pytest.fixture(scope="module")
def app_db():
    url = recreate_database("gorgo_v4_test_featured")
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        migrate(conn)
        with conn.transaction():
            picks = add_week(conn)
        publish_featured(conn, FUTBOL, now=MONDAY_9)
        create_user(conn, "gratis", PASSWORD, "free")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DATABASE_URL", url)
        mp.setattr(featured_api, "_now", lambda: local(8, 10))  # martes de esa semana
        from app.api.main import app

        yield app, picks


@pytest.fixture(scope="module")
def free(app_db):
    return login(app_db[0], "gratis")


def test_free_accounts_see_the_whole_featured_parlays(free):
    data = free.get("/api/featured?sport=futbol").json()
    week, weekend = data["current"]
    assert (week["mode"], week["start"], week["end"], week["label"]) == ("week", "2030-01-07", "2030-01-13", "Parlay de la semana")
    assert [p["n_legs"] for p in week["parlays"]] == [2, 3, 4, 5]
    leg = week["parlays"][0]["legs"][0]
    assert (leg["description"], leg["p_model"], leg["p_market"], leg["odd"], leg["date"]) == (
        "Menos de 4.5 goles", 0.82, 0.76, 1.3, "2030-01-07"
    )
    assert weekend["parlays"] == [] and weekend["publish_at"] == "2030-01-10T08:00:00-06:00"
    assert data["past"] == []
    assert [s["n_legs"] for s in data["record"]["week"]["by_size"]] == [2, 3, 4, 5]
    assert data["rules"]["min_odd"] == 1.3


def test_only_sports_with_featured_parlays(free):
    assert free.get("/api/featured?sport=nba").status_code == 404
    assert free.get("/api/featured?sport=tenis").status_code == 404


def test_day_views_keep_only_their_own_parlays(free, app_db):
    from tests.integration.test_api import db_conn

    with db_conn() as conn:
        assert conn.execute("SELECT count(*) AS n FROM core.parlays WHERE day = '2030-01-07'").fetchone()["n"] == 4
    assert free.get("/api/futbol/days/2030-01-07").json()["parlays"] == []


def test_free_history_and_bets_with_featured_legs(free, app_db):
    _, picks = app_db
    history = free.get("/api/history?sport=futbol&mode=week").json()
    assert history["total"] == 4 and not any(p["locked"] for p in history["items"])
    assert free.get("/api/history?mode=semana").status_code == 422

    legs = [{"pick_id": picks[d], "odd": 1.3} for d in ("Menos de 4.5 goles", "Local o empate")]
    assert free.post("/api/bets", json={"bookmaker": "Caliente", "stake": 50, "legs": legs}).status_code == 201
    other = [{"pick_id": picks["Menos de 4.5 goles (otra semana)"], "odd": 1.3}]
    assert free.post("/api/bets", json={"bookmaker": "Caliente", "stake": 50, "legs": legs + other}).status_code == 403
