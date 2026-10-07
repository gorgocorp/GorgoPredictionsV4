"""Carga el historial desde PostgreSQL a DataFrames para los modelos.

Todas las fechas (`game_date`) están en hora del Este como datetime64. Los modelos
filtran siempre por `game_date < fecha de corte` para no usar información futura.
"""

from dataclasses import dataclass
from datetime import date

import pandas as pd
import psycopg

INACTIVE_STATUSES = ("POST", "CANC", "ABD", "SUSP", "AWD")

GAMES_SQL = """
SELECT id, season, game_date, starts_at, status, phase, is_finished,
       home_team_id, away_team_id, home_total, away_total
FROM nba.v_games
"""

PLAYER_STATS_SQL = """
SELECT p.game_id, p.player_id, p.team_id, g.game_date, g.season, g.phase,
       CASE WHEN p.team_id = g.home_team_id THEN g.away_team_id ELSE g.home_team_id END AS opponent_id,
       p.team_id = g.home_team_id AS is_home,
       p.seconds_played / 60.0 AS minutes,
       p.points, p.rebounds, p.assists, p.fg3_made,
       COALESCE(p.fg2_made_derived, p.fg2_made, 0) + COALESCE(p.fg3_made, 0) AS fgm
FROM nba.player_game_stats p
JOIN nba.v_games g ON g.id = p.game_id
WHERE g.is_finished AND p.points IS NOT NULL
"""

# Una fila por equipo y partido. Los puntos salen del marcador (siempre presente);
# rebotes, asistencias y triples de team_game_stats (puede faltar en algunos partidos).
TEAM_STATS_SQL = """
SELECT g.id AS game_id, g.game_date, g.phase, x.team_id, x.opponent_id, x.points,
       t.rebounds, t.assists, t.fg3_made
FROM nba.v_games g
CROSS JOIN LATERAL (VALUES
    (g.home_team_id, g.away_team_id, g.home_total),
    (g.away_team_id, g.home_team_id, g.away_total)
) AS x (team_id, opponent_id, points)
LEFT JOIN nba.team_game_stats t ON t.game_id = g.id AND t.team_id = x.team_id
WHERE g.is_finished
"""


def _frame(conn: psycopg.Connection, query: str) -> pd.DataFrame:
    df = pd.DataFrame(conn.execute(query).fetchall())
    if "game_date" in df:
        df["game_date"] = pd.to_datetime(df["game_date"])
    return df


@dataclass
class History:
    games: pd.DataFrame
    player_stats: pd.DataFrame
    team_stats: pd.DataFrame
    team_names: dict[int, str]
    player_names: dict[int, str]

    def __post_init__(self) -> None:
        g = self.games
        active = g[~g["status"].isin(INACTIVE_STATUSES)]
        played_on = set(zip(active["home_team_id"], active["game_date"])) | set(
            zip(active["away_team_id"], active["game_date"])
        )
        day = pd.Timedelta(days=1)
        g["home_b2b"] = [(t, d - day) in played_on for t, d in zip(g["home_team_id"], g["game_date"])]
        g["away_b2b"] = [(t, d - day) in played_on for t, d in zip(g["away_team_id"], g["game_date"])]
        for col in ("home_total", "away_total"):
            g[col] = pd.to_numeric(g[col])

        ps = self.player_stats
        for col in ("minutes", "points", "rebounds", "assists", "fg3_made", "fgm"):
            ps[col] = pd.to_numeric(ps[col]).astype(float)
        ps["threes"] = ps["fg3_made"]
        ps["pra"] = ps["points"] + ps["rebounds"] + ps["assists"]
        ps["pr"] = ps["points"] + ps["rebounds"]
        ps["pa"] = ps["points"] + ps["assists"]
        ps["ra"] = ps["rebounds"] + ps["assists"]

        ts = self.team_stats
        for col in ("points", "rebounds", "assists", "fg3_made"):
            ts[col] = pd.to_numeric(ts[col]).astype(float)

    def games_on(self, day: date) -> pd.DataFrame:
        return self.games[self.games["game_date"] == pd.Timestamp(day)].sort_values("starts_at")


def load_history(conn: psycopg.Connection) -> History:
    teams = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM nba.teams")}
    players = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM nba.players")}
    return History(
        games=_frame(conn, GAMES_SQL),
        player_stats=_frame(conn, PLAYER_STATS_SQL),
        team_stats=_frame(conn, TEAM_STATS_SQL),
        team_names=teams,
        player_names=players,
    )
