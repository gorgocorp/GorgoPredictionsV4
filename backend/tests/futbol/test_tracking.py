from datetime import datetime, timedelta, timezone

import pytest

from app.core.evidence import summarize
from app.sports.futbol.engine.evidence import leg_outcome
from app.sports.futbol.engine.tracking import models_day, pick_result

NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def _row(**overrides):
    row = {
        "market": "player", "side": "over", "line": 0.5, "team": None, "stat": "goals", "player_id": 1,
        "status": "FT", "starts_at": NOW - timedelta(hours=10), "ft_home": 2, "ft_away": 1,
        "home_cards": 3, "away_cards": 2, "minutes": 90, "goals": 1, "assists": 0, "shots_total": 4,
        "shots_on": 2, "yellow": 1, "red": 0, "fixture_has_players": True,
        "home_name": "América", "away_name": "Chivas",
    }
    row.update(overrides)
    return row


def test_team_legs():
    team = dict(stat=None, player_id=None, line=None)
    assert pick_result(_row(market="1x2", side="home", **team), NOW) == "won"
    assert pick_result(_row(market="btts", side="no", **team), NOW) == "lost"
    assert pick_result(_row(market="total", side="over", **{**team, "line": 3.5}), NOW) == "lost"
    assert pick_result(_row(market="cards", side="over", **{**team, "line": 4.5}), NOW) == "won"


def test_extra_time_does_not_count():
    # ft_* es el marcador de 90': un partido que terminó 1-1 y se definió en el alargue es empate.
    assert pick_result(_row(market="1x2", side="draw", stat=None, player_id=None, status="AET", ft_home=1, ft_away=1), NOW) == "won"


@pytest.mark.parametrize(
    "stat, line, expected",
    [("goals", 0.5, "won"), ("goals", 1.5, "lost"), ("ga", 0.5, "won"), ("shots_on", 1.5, "won"), ("shots", 4.5, "lost"), ("cards", 0.5, "won")],
)
def test_player_legs(stat, line, expected):
    assert pick_result(_row(stat=stat, line=line), NOW) == expected


def test_player_did_not_play_is_void():
    assert pick_result(_row(minutes=0), NOW) == "void"
    assert pick_result(_row(minutes=None), NOW) == "void"  # hay estadísticas del partido pero no del jugador


def test_waits_for_stats_then_voids_after_grace():
    missing = dict(minutes=None, fixture_has_players=False)
    assert pick_result(_row(**missing), NOW) is None
    assert pick_result(_row(**missing, starts_at=NOW - timedelta(days=3)), NOW) == "void"
    no_cards = dict(market="cards", side="over", line=4.5, stat=None, player_id=None, home_cards=None)
    assert pick_result(_row(**no_cards), NOW) is None
    assert pick_result(_row(**no_cards, starts_at=NOW - timedelta(days=3)), NOW) == "void"


def test_cancelled_fixture_is_void():
    assert pick_result(_row(status="PST", ft_home=None, ft_away=None), NOW) == "void"


def test_leg_outcome_texts():
    team = dict(stat=None, player_id=None, line=None)
    assert leg_outcome(_row(market="1x2", side="home", **team))["text"] == "Terminó América 2-1 Chivas"
    assert leg_outcome(_row(market="total", side="over", **team)) == {"value": 3, "text": "3 goles (2-1)"}
    assert leg_outcome(_row(market="btts", side="yes", **team))["text"] == "Anotaron ambos (2-1)"
    assert leg_outcome(_row(market="cards", side="over", **team))["text"] == "5 tarjetas (América 3, Chivas 2)"
    assert leg_outcome(_row(market="team_total", side="over", team="away", **{k: v for k, v in team.items()}))["text"] == "Chivas anotó 1"
    assert leg_outcome(_row())["text"] == "1 goles en 90 min"
    assert leg_outcome(_row(minutes=0))["text"] == "No jugó"
    assert leg_outcome(_row(status="NS"))["text"] == "Programado"
    assert leg_outcome(_row(status="2H"))["text"] == "En juego"


def test_summary_counts_expected_wins_and_units():
    parlays = [
        {"n_legs": 2, "probability": 0.75, "result": "won", "settled_odd": 1.40},
        {"n_legs": 2, "probability": 0.70, "result": "lost", "settled_odd": 1.50},
        {"n_legs": 3, "probability": 0.60, "result": "won", "settled_odd": None},
        {"n_legs": 3, "probability": 0.55, "result": None, "settled_odd": None},
    ]
    s = summarize(parlays)
    assert (s["parlays"], s["settled"], s["won"], s["lost"], s["pending"]) == (4, 3, 2, 1, 1)
    assert s["expected_wins"] == pytest.approx(2.05)
    assert s["profit_units"] == pytest.approx(0.40 - 1.0)


def test_models_day_reuses_tomorrow_for_later_days():
    from datetime import date

    today = date(2026, 10, 8)
    assert models_day(today, today) == today
    assert models_day(today, date(2026, 10, 9)) == date(2026, 10, 9)
    assert models_day(today, date(2026, 10, 11)) == date(2026, 10, 9)
