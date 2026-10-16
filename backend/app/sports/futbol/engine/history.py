"""Carga el historial desde PostgreSQL a DataFrames para los modelos.

Todas las fechas (`match_date`) están en hora local como datetime64. Los modelos filtran
siempre por `match_date < fecha de corte` para no usar información futura.
"""

import bisect
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd
import psycopg

from app.sports.futbol.config import CUPS

CANCELLED_STATUSES = ("PST", "CANC", "ABD", "AWD", "WO")

# Una fila por partido. Tarjetas = amarillas + rojas de las estadísticas del partido.
FIXTURES_SQL = """
SELECT f.id, f.league_id, f.season, f.round, f.match_date, f.starts_at, f.status, f.is_finished,
       f.home_team_id, f.away_team_id, f.ft_home, f.ft_away, f.referee,
       hs.xg::float AS home_xg, aws.xg::float AS away_xg,
       hs.yellow + COALESCE(hs.red, 0) AS home_cards, aws.yellow + COALESCE(aws.red, 0) AS away_cards,
       hs.shots_on AS home_shots_on, aws.shots_on AS away_shots_on
FROM futbol.v_fixtures f
LEFT JOIN futbol.fixture_team_stats hs ON hs.fixture_id = f.id AND hs.team_id = f.home_team_id
LEFT JOIN futbol.fixture_team_stats aws ON aws.fixture_id = f.id AND aws.team_id = f.away_team_id
"""

# Una fila por jugador convocado y partido terminado (minutes = 0: suplente que no entró).
# Suplente = marca de la API o banca en la alineación publicada: desde mediados de 2026 la API marca
# substitute = false a todo el que juega, también al que entra de cambio; la alineación no cambió.
# team_shots: "Total Shots" de su equipo en ese partido (ver History.__post_init__).
PLAYER_STATS_SQL = """
SELECT p.fixture_id, p.player_id, p.team_id, f.match_date, f.league_id,
       CASE WHEN p.team_id = f.home_team_id THEN f.away_team_id ELSE f.home_team_id END AS opponent_id,
       p.team_id = f.home_team_id AS is_home,
       COALESCE(p.minutes, 0) AS minutes, p.position,
       COALESCE(p.is_substitute, false) OR COALESCE(NOT lu.is_starter, false) AS is_substitute,
       COALESCE(p.goals, 0) AS goals, COALESCE(p.assists, 0) AS assists,
       COALESCE(p.shots_total, 0) AS shots, COALESCE(p.shots_on, 0) AS shots_on,
       COALESCE(p.yellow, 0) + COALESCE(p.red, 0) AS cards,
       ts.shots_total AS team_shots
FROM futbol.fixture_player_stats p
JOIN futbol.v_fixtures f ON f.id = p.fixture_id
LEFT JOIN futbol.fixture_lineups lu ON lu.fixture_id = p.fixture_id AND lu.player_id = p.player_id
LEFT JOIN futbol.fixture_team_stats ts ON ts.fixture_id = p.fixture_id AND ts.team_id = p.team_id
WHERE f.is_finished
"""

# Tope del factor que lleva los remates de los jugadores al total de su equipo (99% de los partidos con la
# definición vieja quedan por debajo de 2.6; más arriba suele faltar algún jugador en las estadísticas).
SHOTS_FACTOR_MAX = 3.0


def _frame(conn: psycopg.Connection, query: str) -> pd.DataFrame:
    df = pd.DataFrame(conn.execute(query).fetchall())
    if "match_date" in df:
        df["match_date"] = pd.to_datetime(df["match_date"])
    return df


@dataclass
class History:
    fixtures: pd.DataFrame
    player_stats: pd.DataFrame
    team_names: dict[int, str]
    player_names: dict[int, str]
    league_names: dict[int, str]
    # Liga doméstica de cada equipo a lo largo del tiempo (para dar contexto a las copas).
    _domestic: dict[int, tuple[list[pd.Timestamp], list[int]]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        f = self.fixtures
        for col in ("ft_home", "ft_away", "home_xg", "away_xg", "home_cards", "away_cards", "home_shots_on", "away_shots_on"):
            f[col] = pd.to_numeric(f[col], errors="coerce").astype(float)
        f["is_cup"] = f["league_id"].isin(CUPS)
        f.sort_values(["match_date", "starts_at"], inplace=True)
        f.reset_index(drop=True, inplace=True)

        domestic = f[~f["is_cup"] & ~f["status"].isin(CANCELLED_STATUSES)]
        stacked = pd.concat(
            [
                domestic[["home_team_id", "match_date", "league_id"]].rename(columns={"home_team_id": "team_id"}),
                domestic[["away_team_id", "match_date", "league_id"]].rename(columns={"away_team_id": "team_id"}),
            ]
        ).sort_values("match_date")
        self._domestic = {
            int(team): (list(g["match_date"]), [int(x) for x in g["league_id"]]) for team, g in stacked.groupby("team_id")
        }

        ps = self.player_stats
        if not ps.empty:
            for col in ("minutes", "goals", "assists", "shots", "shots_on", "cards"):
                ps[col] = pd.to_numeric(ps[col]).astype(float)
            ps["ga"] = ps["goals"] + ps["assists"]

            # API-Football cambió durante 2026 (casi todo desde septiembre), partido por partido y no en una fecha,
            # el "Total Shots" del jugador: antes era a puerta + fuera; ahora suma también los bloqueados, como el del
            # equipo. Las props se liquidan con el dato nuevo, así que para las tasas (`shots_model`) los remates de
            # cada jugador se escalan para que los de su equipo sumen el total del equipo: ~1.36 con la definición
            # vieja, 1 con la nueva. `shots` queda crudo para los resultados y "veces que lo logró".
            if "team_shots" in ps:
                team = pd.to_numeric(ps["team_shots"], errors="coerce").astype(float)
                players = ps.groupby(["fixture_id", "team_id"])["shots"].transform("sum")
                factor = (team / players.where(players > 0)).clip(1.0, SHOTS_FACTOR_MAX).fillna(1.0)
            else:
                factor = pd.Series(1.0, index=ps.index)
            ps["shots_factor"] = factor
            ps["shots_model"] = ps["shots"] * factor
            ps.sort_values("match_date", inplace=True)
            ps.reset_index(drop=True, inplace=True)

    def domestic_league(self, team_id: int, when: pd.Timestamp) -> int | None:
        """Liga doméstica del equipo en esa fecha: la del último partido de liga anterior
        (o el primero posterior si no hay anteriores). None si no juega ninguna de nuestras ligas."""
        entry = self._domestic.get(int(team_id))
        if not entry:
            return None
        dates, leagues = entry
        i = bisect.bisect_left(dates, when)
        return leagues[i - 1] if i > 0 else leagues[0]

    def fixtures_on(self, day: date) -> pd.DataFrame:
        f = self.fixtures
        return f[(f["match_date"] == pd.Timestamp(day)) & ~f["status"].isin(CANCELLED_STATUSES)].sort_values("starts_at")

    def finished_before(self, cutoff: pd.Timestamp) -> pd.DataFrame:
        f = self.fixtures
        return f[f["is_finished"] & (f["match_date"] < cutoff) & f["ft_home"].notna()]


def load_history(conn: psycopg.Connection) -> History:
    teams = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM futbol.teams")}
    players = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM futbol.players")}
    leagues = {r["id"]: r["name"] for r in conn.execute("SELECT id, name FROM futbol.leagues")}
    return History(
        fixtures=_frame(conn, FIXTURES_SQL),
        player_stats=_frame(conn, PLAYER_STATS_SQL),
        team_names=teams,
        player_names=players,
        league_names=leagues,
    )


def recency_weights(cutoff: pd.Timestamp, dates: pd.Series, half_life_days: float) -> np.ndarray:
    age = (cutoff - dates).dt.days.to_numpy(dtype=float)
    return 0.5 ** (age / half_life_days)
