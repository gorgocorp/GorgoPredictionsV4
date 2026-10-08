"""Detalle de partidos de fútbol (/fixtures?ids=) contra PostgreSQL real, con una respuesta real recortada."""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.sports.futbol.ingest import jobs

SAMPLES = Path(__file__).resolve().parents[1] / "fixtures" / "api_football"


def sample_1492399() -> dict:
    return json.loads((SAMPLES / "fixture_1492399.json").read_text(encoding="utf-8"))


class FakeApi:
    """En lugar de ApiSportsClient: devuelve una respuesta fija y cuenta las solicitudes."""

    def __init__(self, response: list[dict]):
        self.response, self.requests_made = response, 0

    def get(self, path: str, **params):
        assert path == "/fixtures" and "ids" in params
        self.requests_made += 1
        return self.response


def add_brasileirao(db):
    db.execute("INSERT INTO futbol.leagues (id, name, fetched_at) VALUES (71, 'Brasileirão', now()) ON CONFLICT DO NOTHING")


def player_teams(db, fixture_id: int) -> dict[int, int]:
    rows = db.execute("SELECT player_id, team_id FROM futbol.fixture_player_stats WHERE fixture_id = %s", (fixture_id,))
    return {r["player_id"]: r["team_id"] for r in rows}


def run_row(db, run_id: int) -> dict:
    return db.execute(
        "SELECT status, requests_made, rows_received, rows_written, rows_skipped FROM core.ingest_runs WHERE id = %s",
        (run_id,),
    ).fetchone()


def test_player_block_with_foreign_team_is_stored_under_the_fixture_team(db):
    add_brasileirao(db)
    run = jobs.fetch_details(db, FakeApi([sample_1492399()]), [1492399])

    assert player_teams(db, 1492399) == {80626: 132, 80173: 132, 352220: 132, 288230: 136, 10085: 136}
    assert db.execute("SELECT count(*) AS n FROM futbol.teams WHERE id = 22722").fetchone()["n"] == 0
    fixture = db.execute("SELECT status, ft_home, ft_away, details_fetched_at FROM futbol.fixtures WHERE id = 1492399").fetchone()
    assert (fixture["status"], fixture["ft_home"], fixture["ft_away"]) == ("FT", 4, 0)
    assert fixture["details_fetched_at"] is not None
    assert run_row(db, run.id) == {"status": "success", "requests_made": 1, "rows_received": 1, "rows_written": 1, "rows_skipped": 0}


def test_fixture_rejected_by_the_database_does_not_sink_the_batch(db):
    add_brasileirao(db)
    bad = sample_1492399()
    bad["fixture"]["id"] = 999000001
    bad["league"]["id"] = 999  # liga que no está en futbol.leagues: la llave foránea rechaza este partido
    run = jobs.fetch_details(db, FakeApi([bad, sample_1492399()]), [999000001, 1492399])

    stored = [r["id"] for r in db.execute("SELECT id FROM futbol.fixtures WHERE id IN (999000001, 1492399)")]
    assert stored == [1492399]
    assert len(player_teams(db, 1492399)) == 5
    assert run_row(db, run.id) == {"status": "success", "requests_made": 1, "rows_received": 2, "rows_written": 1, "rows_skipped": 1}
