"""Historial de jugadores: remates llevados al total del equipo (definición nueva de la API, fútbol v3)."""

from datetime import date, timedelta

import pandas as pd
import pytest

from app.sports.futbol.engine.history import SHOTS_FACTOR_MAX, History
from app.sports.futbol.engine.player_model import PlayerModel

LIGA_MX = 262


def _fixture(fixture_id: int, day: date) -> dict:
    return {
        "id": fixture_id, "league_id": LIGA_MX, "season": 2026, "round": "R", "match_date": day, "starts_at": None,
        "status": "FT", "is_finished": True, "home_team_id": 1, "away_team_id": 2, "ft_home": 1, "ft_away": 0,
        "referee": None, "home_xg": None, "away_xg": None, "home_cards": 2, "away_cards": 2,
        "home_shots_on": None, "away_shots_on": None,
    }


def _player(fixture_id: int, day: date, player_id: int, team_id: int, shots: float, team_shots: float | None,
            minutes: int = 90, substitute: bool = False) -> dict:
    return {
        "fixture_id": fixture_id, "player_id": player_id, "team_id": team_id, "match_date": day, "league_id": LIGA_MX,
        "opponent_id": 3 - team_id, "is_home": team_id == 1, "minutes": minutes, "position": "F",
        "is_substitute": substitute, "goals": 0, "assists": 0, "shots": shots, "shots_on": 0, "cards": 0,
        "team_shots": team_shots,
    }


def _history(fixtures: list[dict], players: list[dict]) -> History:
    f = pd.DataFrame(fixtures)
    f["match_date"] = pd.to_datetime(f["match_date"])
    ps = pd.DataFrame(players)
    ps["match_date"] = pd.to_datetime(ps["match_date"])
    return History(fixtures=f, player_stats=ps, team_names={}, player_names={}, league_names={})


def test_player_shots_are_scaled_to_the_team_total_and_stay_raw_for_results():
    day = date(2026, 9, 12)
    hist = _history([_fixture(1, day)], [
        # Definición vieja: 4 + 2 = 6 sin los bloqueados; el equipo tuvo 9.
        _player(1, day, 10, 1, 4, 9), _player(1, day, 11, 1, 2, 9), _player(1, day, 12, 1, 0, 9),
        # Definición nueva: ya suman el total del equipo.
        _player(1, day, 20, 2, 3, 5), _player(1, day, 21, 2, 2, 5),
    ])
    ps = hist.player_stats.set_index("player_id")
    assert ps["shots_factor"].to_dict() == {10: 1.5, 11: 1.5, 12: 1.5, 20: 1.0, 21: 1.0}
    assert ps["shots_model"].to_dict() == {10: 6.0, 11: 3.0, 12: 0.0, 20: 3.0, 21: 2.0}
    assert ps["shots"].to_dict() == {10: 4.0, 11: 2.0, 12: 0.0, 20: 3.0, 21: 2.0}


@pytest.mark.parametrize(
    ("player_shots", "team_shots", "factor"),
    [
        ((2, 1), None, 1.0),  # sin estadísticas del equipo: no se sabe, se deja igual
        ((0, 0), 4, 1.0),  # nadie remató según los jugadores: no hay a quién repartir
        ((3, 2), 4, 1.0),  # los jugadores suman más que el equipo: no se reduce
        ((1, 0), 9, SHOTS_FACTOR_MAX),  # falta algún jugador: tope
    ],
)
def test_shots_factor_edge_cases(player_shots, team_shots, factor):
    day = date(2026, 9, 12)
    players = [_player(1, day, 10 + i, 1, s, team_shots) for i, s in enumerate(player_shots)]
    hist = _history([_fixture(1, day)], players)
    assert hist.player_stats["shots_factor"].tolist() == [factor] * len(player_shots)


def test_shots_factor_is_one_without_team_shots_column():
    day = date(2026, 9, 12)
    row = _player(1, day, 10, 1, 2, None)
    del row["team_shots"]
    hist = _history([_fixture(1, day)], [row])
    assert hist.player_stats["shots_model"].tolist() == [2.0]


def test_player_model_rates_use_scaled_shots_and_hit_rate_uses_raw_shots():
    start = date(2026, 8, 1)
    fixtures, players = [], []
    for i in range(6):
        day = start + timedelta(days=7 * i)
        fixtures.append(_fixture(i + 1, day))
        # Definición vieja en los dos equipos (2 remates de jugadores, 3 del equipo): factor 1.5 para todos, así
        # que también el promedio de la posición escala 1.5.
        players += [_player(i + 1, day, 10, 1, 2, 3), _player(i + 1, day, 11, 1, 0, 3),
                    _player(i + 1, day, 20, 2, 2, 3)]
    as_of = start + timedelta(days=60)
    model = PlayerModel(_history(fixtures, players), as_of)
    raw = PlayerModel(_history(fixtures, [{**p, "team_shots": None} for p in players]), as_of)
    assert model.profiles.at[10, "rate_shots"] == pytest.approx(raw.profiles.at[10, "rate_shots"] * 1.5)
    assert model.profiles.at[10, "rate_goals"] == pytest.approx(raw.profiles.at[10, "rate_goals"])
    assert model.hit_rate(10, "shots", 3, 10) == (0, 6)  # nunca tuvo 3 remates según la API
    assert model.hit_rate(10, "shots", 2, 10) == (6, 6)
