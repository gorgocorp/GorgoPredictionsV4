"""Backtest: para cada día, ajusta con datos anteriores, predice y compara con lo ocurrido.

No hay momios históricos, así que se mide la calibración (¿lo que el modelo dice 70%
ocurre ~70% de las veces?) en líneas sintéticas alrededor de la proyección, y cómo
habrían salido parlays de N piernas eligiendo las piernas más probables de cada día.
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from app.sports.nba.engine.history import History
from app.sports.nba.engine.player_model import LADDERS, STATS, PlayerModel, PlayerModelParams
from app.sports.nba.engine.team_model import TeamModelParams, fit_team_ratings

PARLAY_SIZES = range(2, 9)
BINS = np.round(np.arange(0.0, 1.0001, 0.1), 2)


@dataclass
class Record:
    group: str
    p: float
    hit: bool
    p_naive: float | None = None


@dataclass
class DayLeg:
    game_id: int
    p: float
    hit: bool


@dataclass
class BacktestResult:
    records: list[Record] = field(default_factory=list)
    residuals: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    parlay_pools: dict[str, list[list[DayLeg]]] = field(default_factory=lambda: defaultdict(list))
    days: int = 0


def _clip(p: float) -> float:
    return min(max(p, 1e-4), 1 - 1e-4)


def _team_day(result: BacktestResult, hist: History, day: pd.Timestamp, params: TeamModelParams) -> list[DayLeg]:
    ratings = fit_team_ratings(hist, day.date(), params)
    games = hist.games
    finished = games[games["is_finished"] & (games["phase"] != "preseason") & (games["game_date"] < day)]
    season = hist.games_on(day.date())["season"].iloc[0]
    wins = defaultdict(lambda: [0, 0])  # tasa de victorias simple de la temporada (referencia ingenua)
    for r in finished[finished["season"] == season].itertuples():
        home_won = r.home_total > r.away_total
        wins[r.home_team_id][0] += home_won
        wins[r.away_team_id][0] += not home_won
        wins[r.home_team_id][1] += 1
        wins[r.away_team_id][1] += 1

    favorites = []
    day_games = hist.games_on(day.date())
    for g in day_games[day_games["is_finished"] & (day_games["phase"] != "preseason")].itertuples():
        pred = ratings.predict(g.home_team_id, g.away_team_id, g.home_b2b, g.away_b2b)
        margin, total = g.home_total - g.away_total, g.home_total + g.away_total
        result.residuals["margen"].append(margin - pred.margin)
        result.residuals["total"].append(total - pred.total)
        result.residuals["puntos equipo"].append(g.home_total - pred.home_points)
        result.residuals["puntos equipo"].append(g.away_total - pred.away_points)

        p_home = pred.p_home_win()
        wh, nh = wins[g.home_team_id]
        wa, na = wins[g.away_team_id]
        ph, pa = (wh + 1) / (nh + 2), (wa + 1) / (na + 2)
        naive = ph * (1 - pa) / (ph * (1 - pa) + pa * (1 - ph))
        fav_home = p_home >= 0.5
        p_fav = p_home if fav_home else 1 - p_home
        hit_fav = (margin > 0) == fav_home
        result.records.append(Record("ganador", p_fav, hit_fav, naive if fav_home else 1 - naive))
        favorites.append(DayLeg(g.id, p_fav, hit_fav))

        center = round(pred.margin)
        for off in (-6, -3, 0, 3, 6):
            t = center + off + 0.5
            result.records.append(Record("handicap", pred.p_margin_over(t), margin > t))
        center = round(pred.total)
        for off in (-10, -5, 0, 5, 10):
            t = center + off + 0.5
            result.records.append(Record("total", pred.p_total_over(t), total > t))
        for side, actual, expected in (("home", g.home_total, pred.home_points), ("away", g.away_total, pred.away_points)):
            center = round(expected)
            for off in (-8, -4, 0, 4, 8):
                t = center + off + 0.5
                result.records.append(Record("total equipo", pred.p_team_over(side, t), actual > t))
    return favorites


def _player_day(result: BacktestResult, hist: History, day: pd.Timestamp, params: PlayerModelParams) -> list[DayLeg]:
    model = PlayerModel(hist, day.date(), params)
    ps = hist.player_stats
    today = ps[(ps["game_date"] == day) & (ps["phase"] != "preseason") & (ps["minutes"] > 0)]
    legs = []
    for row in today.itertuples():
        if not model.is_eligible(row.player_id):
            continue
        for stat in STATS:
            proj = model.projection(row.player_id, stat, row.opponent_id)
            actual = getattr(row, stat)
            for k in LADDERS[stat]:
                p = proj.p_at_least(k)
                if not 0.03 <= p <= 0.97:
                    continue
                hits, n = model.hit_rate(row.player_id, stat, k, 10)
                naive = (hits + 0.5) / (n + 1) if n else None
                hit = actual >= k
                result.records.append(Record(f"jugador: {stat}", p, hit, naive))
                legs.append(DayLeg(row.game_id, p, hit))
    return legs


def run_backtest(
    hist: History,
    start: date,
    end: date,
    team_params: TeamModelParams = TeamModelParams(),
    player_params: PlayerModelParams = PlayerModelParams(),
    players: bool = True,
    every: int = 1,
) -> BacktestResult:
    """`every` > 1 evalúa sólo uno de cada N días (para pruebas rápidas)."""
    result = BacktestResult()
    g = hist.games
    days = sorted(
        g.loc[g["is_finished"] & (g["phase"] != "preseason") & g["game_date"].between(pd.Timestamp(start), pd.Timestamp(end)), "game_date"].unique()
    )
    for day in map(pd.Timestamp, days[::every]):
        result.parlay_pools["ganadores"].append(_team_day(result, hist, day, team_params))
        if players:
            result.parlay_pools["props"].append(_player_day(result, hist, day, player_params))
        result.days += 1
    return result


# ---------------------------------------------------------------- reporte

def _metrics(records: list[Record]) -> dict:
    p = np.array([r.p for r in records])
    y = np.array([r.hit for r in records], dtype=float)
    out = {
        "n": len(records),
        "brier": float(np.mean((p - y) ** 2)),
        "logloss": float(-np.mean(y * np.log(np.clip(p, 1e-4, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-4, 1)))),
    }
    naive = [(r.p_naive, r.hit) for r in records if r.p_naive is not None]
    if naive:
        pn = np.array([_clip(a) for a, _ in naive])
        yn = np.array([b for _, b in naive], dtype=float)
        pm = np.array([r.p for r in records if r.p_naive is not None])
        out["brier_naive"] = float(np.mean((pn - yn) ** 2))
        out["brier_model_same"] = float(np.mean((pm - yn) ** 2))
    return out


def calibration(records: list[Record]) -> list[tuple[str, int, float, float]]:
    rows = []
    p = np.array([r.p for r in records])
    y = np.array([r.hit for r in records], dtype=float)
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        mask = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if mask.sum() >= 30:
            rows.append((f"{lo:.0%}-{hi:.0%}", int(mask.sum()), float(p[mask].mean()), float(y[mask].mean())))
    return rows


def simulate_parlays(pools: list[list[DayLeg]], min_p: float, max_p: float) -> list[tuple[int, int, float, float]]:
    """Cada día, la pierna más probable de cada partido dentro de [min_p, max_p]; luego las N mejores.

    Devuelve [(N, días, probabilidad promedio predicha, frecuencia real de acierto)].
    """
    out = []
    for n in PARLAY_SIZES:
        predicted, actual = [], []
        for legs in pools:
            best: dict[int, DayLeg] = {}
            for leg in legs:
                if min_p <= leg.p <= max_p and (leg.game_id not in best or leg.p > best[leg.game_id].p):
                    best[leg.game_id] = leg
            if len(best) < n:
                continue
            chosen = sorted(best.values(), key=lambda leg: leg.p, reverse=True)[:n]
            predicted.append(math.prod(leg.p for leg in chosen))
            actual.append(all(leg.hit for leg in chosen))
        if predicted:
            out.append((n, len(predicted), float(np.mean(predicted)), float(np.mean(actual))))
    return out


def format_report(result: BacktestResult) -> str:
    lines = [f"Días evaluados: {result.days}", ""]
    lines.append("Desviación estándar de los errores (fuera de muestra):")
    for name, values in result.residuals.items():
        arr = np.array(values)
        lines.append(f"  {name:<14} sd={arr.std():5.2f}  sesgo={arr.mean():+5.2f}  n={len(arr)}")
    lines.append("")

    groups = defaultdict(list)
    for r in result.records:
        groups[r.group].append(r)
    lines.append(f"{'Mercado':<22}{'n':>8}{'Brier':>9}{'LogLoss':>9}   Brier ingenuo vs modelo")
    for name in sorted(groups):
        m = _metrics(groups[name])
        naive = f"   {m['brier_naive']:.4f} vs {m['brier_model_same']:.4f}" if "brier_naive" in m else ""
        lines.append(f"{name:<22}{m['n']:>8}{m['brier']:>9.4f}{m['logloss']:>9.4f}{naive}")
    lines.append("  (Brier: menor es mejor. 'Ingenuo' = tasa de acierto simple: % de victorias o últimos 10)")
    lines.append("")

    for title, keys in (("Equipos", ("ganador", "handicap", "total", "total equipo")), ("Jugadores", None)):
        recs = [r for r in result.records if (r.group in keys if keys else r.group.startswith("jugador"))]
        if not recs:
            continue
        lines.append(f"Calibración — {title} (predicho vs real):")
        for label, n, pred, real in calibration(recs):
            lines.append(f"  {label:<10} n={n:<7} predicho={pred:6.1%}  real={real:6.1%}  dif={real - pred:+6.1%}")
        lines.append("")

    for pool, (lo, hi) in (("ganadores", (0.55, 0.90)), ("props", (0.60, 0.85))):
        if pool not in result.parlay_pools:
            continue
        lines.append(f"Parlays de {pool} (piernas con prob. entre {lo:.0%} y {hi:.0%}, una por partido):")
        lines.append(f"  {'Piernas':>7} {'Días':>6} {'Predicho':>9} {'Real':>7}")
        for n, days, pred, real in simulate_parlays(result.parlay_pools[pool], lo, hi):
            lines.append(f"  {n:>7} {days:>6} {pred:>9.1%} {real:>7.1%}")
        lines.append("")
    return "\n".join(lines)
