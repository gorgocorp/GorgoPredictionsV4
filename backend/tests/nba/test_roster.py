import pandas as pd
import pytest

from app.sports.nba.engine.history import History
from app.sports.nba.engine.roster import roster_changes

A, B = 132, 133


def _history() -> History:
    games, stats = [], []
    # Temporada anterior: 15 partidos oficiales A vs B.
    for i in range(15):
        day = pd.Timestamp("2025-01-01") + pd.Timedelta(days=2 * i)
        games.append(dict(id=i + 1, season="2024-2025", game_date=day, starts_at=day, status="FT", phase="regular",
                          is_finished=True, home_team_id=A, away_team_id=B, home_total=110, away_total=105))
        for pid, team, mins, pts in ((1, A, 30, 20), (2, A, 25, 10), (3, B, 30, 15)):
            stats.append(dict(game_id=i + 1, player_id=pid, team_id=team, game_date=day, season="2024-2025",
                              phase="regular", opponent_id=B if team == A else A, is_home=team == A,
                              minutes=mins, points=pts, rebounds=5, assists=3, fg3_made=1, fgm=7))
    # Pretemporada nueva: el jugador 1 ya juega con B.
    day = pd.Timestamp("2025-10-05")
    games.append(dict(id=100, season="2025-2026", game_date=day, starts_at=day, status="FT", phase="preseason",
                      is_finished=True, home_team_id=B, away_team_id=A, home_total=100, away_total=98))
    for pid, team in ((1, B), (3, B), (2, A)):
        stats.append(dict(game_id=100, player_id=pid, team_id=team, game_date=day, season="2025-2026",
                          phase="preseason", opponent_id=A if team == B else B, is_home=team == B,
                          minutes=20, points=8, rebounds=3, assists=2, fg3_made=1, fgm=3))
    team_stats = pd.DataFrame(columns=["game_id", "game_date", "phase", "team_id", "opponent_id", "points", "rebounds", "assists", "fg3_made"])
    return History(pd.DataFrame(games), pd.DataFrame(stats), team_stats, {A: "A", B: "B"}, {1: "Uno", 2: "Dos", 3: "Tres"})


def test_trade_is_a_departure_and_an_arrival():
    changes = roster_changes(_history(), pd.Timestamp("2025-10-21"), "2025-2026")
    a, b = changes[A], changes[B]
    assert a.departed == [(1, 20.0)] and a.arrived == []
    assert b.arrived == [(1, 20.0)] and b.departed == []
    # A pierde 20 pts en los mismos minutos; B cambia 15 por 20 en sus 30 minutos de cierre.
    assert a.net_lost == pytest.approx(20.0)
    assert b.net_lost == pytest.approx(-5.0)
    # Sin partidos oficiales nuevos, todo el rating viene de la temporada anterior.
    assert a.weight == pytest.approx(1.0)
    assert a.adjustment == pytest.approx(20.0)


def test_injured_arrival_counts_by_probability_of_playing():
    changes = roster_changes(_history(), pd.Timestamp("2025-10-21"), "2025-2026", availability={1: "out"})
    assert changes[B].arrived == [(1, 0.0)]
    assert changes[B].net_lost == pytest.approx(0.0)
