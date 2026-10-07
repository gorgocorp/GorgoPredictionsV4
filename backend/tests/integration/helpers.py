"""Datos mínimos de prueba en los esquemas de V4."""

STARTS = "2026-10-21T23:30:00+00:00"  # 19:30 hora del Este, 17:30 en el centro de México


def add_nba_game(db, game_id, status="NS", starts=STARTS, game_date="2026-10-21", home=132, away=133):
    for team_id in (home, away):
        db.execute(
            "INSERT INTO nba.teams (id, name, raw_payload, fetched_at) VALUES (%s, %s, '{}', now()) ON CONFLICT DO NOTHING",
            (team_id, f"NBA {team_id}"),
        )
    db.execute(
        """
        INSERT INTO nba.games (id, season, starts_at, game_date, status, home_team_id, away_team_id, raw_payload, fetched_at)
        VALUES (%s, '2026-2027', %s, %s, %s, %s, %s, '{}', now())
        """,
        (game_id, starts, game_date, status, home, away),
    )


def add_futbol_fixture(db, fixture_id, status="NS", starts=STARTS, match_date="2026-10-21", home=132, away=133, league=262):
    db.execute("INSERT INTO futbol.leagues (id, name, fetched_at) VALUES (%s, 'Liga MX', now()) ON CONFLICT DO NOTHING", (league,))
    for team_id in (home, away):
        db.execute(
            "INSERT INTO futbol.teams (id, name, fetched_at) VALUES (%s, %s, now()) ON CONFLICT DO NOTHING",
            (team_id, f"Fútbol {team_id}"),
        )
    db.execute(
        """
        INSERT INTO futbol.fixtures (id, league_id, season, starts_at, match_date, status, home_team_id, away_team_id,
                                     raw_payload, fetched_at)
        VALUES (%s, %s, 2026, %s, %s, %s, %s, %s, '{}', now())
        """,
        (fixture_id, league, starts, match_date, status, home, away),
    )


def match_id(db, sport, external_id) -> int:
    return db.execute(
        "SELECT id FROM core.matches WHERE sport = %s AND external_id = %s", (sport, external_id)
    ).fetchone()["id"]


def add_pick(db, sport, match, market, side, line=None, description="pierna"):
    return db.execute(
        """
        INSERT INTO core.picks (sport, match_id, market, side, line, description, p_model, model_version,
                                first_evaluated_at, evaluated_at)
        VALUES (%s, %s, %s, %s, %s, %s, 0.6, 'v1', now(), now())
        RETURNING id
        """,
        (sport, match, market, side, line, description),
    ).fetchone()["id"]
