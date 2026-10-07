from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.sports.nba.ingest import normalize

FETCHED = datetime(2026, 10, 5, tzinfo=timezone.utc)


def _game(**overrides):
    game = {
        "id": 519490,
        "date": "2026-10-06T02:00:00+00:00",
        "venue": "Golden",
        "status": {"long": "Not Started", "short": "NS", "timer": None},
        "league": {"id": 12, "season": "2026-2027"},
        "teams": {"home": {"id": 157, "name": "Sacramento Kings"}, "away": {"id": 145, "name": "Los Angeles Lakers"}},
        "scores": {
            side: {"quarter_1": None, "quarter_2": None, "quarter_3": None, "quarter_4": None, "over_time": None, "total": None}
            for side in ("home", "away")
        },
    }
    game.update(overrides)
    return game


def _player_stat(**overrides):
    row = {
        "game": {"id": 500996},
        "team": {"id": 158},
        "player": {"id": 999, "name": "Vassell Devin"},
        "type": "starters",
        "minutes": "39:12",
        "field_goals": {"total": 3, "attempts": 3, "percentage": None},
        "threepoint_goals": {"total": 2, "attempts": 5, "percentage": None},
        "freethrows_goals": {"total": 0, "attempts": 0, "percentage": None},
        "rebounds": {"total": 7},
        "assists": 2,
        "points": 12,
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize("raw, expected", [("39:12", 2352), ("25", 1500), ("00:00", 0), (None, None), ("", None)])
def test_parse_minutes(raw, expected):
    assert normalize.parse_minutes(raw) == expected


def test_parse_minutes_rejects_garbage():
    with pytest.raises(normalize.InvalidRecord):
        normalize.parse_minutes("DNP")


def test_game_date_uses_eastern_time():
    # 02:00 UTC del 6 de octubre = 10 pm ET del 5 de octubre.
    row = normalize.game_row(_game(), FETCHED)
    assert row["game_date"] == date(2026, 10, 5)
    assert row["season"] == "2026-2027"
    assert row["home_team_id"] == 157 and row["away_team_id"] == 145


def test_game_rejects_same_team_both_sides():
    raw = _game(teams={"home": {"id": 157}, "away": {"id": 157}})
    with pytest.raises(normalize.InvalidRecord):
        normalize.game_row(raw, FETCHED)


def test_franchise_filter_excludes_all_star_teams():
    assert normalize.is_franchise_game(_game(teams={"home": {"id": 133}, "away": {"id": 161}}))
    assert not normalize.is_franchise_game(_game(teams={"home": {"id": 0}, "away": {"id": 0}}))
    assert not normalize.is_franchise_game(_game(teams={"home": {"id": 1414}, "away": {"id": 133}}))


def test_field_goals_are_two_pointers():
    _, stats = normalize.player_rows(_player_stat(), FETCHED)
    assert (stats["fg2_made"], stats["fg3_made"], stats["points"]) == (3, 2, 12)
    assert stats["fg2_made_derived"] == 3
    assert stats["is_starter"] is True
    assert stats["seconds_played"] == 2352


def test_derived_two_pointers_when_api_reports_zero():
    # Caso real: 40 puntos con 6 triples y 4 libres, pero field_goals 0/0.
    raw = _player_stat(
        points=40,
        field_goals={"total": 0, "attempts": 0},
        threepoint_goals={"total": 6, "attempts": 10},
        freethrows_goals={"total": 4, "attempts": 4},
    )
    _, stats = normalize.player_rows(raw, FETCHED)
    assert stats["fg2_made"] == 0
    assert stats["fg2_made_derived"] == 9


@pytest.mark.parametrize("points, fg3, ft, expected", [(None, 0, 0, None), (5, 2, 0, None), (3, 0, 0, None), (0, 0, 0, 0)])
def test_derive_fg2_made_rejects_impossible(points, fg3, ft, expected):
    assert normalize.derive_fg2_made(points, fg3, ft) == expected


def test_player_without_id_is_rejected():
    with pytest.raises(normalize.InvalidRecord):
        normalize.player_rows(_player_stat(player={"id": None, "name": "X"}), FETCHED)


def test_odds_rows_flatten_and_clean():
    raw = {
        "game": {"id": 519490},
        "bookmakers": [
            {
                "id": 8,
                "name": "Bet365",
                "bets": [
                    {"id": 2, "name": "Home/Away", "values": [{"value": "Home", "odd": "2.68"}, {"value": "Away", "odd": "1.43"}]},
                    {"id": 4, "name": "Over/Under", "values": [
                        {"value": "Over 226.5", "odd": "1.61"},
                        {"value": "Over 226.5", "odd": "1.61"},  # duplicado exacto
                        {"value": "Under 226.5", "odd": "N/A"},  # no numérico
                        {"value": "Under 227", "odd": "1.00"},   # imposible
                    ]},
                ],
            }
        ],
    }
    rows = normalize.odds_rows(raw)
    assert [(r["bet_id"], r["selection"], r["odd"]) for r in rows] == [
        (2, "Home", Decimal("2.68")),
        (2, "Away", Decimal("1.43")),
        (4, "Over 226.5", Decimal("1.61")),
    ]
