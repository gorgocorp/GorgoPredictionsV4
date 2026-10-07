import pytest

from app.core.evidence import summarize
from app.sports.nba.engine.evidence import leg_outcome

GAME = {"status": "FT", "home_total": 112, "away_total": 104, "home_name": "Utah Jazz", "away_name": "Denver Nuggets"}


def leg(**overrides):
    row = {"market": "ml", "side": "home", "line": None, "team": None, "stat": None, **GAME}
    row.update(overrides)
    return row


def test_team_market_outcomes():
    assert leg_outcome(leg())["text"] == "Ganó Jazz 112-104"
    assert leg_outcome(leg(market="spread", side="away", line=6.5)) == {"value": -8, "text": "Nuggets perdió por 8"}
    assert leg_outcome(leg(market="total", side="over", line=210.5)) == {"value": 216, "text": "Total: 216 pts (104-112)"}
    assert leg_outcome(leg(market="team_total", side="over", line=100.5, team="away"))["text"] == "Nuggets anotó 104"


def test_player_outcomes():
    base = dict(market="player", side="over", line=24.5, stat="points", seconds_played=2100,
                points=31, rebounds=12, assists=9, fg3_made=2, fgm=11, game_has_stats=True)
    assert leg_outcome(leg(**base)) == {"value": 31, "text": "31 puntos"}
    assert leg_outcome(leg(**{**base, "stat": "pra"}))["text"] == "52 pts+reb+ast"
    assert leg_outcome(leg(**{**base, "seconds_played": 0}))["text"] == "No jugó"
    assert leg_outcome(leg(**{**base, "seconds_played": None}))["text"] == "No jugó"
    assert leg_outcome(leg(**{**base, "seconds_played": None, "game_has_stats": False}))["text"] == "Sin estadísticas todavía"


def test_unfinished_and_cancelled_games():
    assert leg_outcome(leg(status="NS"))["text"] == "Programado"
    assert leg_outcome(leg(status="Q3"))["text"] == "En juego"
    assert leg_outcome(leg(status="POST"))["value"] is None


def test_summary_counts_expected_wins_and_units():
    parlays = [
        {"n_legs": 2, "probability": 0.75, "result": "won", "settled_odd": 1.40},
        {"n_legs": 2, "probability": 0.70, "result": "lost", "settled_odd": 1.50},
        {"n_legs": 3, "probability": 0.60, "result": "won", "settled_odd": None},  # sin momio: no entra a unidades
        {"n_legs": 3, "probability": 0.55, "result": None, "settled_odd": None},
        {"n_legs": 4, "probability": 0.50, "result": "void", "settled_odd": None},
    ]
    s = summarize(parlays)
    assert (s["parlays"], s["settled"], s["won"], s["lost"], s["void"], s["pending"]) == (5, 3, 2, 1, 1, 1)
    assert s["expected_wins"] == pytest.approx(0.75 + 0.70 + 0.60)
    assert s["with_odds"] == 2
    assert s["profit_units"] == pytest.approx(0.40 - 1.0)
    assert s["roi"] == pytest.approx(-0.30)
    assert [b["n_legs"] for b in s["by_size"]] == [2, 3, 4]
    assert s["by_size"][0] == {"n_legs": 2, "parlays": 2, "settled": 2, "won": 1, "expected": pytest.approx(1.45)}


def test_summary_without_odds_has_no_units():
    s = summarize([{"n_legs": 2, "probability": 0.7, "result": "won", "settled_odd": None}])
    assert s["profit_units"] is None and s["roi"] is None
