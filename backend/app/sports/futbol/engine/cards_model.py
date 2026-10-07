"""Modelo de tarjetas: cuántas recibe cada equipo (amarillas + rojas, como en las estadísticas).

    log(tarjetas esperadas) = media + competición + competición×temporada + localía
                              + propias[equipo] + provocadas[rival] + árbitro

Mismo ajuste que el modelo de goles (Poisson con ridge y peso por recencia). El árbitro pesa
mucho en tarjetas; la API lo publica en el partido (a veces sólo unas horas antes). Si no se
conoce, su efecto es 0 (árbitro promedio).

Las tarjetas de un equipo se comportan como Poisson, pero las del partido están sobredispersas
(las de los dos equipos suben y bajan juntas según la intensidad del partido): el total usa una
binomial negativa con varianza = 1.3 × media. Ambos valores, medidos en el backtest.
"""

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from app.sports.futbol.config import LEAGUES
from app.sports.futbol.engine.dist import prob_over
from app.sports.futbol.engine.glm import fit_poisson_ridge
from app.sports.futbol.engine.history import History, recency_weights, referee_key

COMPS = sorted(LEAGUES)
COMP_INDEX = {c: i for i, c in enumerate(COMPS)}


# Varianza / media medidas fuera de muestra (backtest ago-2025 a oct-2026).
DISPERSION_TEAM = 1.0
DISPERSION_TOTAL = 1.3


@dataclass(frozen=True)
class CardsModelParams:
    # Elegidos con backtest (log loss de las líneas de tarjetas): los efectos de equipo y de
    # árbitro son ruidosos y piden mucha regularización.
    half_life_days: float = 300.0
    ridge_team: float = 30.0
    ridge_referee: float = 40.0
    ridge_comp: float = 3.0
    ridge_season: float = 5.0
    window_days: int = 760


@dataclass(frozen=True)
class CardsPrediction:
    home: float
    away: float
    dispersion_team: float
    dispersion_total: float

    @property
    def total(self) -> float:
        return self.home + self.away

    def p_total_over(self, line: float) -> float:
        return prob_over(self.total, self.total * self.dispersion_total, line)

    def p_team_over(self, side: str, line: float) -> float:
        mean = self.home if side == "home" else self.away
        return prob_over(mean, mean * self.dispersion_team, line)


@dataclass
class CardsModel:
    beta: np.ndarray
    team_index: dict[int, int]
    referee_index: dict[str, int]
    season_index: dict[tuple[int, int], int]
    dispersion_team: float
    dispersion_total: float
    params: CardsModelParams

    def _o(self) -> dict[str, int]:
        c, t, r = len(COMPS), len(self.team_index), len(self.referee_index)
        return {"comp": 2, "own": 2 + c, "opp": 2 + c + t, "ref": 2 + c + 2 * t, "season": 2 + c + 2 * t + r + 1}

    def expected(
        self, team_id: int, opp_id: int, comp: int, is_home: bool, referee: str | None, season: int | None = None
    ) -> float:
        o, b = self._o(), self.beta
        eta = b[0] + b[1] * is_home
        if comp in COMP_INDEX:
            eta += b[o["comp"] + COMP_INDEX[comp]]
        if (i := self.season_index.get((comp, season))) is not None:
            eta += b[o["season"] + i]
        if (i := self.team_index.get(int(team_id))) is not None:
            eta += b[o["own"] + i]
        if (i := self.team_index.get(int(opp_id))) is not None:
            eta += b[o["opp"] + i]
        if (i := self.referee_index.get(referee_key(referee) or "")) is not None:
            eta += b[o["ref"] + i]
        return math.exp(eta)

    def predict(self, home_id: int, away_id: int, comp: int, referee: str | None, season: int | None = None) -> CardsPrediction:
        return CardsPrediction(
            home=self.expected(home_id, away_id, comp, True, referee, season),
            away=self.expected(away_id, home_id, comp, False, referee, season),
            dispersion_team=self.dispersion_team,
            dispersion_total=self.dispersion_total,
        )


def fit_cards_model(hist: History, as_of: date, params: CardsModelParams = CardsModelParams()) -> CardsModel | None:
    cutoff = pd.Timestamp(as_of)
    g = hist.finished_before(cutoff)
    g = g[(g["match_date"] >= cutoff - pd.Timedelta(days=params.window_days)) & g["home_cards"].notna() & g["away_cards"].notna()]
    if len(g) < 50:
        return None

    teams = sorted(set(g["home_team_id"]) | set(g["away_team_id"]))
    team_index = {int(t): i for i, t in enumerate(teams)}
    refs = sorted({r for r in g["referee_key"] if r})
    referee_index = {r: i for i, r in enumerate(refs)}
    seasons = sorted(set(zip(g["league_id"].astype(int), g["season"].astype(int))))
    season_index = {s: i for i, s in enumerate(seasons)}
    c, t, nr = len(COMPS), len(teams), len(refs)
    o_comp, o_own, o_opp, o_ref = 2, 2 + c, 2 + c + t, 2 + c + 2 * t
    unknown_ref = o_ref + nr  # columna "árbitro desconocido" (siempre 0 por la penalización)
    o_season = unknown_ref + 1
    n_params = o_season + len(seasons)

    n = len(g)
    comp = g["league_id"].map(COMP_INDEX).to_numpy()
    hi = g["home_team_id"].map(team_index).to_numpy()
    ai = g["away_team_id"].map(team_index).to_numpy()
    ri = np.array([referee_index.get(r, -1) if r else -1 for r in g["referee_key"]])
    ref_col = np.where(ri >= 0, o_ref + ri, unknown_ref)
    ref_val = (ri >= 0).astype(float)

    si = o_season + np.array([season_index[(lg, s)] for lg, s in zip(g["league_id"], g["season"])])
    cols = np.zeros((2 * n, 7), dtype=np.int64)
    vals = np.ones((2 * n, 7))
    cols[:n] = np.column_stack([np.zeros(n), np.ones(n), o_comp + comp, o_own + hi, o_opp + ai, ref_col, si])
    cols[n:] = np.column_stack([np.zeros(n), np.ones(n), o_comp + comp, o_own + ai, o_opp + hi, ref_col, si])
    vals[n:, 1] = 0.0
    vals[:n, 5] = ref_val
    vals[n:, 5] = ref_val

    y = np.concatenate([g["home_cards"].to_numpy(), g["away_cards"].to_numpy()])
    w_game = recency_weights(cutoff, g["match_date"], params.half_life_days)
    w = np.concatenate([w_game, w_game])
    penalty = np.concatenate([
        [0.0, 0.0],
        np.full(c, params.ridge_comp),
        np.full(2 * t, params.ridge_team),
        np.full(nr, params.ridge_referee),
        [1e6],
        np.full(len(seasons), params.ridge_season),
    ])
    beta0 = np.zeros(n_params)
    beta0[0] = math.log(max(float(np.average(y, weights=w)), 0.1))
    beta = fit_poisson_ridge(cols, vals, y, w, penalty, beta0)

    return CardsModel(
        beta=beta,
        team_index=team_index,
        referee_index=referee_index,
        season_index=season_index,
        dispersion_team=DISPERSION_TEAM,
        dispersion_total=DISPERSION_TOTAL,
        params=params,
    )
