"""Parlays destacados contra PostgreSQL real: publicación única, ventana, acceso free, liquidación y contador.

Semana sintética del lunes 7 al domingo 13 de enero de 2030 (hora del centro de México, UTC−6).
"""

from datetime import datetime, timezone

import pytest
from psycopg.types.json import Jsonb

from app.config import LOCAL_TZ
from app.core.access import free_visible_picks
from app.core.featured import featured_data, publish_featured
from app.core.tracking import settle_all
from app.sports import all_sports
from app.sports.futbol.matches import sync_matches as sync_futbol
from tests.integration.helpers import add_futbol_fixture, match_id

FUTBOL = all_sports()["futbol"]


def local(day: int, hour: int) -> datetime:
    return datetime(2030, 1, day, hour, 0, tzinfo=LOCAL_TZ)


MONDAY_9 = local(7, 9)
THURSDAY_8 = local(10, 8)

# fixture: (inicio local, [(mercado, lado, línea, equipo, descripción, p_modelo, p_mercado, momio Bet365, otras casas)])
FIXTURES = {
    3001: (local(7, 7), [("total", "under", 4.5, None, "Menos de 4.5 goles (ya empezó)", 0.80, 0.78, 1.30, None)]),
    3002: (local(7, 20), [
        ("total", "under", 4.5, None, "Menos de 4.5 goles", 0.82, 0.76, 1.30, None),
        ("player", "over", 0.5, None, "Anota", 0.90, 0.85, 1.35, None),  # prop de jugador: no entra
    ]),
    3003: (local(8, 13), [("total", "under", 4.5, None, "Menos de 4.5 goles (martes)", 0.80, 0.75, 1.31, None)]),
    3004: (local(9, 13), [
        ("total", "under", 3.5, None, "Menos de 3.5 goles", 0.78, 0.74, 1.33, None),  # tercera de goles: no entra
        ("team_total", "over", 0.5, "home", "Local anota", 0.76, 0.73, 1.36, None),
    ]),
    3005: (local(12, 10), [
        ("dc", "1x", None, None, "Local o empate", 0.77, 0.72, 1.32, None),
        ("1x2", "home", None, None, "Gana local", 0.60, 0.50, 1.90, None),  # el mercado no la ve probable
    ]),
    3006: (local(13, 10), [("btts", "no", None, None, "No anotan ambos", 0.74, 0.71, None, {"1xBet": 1.38})]),
    3007: (local(14, 10), [("total", "under", 4.5, None, "Menos de 4.5 goles (otra semana)", 0.85, 0.80, 1.30, None)]),
    3008: (local(11, 12), [("total", "under", 2.5, None, "Menos de 2.5 goles (viernes)", 0.70, 0.68, 1.40, None)]),
}


def add_week(db) -> dict[str, int]:
    """Partidos y piernas registradas el domingo anterior; devuelve {descripción: pick_id}."""
    picks = {}
    for i, (fixture, (starts, legs)) in enumerate(FIXTURES.items()):
        add_futbol_fixture(db, fixture, starts=starts.isoformat(), match_date=starts.date().isoformat(),
                           home=100 + 2 * i, away=101 + 2 * i)
    sync_futbol(db, list(FIXTURES))
    for fixture, (_, legs) in FIXTURES.items():
        for market, side, line, team, desc, p, pm, odd, books in legs:
            picks[desc] = db.execute(
                """
                INSERT INTO core.picks (sport, match_id, market, side, line, team, stat, player_id, description, p_model,
                                        odd, bookmaker, p_market, book_odds, model_version, first_evaluated_at, evaluated_at)
                VALUES ('futbol', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'v3', %s, %s)
                RETURNING id
                """,
                (match_id(db, "futbol", fixture), market, side, line, team, "goals" if market == "player" else None,
                 10 if market == "player" else None, desc, p, odd, "Bet365" if odd else None, pm,
                 Jsonb({"Bet365": odd} if odd else books), local(6, 12), local(6, 12)),
            ).fetchone()["id"]
    return picks


@pytest.fixture
def week(db):
    return add_week(db)


def featured(db, mode="week"):
    return db.execute(
        """
        SELECT p.id, p.day, p.n_legs, p.probability::float AS probability, p.odd::float AS odd,
               array_agg(l.description ORDER BY l.position) AS legs
        FROM core.parlays p JOIN core.parlay_legs l ON l.parlay_id = p.id
        WHERE p.mode = %s GROUP BY p.id ORDER BY p.n_legs
        """,
        (mode,),
    ).fetchall()


def test_the_weekly_parlay_is_published_once_with_nested_sizes(db, week):
    assert publish_featured(db, FUTBOL, now=local(7, 7)) == 0  # antes de las 8 no toca
    assert publish_featured(db, FUTBOL, now=MONDAY_9) == 4

    parlays = featured(db)
    order = ["Menos de 4.5 goles", "Menos de 4.5 goles (martes)", "Local anota", "Local o empate", "No anotan ambos"]
    assert [(p["n_legs"], p["legs"]) for p in parlays] == [(n, order[:n]) for n in (2, 3, 4, 5)]
    assert {p["day"].isoformat() for p in parlays} == {"2030-01-07"}
    assert parlays[0]["probability"] == pytest.approx(0.76 * 0.75)  # la menor entre modelo y mercado
    assert parlays[0]["odd"] == pytest.approx(1.30 * 1.31)
    assert parlays[3]["odd"] is None  # "No anotan ambos" sólo la cotiza 1xBet: sin momio de Bet365 no hay ROI
    leg = db.execute(
        "SELECT p_model::float AS p_model, p_market::float AS p_market FROM core.parlay_legs WHERE pick_id = %s LIMIT 1",
        (week["Menos de 4.5 goles"],),
    ).fetchone()
    assert leg == {"p_model": 0.82, "p_market": 0.76}

    # Ya publicado no cambia aunque cambien las piernas, ni se agrega otro.
    db.execute("UPDATE core.picks SET p_model = 0.95, p_market = 0.79 WHERE id = %s", (week["Menos de 4.5 goles (otra semana)"],))
    assert publish_featured(db, FUTBOL, now=local(8, 9)) == 0
    assert [p["id"] for p in featured(db)] == [p["id"] for p in parlays]


def test_the_weekend_parlay_only_uses_friday_to_sunday(db, week):
    assert publish_featured(db, FUTBOL, now=local(9, 9)) == 3  # miércoles: sólo la semana, con lo que queda de ella
    assert featured(db, "weekend") == []
    assert publish_featured(db, FUTBOL, now=THURSDAY_8) == 2
    assert [(p["day"].isoformat(), p["legs"]) for p in featured(db, "weekend")] == [
        ("2030-01-11", ["Local o empate", "No anotan ambos"]),
        ("2030-01-11", ["Local o empate", "No anotan ambos", "Menos de 2.5 goles (viernes)"]),
    ]
    # El de la semana publicado el miércoles ya no tenía los partidos del lunes y martes.
    assert featured(db)[-1]["legs"] == ["Menos de 3.5 goles", "Local o empate", "No anotan ambos", "Menos de 2.5 goles (viernes)"]


def test_not_enough_legs_publishes_nothing_and_retries_later(db, week):
    db.execute("UPDATE core.picks SET odd = 1.10, book_odds = NULL WHERE match_id = ANY(%s)",
               ([match_id(db, "futbol", f) for f in FIXTURES],))
    assert publish_featured(db, FUTBOL, now=MONDAY_9) == 0
    db.execute("UPDATE core.picks SET odd = 1.30 WHERE description IN ('Menos de 4.5 goles', 'Local o empate')")
    assert publish_featured(db, FUTBOL, now=local(7, 12)) == 1  # sólo alcanza para el de 2


def test_sports_without_featured_parlays_publish_nothing(db, week):
    assert publish_featured(db, all_sports()["nba"], now=MONDAY_9) == 0


def test_free_accounts_see_the_legs_of_the_featured_parlays(db, week):
    publish_featured(db, FUTBOL, now=MONDAY_9)
    visible = free_visible_picks(db, list(week.values()), now=MONDAY_9)
    assert visible == {week[d] for d in ("Menos de 4.5 goles", "Menos de 4.5 goles (martes)", "Local anota",
                                         "Local o empate", "No anotan ambos", "Menos de 4.5 goles (ya empezó)")}


def test_settles_and_counts_hits_by_size(db, week):
    publish_featured(db, FUTBOL, now=MONDAY_9)
    scores = {3001: (0, 0), 3002: (1, 1), 3003: (2, 1), 3004: (1, 0), 3005: (2, 2), 3006: (2, 2), 3007: (0, 0), 3008: (0, 0)}
    for fixture, (home, away) in scores.items():
        db.execute("UPDATE futbol.fixtures SET status = 'FT', ft_home = %s, ft_away = %s WHERE id = %s", (home, away, fixture))
    sync_futbol(db, list(FIXTURES))
    settle_all(db, [FUTBOL], now=datetime(2030, 1, 15, tzinfo=timezone.utc))

    data = featured_data(db, FUTBOL, now=local(15, 10))  # el martes siguiente
    assert [w["mode"] for w in data["current"]] == ["week", "weekend"]
    assert all(w["parlays"] == [] for w in data["current"])
    assert data["current"][1]["publish_at"] == "2030-01-17T08:00:00-06:00"
    (past,) = data["past"]
    assert (past["mode"], past["start"], past["end"]) == ("week", "2030-01-07", "2030-01-13")
    # 1-1, 2-1, 1-0 y 2-2 ganan las cuatro primeras; "No anotan ambos" pierde con 2-2.
    assert [(p["n_legs"], p["result"]) for p in past["parlays"]] == [(2, "won"), (3, "won"), (4, "won"), (5, "lost")]
    first = past["parlays"][0]["legs"][0]
    assert (first["matchup"], first["date"], first["p_model"], first["p_market"], first["result"]) == (
        "Fútbol 102 vs Fútbol 103", "2030-01-07", 0.82, 0.76, "won"
    )
    assert first["outcome"]["text"]
    week_record = {s["n_legs"]: (s["settled"], s["won"]) for s in data["record"]["week"]["by_size"]}
    assert week_record == {2: (1, 1), 3: (1, 1), 4: (1, 1), 5: (1, 0)}
    assert data["record"]["weekend"]["parlays"] == 0
