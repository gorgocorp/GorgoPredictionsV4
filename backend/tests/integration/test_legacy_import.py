"""import-legacy contra dos bases con el esquema de los proyectos anteriores (copias de sus migraciones)."""

from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

from app.db import migrate
from app.legacy_import import NBA, LegacyImportError, _snapshot, run_import
from tests.pg import recreate_database

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "legacy"

NBA_ROWS = """
INSERT INTO ingest_runs (job, status, started_at, finished_at) VALUES ('odds', 'success', now(), now());
INSERT INTO teams (id, name, raw_payload, fetched_at) VALUES (132, 'Atlanta Hawks', '{}', now()), (133, 'Boston Celtics', '{}', now());
INSERT INTO players (id, name, fetched_at) VALUES (77, 'Jugador NBA', now());
INSERT INTO games (id, season, starts_at, game_date, status, home_team_id, away_team_id, raw_payload, fetched_at)
VALUES (1000, '2026-2027', '2026-10-21T23:30:00Z', '2026-10-21', 'NS', 132, 133, '{}', now());
INSERT INTO odds_history (game_id, bookmaker_id, bookmaker_name, bet_id, bet_name, selection, odd,
                          first_seen_at, last_seen_at, first_run_id, last_run_id)
VALUES (1000, 8, 'Bet365', 2, 'Home/Away', 'Home', 1.8, now(), now(), 1, 1);
INSERT INTO picks (game_id, market, side, line, team, stat, player_id, description, p_model, odd, bookmaker,
                   model_version, first_evaluated_at, evaluated_at, book_odds)
VALUES (1000, 'ml', 'home', NULL, NULL, NULL, NULL, 'Gana Atlanta Hawks', 0.6, 1.8, 'Bet365', 'v1',
        '2026-10-20T10:00:00Z', '2026-10-20T11:00:00Z', '{"Bet365": 1.8, "1xBet": 1.84}'),
       (1000, 'player', 'over', 19.5, NULL, 'points', 77, 'Jugador NBA 20+ puntos', 0.55, NULL, NULL, 'v1',
        '2026-10-20T10:00:00Z', '2026-10-20T11:00:00Z', NULL);
INSERT INTO parlays (game_date, mode, n_legs, probability, bookmaker, model_version, evaluated_at)
VALUES ('2026-10-21', 'prob', 2, 0.33, 'Bet365', 'v1', now());
INSERT INTO parlay_legs (parlay_id, pick_id, position, description, p_model, odd)
VALUES (1, 1, 1, 'Gana Atlanta Hawks', 0.6, 1.8), (1, 2, 2, 'Jugador NBA 20+ puntos', 0.55, NULL);
INSERT INTO user_bets (bookmaker, stake, odd, model_probability, created_at, first_start)
VALUES ('Caliente', 50, 3.1, 0.33, '2026-10-20T12:00:00Z', '2026-10-21T23:30:00Z');
INSERT INTO user_bet_legs (bet_id, position, pick_id, description, p_model, odd)
VALUES (1, 1, 1, 'Gana Atlanta Hawks', 0.6, 1.75), (1, 2, 2, 'Jugador NBA 20+ puntos', 0.55, 1.77);
"""

# Mismos IDs de equipo, jugador y partido que en NBA: en el proveedor de fútbol son otros.
FUTBOL_ROWS = """
INSERT INTO ingest_runs (job, status, started_at, finished_at)
VALUES ('odds', 'success', now(), now()), ('odds', 'success', now(), now());
INSERT INTO leagues (id, name, fetched_at) VALUES (262, 'Liga MX', now());
INSERT INTO teams (id, name, fetched_at) VALUES (132, 'América', now()), (133, 'Chivas', now());
INSERT INTO players (id, name, fetched_at) VALUES (77, 'Jugador Fútbol', now());
INSERT INTO fixtures (id, league_id, season, starts_at, match_date, status, home_team_id, away_team_id, raw_payload, fetched_at)
VALUES (1000, 262, 2026, '2026-10-22T02:00:00Z', '2026-10-21', 'NS', 132, 133, '{}', now());
INSERT INTO odds_history (fixture_id, bookmaker_id, bookmaker_name, bet_id, bet_name, selection, odd,
                          first_seen_at, last_seen_at, first_run_id, last_run_id)
VALUES (1000, 8, 'Bet365', 1, 'Match Winner', 'Home', 2.1, now(), now(), 1, 2);
INSERT INTO picks (fixture_id, market, side, description, p_model, model_version, first_evaluated_at, evaluated_at)
VALUES (1000, '1x2', 'home', 'Gana América', 0.5, 'v1', now(), now()),
       (1000, 'score', '2-1', 'Marcador exacto América 2-1 Chivas', 0.09, 'v1', now(), now());
INSERT INTO parlays (match_date, mode, n_legs, probability, model_version, evaluated_at)
VALUES ('2026-10-21', 'prob', 2, 0.05, 'v1', now());
INSERT INTO parlay_legs (parlay_id, pick_id, position, description, p_model)
VALUES (1, 1, 1, 'Gana América', 0.5), (1, 2, 2, 'Marcador exacto América 2-1 Chivas', 0.09);
INSERT INTO user_bets (bookmaker, stake, odd, model_probability, created_at, first_start)
VALUES ('Caliente', 20, 2.0, 0.5, '2026-10-20T12:00:00Z', '2026-10-22T02:00:00Z');
INSERT INTO user_bet_legs (bet_id, position, pick_id, description, p_model, odd) VALUES (1, 1, 1, 'Gana América', 0.5, 2.0);
"""


def legacy_database(name: str, sport: str, rows: str) -> str:
    url = recreate_database(name)
    with psycopg.connect(url, autocommit=True) as conn:
        for path in sorted((FIXTURES / sport).glob("*.sql")):
            conn.execute(path.read_text(encoding="utf-8"))
        conn.execute(rows)
    return url


@pytest.fixture(scope="module")
def legacy(request):
    return {
        "nba": legacy_database("gorgo_v4_test_legacy_nba", "nba", NBA_ROWS),
        "futbol": legacy_database("gorgo_v4_test_legacy_futbol", "futbol", FUTBOL_ROWS),
    }


@pytest.fixture
def v4(legacy, monkeypatch):
    monkeypatch.setenv("LEGACY_NBA_DATABASE_URL", legacy["nba"])
    monkeypatch.setenv("LEGACY_FUTBOL_DATABASE_URL", legacy["futbol"])
    url = recreate_database("gorgo_v4_test_import")
    with psycopg.connect(url, autocommit=True, row_factory=dict_row) as conn:
        migrate(conn)
        yield conn


def rows(conn, query, params=None):
    return conn.execute(query, params).fetchall()


def test_imports_both_projects_without_id_collisions(v4):
    reports = run_import(v4)

    assert [r.sport for r in reports] == ["nba", "futbol"]
    for report in reports:
        assert all(old == new for _, old, new in report.tables)
        assert all(old == new for _, old, new in report.checks)

    # Mismo ID de partido en los dos proveedores: dos partidos distintos.
    assert rows(v4, "SELECT sport, competition, home_name FROM core.matches ORDER BY sport") == [
        {"sport": "futbol", "competition": "Liga MX", "home_name": "América"},
        {"sport": "nba", "competition": "NBA", "home_name": "Atlanta Hawks"},
    ]
    # Picks renumerados: primero NBA, luego fútbol, en el orden original y con la correspondencia guardada.
    assert rows(
        v4,
        """
        SELECT li.sport, li.legacy_id, k.id, k.description FROM core.legacy_ids li JOIN core.picks k ON k.id = li.id
        WHERE li.entity = 'pick' ORDER BY k.id
        """,
    ) == [
        {"sport": "nba", "legacy_id": 1, "id": 1, "description": "Gana Atlanta Hawks"},
        {"sport": "nba", "legacy_id": 2, "id": 2, "description": "Jugador NBA 20+ puntos"},
        {"sport": "futbol", "legacy_id": 1, "id": 3, "description": "Gana América"},
        {"sport": "futbol", "legacy_id": 2, "id": 4, "description": "Marcador exacto América 2-1 Chivas"},
    ]
    # Las marcas de tiempo (evidencia de "antes del partido") y los momios por casa se conservan.
    pick = rows(v4, "SELECT first_evaluated_at, book_odds FROM core.picks WHERE id = 1")[0]
    assert pick["first_evaluated_at"].isoformat() == "2026-10-20T10:00:00+00:00"
    assert pick["book_odds"] == {"Bet365": 1.8, "1xBet": 1.84}
    # Las apuestas importadas son del dueño, y cada una apunta a sus picks renumerados.
    assert rows(v4, "SELECT DISTINCT u.username FROM core.user_bets b JOIN core.users u ON u.id = b.user_id") == [
        {"username": "GorgoAdmin"}
    ]
    assert rows(v4, "SELECT bet_id, pick_id, odd::float AS odd FROM core.user_bet_legs ORDER BY bet_id, position") == [
        {"bet_id": 1, "pick_id": 1, "odd": 1.75},
        {"bet_id": 1, "pick_id": 2, "odd": 1.77},
        {"bet_id": 2, "pick_id": 3, "odd": 2.0},
    ]
    # Los momios conservan su ID y apuntan a las ingestas renumeradas (NBA: 1; fútbol: 2 y 3).
    assert rows(v4, "SELECT id, first_run_id, last_run_id FROM futbol.odds_history") == [{"id": 1, "first_run_id": 2, "last_run_id": 3}]
    assert rows(v4, "SELECT sport, day::text AS day FROM core.parlays ORDER BY id") == [
        {"sport": "nba", "day": "2026-10-21"},
        {"sport": "futbol", "day": "2026-10-21"},
    ]
    # Las secuencias siguen después de lo importado.
    assert v4.execute(
        "INSERT INTO core.ingest_runs (sport, job) VALUES ('nba', 'prueba') RETURNING id"
    ).fetchone()["id"] == 6  # 3 importadas + 2 registros de la importación + ésta


def test_refuses_to_overwrite_without_replace_and_reimports_with_it(v4, legacy):
    # Las cuentas no son datos importados: con una cuenta y su sesión, la base sigue "vacía" para importar,
    # y --replace no las borra.
    v4.execute("INSERT INTO core.users (username, role) VALUES ('cliente', 'free')")
    run_import(v4)
    with pytest.raises(LegacyImportError, match="--replace"):
        run_import(v4)

    with psycopg.connect(legacy["nba"], autocommit=True) as conn:
        conn.execute(
            """
            INSERT INTO picks (game_id, market, side, line, description, p_model, model_version, first_evaluated_at, evaluated_at)
            VALUES (1000, 'total', 'over', 220.5, 'Más de 220.5 pts en el partido', 0.52, 'v1', now(), now())
            """
        )
    try:
        run_import(v4, replace=True)
        assert v4.execute("SELECT count(*) AS n FROM core.picks").fetchone()["n"] == 5
        assert v4.execute("SELECT count(*) AS n FROM core.matches").fetchone()["n"] == 2
        assert [r["username"] for r in rows(v4, "SELECT username FROM core.users ORDER BY id")] == ["GorgoAdmin", "cliente"]
    finally:
        with psycopg.connect(legacy["nba"], autocommit=True) as conn:
            conn.execute("DELETE FROM picks WHERE market = 'total'")


def test_a_failure_rolls_back_everything(v4, legacy):
    run_import(v4)
    # Una columna inesperada en el origen se quedaría fuera: la importación se niega y V4 queda como estaba.
    with psycopg.connect(legacy["futbol"], autocommit=True) as conn:
        conn.execute("ALTER TABLE picks ADD COLUMN nota TEXT")
    try:
        with pytest.raises(LegacyImportError, match="nota"):
            run_import(v4, replace=True)
        assert v4.execute("SELECT count(*) AS n FROM core.picks").fetchone()["n"] == 4
        assert v4.execute("SELECT count(*) AS n FROM core.ingest_runs WHERE job = 'import-legacy'").fetchone()["n"] == 2
    finally:
        with psycopg.connect(legacy["futbol"], autocommit=True) as conn:
            conn.execute("ALTER TABLE picks DROP COLUMN nota")


def test_source_snapshot_cannot_write(legacy):
    with _snapshot(legacy["nba"]) as src:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            with src.transaction():  # punto de guardado: la foto sigue usable después del error
                src.execute("DELETE FROM picks")
    with psycopg.connect(legacy["nba"]) as conn:
        assert conn.execute("SELECT count(*) FROM picks").fetchone()[0] == 2


def test_rejects_a_v4_database_as_source(v4, monkeypatch, test_db_url):
    monkeypatch.setenv(NBA.url_var, test_db_url)  # una base con el esquema de V4, no la del proyecto NBA
    with pytest.raises(LegacyImportError, match="parece ser la de V4"):
        run_import(v4)
