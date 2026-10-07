"""Backtest: para cada día, ajusta con datos anteriores, predice y compara con lo ocurrido.

No hay momios históricos, así que se mide la calibración (¿lo que el modelo dice 70% ocurre
~70% de las veces?), el log loss contra una referencia ingenua (frecuencias de la liga) y cómo
habrían salido parlays de N piernas eligiendo la pierna más probable de cada partido.

Las props se evalúan como se apostarían antes del partido con la alineación publicada: sólo
titulares (la casa anula la apuesta si el jugador no juega).
"""

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from app.sports.futbol.engine.cards_model import CardsModelParams, fit_cards_model
from app.sports.futbol.engine.history import History
from app.sports.futbol.engine.legs import LegSpec, settle
from app.sports.futbol.engine.picks import model_line_specs, team_probability
from app.sports.futbol.engine.player_model import LADDERS, STATS, PlayerModel, PlayerModelParams
from app.sports.futbol.engine.team_model import GoalModelParams, fit_goal_ratings

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
    fixture_id: int
    p: float
    hit: bool


@dataclass
class BacktestResult:
    records: list[Record] = field(default_factory=list)
    outcome_loss: dict[str, list[float]] = field(default_factory=lambda: defaultdict(list))
    parlay_pools: dict[str, list[list[DayLeg]]] = field(default_factory=lambda: defaultdict(list))
    days: int = 0
    fixtures: int = 0


def _clip(p: float) -> float:
    return min(max(p, 1e-4), 1 - 1e-4)


def _league_rates(hist: History, cutoff: pd.Timestamp) -> dict[int, dict[str, float]]:
    """Frecuencias de la liga en el último año (referencia ingenua)."""
    f = hist.finished_before(cutoff)
    f = f[f["match_date"] >= cutoff - pd.Timedelta(days=365)]
    out = {}
    for lg, g in f.groupby("league_id"):
        total = g["ft_home"] + g["ft_away"]
        cards = g["home_cards"] + g["away_cards"]
        rates = {
            "home": float((g["ft_home"] > g["ft_away"]).mean()),
            "draw": float((g["ft_home"] == g["ft_away"]).mean()),
            "away": float((g["ft_home"] < g["ft_away"]).mean()),
            "btts": float(((g["ft_home"] > 0) & (g["ft_away"] > 0)).mean()),
        }
        for line in (0.5, 1.5, 2.5, 3.5, 4.5):
            rates[f"over{line}"] = float((total > line).mean())
        for line in np.arange(0.5, 10.0, 1.0):
            rates[f"cards{line}"] = float((cards.dropna() > line).mean()) if cards.notna().any() else 0.5
        out[int(lg)] = rates
    return out


def _team_day(result, hist, day, ratings, cards_model) -> list[DayLeg]:
    naive = _league_rates(hist, day)
    legs = []
    today = hist.fixtures_on(day.date())
    for f in today[today["is_finished"] & today["ft_home"].notna()].itertuples():
        result.fixtures += 1
        pred = ratings.predict(f.home_team_id, f.away_team_id, f.league_id, day, f.season)
        cards = cards_model.predict(f.home_team_id, f.away_team_id, f.league_id, f.referee, f.season) if cards_model else None
        h, a = int(f.ft_home), int(f.ft_away)
        hc, ac = f.home_cards, f.away_cards
        has_cards = not (math.isnan(hc) or math.isnan(ac))
        rates = naive.get(int(f.league_id))

        outcome = "home" if h > a else "draw" if h == a else "away"
        probs = {"home": pred.p_home(), "draw": pred.p_draw(), "away": pred.p_away()}
        result.outcome_loss["modelo"].append(-math.log(_clip(probs[outcome])))
        if rates:
            result.outcome_loss["ingenuo (liga)"].append(-math.log(_clip(rates[outcome])))
        for side, p in probs.items():
            result.records.append(Record(f"1x2: {side}", p, outcome == side, rates[side] if rates else None))

        for line in (0.5, 1.5, 2.5, 3.5, 4.5):
            result.records.append(Record("goles: total", pred.p_total_over(line), h + a > line, rates[f"over{line}"] if rates else None))
        for side, goals in (("home", h), ("away", a)):
            for line in (0.5, 1.5, 2.5):
                result.records.append(Record("goles: equipo", pred.p_team_over(side, line), goals > line))
        result.records.append(Record("ambos anotan", pred.p_btts(), h > 0 and a > 0, rates["btts"] if rates else None))
        for score, p in pred.top_scores(3):
            result.records.append(Record("marcador exacto (top 3)", p, score == f"{h}-{a}"))
        if cards and has_cards:
            center = round(cards.total)
            for off in (-2, -1, 0, 1, 2):
                line = max(center + off, 0) + 0.5
                result.records.append(Record("tarjetas: total", cards.p_total_over(line), hc + ac > line, rates.get(f"cards{line}") if rates else None))
            for side, n in (("home", hc), ("away", ac)):
                for line in (0.5, 1.5, 2.5, 3.5):
                    result.records.append(Record("tarjetas: equipo", cards.p_team_over(side, line), n > line))

        # Para parlays: todas las piernas de equipo que el sistema ofrecería, con su resultado.
        for spec in model_line_specs(pred, cards):
            if spec.market in ("cards", "team_cards") and not has_cards:
                continue
            p = team_probability(spec, pred, cards)
            if p is None:
                continue
            hit = settle(spec, h, a, hc if has_cards else None, ac if has_cards else None)
            legs.append(DayLeg(f.id, p, bool(hit)))
    return legs


def _player_day(result, hist, day, players: PlayerModel, goal_ratings, cards_model) -> list[DayLeg]:
    ps = hist.player_stats
    today = ps[(ps["match_date"] == day) & (ps["minutes"] > 0) & ~ps["is_substitute"].astype(bool)]
    fixtures = hist.fixtures.set_index("id")
    legs = []
    context: dict[tuple[int, int], tuple[float, float | None]] = {}
    for row in today.itertuples():
        if not players.is_eligible(row.player_id, "starter") or players.current_team.get(row.player_id) != row.team_id:
            continue
        key = (row.fixture_id, row.team_id)
        if key not in context:
            f = fixtures.loc[row.fixture_id]
            is_home = row.team_id == f["home_team_id"]
            opp = f["away_team_id"] if is_home else f["home_team_id"]
            goals = goal_ratings.expected_goals(row.team_id, opp, f["league_id"], is_home, day, f["season"])
            cards = cards_model.expected(row.team_id, opp, f["league_id"], is_home, f["referee"], f["season"]) if cards_model else None
            context[key] = (goals, cards)
        team_goals, team_cards = context[key]
        for stat in STATS:
            proj = players.projection(row.player_id, stat, team_goals, team_cards, "starter")
            actual = getattr(row, stat)
            for k in LADDERS[stat]:
                p = proj.p_at_least(k)
                if not 0.03 <= p <= 0.97:
                    continue
                hits, n = players.hit_rate(row.player_id, stat, k, 10)
                naive = (hits + 0.5) / (n + 1) if n else None
                hit = actual >= k
                result.records.append(Record(f"jugador: {stat}", p, hit, naive))
                legs.append(DayLeg(row.fixture_id, p, hit))
    return legs


def run_backtest(
    hist: History,
    start: date,
    end: date,
    goal_params: GoalModelParams = GoalModelParams(),
    cards_params: CardsModelParams = CardsModelParams(),
    player_params: PlayerModelParams = PlayerModelParams(),
    players: bool = True,
    every: int = 1,
    leagues: set[int] | None = None,
) -> BacktestResult:
    """`every` > 1 evalúa sólo uno de cada N días (para pruebas rápidas)."""
    result = BacktestResult()
    f = hist.fixtures
    mask = f["is_finished"] & f["match_date"].between(pd.Timestamp(start), pd.Timestamp(end))
    if leagues:
        mask &= f["league_id"].isin(leagues)
    days = sorted(f.loc[mask, "match_date"].unique())
    for day in map(pd.Timestamp, days[::every]):
        ratings = fit_goal_ratings(hist, day.date(), goal_params)
        cards_model = fit_cards_model(hist, day.date(), cards_params)
        result.parlay_pools["equipos"].append(_team_day(result, hist, day, ratings, cards_model))
        if players:
            pm = PlayerModel(hist, day.date(), player_params)
            result.parlay_pools["props"].append(_player_day(result, hist, day, pm, ratings, cards_model))
        result.days += 1
    return result


# ---------------------------------------------------------------- reporte

def _metrics(records: list[Record]) -> dict:
    p = np.array([_clip(r.p) for r in records])
    y = np.array([r.hit for r in records], dtype=float)
    out = {
        "n": len(records),
        "brier": float(np.mean((p - y) ** 2)),
        "logloss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
    }
    naive = [(r.p_naive, r.hit, r.p) for r in records if r.p_naive is not None]
    if naive:
        pn = np.array([_clip(a) for a, _, _ in naive])
        yn = np.array([b for _, b, _ in naive], dtype=float)
        pm = np.array([c for _, _, c in naive])
        out["brier_naive"] = float(np.mean((pn - yn) ** 2))
        out["brier_model_same"] = float(np.mean((pm - yn) ** 2))
    return out


def calibration(records: list[Record], min_n: int = 30) -> list[tuple[str, int, float, float]]:
    rows = []
    p = np.array([r.p for r in records])
    y = np.array([r.hit for r in records], dtype=float)
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        mask = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if mask.sum() >= min_n:
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
                if min_p <= leg.p <= max_p and (leg.fixture_id not in best or leg.p > best[leg.fixture_id].p):
                    best[leg.fixture_id] = leg
            if len(best) < n:
                continue
            chosen = sorted(best.values(), key=lambda leg: leg.p, reverse=True)[:n]
            predicted.append(math.prod(leg.p for leg in chosen))
            actual.append(all(leg.hit for leg in chosen))
        if predicted:
            out.append((n, len(predicted), float(np.mean(predicted)), float(np.mean(actual))))
    return out


def format_report(result: BacktestResult) -> str:
    lines = [f"Días evaluados: {result.days} · partidos: {result.fixtures}", ""]
    lines.append("Log loss del 1X2 (menor es mejor):")
    for name, values in result.outcome_loss.items():
        lines.append(f"  {name:<16} {np.mean(values):.4f}  (n={len(values)})")
    lines.append("")

    groups = defaultdict(list)
    for r in result.records:
        groups[r.group].append(r)
    lines.append(f"{'Mercado':<26}{'n':>8}{'Brier':>9}{'LogLoss':>9}   Brier ingenuo vs modelo")
    for name in sorted(groups):
        m = _metrics(groups[name])
        naive = f"   {m['brier_naive']:.4f} vs {m['brier_model_same']:.4f}" if "brier_naive" in m else ""
        lines.append(f"{name:<26}{m['n']:>8}{m['brier']:>9.4f}{m['logloss']:>9.4f}{naive}")
    lines.append("  (Brier: menor es mejor. 'Ingenuo' = frecuencia de la liga en el último año, o últimos 10 del jugador)")
    lines.append("")

    sections = (
        ("Goles y resultado", lambda g: g.startswith(("1x2", "goles", "ambos"))),
        ("Tarjetas", lambda g: g.startswith("tarjetas")),
        ("Jugadores", lambda g: g.startswith("jugador")),
    )
    for title, pick in sections:
        recs = [r for r in result.records if pick(r.group)]
        if not recs:
            continue
        lines.append(f"Calibración — {title} (predicho vs real):")
        for label, n, pred, real in calibration(recs):
            lines.append(f"  {label:<10} n={n:<7} predicho={pred:6.1%}  real={real:6.1%}  dif={real - pred:+6.1%}")
        lines.append("")

    for pool, (lo, hi) in (("equipos", (0.60, 0.87)), ("props", (0.60, 0.87))):
        if pool not in result.parlay_pools:
            continue
        lines.append(f"Parlays de {pool} (pierna más probable de cada partido entre {lo:.0%} y {hi:.0%}):")
        lines.append(f"  {'Piernas':>7} {'Días':>6} {'Predicho':>9} {'Real':>7}")
        for n, days, pred, real in simulate_parlays(result.parlay_pools[pool], lo, hi):
            lines.append(f"  {n:>7} {days:>6} {pred:>9.1%} {real:>7.1%}")
        lines.append("")
    return "\n".join(lines)
