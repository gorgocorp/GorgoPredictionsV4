"""Parte común del registro (core.tracking y core.bets) contra PostgreSQL real, con partidos sintéticos.

Los contratos de NBA y fútbol son los reales (liquidación, textos, registro de partidos); sólo el motor que
genera las piernas se sustituye por piernas fijas.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime, timezone

import pandas as pd

from app.core.bets import LegInput, create_bet, list_bets
from app.core.parlay import Candidate
from app.core.tracking import record_picks, settle_all
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
    return Card(
        match,
        pd.Timestamp(starts),
        [Candidate(sport, match, "A vs B", spec, desc, p, odd=odd) for spec, desc, p, odd in legs],
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
    bet = create_bet(
        db, "Caliente", 100,
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

    bets = list_bets(db, AFTER, all_sports())
    item = next(b for b in bets["items"] if b["id"] == bet)
    assert (item["result"], item["payout"]) == ("won", 255.0)  # 100 × 1.5 × 1.7
    assert [(leg["sport"], leg["matchup"], leg["outcome"]["text"]) for leg in item["legs"]] == [
        ("nba", "133 @ 132", "Ganó 132 110-100"),
        ("futbol", "Fútbol 132 vs Fútbol 133", "Terminó Fútbol 132 2-1 Fútbol 133"),
    ]
    assert bets["summary"]["won"] == 1
