"""Modelo de puntos por equipo: ratings de ofensiva y defensa con peso por recencia.

Cada equipo en cada partido es una observación:

    puntos = media + localía·es_local + b2b_propio·jugó_ayer + b2b_rival·rival_jugó_ayer
             + ofensiva[equipo] + defensiva[rival]

Se ajusta por mínimos cuadrados ponderados (más peso a partidos recientes) con
penalización ridge sobre ofensiva/defensiva, que las jala hacia 0 cuando hay pocos datos.
De los puntos esperados de cada lado salen el margen y el total; con una desviación
estándar fija (medida en el backtest) se obtiene la probabilidad de cualquier línea.
"""

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from app.sports.nba.config import NBA_FRANCHISE_IDS
from app.sports.nba.engine.history import History

TEAM_IDS = sorted(NBA_FRANCHISE_IDS)
TEAM_INDEX = {team_id: i for i, team_id in enumerate(TEAM_IDS)}
N_TEAMS = len(TEAM_IDS)
N_FIXED = 4  # media, localía, b2b propio, b2b rival


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass(frozen=True)
class TeamModelParams:
    # Elegidos con backtest sobre 2025-26 (búsqueda en rejilla por log loss del ganador).
    half_life_days: float = 60.0
    ridge: float = 2.0
    # Desviaciones que minimizan el log loss de cada mercado en el backtest. La del margen
    # queda por debajo de la sd medida (14.6) porque los márgenes tienen colas pesadas
    # (palizas) y lo que decide al ganador es la zona cercana a 0.
    sigma_margin: float = 13.0
    sigma_total: float = 19.0
    sigma_team_points: float = 12.0


@dataclass(frozen=True)
class GamePrediction:
    home_points: float
    away_points: float
    params: TeamModelParams

    @property
    def margin(self) -> float:
        """Margen esperado del local (positivo = gana el local)."""
        return self.home_points - self.away_points

    @property
    def total(self) -> float:
        return self.home_points + self.away_points

    def p_home_win(self) -> float:
        return normal_cdf(self.margin / self.params.sigma_margin)

    def p_margin_over(self, threshold: float) -> float:
        """P(margen del local > threshold)."""
        return 1.0 - normal_cdf((threshold - self.margin) / self.params.sigma_margin)

    def p_total_over(self, line: float) -> float:
        return 1.0 - normal_cdf((line - self.total) / self.params.sigma_total)

    def p_team_over(self, side: str, line: float) -> float:
        points = self.home_points if side == "home" else self.away_points
        return 1.0 - normal_cdf((line - points) / self.params.sigma_team_points)


@dataclass(frozen=True)
class TeamRatings:
    mean: float
    home: float
    b2b_own: float
    b2b_opp: float
    offense: np.ndarray
    defense: np.ndarray
    params: TeamModelParams

    def expected_points(self, team_id: int, opp_id: int, is_home: bool, own_b2b: bool, opp_b2b: bool) -> float:
        return (
            self.mean
            + self.home * is_home
            + self.b2b_own * own_b2b
            + self.b2b_opp * opp_b2b
            + self.offense[TEAM_INDEX[team_id]]
            + self.defense[TEAM_INDEX[opp_id]]
        )

    def predict(self, home_id: int, away_id: int, home_b2b: bool, away_b2b: bool) -> GamePrediction:
        return GamePrediction(
            home_points=self.expected_points(home_id, away_id, True, home_b2b, away_b2b),
            away_points=self.expected_points(away_id, home_id, False, away_b2b, home_b2b),
            params=self.params,
        )

    def defense_factor(self, team_id: int) -> float:
        """Puntos que permite el equipo relativo a la media (1.05 = permite 5% más)."""
        return (self.mean + self.defense[TEAM_INDEX[team_id]]) / self.mean


# Efecto de las bajas, medido sobre 2025-26 (1,970 equipo-partido): por cada punto por partido que
# aporta un jugador de rotación que no juega, su equipo anota 0.077 menos (±0.026) y el rival
# 0.060 más (±0.026). Sin un anotador de 25 pts el margen se mueve ~3.4 puntos.
ABSENCE_OWN = -0.077
ABSENCE_OPP = 0.060

# Probabilidad de que no juegue según la designación del reporte oficial.
P_MISSING = {"out": 1.0, "doubtful": 0.8, "questionable": 0.35, "probable": 0.05, "available": 0.0}


def with_absences(pred: GamePrediction, home_missing: float, away_missing: float) -> GamePrediction:
    """Ajusta la proyección por los puntos por partido esperados que faltan en cada equipo."""
    return GamePrediction(
        home_points=pred.home_points + ABSENCE_OWN * home_missing + ABSENCE_OPP * away_missing,
        away_points=pred.away_points + ABSENCE_OWN * away_missing + ABSENCE_OPP * home_missing,
        params=pred.params,
    )


def fit_team_ratings(hist: History, as_of: date, params: TeamModelParams = TeamModelParams()) -> TeamRatings:
    """Ajusta con partidos terminados (sin pretemporada) anteriores a `as_of`."""
    cutoff = pd.Timestamp(as_of)
    g = hist.games
    g = g[g["is_finished"] & (g["phase"] != "preseason") & (g["game_date"] < cutoff)]
    if g.empty:
        raise ValueError(f"No hay partidos anteriores a {as_of} para ajustar el modelo")

    # La antigüedad incluye el receso de verano a propósito: se probó no contarlo (la temporada
    # anterior llega con más peso al debut) y empeoró el log loss de las primeras 8 semanas de
    # 2025-26 de 0.594 a 0.613. Los equipos cambian mucho en el verano; olvidar rápido funciona mejor.
    age = (cutoff - g["game_date"]).dt.days.to_numpy(dtype=float)
    w_game = 0.5 ** (age / params.half_life_days)
    n = len(g)
    home_idx = g["home_team_id"].map(TEAM_INDEX).to_numpy()
    away_idx = g["away_team_id"].map(TEAM_INDEX).to_numpy()
    home_b2b = g["home_b2b"].to_numpy(dtype=float)
    away_b2b = g["away_b2b"].to_numpy(dtype=float)

    X = np.zeros((2 * n, N_FIXED + 2 * N_TEAMS))
    rows = np.arange(n)
    # Filas 0..n-1: anota el local.
    X[rows, 0] = 1.0
    X[rows, 1] = 1.0
    X[rows, 2] = home_b2b
    X[rows, 3] = away_b2b
    X[rows, N_FIXED + home_idx] = 1.0
    X[rows, N_FIXED + N_TEAMS + away_idx] = 1.0
    # Filas n..2n-1: anota el visitante.
    X[n + rows, 0] = 1.0
    X[n + rows, 2] = away_b2b
    X[n + rows, 3] = home_b2b
    X[n + rows, N_FIXED + away_idx] = 1.0
    X[n + rows, N_FIXED + N_TEAMS + home_idx] = 1.0

    y = np.concatenate([g["home_total"].to_numpy(dtype=float), g["away_total"].to_numpy(dtype=float)])
    w = np.concatenate([w_game, w_game])

    penalty = np.r_[np.zeros(N_FIXED), np.full(2 * N_TEAMS, params.ridge)]
    A = X.T @ (X * w[:, None]) + np.diag(penalty)
    b = X.T @ (w * y)
    beta = np.linalg.solve(A, b)

    return TeamRatings(
        mean=float(beta[0]),
        home=float(beta[1]),
        b2b_own=float(beta[2]),
        b2b_opp=float(beta[3]),
        offense=beta[N_FIXED : N_FIXED + N_TEAMS],
        defense=beta[N_FIXED + N_TEAMS :],
        params=params,
    )
