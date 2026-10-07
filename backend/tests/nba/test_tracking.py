from datetime import datetime, timedelta, timezone

import pytest

from app.sports.nba.engine.tracking import pick_result as _pick_result

NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def _row(**overrides):
    row = {
        "market": "player", "side": "over", "line": 19.5, "team": None, "stat": "points", "player_id": 1,
        "status": "FT", "starts_at": NOW - timedelta(hours=10), "home_total": 110, "away_total": 100,
        "seconds_played": 1800, "points": 22, "rebounds": 5, "assists": 4, "fg3_made": 2, "fgm": 8,
        "game_has_stats": True,
    }
    row.update(overrides)
    return row


def test_team_leg():
    assert _pick_result(_row(market="ml", side="home", line=None, stat=None, player_id=None), NOW) == "won"
    assert _pick_result(_row(market="total", side="over", line=215.5, stat=None, player_id=None), NOW) == "lost"


@pytest.mark.parametrize(
    "stat, line, expected",
    [("points", 19.5, "won"), ("points", 22.5, "lost"), ("pra", 30.5, "won"), ("fgm", 8.5, "lost"), ("threes", 1.5, "won")],
)
def test_player_leg(stat, line, expected):
    assert _pick_result(_row(stat=stat, line=line), NOW) == expected


def test_player_did_not_play_is_void():
    assert _pick_result(_row(seconds_played=0), NOW) == "void"
    # Hay estadísticas del partido pero no del jugador.
    assert _pick_result(_row(seconds_played=None, points=None), NOW) == "void"


def test_waits_for_stats_then_voids_after_grace():
    missing = dict(seconds_played=None, points=None, game_has_stats=False)
    assert _pick_result(_row(**missing), NOW) is None
    assert _pick_result(_row(**missing, starts_at=NOW - timedelta(days=3)), NOW) == "void"


def test_cancelled_game_is_void():
    assert _pick_result(_row(status="POST"), NOW) == "void"
