"""Historial de fútbol para los modelos (load_history) contra PostgreSQL real: suplentes según la alineación y
remates de jugador llevados al total del equipo (fútbol v3)."""

from app.sports.futbol.engine.history import load_history
from tests.integration.helpers import add_futbol_fixture

FIXTURE = 3001
HOME, AWAY = 132, 133


def add_player(db, player_id, team_id, minutes, is_substitute, shots, starter=None):
    db.execute(
        "INSERT INTO futbol.players (id, name, fetched_at) VALUES (%s, %s, now()) ON CONFLICT DO NOTHING",
        (player_id, f"Jugador {player_id}"),
    )
    db.execute(
        """
        INSERT INTO futbol.fixture_player_stats (fixture_id, player_id, team_id, minutes, position, is_substitute,
                                                 shots_total, shots_on, raw_payload, fetched_at)
        VALUES (%s, %s, %s, %s, 'F', %s, %s, 0, '{}', now())
        """,
        (FIXTURE, player_id, team_id, minutes, is_substitute, shots),
    )
    if starter is not None:
        db.execute(
            "INSERT INTO futbol.fixture_lineups (fixture_id, team_id, player_id, is_starter, fetched_at) VALUES (%s, %s, %s, %s, now())",
            (FIXTURE, team_id, player_id, starter),
        )


def add_team_shots(db, team_id, shots_total):
    db.execute(
        "INSERT INTO futbol.fixture_team_stats (fixture_id, team_id, shots_total, raw_payload, fetched_at) VALUES (%s, %s, %s, '{}', now())",
        (FIXTURE, team_id, shots_total),
    )


def test_load_history_fixes_substitutes_from_lineups_and_scales_old_player_shots(db):
    add_futbol_fixture(db, FIXTURE, status="FT", match_date="2026-10-10", home=HOME, away=AWAY)
    db.execute("UPDATE futbol.fixtures SET ft_home = 1, ft_away = 0 WHERE id = %s", (FIXTURE,))
    # Local, definición vieja: sus jugadores suman 4 + 2 = 6 remates (sin bloqueados) y el equipo 9.
    add_player(db, 9001, HOME, 90, False, 4, starter=True)
    add_player(db, 9002, HOME, 25, False, 2, starter=False)  # entró de cambio y la API ya no lo marca
    add_player(db, 9003, HOME, 0, True, 0, starter=False)
    add_team_shots(db, HOME, 9)
    # Visitante, definición nueva (ya suman el total) y sin alineación: manda la marca de la API.
    add_player(db, 9004, AWAY, 90, False, 3)
    add_player(db, 9005, AWAY, 30, True, 2)
    add_team_shots(db, AWAY, 5)

    ps = load_history(db).player_stats
    ps = ps[ps["fixture_id"] == FIXTURE].set_index("player_id")

    assert ps["is_substitute"].to_dict() == {9001: False, 9002: True, 9003: True, 9004: False, 9005: True}
    assert ps["shots"].to_dict() == {9001: 4.0, 9002: 2.0, 9003: 0.0, 9004: 3.0, 9005: 2.0}
    assert ps["shots_model"].to_dict() == {9001: 6.0, 9002: 3.0, 9003: 0.0, 9004: 3.0, 9005: 2.0}
