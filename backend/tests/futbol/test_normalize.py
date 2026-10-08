import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.sports.futbol.ingest import normalize

FETCHED = datetime(2026, 10, 6, 20, 0, tzinfo=timezone.utc)
SAMPLES = Path(__file__).resolve().parents[1] / "fixtures" / "api_football"


def sample_1492399() -> dict:
    """Vitória-Chapecoense real: el bloque de jugadores de Chapecoense (132) llega como equipo 22722."""
    return json.loads((SAMPLES / "fixture_1492399.json").read_text(encoding="utf-8"))

FIXTURE = {
    "fixture": {
        "id": 1550894, "referee": "Yonatan Peinado Aguirre, Mexico", "timezone": "UTC",
        "date": "2026-07-17T01:00:00+00:00",
        "venue": {"id": 20474, "name": "Estadio Victoria", "city": "Aguascalientes"},
        "status": {"long": "Match Finished", "short": "FT", "elapsed": 90, "extra": 14},
    },
    "league": {"id": 262, "name": "Liga MX", "season": 2026, "round": "Apertura - 1"},
    "teams": {
        "home": {"id": 2288, "name": "Necaxa", "logo": "n.png", "winner": True},
        "away": {"id": 2312, "name": "Atlante FC", "logo": "a.png", "winner": False},
    },
    "goals": {"home": 2, "away": 1},
    "score": {"halftime": {"home": 0, "away": 0}, "fulltime": {"home": 2, "away": 1},
              "extratime": {"home": None, "away": None}, "penalty": {"home": None, "away": None}},
}


def test_fixture_row_uses_local_date_and_90_minute_score():
    row = normalize.fixture_row(FIXTURE, FETCHED)
    # 01:00 UTC del 17 de julio = 19:00 del 16 de julio en el centro de México.
    assert str(row["match_date"]) == "2026-07-16"
    assert (row["ft_home"], row["ft_away"], row["ht_home"]) == (2, 1, 0)
    assert row["referee"] == "Yonatan Peinado Aguirre, Mexico"
    assert row["season"] == 2026 and row["round"] == "Apertura - 1"


def test_extra_time_keeps_regular_time_score():
    raw = {**FIXTURE, "fixture": {**FIXTURE["fixture"], "status": {"short": "PEN", "elapsed": 120}},
           "goals": {"home": 2, "away": 2},
           "score": {"halftime": {"home": 1, "away": 0}, "fulltime": {"home": 1, "away": 1},
                     "extratime": {"home": 1, "away": 1}, "penalty": {"home": 4, "away": 3}}}
    row = normalize.fixture_row(raw, FETCHED)
    assert (row["ft_home"], row["ft_away"], row["goals_home"], row["pen_home"]) == (1, 1, 2, 4)


def test_same_team_both_sides_is_rejected():
    raw = {**FIXTURE, "teams": {"home": FIXTURE["teams"]["home"], "away": FIXTURE["teams"]["home"]}}
    with pytest.raises(normalize.InvalidRecord):
        normalize.fixture_row(raw, FETCHED)


def test_team_stats_rows_parse_percent_and_xg():
    raw = {**FIXTURE, "statistics": [{"team": {"id": 2288}, "statistics": [
        {"type": "Shots on Goal", "value": 5}, {"type": "Total Shots", "value": 12},
        {"type": "Ball Possession", "value": "54%"}, {"type": "Yellow Cards", "value": 2},
        {"type": "Red Cards", "value": None}, {"type": "expected_goals", "value": "1.37"},
    ]}]}
    (row,) = normalize.team_stats_rows(raw, FETCHED)
    assert (row["shots_on"], row["possession"], row["yellow"], row["red"]) == (5, 54, 2, 0)
    assert row["xg"] == Decimal("1.37")


def test_player_rows_zero_counts_only_when_played():
    def player(pid, minutes, sub, goals):
        return {"player": {"id": pid, "name": f"Jugador {pid}", "photo": None}, "statistics": [{
            "games": {"minutes": minutes, "position": "F", "rating": "7.1", "substitute": sub},
            "shots": {"total": None, "on": None}, "goals": {"total": goals, "assists": None},
            "cards": {"yellow": 0, "red": 0}, "fouls": {"committed": 1}, "passes": {"key": None},
            "penalty": {"scored": 0, "missed": 0},
        }]}

    raw = {**FIXTURE, "players": [{"team": {"id": 2288}, "players": [player(1, 90, False, 1), player(2, None, True, None)]}]}
    players, stats = normalize.player_stats_rows(raw, FETCHED)
    assert [p["name"] for p in players] == ["Jugador 1", "Jugador 2"]
    played, bench = stats
    assert (played["minutes"], played["goals"], played["shots_on"], played["assists"]) == (90, 1, 0, 0)
    assert (bench["minutes"], bench["goals"], bench["shots_on"]) == (0, None, None)


def test_injury_rows():
    raw = {"player": {"id": 129682, "name": "A. Adli", "type": "Missing Fixture", "reason": "Calf Injury"},
           "team": {"id": 35}, "fixture": {"id": 1557407}}
    player, row = normalize.injury_rows(raw, FETCHED)
    assert player["name"] == "A. Adli"
    assert (row["status"], row["reason"]) == ("out", "Calf Injury")
    raw["player"]["type"] = "Questionable"
    assert normalize.injury_rows(raw, FETCHED)[1]["status"] == "questionable"
    raw["player"]["type"] = "Otro"
    assert normalize.injury_rows(raw, FETCHED) is None


def test_odds_rows_skip_invalid_and_duplicates():
    raw = {"fixture": {"id": 1}, "bookmakers": [{"id": 8, "name": "Bet365", "bets": [
        {"id": 1, "name": "Match Winner", "values": [
            {"value": "Home", "odd": "1.38"}, {"value": "Draw", "odd": "4.50"}, {"value": "Away", "odd": "x"},
            {"value": "Home", "odd": "1.40"}, {"value": "", "odd": "2.0"}, {"value": "Away", "odd": "1.00"},
        ]},
    ]}]}
    rows = normalize.odds_rows(raw)
    assert {(r["selection"], r["odd"]) for r in rows} == {("Home", Decimal("1.40")), ("Draw", Decimal("4.50"))}


def test_lineup_rows():
    raw = {**FIXTURE, "lineups": [{"team": {"id": 2288}, "formation": "4-3-3",
                                   "startXI": [{"player": {"id": 1, "name": "Z. Suzuki", "pos": "G", "grid": "1:1"}}],
                                   "substitutes": [{"player": {"id": 2, "name": "B. Suplente", "pos": "M", "grid": None}}]}]}
    players, rows = normalize.lineup_rows(raw, FETCHED)
    assert [(r["player_id"], r["is_starter"], r["formation"]) for r in rows] == [(1, True, "4-3-3"), (2, False, "4-3-3")]


def test_player_block_with_foreign_team_goes_to_the_team_its_lineup_shows():
    _, stats = normalize.player_stats_rows(sample_1492399(), FETCHED)
    # Los de 22722 están en la alineación y los eventos de Chapecoense; el de id 0 se descarta como siempre.
    assert {s["player_id"]: s["team_id"] for s in stats} == {80626: 132, 80173: 132, 352220: 132, 288230: 136, 10085: 136}
    kauan = next(s for s in stats if s["player_id"] == 352220)
    assert (kauan["minutes"], kauan["yellow"]) == (90, 1)


def test_player_block_with_foreign_team_and_no_evidence_is_dropped(caplog):
    raw = sample_1492399()
    raw["lineups"], raw["events"] = [], []
    players, stats = normalize.player_stats_rows(raw, FETCHED)
    assert {s["player_id"]: s["team_id"] for s in stats} == {288230: 136, 10085: 136}
    assert [p["id"] for p in players] == [288230, 10085]
    assert "22722" in caplog.text


def test_player_block_is_not_moved_to_a_team_that_already_has_one():
    raw = sample_1492399()
    raw["lineups"][1]["team"]["id"] = 136  # sus jugadores aparecerían con Vitória, que ya trae su propio bloque
    raw["events"] = []
    _, stats = normalize.player_stats_rows(raw, FETCHED)
    assert {s["team_id"] for s in stats} == {136}


def test_team_stats_and_lineups_of_a_team_outside_the_fixture_are_dropped():
    raw = sample_1492399()
    assert [r["team_id"] for r in normalize.team_stats_rows(raw, FETCHED)] == [136, 132]
    raw["statistics"][1]["team"]["id"] = 22722
    raw["lineups"][1]["team"]["id"] = 22722
    assert [r["team_id"] for r in normalize.team_stats_rows(raw, FETCHED)] == [136]
    assert {r["team_id"] for r in normalize.lineup_rows(raw, FETCHED)[1]} == {136}
