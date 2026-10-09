"""Contrato del esquema de V4 contra PostgreSQL real: identidades por deporte y restricciones de core."""

import psycopg
import pytest
from psycopg import sql

from app.sports.futbol.matches import sync_matches as sync_futbol
from app.sports.nba.matches import sync_matches as sync_nba
from tests.integration.helpers import STARTS, add_futbol_fixture, add_nba_game, add_pick, match_id, owner_id


def test_same_provider_ids_in_both_sports_are_different_matches(db):
    # El equipo 132 y el partido 1000 existen en los dos proveedores y no son lo mismo.
    add_nba_game(db, 1000)
    add_futbol_fixture(db, 1000)
    assert sync_nba(db) == 1
    assert sync_futbol(db) == 1
    rows = db.execute("SELECT sport, competition, home_name FROM core.matches WHERE external_id = 1000 ORDER BY sport").fetchall()
    assert rows == [
        {"sport": "futbol", "competition": "Liga MX", "home_name": "Fútbol 132"},
        {"sport": "nba", "competition": "NBA", "home_name": "NBA 132"},
    ]
    assert match_id(db, "nba", 1000) != match_id(db, "futbol", 1000)


@pytest.mark.parametrize(
    "sport, status, state",
    [
        ("nba", "NS", "scheduled"), ("nba", "Q2", "live"), ("nba", "HT", "live"), ("nba", "FT", "finished"),
        ("nba", "AOT", "finished"), ("nba", "POST", "cancelled"), ("nba", "AWD", "cancelled"),
        ("futbol", "TBD", "scheduled"), ("futbol", "2H", "live"), ("futbol", "PEN", "finished"),
        ("futbol", "AET", "finished"), ("futbol", "PST", "cancelled"), ("futbol", "WO", "cancelled"),
    ],
)
def test_match_state_follows_each_provider(db, sport, status, state):
    if sport == "nba":
        add_nba_game(db, 2000, status=status)
        sync_nba(db)
    else:
        add_futbol_fixture(db, 2000, status=status)
        sync_futbol(db)
    assert db.execute("SELECT state FROM core.matches WHERE sport = %s AND external_id = 2000", (sport,)).fetchone()["state"] == state


def test_sync_only_touches_changed_matches(db):
    add_nba_game(db, 3000)
    assert sync_nba(db) == 1
    assert sync_nba(db) == 0  # sin cambios no reescribe
    db.execute("UPDATE nba.games SET status = 'FT', home_total = 110, away_total = 104 WHERE id = 3000")
    assert sync_nba(db, [3000]) == 1
    assert db.execute("SELECT state FROM core.matches WHERE external_id = 3000").fetchone()["state"] == "finished"


def test_nba_day_is_local_even_for_late_games(db):
    # 22:30 hora del Este del 21-oct = 02:30 UTC del 22 = 20:30 del 21 en el centro de México.
    add_nba_game(db, 4000, starts="2026-10-22T02:30:00+00:00", game_date="2026-10-21")
    sync_nba(db)
    assert str(db.execute("SELECT local_date FROM core.matches WHERE external_id = 4000").fetchone()["local_date"]) == "2026-10-21"


def test_pick_markets_belong_to_their_sport(db):
    add_nba_game(db, 5000)
    add_futbol_fixture(db, 5000)
    sync_nba(db)
    sync_futbol(db)
    nba, futbol = match_id(db, "nba", 5000), match_id(db, "futbol", 5000)

    add_pick(db, "nba", nba, "spread", "home", -5.5)
    add_pick(db, "futbol", futbol, "score", "2-1")
    add_pick(db, "futbol", futbol, "1x2", "draw")
    for sport, match, market, side in (
        ("nba", nba, "btts", "yes"),  # mercado de fútbol en NBA
        ("futbol", futbol, "spread", "home"),  # mercado de NBA en fútbol
        ("nba", nba, "ml", "draw"),  # en NBA no hay empate
        ("futbol", futbol, "score", "dos-uno"),
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            with db.transaction():
                add_pick(db, sport, match, market, side)


def test_pick_first_price_is_complete(db):
    add_nba_game(db, 5500)
    sync_nba(db)
    pick = add_pick(db, "nba", match_id(db, "nba", 5500), "ml", "home")
    set_first = "UPDATE core.picks SET first_odd = %s, first_p_model = %s, first_p_market = %s, first_priced_at = {} WHERE id = %s"
    db.execute(set_first.format("evaluated_at"), (2.1, 0.55, None, pick))  # sin probabilidad del mercado: válido
    for odd, p_model, p_market, priced_at in (
        (2.1, None, None, "evaluated_at"),  # momio sin probabilidad del modelo
        (None, None, 0.5, "NULL"),  # probabilidad del mercado sin momio
        (2.1, 0.55, None, "NULL"),  # momio sin hora
        (2.1, 0.55, None, "evaluated_at + interval '1 hour'"),  # publicado después de su última evaluación
        (1.0, 0.55, None, "evaluated_at"),  # momio inválido
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            with db.transaction():
                db.execute(set_first.format(priced_at), (odd, p_model, p_market, pick))


def test_pick_sharp_price_needs_a_first_price(db):
    add_nba_game(db, 5600)
    sync_nba(db)
    pick = add_pick(db, "nba", match_id(db, "nba", 5600), "ml", "home")
    db.execute("UPDATE core.picks SET p_sharp = 0.52 WHERE id = %s", (pick,))  # Pinnacle al cierre sin publicar: válido
    for column, value in (
        ("first_p_sharp", 0.5),  # probabilidad de Pinnacle al publicarse sin momio de publicación
        ("p_sharp", 1.2),  # fuera de rango
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            with db.transaction():
                query = sql.SQL("UPDATE core.picks SET {} = %s WHERE id = %s").format(sql.Identifier(column))
                db.execute(query, (value, pick))
    db.execute(
        """
        UPDATE core.picks SET first_odd = 2.1, first_p_model = 0.55, first_p_sharp = 0.47, first_priced_at = evaluated_at
        WHERE id = %s
        """,
        (pick,),
    )


def test_pick_sport_must_be_its_match_sport(db):
    add_nba_game(db, 6000)
    sync_nba(db)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with db.transaction():
            add_pick(db, "futbol", match_id(db, "nba", 6000), "1x2", "home")


def test_one_bet_can_mix_nba_and_futbol_legs(db):
    add_nba_game(db, 7000)
    add_futbol_fixture(db, 7000)
    sync_nba(db)
    sync_futbol(db)
    nba_pick = add_pick(db, "nba", match_id(db, "nba", 7000), "ml", "home")
    futbol_pick = add_pick(db, "futbol", match_id(db, "futbol", 7000), "btts", "yes")
    bet = db.execute(
        """
        INSERT INTO core.user_bets (user_id, bookmaker, stake, odd, model_probability, created_at, first_start)
        VALUES (%s, 'Caliente', 100, 3.2, 0.36, now(), %s) RETURNING id
        """,
        (owner_id(db), STARTS),
    ).fetchone()["id"]
    for position, pick in enumerate((nba_pick, futbol_pick), 1):
        db.execute(
            "INSERT INTO core.user_bet_legs (bet_id, position, pick_id, description, p_model, odd) VALUES (%s, %s, %s, 'x', 0.6, 1.8)",
            (bet, position, pick),
        )
    sports = db.execute(
        "SELECT k.sport FROM core.user_bet_legs l JOIN core.picks k ON k.id = l.pick_id WHERE l.bet_id = %s ORDER BY l.position",
        (bet,),
    ).fetchall()
    assert [r["sport"] for r in sports] == ["nba", "futbol"]


def test_bet_must_be_registered_before_first_start(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        with db.transaction():
            db.execute(
                """
                INSERT INTO core.user_bets (user_id, bookmaker, stake, odd, model_probability, created_at, first_start)
                VALUES (%s, 'Caliente', 100, 2.0, 0.5, '2026-10-21T23:31:00+00:00', %s)
                """,
                (owner_id(db), STARTS),
            )


def test_parlay_slots_are_per_sport(db):
    insert = """
        INSERT INTO core.parlays (sport, day, mode, n_legs, probability, model_version, evaluated_at)
        VALUES (%s, '2026-10-21', 'prob', 3, 0.4, 'v1', now())
    """
    db.execute(insert, ("nba",))
    db.execute(insert, ("futbol",))
    with pytest.raises(psycopg.errors.UniqueViolation):
        with db.transaction():
            db.execute(insert, ("nba",))


def test_accounts_constraints(db):
    db.execute("INSERT INTO core.users (username) VALUES ('cliente')")
    for bad in (
        "INSERT INTO core.users (username) VALUES ('CLIENTE')",  # mismo usuario sin importar mayúsculas
        "INSERT INTO core.users (username) VALUES ('con espacio')",
        "INSERT INTO core.users (username, role) VALUES ('otro', 'vip')",
        "INSERT INTO core.users (username, subscription_until) VALUES ('otro', '2026-11-08')",  # free con vencimiento
        "INSERT INTO core.users (username, password_hash) VALUES ('otro', 'bolas')",  # nunca en claro
    ):
        with pytest.raises((psycopg.errors.UniqueViolation, psycopg.errors.CheckViolation)):
            with db.transaction():
                db.execute(bad)


def test_every_bet_has_an_owner_that_cannot_be_deleted(db):
    with pytest.raises(psycopg.errors.NotNullViolation):
        with db.transaction():
            db.execute(
                """
                INSERT INTO core.user_bets (bookmaker, stake, odd, model_probability, created_at, first_start)
                VALUES ('Caliente', 100, 2.0, 0.5, now(), %s)
                """,
                (STARTS,),
            )
    db.execute(
        """
        INSERT INTO core.user_bets (user_id, bookmaker, stake, odd, model_probability, created_at, first_start)
        VALUES (%s, 'Caliente', 100, 2.0, 0.5, now(), %s)
        """,
        (owner_id(db), STARTS),
    )
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with db.transaction():
            db.execute("DELETE FROM core.users WHERE username = 'GorgoAdmin'")
