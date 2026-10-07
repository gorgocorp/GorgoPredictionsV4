"""Proyección de estadísticas de jugador para props (goleador, remates, asistencias, tarjeta).

Para cada jugador, con partidos anteriores a la fecha de corte:
- tasa por 90 minutos de cada estadística, ponderada por recencia y encogida hacia la tasa
  de su posición (portero, defensa, medio, delantero) para que pocos partidos no den extremos;
- perfil de minutos: probabilidad de ser titular y de entrar de cambio en los últimos partidos
  de su equipo, y minutos promedio en cada caso.

Contra un rival concreto, las tasas ofensivas se escalan por los goles esperados de su equipo
en ese partido contra lo que su equipo genera normalmente; las tarjetas, por las tarjetas
esperadas (incluye al árbitro).

Las casas anulan la apuesta si el jugador no juega, así que la probabilidad es *condicional a
que juegue*: mezcla de "titular" y "entra de cambio", cada una con sus minutos.
"""

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from app.sports.futbol.engine.dist import prob_at_least
from app.sports.futbol.engine.history import History, recency_weights

STATS = ("goals", "assists", "ga", "shots", "shots_on", "cards")

STAT_LABELS = {
    "goals": "goles",
    "assists": "asistencias",
    "ga": "goles o asistencias",
    "shots": "remates",
    "shots_on": "remates a puerta",
    "cards": "tarjetas",
}

# Escalones "N o más" que se evalúan cuando no hay momio de la casa.
LADDERS = {
    "goals": (1, 2),
    "assists": (1,),
    "ga": (1,),
    "shots": (1, 2, 3, 4),
    "shots_on": (1, 2, 3),
    "cards": (1,),
}

# Estadísticas que dependen del ataque del equipo en el partido (las tarjetas, de las tarjetas esperadas).
ATTACKING = frozenset({"goals", "assists", "ga", "shots", "shots_on"})

# Calibración medida en el backtest (titulares, ago-2025 a oct-2026, ~18,000 por estadística):
# la tasa histórica sobreestima 3–7% lo que el titular produce en el partido siguiente, y los
# remates están un poco sobredispersos (varianza = 1.1 × media).
STAT_SCALE = {"goals": 0.93, "assists": 0.95, "ga": 0.93, "shots": 0.97, "shots_on": 0.95, "cards": 1.0}
STAT_DISPERSION = {"goals": 1.0, "assists": 1.0, "ga": 1.0, "shots": 1.1, "shots_on": 1.1, "cards": 1.0}
POSITIONS = ("G", "D", "M", "F")


@dataclass(frozen=True)
class PlayerModelParams:
    half_life_days: float = 180.0
    window_days: int = 500
    prior_90s: float = 4.0  # peso del promedio de su posición, en partidos completos
    team_games: int = 6  # partidos recientes del equipo para el perfil de minutos
    team_decay: float = 0.8  # peso del partido k-ésimo más reciente: 0.8^k
    context_shrink: float = 0.7  # exponente del ajuste por partido (1 = completo, 0 = ninguno)
    min_starts: float = 0.5  # probabilidad mínima de ser titular para ofrecer props
    min_games: int = 3


@dataclass(frozen=True)
class PlayerProjection:
    rate90: float  # tasa por 90 minutos ya ajustada al partido
    dispersion: float  # varianza / media de la binomial negativa
    p_start: float
    p_sub: float
    min_start: float
    min_sub: float

    def _p_given_minutes(self, minutes: float, k: int) -> float:
        mean = self.rate90 * minutes / 90.0
        return prob_at_least(mean, mean * self.dispersion, k)

    def p_at_least(self, k: int) -> float:
        """P(k o más | juega)."""
        appear = self.p_start + self.p_sub
        if appear <= 0:
            return self._p_given_minutes(self.min_start, k)
        return (
            self.p_start * self._p_given_minutes(self.min_start, k)
            + self.p_sub * self._p_given_minutes(self.min_sub, k)
        ) / appear

    def p_over(self, line: float) -> float:
        return self.p_at_least(math.floor(line) + 1)

    @property
    def expected_minutes(self) -> float:
        return self.p_start * self.min_start + self.p_sub * self.min_sub


class PlayerModel:
    """Perfiles de todos los jugadores a una fecha de corte."""

    def __init__(self, hist: History, as_of: date, params: PlayerModelParams = PlayerModelParams()):
        self.params = params
        self.as_of = pd.Timestamp(as_of)
        ps = hist.player_stats
        before = ps[(ps["match_date"] < self.as_of) & (ps["match_date"] >= self.as_of - pd.Timedelta(days=params.window_days))]

        # Equipo actual: el del último partido en que estuvo convocado (refleja traspasos).
        latest = before.groupby("player_id").tail(1).set_index("player_id")
        self.current_team = latest["team_id"].astype(int).to_dict()
        self.last_seen = latest["match_date"].to_dict()

        played = before[before["minutes"] > 0]
        self._recent = {pid: g for pid, g in played.groupby("player_id")}
        self.position = played.groupby("player_id")["position"].agg(lambda s: s.dropna().iloc[-1] if s.notna().any() else "M").to_dict()
        self.profiles = self._profiles(played)
        self._minutes_profile(hist, before)
        self._team_baselines(hist)

    # ------------------------------------------------------------ tasas

    def _profiles(self, played: pd.DataFrame) -> pd.DataFrame:
        if played.empty:
            return pd.DataFrame()
        w = recency_weights(self.as_of, played["match_date"], self.params.half_life_days)
        work = pd.DataFrame({"player_id": played["player_id"].to_numpy(), "w": w, "wmin": w * played["minutes"].to_numpy()})
        for s in STATS:
            work[f"wx_{s}"] = w * played[s].to_numpy()
        agg = work.groupby("player_id").sum()
        agg["games"] = work.groupby("player_id").size()
        agg["position"] = pd.Series(self.position).reindex(agg.index).fillna("M")

        # Tasa por 90 de cada posición (valor previo).
        by_pos = agg.groupby("position")[[f"wx_{s}" for s in STATS] + ["wmin"]].sum()
        nineties = agg["wmin"] / 90.0
        k = self.params.prior_90s
        out = agg[["games", "position"]].copy()
        out["nineties"] = nineties
        for s in STATS:
            prior = (by_pos[f"wx_{s}"] / by_pos["wmin"] * 90.0).reindex(agg["position"]).to_numpy()
            out[f"rate_{s}"] = (agg[f"wx_{s}"] + k * prior) / (nineties + k)
        return out

    # ------------------------------------------------------------ minutos

    def _minutes_profile(self, hist: History, before: pd.DataFrame) -> None:
        p = self.params
        fx = hist.finished_before(self.as_of)
        apps = pd.concat(
            [
                fx[["id", "home_team_id", "match_date"]].rename(columns={"id": "fixture_id", "home_team_id": "team_id"}),
                fx[["id", "away_team_id", "match_date"]].rename(columns={"id": "fixture_id", "away_team_id": "team_id"}),
            ]
        ).sort_values("match_date")
        last = apps.groupby("team_id").tail(p.team_games).copy()
        last["rank"] = last.groupby("team_id")["match_date"].rank(ascending=False, method="first") - 1
        last["w"] = p.team_decay ** last["rank"]
        self.team_last_fixtures = {
            int(t): list(g.sort_values("match_date")["fixture_id"]) for t, g in last.groupby("team_id")
        }

        # Cada jugador contra los últimos partidos de SU equipo actual (0 si no estuvo).
        cur = pd.DataFrame({"player_id": list(self.current_team), "team_id": list(self.current_team.values())})
        grid = cur.merge(last[["team_id", "fixture_id", "w", "rank"]], on="team_id")
        rows = before[["fixture_id", "player_id", "minutes", "is_substitute"]]
        grid = grid.merge(rows, on=["fixture_id", "player_id"], how="left")
        grid["minutes"] = grid["minutes"].fillna(0.0)
        sub = grid["is_substitute"].astype("boolean")
        grid["started"] = (grid["minutes"] > 0) & ~sub.fillna(True).astype(bool)
        grid["subbed"] = (grid["minutes"] > 0) & sub.fillna(False).astype(bool)
        grid["recent"] = (grid["rank"] < 2) & (grid["minutes"] > 0)
        g = grid.groupby("player_id")
        wsum = g["w"].sum()
        self.p_start = (grid["w"] * grid["started"]).groupby(grid["player_id"]).sum().div(wsum).to_dict()
        self.p_sub = (grid["w"] * grid["subbed"]).groupby(grid["player_id"]).sum().div(wsum).to_dict()
        self.played_recently = g["recent"].any().to_dict()

        played = before[before["minutes"] > 0]
        w = recency_weights(self.as_of, played["match_date"], p.half_life_days)
        frame = pd.DataFrame({"player_id": played["player_id"].to_numpy(), "w": w, "wm": w * played["minutes"].to_numpy(),
                              "sub": played["is_substitute"].to_numpy()})
        starts = frame[~frame["sub"]].groupby("player_id")[["w", "wm"]].sum()
        subs = frame[frame["sub"]].groupby("player_id")[["w", "wm"]].sum()
        self.min_start = (starts["wm"] / starts["w"]).to_dict()
        self.min_sub = (subs["wm"] / subs["w"]).to_dict()

    # ------------------------------------------------------------ contexto del equipo

    def _team_baselines(self, hist: History) -> None:
        """Goles (mezcla goles/xG) y tarjetas que suele producir cada equipo, con la misma recencia."""
        fx = hist.finished_before(self.as_of)
        fx = fx[fx["match_date"] >= self.as_of - pd.Timedelta(days=self.params.window_days)]
        w = recency_weights(self.as_of, fx["match_date"], self.params.half_life_days)

        def blend(goals: pd.Series, xg: pd.Series) -> np.ndarray:
            g, x = goals.to_numpy(dtype=float), xg.to_numpy(dtype=float)
            return np.where(np.isnan(x), g, 0.5 * g + 0.5 * x)

        frame = pd.DataFrame({
            "team_id": np.concatenate([fx["home_team_id"], fx["away_team_id"]]),
            "w": np.concatenate([w, w]),
            "goals": np.concatenate([blend(fx["ft_home"], fx["home_xg"]), blend(fx["ft_away"], fx["away_xg"])]),
            "cards": np.concatenate([fx["home_cards"], fx["away_cards"]]),
        })
        frame["wg"] = frame["w"] * frame["goals"]
        has_cards = frame["cards"].notna()
        frame["wc"] = (frame["w"] * frame["cards"]).where(has_cards, 0.0)
        frame["w_cards"] = frame["w"].where(has_cards, 0.0)
        agg = frame.groupby("team_id")[["w", "wg", "wc", "w_cards"]].sum()
        self.team_goals = (agg["wg"] / agg["w"]).to_dict()
        self.team_cards = (agg["wc"] / agg["w_cards"].where(agg["w_cards"] > 0)).dropna().to_dict()

    # ------------------------------------------------------------ consultas

    def is_eligible(self, player_id: int, lineup: str | None = None) -> bool:
        """Props sólo para titulares habituales (o confirmados en la alineación) de campo."""
        if player_id not in self.profiles.index or self.position.get(player_id) == "G":
            return False
        if self.profiles.at[player_id, "games"] < self.params.min_games:
            return False
        if lineup == "starter":
            return True
        if lineup == "bench":
            return False
        return self.p_start.get(player_id, 0.0) >= self.params.min_starts and self.played_recently.get(player_id, False)

    def projection(
        self,
        player_id: int,
        stat: str,
        team_goals: float | None = None,
        team_cards: float | None = None,
        lineup: str | None = None,
    ) -> PlayerProjection:
        """`team_goals` / `team_cards`: lo esperado para su equipo en este partido (None = sin ajuste)."""
        rate = float(self.profiles.at[player_id, f"rate_{stat}"])
        team = self.current_team.get(player_id)
        factor = 1.0
        if stat in ATTACKING and team_goals and self.team_goals.get(team):
            factor = (team_goals / self.team_goals[team]) ** self.params.context_shrink
        elif stat == "cards" and team_cards and self.team_cards.get(team):
            factor = (team_cards / self.team_cards[team]) ** self.params.context_shrink
        pos = self.position.get(player_id, "M")
        min_start = min(self.min_start.get(player_id, 80.0 if pos != "F" else 75.0), 95.0)
        min_sub = min(self.min_sub.get(player_id, 20.0), 45.0)
        if lineup == "starter":
            p_start, p_sub = 1.0, 0.0
        else:
            p_start, p_sub = self.p_start.get(player_id, 0.0), self.p_sub.get(player_id, 0.0)
        return PlayerProjection(
            rate90=rate * factor * STAT_SCALE[stat],
            dispersion=STAT_DISPERSION[stat],
            p_start=p_start,
            p_sub=p_sub,
            min_start=min_start,
            min_sub=min_sub,
        )

    def hit_rate(self, player_id: int, stat: str, k: int, last_n: int) -> tuple[int, int]:
        """(aciertos, partidos) de "k o más" en sus últimos `last_n` partidos jugados."""
        games = self._recent.get(player_id)
        if games is None:
            return 0, 0
        games = games.tail(last_n)
        return int((games[stat] >= k).sum()), len(games)
