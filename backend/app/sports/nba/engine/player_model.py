"""Proyección de estadísticas de jugador para props.

Para cada jugador se calcula, con partidos anteriores a la fecha de corte:
- media y varianza ponderadas por recencia de cada estadística,
- encogidas hacia un valor previo (tasa de la liga por minuto × sus minutos esperados)
  para que pocos partidos no den porcentajes extremos.

Contra un rival concreto, la media se ajusta por lo que ese rival permite en la
estadística. La probabilidad de "N o más" sale de:
- una binomial negativa para conteos chicos (rebotes, asistencias, triples, tiros),
- una normal discretizada para puntos y combinados: su distribución es más simétrica y
  la binomial negativa subestimaba 3–5 puntos porcentuales las probabilidades medias (backtest).
"""

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from app.sports.nba.engine.history import History

# Estadísticas soportadas y sus componentes base (para el ajuste por rival).
STAT_COMPONENTS: dict[str, tuple[str, ...]] = {
    "points": ("points",),
    "rebounds": ("rebounds",),
    "assists": ("assists",),
    "threes": ("threes",),
    "fgm": ("fgm",),
    "pra": ("points", "rebounds", "assists"),
    "pr": ("points", "rebounds"),
    "pa": ("points", "assists"),
    "ra": ("rebounds", "assists"),
}
STATS = tuple(STAT_COMPONENTS)

STAT_LABELS = {
    "points": "puntos",
    "rebounds": "rebotes",
    "assists": "asistencias",
    "threes": "triples",
    "fgm": "tiros de campo anotados",
    "pra": "pts+reb+ast",
    "pr": "pts+reb",
    "pa": "pts+ast",
    "ra": "reb+ast",
}

# Escalones "N o más" que se evalúan cuando no hay momio de la casa.
LADDERS = {
    "points": (10, 15, 20, 25, 30, 35, 40),
    "rebounds": (4, 6, 8, 10, 12, 14),
    "assists": (2, 4, 6, 8, 10, 12),
    "threes": (1, 2, 3, 4, 5, 6),
    "fgm": (3, 5, 7, 9, 11, 13),
    "pra": (15, 20, 25, 30, 35, 40, 45, 50),
    "pr": (15, 20, 25, 30, 35, 40),
    "pa": (15, 20, 25, 30, 35, 40),
    "ra": (6, 8, 10, 12, 15, 18),
}

# Estadísticas que se modelan con normal discretizada (ver docstring del módulo).
NORMAL_STATS = frozenset({"points", "pra", "pr", "pa"})

# Qué estadística de equipo permitida ajusta cada componente.
OPPONENT_STAT = {"points": "points", "rebounds": "rebounds", "assists": "assists", "threes": "fg3_made", "fgm": "points"}


@dataclass(frozen=True)
class PlayerModelParams:
    # Elegidos con backtest sobre 2025-26 (calibración dentro de ±1% en todos los rangos).
    half_life_days: float = 90.0
    prior_weight: float = 3.0
    opponent_shrink: float = 0.5
    min_games: int = 5
    min_minutes: float = 15.0


def prob_at_least(mean: float, var: float, k: int) -> float:
    """P(X >= k) con X ~ binomial negativa (o Poisson si no hay sobredispersión)."""
    if k <= 0:
        return 1.0
    if mean <= 0:
        return 0.0
    if var <= mean * 1.0001:
        pmf = math.exp(-mean)
        cdf = pmf
        for i in range(1, k):
            pmf *= mean / i
            cdf += pmf
    else:
        r = mean * mean / (var - mean)
        p = r / (r + mean)
        pmf = math.exp(r * math.log(p))
        cdf = pmf
        for i in range(1, k):
            pmf *= (i - 1 + r) / i * (1.0 - p)
            cdf += pmf
    return min(1.0, max(0.0, 1.0 - cdf))


def prob_at_least_normal(mean: float, var: float, k: int) -> float:
    """P(X >= k) con X normal discretizada (corrección de continuidad de 0.5)."""
    sd = math.sqrt(max(var, 1e-9))
    return 1.0 - 0.5 * (1.0 + math.erf((k - 0.5 - mean) / (sd * math.sqrt(2.0))))


@dataclass(frozen=True)
class Projection:
    mean: float
    var: float
    normal: bool = False

    def p_at_least(self, k: int) -> float:
        if self.normal:
            return prob_at_least_normal(self.mean, self.var, k)
        return prob_at_least(self.mean, self.var, k)

    def p_over(self, line: float) -> float:
        return self.p_at_least(math.floor(line) + 1)


class PlayerModel:
    """Perfiles de todos los jugadores a una fecha de corte."""

    def __init__(self, hist: History, as_of: date, params: PlayerModelParams = PlayerModelParams()):
        self.params = params
        self.as_of = pd.Timestamp(as_of)
        ps = hist.player_stats
        before = ps[ps["game_date"] < self.as_of]

        # Equipo actual: el del partido más reciente, incluida la pretemporada (refleja traspasos).
        latest = before.sort_values("game_date").groupby("player_id").tail(1).set_index("player_id")
        self.current_team = latest["team_id"].to_dict()
        self.last_game = latest["game_date"].to_dict()

        played = before[(before["phase"] != "preseason") & (before["minutes"] > 0)]
        self._recent_by_player = {pid: g for pid, g in played.sort_values("game_date").groupby("player_id")}
        self.profiles = self._profiles(played)
        self.opponent_factors = self._opponent_factors(hist)

    def _weights(self, dates: pd.Series) -> np.ndarray:
        age = (self.as_of - dates).dt.days.to_numpy(dtype=float)
        return 0.5 ** (age / self.params.half_life_days)

    def _profiles(self, played: pd.DataFrame) -> pd.DataFrame:
        if played.empty:
            return pd.DataFrame()
        w = self._weights(played["game_date"])
        work = pd.DataFrame({"player_id": played["player_id"].to_numpy(), "w": w, "w2": w * w})
        work["wmin"] = w * played["minutes"].to_numpy()
        for s in STATS:
            x = played[s].to_numpy()
            work[f"wx_{s}"] = w * x
            work[f"wxx_{s}"] = w * x * x
        agg = work.groupby("player_id").sum()
        agg["games"] = work.groupby("player_id").size()
        agg["exp_minutes"] = agg["wmin"] / agg["w"]
        n_eff = agg["w"] ** 2 / agg["w2"]
        bessel = (n_eff / (n_eff - 1)).where(n_eff > 1.5, 1.0)

        k = self.params.prior_weight
        total_min = agg["wmin"].sum()
        out = agg[["games", "w", "exp_minutes"]].copy()
        for s in STATS:
            rate = agg[f"wx_{s}"].sum() / total_min  # tasa de la liga por minuto
            mean_raw = agg[f"wx_{s}"] / agg["w"]
            var_raw = (agg[f"wxx_{s}"] / agg["w"] - mean_raw**2).clip(lower=0) * bessel
            prior_mean = rate * agg["exp_minutes"]
            mean = (agg[f"wx_{s}"] + k * prior_mean) / (agg["w"] + k)
            # Índice de dispersión típico (varianza/media) para el valor previo de la varianza.
            regulars = agg["games"] >= 20
            dispersion = float((var_raw[regulars] / mean_raw[regulars].where(mean_raw[regulars] > 0)).median())
            dispersion = max(dispersion, 1.0) if not math.isnan(dispersion) else 1.5
            var = (agg["w"] * var_raw + k * dispersion * mean) / (agg["w"] + k)
            out[f"mean_{s}"] = mean
            out[f"var_{s}"] = var
        return out

    def _opponent_factors(self, hist: History) -> dict[int, dict[str, float]]:
        ts = hist.team_stats
        ts = ts[(ts["game_date"] < self.as_of) & (ts["phase"] != "preseason")]
        if ts.empty:
            return {}
        w = pd.Series(self._weights(ts["game_date"]), index=ts.index)
        factors: dict[int, dict[str, float]] = {}
        for stat in ("points", "rebounds", "assists", "fg3_made"):
            valid = ts[stat].notna()
            x, wv = ts.loc[valid, stat], w[valid]
            league = (wv * x).sum() / wv.sum()
            allowed = (wv * x).groupby(ts.loc[valid, "opponent_id"]).sum() / wv.groupby(ts.loc[valid, "opponent_id"]).sum()
            for team_id, value in allowed.items():
                factor = 1.0 + self.params.opponent_shrink * (value / league - 1.0)
                factors.setdefault(int(team_id), {})[stat] = float(factor)
        return factors

    def is_eligible(self, player_id: int) -> bool:
        if player_id not in self.profiles.index:
            return False
        row = self.profiles.loc[player_id]
        return row["games"] >= self.params.min_games and row["exp_minutes"] >= self.params.min_minutes

    def projection(self, player_id: int, stat: str, opponent_id: int | None) -> Projection:
        row = self.profiles.loc[player_id]
        mean, var = float(row[f"mean_{stat}"]), float(row[f"var_{stat}"])
        normal = stat in NORMAL_STATS
        if opponent_id is None or opponent_id not in self.opponent_factors:
            return Projection(mean, var, normal)
        opp = self.opponent_factors[opponent_id]
        comps = STAT_COMPONENTS[stat]
        raw = sum(float(row[f"mean_{c}"]) for c in comps)
        adj = sum(float(row[f"mean_{c}"]) * opp.get(OPPONENT_STAT[c], 1.0) for c in comps)
        ratio = adj / raw if raw > 0 else 1.0
        return Projection(mean * ratio, var * ratio, normal)

    def hit_rate(self, player_id: int, stat: str, k: int, last_n: int) -> tuple[int, int]:
        """(aciertos, partidos) de "k o más" en sus últimos `last_n` partidos jugados."""
        games = self._recent_by_player.get(player_id)
        if games is None:
            return 0, 0
        games = games.tail(last_n)
        return int((games[stat] >= k).sum()), len(games)
