"""Parte común del registro (core.tracking y core.bets) contra PostgreSQL real, con partidos sintéticos.

Los contratos de NBA y fútbol son los reales (liquidación, textos, registro de partidos); sólo el motor que
genera las piernas se sustituye por piernas fijas.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from app.core.bets import LegInput, create_bet, list_bets
from app.core.parlay import Candidate
from app.core.tracking import performance_data, performance_report, record_picks, settle_all
from app.sports import all_sports
from app.sports.futbol.engine.legs import LegSpec as FutbolLeg
from app.sports.futbol.matches import sync_matches as sync_futbol
from app.sports.nba.engine.legs import LegSpec as NbaLeg
from app.sports.nba.matches import sync_matches as sync_nba
from tests.integration.helpers import add_futbol_fixture, add_nba_game

DAY = date(2026, 10, 21)
EARLY, LATE = "2026-10-21T23:30:00+00:00", "2026-10-22T02:00:00+00:00"
BEFORE = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
BETWEEN = datetime(2026, 10, 22, 0, 0, tzinfo=timezone.utc)  # empezó el primero, no el segundo
AFTER = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)


@dataclass
class Card:
    external_id: int
    starts_at: pd.Timestamp
    candidates: list


def with_engine(sport_key: str, cards: list[Card]):
    """El contrato real del deporte con un motor que devuelve piernas fijas."""
    sport = all_sports()[sport_key]
    return replace(
        sport,
        generate_day=lambda conn, hist, day, bookmaker, models=None: cards,
        save_projections=lambda conn, cards, now: None,
    )


def card(sport: str, match: int, starts: str, legs: list[tuple]) -> Card:
    """Cada pierna: (spec, descripción, p, momio de la casa del sistema[, momios de las casas de la lista])."""
    return Card(
        match,
        pd.Timestamp(starts),
        [
            Candidate(sport, match, "A vs B", spec, desc, p, odd=odd, book_odds=books[0] if books else {})
            for spec, desc, p, odd, *books in legs
        ],
    )


def nba_legs(match: int, starts: str, p_home: float = 0.7) -> Card:
    return card("nba", match, starts, [
        (NbaLeg("ml", "home"), f"Gana local {match}", p_home, 1.5),
        (NbaLeg("ml", "away"), f"Gana visitante {match}", 1 - p_home, 2.6),
        (NbaLeg("total", "over", 220.5), f"Más de 220.5 ({match})", 0.65, None),
    ])


def test_records_picks_and_parlays_and_freezes_started_parlays(db):
    add_nba_game(db, 1001, starts=EARLY)
    add_nba_game(db, 1002, starts=LATE, home=134, away=135)
    sport = with_engine("nba", [nba_legs(1001, EARLY), nba_legs(1002, LATE)])

    counts = record_picks(db, sport, None, DAY, "Bet365", now=BEFORE)
    assert counts == {"games": 2, "picks": 6, "parlays": 2}  # 2 piernas (máx. probabilidad y máx. valor)
    parlays = db.execute(
        """
        SELECT p.id, p.mode, p.n_legs, p.probability::float AS probability, array_agg(l.description ORDER BY l.position) AS legs
        FROM core.parlays p JOIN core.parlay_legs l ON l.parlay_id = p.id
        WHERE p.sport = 'nba' AND p.day = %s GROUP BY p.id ORDER BY p.mode
        """,
        (DAY,),
    ).fetchall()
    assert [(p["mode"], p["n_legs"], round(p["probability"], 4)) for p in parlays] == [("ev", 2, 0.49), ("prob", 2, 0.49)]
    assert sorted(parlays[0]["legs"]) == ["Gana local 1001", "Gana local 1002"]

    # Ya empezó el primer partido: sus piernas y los parlays que lo incluyen quedan congelados aunque
    # el modelo cambie para el segundo.
    sport = with_engine("nba", [nba_legs(1001, EARLY, p_home=0.9), nba_legs(1002, LATE, p_home=0.8)])
    counts = record_picks(db, sport, None, DAY, "Bet365", now=BETWEEN)
    assert counts == {"games": 1, "picks": 3, "parlays": 0}
    frozen = db.execute("SELECT id, probability::float AS probability FROM core.parlays WHERE sport = 'nba' ORDER BY mode").fetchall()
    assert [(p["id"], round(p["probability"], 4)) for p in frozen] == [(p["id"], 0.49) for p in parlays]
    p_first = db.execute(
        """
        SELECT k.p_model::float AS p FROM core.picks k JOIN core.matches m ON m.id = k.match_id
        WHERE m.external_id = 1001 AND k.market = 'ml' AND k.side = 'home'
        """
    ).fetchone()["p"]
    assert p_first == 0.7


def test_settles_both_sports_and_a_mixed_bet(db):
    add_nba_game(db, 1001, starts=EARLY)
    add_futbol_fixture(db, 1001, starts=EARLY)  # mismo ID de proveedor, otro deporte
    record_picks(db, with_engine("nba", [nba_legs(1001, EARLY)]), None, DAY, "Bet365", now=BEFORE)
    record_picks(
        db,
        with_engine("futbol", [card("futbol", 1001, EARLY, [
            (FutbolLeg("1x2", "home"), "Gana local", 0.62, 1.7),
            (FutbolLeg("btts", "yes"), "Ambos anotan", 0.55, 1.8),
        ])]),
        None, DAY, "Bet365", now=BEFORE,
    )
    pick = {
        (r["sport"], r["description"]): r["id"]
        for r in db.execute("SELECT sport, description, id FROM core.picks")
    }
    owner = db.execute("SELECT id FROM core.users WHERE username = 'GorgoAdmin'").fetchone()["id"]
    bet = create_bet(
        db, owner, "Caliente", 100,
        [LegInput(pick[("nba", "Gana local 1001")], 1.5), LegInput(pick[("futbol", "Gana local")], 1.7)],
        BEFORE,
    )

    # Terminan los dos partidos: gana el local en ambos (110-100 y 2-1).
    db.execute("UPDATE nba.games SET status = 'FT', home_total = 110, away_total = 100 WHERE id = 1001")
    db.execute("UPDATE futbol.fixtures SET status = 'FT', ft_home = 2, ft_away = 1, goals_home = 2, goals_away = 1 WHERE id = 1001")
    sync_nba(db, [1001])
    sync_futbol(db, [1001])

    counts = settle_all(db, all_sports().values(), now=AFTER)
    assert counts["picks"] == 5 and counts["bets"] == 1
    results = {(r["sport"], r["description"]): r["result"] for r in db.execute("SELECT sport, description, result FROM core.picks")}
    assert results == {
        ("nba", "Gana local 1001"): "won",
        ("nba", "Gana visitante 1001"): "lost",
        ("nba", "Más de 220.5 (1001)"): "lost",  # 210 puntos
        ("futbol", "Gana local"): "won",
        ("futbol", "Ambos anotan"): "won",
    }

    bets = list_bets(db, owner, AFTER, all_sports())
    item = next(b for b in bets["items"] if b["id"] == bet)
    assert (item["result"], item["payout"]) == ("won", 255.0)  # 100 × 1.5 × 1.7
    assert [(leg["sport"], leg["matchup"], leg["outcome"]["text"]) for leg in item["legs"]] == [
        ("nba", "133 @ 132", "Ganó 132 110-100"),
        ("futbol", "Fútbol 132 vs Fútbol 133", "Terminó Fútbol 132 2-1 Fútbol 133"),
    ]
    assert bets["summary"]["won"] == 1


# ---------------------------------------------------------------- momio de publicación y CLV

CLOSE = datetime(2026, 10, 21, 23, 20, tzinfo=timezone.utc)  # 10 min antes del primer partido


def priced(match: int, starts: str, legs: list[tuple]) -> Card:
    """Tarjeta con piernas (spec, descripción, p_modelo, momio, p_mercado, p_Pinnacle)."""
    return Card(
        match,
        pd.Timestamp(starts),
        [Candidate("nba", match, "A vs B", spec, desc, p, odd=odd, bookmaker="Bet365" if odd else None, p_market=pm,
                   p_sharp=ps)
         for spec, desc, p, odd, pm, ps in legs],
    )


def test_first_price_is_kept_and_the_last_price_is_the_close(db):
    add_nba_game(db, 1001, starts=EARLY)
    publish = [priced(1001, EARLY, [
        (NbaLeg("ml", "home"), "Gana local", 0.55, 2.10, 0.47, 0.46),
        (NbaLeg("total", "over", 220.5), "Más de 220.5", 0.65, None, None, None),  # todavía sin momio
    ])]
    close = [priced(1001, EARLY, [
        (NbaLeg("ml", "home"), "Gana local", 0.58, 1.90, 0.52, 0.53),
        (NbaLeg("total", "over", 220.5), "Más de 220.5", 0.66, 1.95, 0.50, 0.49),
    ])]
    record_picks(db, with_engine("nba", publish), None, DAY, "Bet365", now=BEFORE)
    record_picks(db, with_engine("nba", close), None, DAY, "Bet365", now=CLOSE)
    # Ya empezó: una corrida posterior no toca nada.
    record_picks(db, with_engine("nba", publish), None, DAY, "Bet365", now=BETWEEN)

    rows = {
        r["description"]: r
        for r in db.execute(
            """
            SELECT description, odd::float, p_market::float, p_sharp::float, evaluated_at, first_odd::float,
                   first_p_model::float, first_p_market::float, first_p_sharp::float, first_priced_at
            FROM core.picks
            """
        )
    }
    home, over = rows["Gana local"], rows["Más de 220.5"]
    first = ("first_odd", "first_p_model", "first_p_market", "first_p_sharp", "first_priced_at")
    assert tuple(home[k] for k in first) == (2.10, 0.55, 0.47, 0.46, BEFORE)
    assert (home["odd"], home["p_market"], home["p_sharp"], home["evaluated_at"]) == (1.90, 0.52, 0.53, CLOSE)
    # Sin momio al publicarse: su momio de publicación (y su probabilidad de Pinnacle) es el primero que tuvo.
    assert tuple(over[k] for k in first if k != "first_p_market") == (1.95, 0.66, 0.49, CLOSE)


def test_performance_reports_clv_against_the_pinnacle_close(db):
    add_nba_game(db, 1001, starts=EARLY)
    add_nba_game(db, 1002, starts=LATE, home=134, away=135)  # su última evaluación queda lejos del inicio
    late = (NbaLeg("ml", "home"), "Gana local 1002", 0.60, 2.00, 0.50, 0.50)
    # (spec, descripción, p_modelo, momio, p_mercado, p_Pinnacle) al publicar y al cierre.
    publish = [
        priced(1001, EARLY, [
            (NbaLeg("ml", "home"), "Gana local", 0.55, 2.10, 0.47, 0.47),
            (NbaLeg("ml", "away"), "Gana visitante", 0.45, 1.80, 0.53, 0.53),
            (NbaLeg("total", "over", 215.5), "Más de 215.5", 0.60, 1.90, 0.31, 0.30),
            (NbaLeg("total", "over", 220.5), "Más de 220.5", 0.65, None, None, None),
            (NbaLeg("total", "under", 220.5), "Menos de 220.5", 0.55, None, None, None),
            (NbaLeg("total", "over", 240.5), "Más de 240.5", 0.12, 11.0, 0.085, 0.085),
        ]),
        priced(1002, LATE, [late]),
    ]
    close = [
        priced(1001, EARLY, [
            (NbaLeg("ml", "home"), "Gana local", 0.58, 1.90, 0.52, 0.52),
            (NbaLeg("ml", "away"), "Gana visitante", 0.42, 1.95, 0.48, 0.48),
            (NbaLeg("total", "over", 215.5), "Más de 215.5", 0.60, 1.90, 0.31, 0.30),
            (NbaLeg("total", "over", 220.5), "Más de 220.5", 0.65, 1.95, 0.50, None),  # Pinnacle no la cotiza
            (NbaLeg("total", "under", 220.5), "Menos de 220.5", 0.55, 2.00, 0.50, 0.50),
            (NbaLeg("total", "over", 240.5), "Más de 240.5", 0.12, 11.0, 0.095, 0.095),
        ]),
        priced(1002, LATE, [late]),
    ]
    record_picks(db, with_engine("nba", publish), None, DAY, "Bet365", now=BEFORE)
    record_picks(db, with_engine("nba", close), None, DAY, "Bet365", now=CLOSE)

    # Gana el local 110-100 en los dos partidos (210 puntos).
    db.execute("UPDATE nba.games SET status = 'FT', home_total = 110, away_total = 100 WHERE id IN (1001, 1002)")
    sync_nba(db, [1001, 1002])
    settle_all(db, [all_sports()["nba"]], now=AFTER)

    data = performance_data(db, all_sports()["nba"], include_preseason=True)
    clv = data["clv"]
    # CLV = momio de publicación × probabilidad de Pinnacle al cierre − 1. Sólo cuenta el local: tenía valor
    # (0.55 × 2.10), Pinnacle cotizaba su cierre y se publicó 11 h antes.
    value = clv["value"]
    assert (value["n"], value["beat_rate"]) == (1, 1.0)
    assert (value["avg"], value["median"]) == (pytest.approx(2.10 * 0.52 - 1), pytest.approx(2.10 * 0.52 - 1))
    assert (value["n_move"], value["avg_move"]) == (1, pytest.approx(0.05))  # Pinnacle subió 5 pts hacia el local
    # Momio de 10 o más: aparte.
    assert clv["long_shots"]["n"] == 1
    assert clv["long_shots"]["avg"] == pytest.approx(11.0 * 0.095 - 1)
    # Referencia: los dos lados del ganador (el visitante no tenía valor: 0.45 × 1.80).
    assert clv["all"]["n"] == 2
    assert clv["all"]["avg"] == pytest.approx(((2.10 * 0.52 - 1) + (1.80 * 0.48 - 1)) / 2)
    # Con valor pero no cuentan: el del partido 1002 (última lectura 2 h 40 min antes del inicio), más de 220.5
    # (Pinnacle no la cotizaba al cierre), menos de 220.5 (publicada en el cierre mismo) y más de 215.5 (1.90 contra
    # 30% de Pinnacle: precio dudoso).
    assert clv["excluded"] == {"no_close": 1, "no_reference": 1, "short_window": 1, "doubtful": 1}
    assert clv["hours_before"] == pytest.approx(11.5)  # mediana: 4 piernas de 11.5 h y 2 de 10 min
    by_market = {m["market"]: (m["clv_n"], m["clv"]) for m in data["by_market"]}
    assert by_market["ml"] == (1, pytest.approx(2.10 * 0.52 - 1))
    assert by_market["total"] == (0, None)

    report = performance_report(db, all_sports()["nba"], include_preseason=True)
    assert "Con valor al publicarse (momio < 10): n=1  CLV prom.=+9.2%  mediana=+9.2%  le ganan al cierre=100.0%" in report
    assert (
        "Piernas con valor que no cuentan: 1 sin lectura a ≤90 min del inicio · 1 sin Pinnacle al cierre · "
        "1 publicada a menos de 2 h del cierre · 1 con precio dudoso (a más de 20% del precio justo al publicarse)"
    ) in report


def test_performance_without_first_prices_has_no_clv(db):
    # Piernas registradas antes de guardar el momio de publicación (o importadas): sin CLV.
    add_nba_game(db, 1001, starts=EARLY)
    record_picks(db, with_engine("nba", [nba_legs(1001, EARLY)]), None, DAY, "Bet365", now=BEFORE)
    db.execute(
        "UPDATE core.picks SET first_odd = NULL, first_p_model = NULL, first_p_market = NULL, first_p_sharp = NULL, "
        "first_priced_at = NULL"
    )
    db.execute("UPDATE nba.games SET status = 'FT', home_total = 110, away_total = 100 WHERE id = 1001")
    sync_nba(db, [1001])
    settle_all(db, [all_sports()["nba"]], now=AFTER)

    data = performance_data(db, all_sports()["nba"], include_preseason=True)
    assert data["legs"]["settled"] == 3
    assert data["clv"] is None
    assert all(m["clv"] is None and m["clv_n"] == 0 for m in data["by_market"])
