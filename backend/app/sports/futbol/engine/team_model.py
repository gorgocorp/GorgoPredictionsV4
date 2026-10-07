"""Modelo de goles: ratings de ataque y defensa con peso por recencia (Poisson + Dixon-Coles).

Cada equipo en cada partido es una observación:

    log(goles esperados) = media + competición + competición×temporada + localía (+ de la competición)
                           + ataque[equipo] + defensa[rival]
                           + ataque_liga[liga del equipo] + defensa_liga[liga del rival]

- Se ajusta por máxima verosimilitud de Poisson con penalización ridge (los ratings con pocos
  datos se jalan hacia 0 = equipo promedio) y peso por recencia.
- El objetivo mezcla goles y xG del proveedor (los xG son menos ruidosos que los goles).
- "competición×temporada" capta que una temporada sale más goleadora que la anterior (en 2026-27
  varias ligas subieron 0.3–0.6 goles por partido); con pocos partidos se queda cerca de 0.
- La fuerza por liga sólo se identifica con partidos entre ligas: copas internacionales y
  equipos que suben o bajan. Así una copa (Champions, Europa, Libertadores) compara equipos
  de ligas distintas. En un partido de liga, la "liga del equipo" es esa misma liga; en una
  copa, la última liga doméstica que jugó el equipo (u "otra" si no es de nuestras ligas).

De los goles esperados de cada lado sale la matriz de marcadores (Poisson independientes con
la corrección de Dixon-Coles para 0-0, 1-0, 0-1 y 1-1), y de ella todos los mercados.

No hay ajuste por bajas: se probó restar a cada equipo la parte de su ataque que aporta un titular
habitual ausente (según la lista de bajas de la API o según la alineación confirmada) y en el
backtest empeoró siempre, más cuanto mayor el ajuste (log loss del 1X2 1.0109 sin ajuste, 1.0131
con la mitad del aporte). Los ratings con recencia ya reflejan las ausencias largas.
"""

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from app.sports.futbol.config import CUPS, LEAGUES
from app.sports.futbol.engine.dist import poisson_pmf
from app.sports.futbol.engine.glm import fit_poisson_ridge
from app.sports.futbol.engine.history import History, recency_weights

COMPS = sorted(LEAGUES)
COMP_INDEX = {c: i for i, c in enumerate(COMPS)}
DOMESTIC = [c for c in COMPS if c not in CUPS]
OTHER_LEAGUE = 0  # equipos de copa cuya liga no seguimos
LEAGUE_KEYS = DOMESTIC + [OTHER_LEAGUE]
LEAGUE_INDEX = {lg: i for i, lg in enumerate(LEAGUE_KEYS)}


@dataclass(frozen=True)
class GoalModelParams:
    # Elegidos con backtest (ver README): búsqueda en rejilla por log loss del 1X2 y de los totales.
    half_life_days: float = 180.0
    ridge_team: float = 6.0
    ridge_league: float = 3.0
    ridge_comp: float = 5.0
    ridge_season: float = 5.0
    ridge_home: float = 20.0
    xg_weight: float = 0.5
    rho: float = -0.06
    window_days: int = 760  # partidos más viejos pesan < 1/8 y sólo alentan el ajuste


@dataclass(frozen=True)
class MatchPrediction:
    """Goles esperados de cada lado y la matriz de marcadores a 90 minutos."""

    home_goals: float
    away_goals: float
    matrix: np.ndarray = field(repr=False)

    @classmethod
    def from_rates(cls, home: float, away: float, rho: float, max_goals: int = 10) -> "MatchPrediction":
        return cls(home, away, score_matrix(home, away, rho, max_goals))

    def p_home(self) -> float:
        return float(np.tril(self.matrix, -1).sum())

    def p_draw(self) -> float:
        return float(np.trace(self.matrix))

    def p_away(self) -> float:
        return float(np.triu(self.matrix, 1).sum())

    def p_total_over(self, line: float) -> float:
        n = self.matrix.shape[0]
        totals = np.add.outer(np.arange(n), np.arange(n))
        return float(self.matrix[totals > line].sum())

    def p_team_over(self, side: str, line: float) -> float:
        marginal = self.matrix.sum(axis=1) if side == "home" else self.matrix.sum(axis=0)
        return float(marginal[np.arange(len(marginal)) > line].sum())

    def p_btts(self) -> float:
        return float(self.matrix[1:, 1:].sum())

    def p_score(self, home: int, away: int) -> float:
        n = self.matrix.shape[0]
        return float(self.matrix[home, away]) if home < n and away < n else 0.0

    def top_scores(self, n: int = 5) -> list[tuple[str, float]]:
        flat = np.argsort(self.matrix, axis=None)[::-1][:n]
        size = self.matrix.shape[1]
        return [(f"{i // size}-{i % size}", float(self.matrix.flat[i])) for i in flat]


def score_matrix(home: float, away: float, rho: float, max_goals: int = 10) -> np.ndarray:
    ph = np.array(poisson_pmf(home, max_goals))
    pa = np.array(poisson_pmf(away, max_goals))
    m = np.outer(ph, pa)
    # Dixon-Coles: corrige la dependencia en marcadores bajos (más empates 0-0 y 1-1 que Poisson).
    m[0, 0] *= max(1 - home * away * rho, 0.0)
    m[0, 1] *= max(1 + home * rho, 0.0)
    m[1, 0] *= max(1 + away * rho, 0.0)
    m[1, 1] *= max(1 - rho, 0.0)
    return m / m.sum()


@dataclass
class GoalRatings:
    beta: np.ndarray
    team_index: dict[int, int]
    n_teams: int
    season_index: dict[tuple[int, int], int]
    params: GoalModelParams
    hist: History = field(repr=False)

    # Posiciones en beta.
    @property
    def _o(self) -> dict[str, int]:
        return _offsets(self.n_teams)

    def _team(self, kind: str, team_id: int) -> float:
        i = self.team_index.get(int(team_id))
        return 0.0 if i is None else float(self.beta[self._o[kind] + i])

    def _league(self, kind: str, league: int) -> float:
        return float(self.beta[self._o[kind] + LEAGUE_INDEX[league]])

    def league_of(self, team_id: int, comp: int, when: pd.Timestamp) -> int:
        if comp not in CUPS:
            return comp
        lg = self.hist.domestic_league(team_id, when)
        return lg if lg in LEAGUE_INDEX else OTHER_LEAGUE

    def expected_goals(
        self, team_id: int, opp_id: int, comp: int, is_home: bool, when: pd.Timestamp, season: int | None = None
    ) -> float:
        o, b = self._o, self.beta
        ci = COMP_INDEX.get(comp)
        eta = b[0] + (b[o["comp"] + ci] if ci is not None else 0.0)
        si = self.season_index.get((comp, season))
        if si is not None:
            eta += b[o["season"] + si]
        if is_home:
            eta += b[1] + (b[o["home_dev"] + ci] if ci is not None else 0.0)
        eta += self._team("att", team_id) + self._team("def", opp_id)
        eta += self._league("latt", self.league_of(team_id, comp, when))
        eta += self._league("ldef", self.league_of(opp_id, comp, when))
        return math.exp(eta)

    def predict(self, home_id: int, away_id: int, comp: int, when: pd.Timestamp, season: int | None = None) -> MatchPrediction:
        return MatchPrediction.from_rates(
            self.expected_goals(home_id, away_id, comp, True, when, season),
            self.expected_goals(away_id, home_id, comp, False, when, season),
            self.params.rho,
        )

    def team_strength(self, team_id: int, comp: int, when: pd.Timestamp) -> tuple[float, float]:
        """(ataque, defensa) totales en escala log, para mostrar o depurar."""
        lg = self.league_of(team_id, comp, when)
        return (self._team("att", team_id) + self._league("latt", lg), self._team("def", team_id) + self._league("ldef", lg))


def _offsets(n_teams: int) -> dict[str, int]:
    """Posición de cada bloque de parámetros: media, localía, competición, localía por competición,
    ataque y defensa por equipo, ataque y defensa por liga, y competición×temporada (al final)."""
    c, t, nl = len(COMPS), n_teams, len(LEAGUE_KEYS)
    return {"comp": 2, "home_dev": 2 + c, "att": 2 + 2 * c, "def": 2 + 2 * c + t, "latt": 2 + 2 * c + 2 * t,
            "ldef": 2 + 2 * c + 2 * t + nl, "season": 2 + 2 * c + 2 * t + 2 * nl}


def _design(
    hist: History, g: pd.DataFrame, team_index: dict[int, int], n_teams: int, season_index: dict[tuple[int, int], int]
) -> tuple[np.ndarray, np.ndarray]:
    """Dos filas por partido (anota el local, anota el visitante), 9 columnas activas cada una."""
    o = _offsets(n_teams)
    o_comp, o_home, o_att, o_def, o_latt, o_ldef = o["comp"], o["home_dev"], o["att"], o["def"], o["latt"], o["ldef"]
    n = len(g)
    comp = g["league_id"].map(COMP_INDEX).to_numpy()
    hi = g["home_team_id"].map(team_index).to_numpy()
    ai = g["away_team_id"].map(team_index).to_numpy()

    def league_idx(team_col: str) -> np.ndarray:
        out = []
        for team, lg, when, cup in zip(g[team_col], g["league_id"], g["match_date"], g["is_cup"]):
            if not cup:
                out.append(LEAGUE_INDEX[lg])
            else:
                dom = hist.domestic_league(team, when)
                out.append(LEAGUE_INDEX.get(dom, LEAGUE_INDEX[OTHER_LEAGUE]))
        return np.array(out)

    hl, al = league_idx("home_team_id"), league_idx("away_team_id")
    si = o["season"] + np.array([season_index[(lg, s)] for lg, s in zip(g["league_id"], g["season"])])
    cols = np.zeros((2 * n, 9), dtype=np.int64)
    vals = np.ones((2 * n, 9))
    # Local anota.
    cols[:n] = np.column_stack([np.zeros(n), np.ones(n), o_comp + comp, o_home + comp, o_att + hi, o_def + ai, o_latt + hl, o_ldef + al, si])
    # Visitante anota (sin localía: columnas de localía con valor 0).
    cols[n:] = np.column_stack([np.zeros(n), np.ones(n), o_comp + comp, o_home + comp, o_att + ai, o_def + hi, o_latt + al, o_ldef + hl, si])
    vals[n:, 1] = 0.0
    vals[n:, 3] = 0.0
    return cols, vals


def fit_goal_ratings(hist: History, as_of: date, params: GoalModelParams = GoalModelParams()) -> GoalRatings:
    """Ajusta con partidos terminados anteriores a `as_of`."""
    cutoff = pd.Timestamp(as_of)
    g = hist.finished_before(cutoff)
    g = g[g["match_date"] >= cutoff - pd.Timedelta(days=params.window_days)]
    if len(g) < 50:
        raise ValueError(f"No hay suficientes partidos anteriores a {as_of} para ajustar el modelo")

    teams = sorted(set(g["home_team_id"]) | set(g["away_team_id"]))
    team_index = {int(t): i for i, t in enumerate(teams)}
    n_teams = len(teams)
    seasons = sorted(set(zip(g["league_id"].astype(int), g["season"].astype(int))))
    season_index = {s: i for i, s in enumerate(seasons)}
    cols, vals = _design(hist, g, team_index, n_teams, season_index)

    goals = np.concatenate([g["ft_home"].to_numpy(), g["ft_away"].to_numpy()])
    xg = np.concatenate([g["home_xg"].to_numpy(), g["away_xg"].to_numpy()])
    has_xg = ~np.isnan(xg)
    y = goals.copy()
    y[has_xg] = (1 - params.xg_weight) * goals[has_xg] + params.xg_weight * xg[has_xg]
    w_game = recency_weights(cutoff, g["match_date"], params.half_life_days)
    w = np.concatenate([w_game, w_game])

    c, nl = len(COMPS), len(LEAGUE_KEYS)
    penalty = np.concatenate([
        [0.0, 0.0],
        np.full(c, params.ridge_comp),
        np.full(c, params.ridge_home),
        np.full(2 * n_teams, params.ridge_team),
        np.full(2 * nl, params.ridge_league),
        np.full(len(seasons), params.ridge_season),
    ])
    beta0 = np.zeros(len(penalty))
    beta0[0] = math.log(max(float(np.average(y, weights=w)), 0.1))
    beta = fit_poisson_ridge(cols, vals, y, w, penalty, beta0)
    return GoalRatings(beta=beta, team_index=team_index, n_teams=n_teams, season_index=season_index, params=params, hist=hist)
