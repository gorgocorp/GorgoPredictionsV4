"""Picks de un día: evalúa todas las piernas posibles y arma parlays de 2 a 8 piernas."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

import pandas as pd
import psycopg

from app.config import BOOKMAKER, PRICE_BOOKMAKERS
from app.core.parlay import Candidate
from app.sports.nba.engine.history import History
from app.sports.nba.engine.legs import LegSpec, describe
from app.sports.nba.engine.odds import Quote, market_probabilities, match_player, parse_selection
from app.sports.nba.engine.player_model import LADDERS, STATS, PlayerModel, PlayerModelParams, Projection
from app.sports.nba.engine.roster import RosterChange, roster_changes
from app.sports.nba.engine.team_model import (
    P_MISSING,
    GamePrediction,
    TeamModelParams,
    TeamRatings,
    fit_team_ratings,
    with_absences,
)

AVAILABILITY_SQL = "SELECT player_id, status FROM nba.v_player_availability WHERE game_date = %s"
# Sin props para quien probablemente no juega; "en duda" se conserva marcado.
NOT_PLAYING = frozenset({"out", "doubtful"})
FLAGGED = frozenset({"questionable", "probable"})

ODDS_SQL = """
SELECT game_id, bookmaker_name, bet_id, bet_name, selection, odd::float AS odd
FROM nba.v_odds_latest
WHERE game_id = ANY(%s)
"""

# Un jugador es candidato sólo si jugó alguno de los últimos partidos oficiales de su equipo.
# Backtest de 10 días: sin filtro se anulaba el 32% de las props (jugador no jugó); con los
# últimos 5 partidos, 17%; con los últimos 2, 12% (perdiendo sólo 2.5% de jugadores que sí jugaron).
RECENT_TEAM_GAMES = 2
# Al inicio de temporada (menos de RECENT_TEAM_GAMES partidos oficiales) se usan los últimos
# partidos incluida la pretemporada, donde las estrellas descansan seguido.
EARLY_SEASON_GAMES = 5

# Líneas propias del modelo para mercados de equipo cuando la casa no publica esa línea
# (pretemporada, partidos sin cobertura). Desplazamientos alrededor de la proyección:
# las mismas que se validaron en el backtest (calibración dentro de ±1.3 pts).
MODEL_LINE_OFFSETS = {
    "spread": (-9, -6, -3, 0, 3, 6, 9),
    "total": (-15, -10, -5, 0, 5, 10, 15),
    "team_total": (-12, -8, -4, 0, 4, 8, 12),
}


@dataclass
class GameCard:
    game_id: int
    matchup: str
    starts_at: pd.Timestamp
    prediction: GamePrediction
    has_odds: bool
    home_missing: float = 0.0
    away_missing: float = 0.0
    home_roster: float = 0.0
    away_roster: float = 0.0
    roster_detail: dict | None = None
    preseason: bool = False
    candidates: list[Candidate] = field(default_factory=list)

    @property
    def external_id(self) -> int:
        """Partido en el proveedor (para el registro común core.matches)."""
        return self.game_id

    @property
    def p_home_win(self) -> float:
        return adjust_team_probability("ml", self.prediction.p_home_win(), self.preseason)


# Pretemporada (medido con los 65 partidos de oct-2025, prediciendo sólo con datos previos):
# - Ganador y handicap: el modelo sobreestima al favorito (82% esperado, 70% real en piernas de
#   75%+). Acercar a 50% a la mitad bajó el log loss de 0.700 a 0.678.
# - Totales: bien calibrados, sin ajuste.
# - Props: los jugadores juegan 75% de sus minutos (19 vs 25.5). Producción esperada x0.75 bajó el
#   log loss de 0.500 a 0.437 (piernas de 75%+: 85% esperado / 66% real -> 81% / 80%).
PRESEASON_WIN_SHRINK = 0.48
PRESEASON_PRODUCTION = 0.75


def adjust_team_probability(market: str, p: float, preseason: bool) -> float:
    if preseason and market in ("ml", "spread"):
        return 0.5 + PRESEASON_WIN_SHRINK * (p - 0.5)
    return p


def adjust_projection(proj: Projection, preseason: bool) -> Projection:
    if not preseason:
        return proj
    return Projection(proj.mean * PRESEASON_PRODUCTION, proj.var * PRESEASON_PRODUCTION, proj.normal)


def _team_probability(spec: LegSpec, pred: GamePrediction) -> float:
    if spec.market == "ml":
        p = pred.p_home_win()
        return p if spec.side == "home" else 1 - p
    if spec.market == "spread":
        # Home -5.5 gana si margen > 5.5; Away +5.5 gana si margen < 5.5.
        p_home_cover = pred.p_margin_over(-spec.line if spec.side == "home" else spec.line)
        return p_home_cover if spec.side == "home" else 1 - p_home_cover
    if spec.market == "total":
        p = pred.p_total_over(spec.line)
        return p if spec.side == "over" else 1 - p
    if spec.market == "team_total":
        p = pred.p_team_over(spec.team, spec.line)
        return p if spec.side == "over" else 1 - p
    raise ValueError(spec.market)


def _recent_game_cutoffs(hist: History, cutoff: pd.Timestamp, season: str) -> dict[int, pd.Timestamp]:
    """Fecha desde la que un jugador debe haber jugado para considerarse activo, por equipo."""
    g = hist.games
    g = g[g["is_finished"] & (g["game_date"] < cutoff)]
    appearances = pd.concat(
        [g[["home_team_id", "game_date", "season", "phase"]].rename(columns={"home_team_id": "team_id"}),
         g[["away_team_id", "game_date", "season", "phase"]].rename(columns={"away_team_id": "team_id"})]
    ).sort_values("game_date")
    official = appearances[(appearances["season"] == season) & (appearances["phase"] != "preseason")]
    out = appearances.groupby("team_id").tail(EARLY_SEASON_GAMES).groupby("team_id")["game_date"].min().to_dict()
    recent = official.groupby("team_id").tail(RECENT_TEAM_GAMES)
    counts = recent.groupby("team_id").size()
    for team_id, first in recent.groupby("team_id")["game_date"].min().items():
        if counts[team_id] >= RECENT_TEAM_GAMES:
            out[team_id] = first
    return out


# Rotación para el ajuste por bajas: jugadores con al menos 5 apariciones y 20+ minutos de
# promedio en los últimos 15 partidos oficiales de su equipo. Un lesionado de larga duración
# queda fuera: sus ausencias ya están reflejadas en los ratings del equipo.
ROTATION_TEAM_GAMES = 15
ROTATION_MIN_GAMES = 5
ROTATION_MIN_MINUTES = 20.0


def rotation_points(hist: History, cutoff: pd.Timestamp, current_team: dict[int, int]) -> dict[int, tuple[int, float]]:
    """{jugador: (equipo, puntos por partido)} de la rotación actual de cada equipo."""
    g = hist.games
    g = g[g["is_finished"] & (g["phase"] != "preseason") & (g["game_date"] < cutoff)]
    appearances = pd.concat(
        [g[["id", "home_team_id", "game_date"]].rename(columns={"id": "game_id", "home_team_id": "team_id"}),
         g[["id", "away_team_id", "game_date"]].rename(columns={"id": "game_id", "away_team_id": "team_id"})]
    )
    last = appearances.sort_values("game_date").groupby("team_id").tail(ROTATION_TEAM_GAMES)[["game_id", "team_id"]]
    ps = hist.player_stats
    rows = ps[ps["minutes"] > 0].merge(last, on=["game_id", "team_id"])
    agg = rows.groupby(["player_id", "team_id"]).agg(games=("minutes", "size"), mins=("minutes", "mean"), pts=("points", "mean"))
    agg = agg[(agg["games"] >= ROTATION_MIN_GAMES) & (agg["mins"] >= ROTATION_MIN_MINUTES)]
    return {
        int(pid): (int(team), float(r["pts"]))
        for (pid, team), r in agg.iterrows()
        if current_team.get(pid) == team
    }


def missing_points(rotation: dict[int, tuple[int, float]], availability: dict[int, str], team_id: int) -> float:
    """Puntos por partido esperados que faltan en un equipo según la disponibilidad."""
    return sum(
        P_MISSING.get(availability.get(pid, "available"), 0.0) * pts
        for pid, (team, pts) in rotation.items()
        if team == team_id
    )


def model_line_specs(pred: GamePrediction) -> list[LegSpec]:
    """Piernas de equipo en líneas de medio punto alrededor de la proyección del modelo."""
    specs = [LegSpec("ml", "home"), LegSpec("ml", "away")]
    center = round(pred.margin)
    for off in MODEL_LINE_OFFSETS["spread"]:
        t = center + off + 0.5  # el local cubre "-t" si gana por más de t
        specs += [LegSpec("spread", "home", -t), LegSpec("spread", "away", t)]
    center = round(pred.total)
    for off in MODEL_LINE_OFFSETS["total"]:
        t = center + off + 0.5
        specs += [LegSpec("total", "over", t), LegSpec("total", "under", t)]
    for team, points in (("home", pred.home_points), ("away", pred.away_points)):
        center = round(points)
        for off in MODEL_LINE_OFFSETS["team_total"]:
            t = center + off + 0.5
            specs += [LegSpec("team_total", "over", t, team=team), LegSpec("team_total", "under", t, team=team)]
    return specs


def book_odds(quotes: list[Quote], books: list[str] = PRICE_BOOKMAKERS) -> dict[str, float]:
    """Momio de cada casa de `books` que cotiza la pierna, con el nombre tal como está en `books`."""
    wanted = {b.lower(): b for b in books}
    return {wanted[q.bookmaker.lower()]: q.odd for q in quotes if q.bookmaker.lower() in wanted}


def _pick_price(quotes: list[Quote], bookmaker: str) -> Quote | None:
    if bookmaker == "best":
        return max(quotes, key=lambda q: q.odd, default=None)
    return next((q for q in quotes if q.bookmaker.lower() == bookmaker.lower()), None)


@dataclass
class DayModels:
    """Modelos ajustados con datos anteriores al día (se reutilizan al recalcular)."""

    ratings: TeamRatings
    players: PlayerModel


def fit_models(
    hist: History,
    day: date,
    team_params: TeamModelParams = TeamModelParams(),
    player_params: PlayerModelParams = PlayerModelParams(),
) -> DayModels:
    return DayModels(ratings=fit_team_ratings(hist, day, team_params), players=PlayerModel(hist, day, player_params))


def generate_day(
    conn: psycopg.Connection,
    hist: History,
    day: date,
    bookmaker: str = BOOKMAKER,
    models: DayModels | None = None,
    team_params: TeamModelParams = TeamModelParams(),
    player_params: PlayerModelParams = PlayerModelParams(),
) -> list[GameCard]:
    """Piernas de los partidos de `day`. Los modelos deben estar ajustados con `day` como fecha de corte."""
    games = hist.games_on(day)
    games = games[games["phase"] != "preseason"] if (games["phase"] != "preseason").any() else games
    if games.empty:
        return []

    models = models or fit_models(hist, day, team_params, player_params)
    ratings, players = models.ratings, models.players
    odds_rows = conn.execute(ODDS_SQL, (games["id"].tolist(),)).fetchall()
    odds_by_game = defaultdict(list)
    for r in odds_rows:
        odds_by_game[r["game_id"]].append(r)

    cutoff = pd.Timestamp(day)
    recent_cutoff = _recent_game_cutoffs(hist, cutoff, games["season"].iloc[0])
    availability = {r["player_id"]: r["status"] for r in conn.execute(AVAILABILITY_SQL, (day,))}
    rotation = rotation_points(hist, cutoff, players.current_team)
    changes = roster_changes(hist, cutoff, games["season"].iloc[0], availability, team_params)

    def roster_summary(change: RosterChange | None) -> dict | None:
        if change is None or not (change.departed or change.arrived):
            return None
        name = lambda pid: hist.player_names.get(pid, str(pid))  # noqa: E731
        return {
            "gain": round(-change.net_lost, 1),
            "weight": round(change.weight, 2),
            "departed": [[name(pid), round(pts, 1)] for pid, pts in sorted(change.departed, key=lambda x: -x[1])],
            "arrived": [[name(pid), round(pts, 1)] for pid, pts in sorted(change.arrived, key=lambda x: -x[1])],
        }
    cards = []
    for g in games.itertuples():
        home, away = hist.team_names[g.home_team_id], hist.team_names[g.away_team_id]
        matchup = f"{away} @ {home}"
        pred = ratings.predict(g.home_team_id, g.away_team_id, g.home_b2b, g.away_b2b)
        home_missing = missing_points(rotation, availability, g.home_team_id)
        away_missing = missing_points(rotation, availability, g.away_team_id)
        home_change, away_change = changes.get(g.home_team_id), changes.get(g.away_team_id)
        home_roster = home_change.adjustment if home_change else 0.0
        away_roster = away_change.adjustment if away_change else 0.0
        pred = with_absences(pred, home_missing + home_roster, away_missing + away_roster)
        preseason = g.phase == "preseason"

        roster = {
            pid: hist.player_names.get(pid, str(pid))
            for pid, team in players.current_team.items()
            if team in (g.home_team_id, g.away_team_id)
            and players.last_game[pid] >= recent_cutoff.get(team, cutoff)
            and availability.get(pid) not in NOT_PLAYING
        }

        # Momios de la casa -> especificaciones de pierna.
        quotes: list[Quote] = []
        for r in odds_by_game.get(g.id, []):
            parsed = parse_selection(r["bet_id"], r["bet_name"], r["selection"])
            if parsed is None or parsed.spec is None:
                continue
            spec = parsed.spec
            if spec.market == "player":
                pid = match_player(parsed.player_name, roster)
                if pid is None or not players.is_eligible(pid):
                    continue
                spec = LegSpec("player", spec.side, spec.line, stat=spec.stat, player_id=pid)
            quotes.append(Quote(spec, r["bookmaker_name"] or "?", r["odd"]))
        p_market = market_probabilities(quotes)
        quotes_by_spec = defaultdict(list)
        for q in quotes:
            quotes_by_spec[q.spec].append(q)

        card = GameCard(
            g.id, matchup, g.starts_at, pred, has_odds=bool(quotes),
            home_missing=home_missing, away_missing=away_missing,
            home_roster=home_roster, away_roster=away_roster,
            roster_detail={"home": roster_summary(home_change), "away": roster_summary(away_change)},
            preseason=preseason,
        )

        def status_of(pid: int) -> str | None:
            status = availability.get(pid)
            return status if status in FLAGGED else None

        def player_context(spec: LegSpec) -> list[tuple[int, int]]:
            k = int(spec.line) + 1 if spec.side == "over" else None
            if k is None:
                return []
            return [players.hit_rate(spec.player_id, spec.stat, k, n) for n in (10, 25)]

        def opponent(pid: int) -> int:
            return g.away_team_id if players.current_team[pid] == g.home_team_id else g.home_team_id

        # 1) Piernas con momio.
        for spec, spec_quotes in quotes_by_spec.items():
            if spec.market == "player":
                proj = adjust_projection(players.projection(spec.player_id, spec.stat, opponent(spec.player_id)), preseason)
                p = proj.p_over(spec.line) if spec.side == "over" else 1 - proj.p_over(spec.line)
                name = roster[spec.player_id]
                hits = player_context(spec)
            else:
                p = adjust_team_probability(spec.market, _team_probability(spec, pred), preseason)
                name, hits = None, []
            price = _pick_price(spec_quotes, bookmaker)
            card.candidates.append(
                Candidate(
                    sport="nba",
                    external_id=g.id,
                    matchup=matchup,
                    spec=spec,
                    description=describe(spec, home, away, name),
                    p_model=p,
                    odd=price.odd if price else None,
                    bookmaker=price.bookmaker if price else None,
                    p_market=p_market.get(spec),
                    hits=hits,
                    player_status=status_of(spec.player_id) if spec.market == "player" else None,
                    book_odds=book_odds(spec_quotes),
                )
            )

        # 2) Mercados de equipo sin momio: líneas propias del modelo (si la casa no tiene esa línea).
        priced_team = {c.spec for c in card.candidates if c.spec.market != "player"}
        for spec in model_line_specs(pred):
            if spec in priced_team:
                continue
            p = adjust_team_probability(spec.market, _team_probability(spec, pred), preseason)
            if 0.05 <= p <= 0.97:
                card.candidates.append(
                    Candidate(sport="nba", external_id=g.id, matchup=matchup, spec=spec, description=describe(spec, home, away), p_model=p)
                )

        # 3) Props sin momio: escalones "N o más" para cada jugador elegible.
        priced = {(c.spec.player_id, c.spec.stat, c.spec.line) for c in card.candidates if c.spec.market == "player"}
        for pid, name in roster.items():
            if not players.is_eligible(pid):
                continue
            for stat in STATS:
                proj = adjust_projection(players.projection(pid, stat, opponent(pid)), preseason)
                for k in LADDERS[stat]:
                    spec = LegSpec("player", "over", k - 0.5, stat=stat, player_id=pid)
                    if (pid, stat, spec.line) in priced:
                        continue
                    p = proj.p_at_least(k)
                    if not 0.05 <= p <= 0.97:
                        continue
                    card.candidates.append(
                        Candidate(
                            sport="nba",
                            external_id=g.id,
                            matchup=matchup,
                            spec=spec,
                            description=describe(spec, home, away, name),
                            p_model=p,
                            hits=player_context(spec),
                            player_status=status_of(pid),
                        )
                    )
        cards.append(card)
    return cards
