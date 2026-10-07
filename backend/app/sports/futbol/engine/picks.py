"""Picks de un día: evalúa todas las piernas posibles de cada partido."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

import pandas as pd
import psycopg

from app.config import PRICE_BOOKMAKERS
from app.sports.futbol.engine.cards_model import CardsModel, CardsModelParams, CardsPrediction, fit_cards_model
from app.sports.futbol.engine.history import History
from app.sports.futbol.engine.legs import LegSpec, describe
from app.sports.futbol.engine.odds import Quote, market_probabilities, match_player, parse_selection
from app.core.parlay import Candidate
from app.sports.futbol.engine.player_model import LADDERS, STATS, PlayerModel, PlayerModelParams
from app.sports.futbol.engine.team_model import GoalModelParams, MatchPrediction, fit_goal_ratings

ODDS_SQL = """
SELECT fixture_id, bookmaker_name, bet_id, bet_name, selection, odd::float AS odd
FROM futbol.v_odds_latest
WHERE fixture_id = ANY(%s)
"""
AVAILABILITY_SQL = "SELECT fixture_id, player_id, status FROM futbol.v_player_availability WHERE fixture_id = ANY(%s)"
LINEUPS_SQL = "SELECT fixture_id, team_id, player_id, is_starter FROM futbol.fixture_lineups WHERE fixture_id = ANY(%s)"

# Líneas propias del modelo cuando la casa no publica esa línea.
TOTAL_LINES = (0.5, 1.5, 2.5, 3.5, 4.5)
TEAM_TOTAL_LINES = (0.5, 1.5, 2.5)
TEAM_CARD_LINES = (0.5, 1.5, 2.5, 3.5)
CARD_OFFSETS = (-2, -1, 0, 1, 2)  # alrededor de las tarjetas esperadas del partido
TOP_SCORES = 8

UNPRICED_RANGE = (0.05, 0.97)


@dataclass
class FixtureCard:
    fixture_id: int
    league_id: int
    matchup: str
    starts_at: pd.Timestamp
    prediction: MatchPrediction
    cards: CardsPrediction | None
    has_odds: bool
    lineups: bool = False
    candidates: list[Candidate] = field(default_factory=list)

    @property
    def external_id(self) -> int:
        """Partido en el proveedor (para el registro común core.matches)."""
        return self.fixture_id


def team_probability(spec: LegSpec, pred: MatchPrediction, cards: CardsPrediction | None) -> float | None:
    m, side = spec.market, spec.side
    if m == "1x2":
        return {"home": pred.p_home, "draw": pred.p_draw, "away": pred.p_away}[side]()
    if m == "dc":
        h, d, a = pred.p_home(), pred.p_draw(), pred.p_away()
        return {"1x": h + d, "x2": d + a, "12": h + a}[side]
    if m == "total":
        p = pred.p_total_over(spec.line)
        return p if side == "over" else 1 - p
    if m == "team_total":
        p = pred.p_team_over(spec.team, spec.line)
        return p if side == "over" else 1 - p
    if m == "btts":
        p = pred.p_btts()
        return p if side == "yes" else 1 - p
    if m == "score":
        h, a = (int(x) for x in side.split("-"))
        return pred.p_score(h, a)
    if cards is None:
        return None
    if m == "cards":
        p = cards.p_total_over(spec.line)
        return p if side == "over" else 1 - p
    if m == "team_cards":
        p = cards.p_team_over(spec.team, spec.line)
        return p if side == "over" else 1 - p
    raise ValueError(m)


def model_line_specs(pred: MatchPrediction, cards: CardsPrediction | None) -> list[LegSpec]:
    """Piernas de equipo que el modelo evalúa aunque la casa no las publique."""
    specs = [LegSpec("1x2", s) for s in ("home", "draw", "away")]
    specs += [LegSpec("dc", s) for s in ("1x", "x2", "12")]
    specs += [LegSpec("btts", s) for s in ("yes", "no")]
    for line in TOTAL_LINES:
        specs += [LegSpec("total", "over", line), LegSpec("total", "under", line)]
    for team in ("home", "away"):
        for line in TEAM_TOTAL_LINES:
            specs += [LegSpec("team_total", "over", line, team=team), LegSpec("team_total", "under", line, team=team)]
    specs += [LegSpec("score", s) for s, _ in pred.top_scores(TOP_SCORES)]
    if cards is not None:
        center = round(cards.total)
        for off in CARD_OFFSETS:
            line = max(center + off, 0) + 0.5
            specs += [LegSpec("cards", "over", line), LegSpec("cards", "under", line)]
        for team in ("home", "away"):
            for line in TEAM_CARD_LINES:
                specs += [LegSpec("team_cards", "over", line, team=team), LegSpec("team_cards", "under", line, team=team)]
    return list(dict.fromkeys(specs))


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

    ratings: object
    cards: CardsModel | None
    players: PlayerModel


def fit_models(
    hist: History,
    day: date,
    goal_params: GoalModelParams = GoalModelParams(),
    cards_params: CardsModelParams = CardsModelParams(),
    player_params: PlayerModelParams = PlayerModelParams(),
) -> DayModels:
    return DayModels(
        ratings=fit_goal_ratings(hist, day, goal_params),
        cards=fit_cards_model(hist, day, cards_params),
        players=PlayerModel(hist, day, player_params),
    )


def generate_day(
    conn: psycopg.Connection,
    hist: History,
    day: date,
    bookmaker: str = "Bet365",
    models: DayModels | None = None,
) -> list[FixtureCard]:
    fixtures = hist.fixtures_on(day)
    if fixtures.empty:
        return []
    models = models or fit_models(hist, day)
    ratings, cards_model, players = models.ratings, models.cards, models.players
    ids = fixtures["id"].tolist()

    odds_by_fixture = defaultdict(list)
    for r in conn.execute(ODDS_SQL, (ids,)):
        odds_by_fixture[r["fixture_id"]].append(r)
    availability = {(r["fixture_id"], r["player_id"]): r["status"] for r in conn.execute(AVAILABILITY_SQL, (ids,))}
    lineups: dict[int, dict[int, dict[int, bool]]] = defaultdict(lambda: defaultdict(dict))
    for r in conn.execute(LINEUPS_SQL, (ids,)):
        lineups[r["fixture_id"]][r["team_id"]][r["player_id"]] = r["is_starter"]

    cards_out = []
    for f in fixtures.itertuples():
        home, away = hist.team_names[f.home_team_id], hist.team_names[f.away_team_id]
        matchup = f"{home} vs {away}"
        when = pd.Timestamp(day)
        side_of = {f.home_team_id: "home", f.away_team_id: "away"}
        fixture_lineups = lineups.get(f.id, {})
        has_lineups = all(fixture_lineups.get(t) for t in side_of)

        # Plantel de cada lado: jugadores cuyo equipo actual es uno de los dos.
        squad = {pid: team for pid, team in players.current_team.items() if team in side_of}
        if has_lineups:
            # Con alineación confirmada, quien no está en la lista no juega.
            for team_id, listed in fixture_lineups.items():
                for pid in listed:
                    squad.setdefault(pid, team_id)

        def lineup_of(pid: int) -> str | None:
            listed = fixture_lineups.get(squad[pid])
            if not has_lineups or not listed:
                return None
            if pid not in listed:
                return "absent"
            return "starter" if listed[pid] else "bench"

        pred = ratings.predict(f.home_team_id, f.away_team_id, f.league_id, when, f.season)
        cards = cards_model.predict(f.home_team_id, f.away_team_id, f.league_id, f.referee, f.season) if cards_model else None
        team_goals = {"home": pred.home_goals, "away": pred.away_goals}
        team_cards = {"home": cards.home, "away": cards.away} if cards else {"home": None, "away": None}

        roster: dict[int, str] = {}
        lineup_status: dict[int, str | None] = {}
        for pid, team in squad.items():
            status = availability.get((f.id, pid))
            lineup = lineup_of(pid)
            if status == "out" or lineup in ("absent", "bench"):
                continue
            if not players.is_eligible(pid, lineup):
                continue
            roster[pid] = hist.player_names.get(pid, str(pid))
            lineup_status[pid] = lineup

        def player_flag(pid: int) -> str | None:
            if lineup_status.get(pid) == "starter":
                return "starter"
            return "questionable" if availability.get((f.id, pid)) == "questionable" else None

        def player_probability(spec: LegSpec) -> float:
            side = side_of[squad[spec.player_id]]
            proj = players.projection(spec.player_id, spec.stat, team_goals[side], team_cards[side], lineup_status.get(spec.player_id))
            p = proj.p_over(spec.line)
            return p if spec.side == "over" else 1 - p

        def hits(spec: LegSpec) -> list[tuple[int, int]]:
            if spec.side != "over":
                return []
            k = int(spec.line) + 1
            return [players.hit_rate(spec.player_id, spec.stat, k, n) for n in (10, 25)]

        # Momios de la casa -> especificaciones de pierna.
        quotes: list[Quote] = []
        for r in odds_by_fixture.get(f.id, []):
            parsed = parse_selection(r["bet_id"], r["bet_name"], r["selection"])
            if parsed is None:
                continue
            spec = parsed.spec
            if spec.market == "player":
                pid = match_player(parsed.player_name, roster)
                if pid is None:
                    continue
                spec = LegSpec("player", spec.side, spec.line, stat=spec.stat, player_id=pid)
            quotes.append(Quote(spec, r["bookmaker_name"] or "?", r["odd"]))
        p_market = market_probabilities(quotes)
        quotes_by_spec = defaultdict(list)
        for q in quotes:
            quotes_by_spec[q.spec].append(q)

        card = FixtureCard(
            f.id, f.league_id, matchup, f.starts_at, pred, cards, has_odds=bool(quotes), lineups=has_lineups,
        )

        def add(spec: LegSpec, p: float, price: Quote | None = None, prices: dict[str, float] | None = None) -> None:
            is_player = spec.market == "player"
            card.candidates.append(
                Candidate(
                    sport="futbol",
                    external_id=f.id,
                    matchup=matchup,
                    spec=spec,
                    description=describe(spec, home, away, roster.get(spec.player_id) if is_player else None),
                    p_model=p,
                    odd=price.odd if price else None,
                    bookmaker=price.bookmaker if price else None,
                    p_market=p_market.get(spec),
                    hits=hits(spec) if is_player else [],
                    player_status=player_flag(spec.player_id) if is_player else None,
                    book_odds=prices or {},
                )
            )

        # 1) Piernas con momio.
        for spec, spec_quotes in quotes_by_spec.items():
            p = player_probability(spec) if spec.market == "player" else team_probability(spec, pred, cards)
            if p is None or not 0.0 < p < 1.0:
                continue
            add(spec, p, _pick_price(spec_quotes, bookmaker), book_odds(spec_quotes))

        # 2) Mercados de equipo sin momio: líneas propias del modelo.
        priced = set(quotes_by_spec)
        lo, hi = UNPRICED_RANGE
        for spec in model_line_specs(pred, cards):
            if spec in priced:
                continue
            p = team_probability(spec, pred, cards)
            if p is not None and lo <= p <= hi:
                add(spec, p)

        # 3) Props sin momio: escalones "N o más" para cada jugador elegible.
        for pid in roster:
            for stat in STATS:
                for k in LADDERS[stat]:
                    spec = LegSpec("player", "over", k - 0.5, stat=stat, player_id=pid)
                    if spec in priced:
                        continue
                    p = player_probability(spec)
                    if lo <= p <= hi:
                        add(spec, p)
        cards_out.append(card)
    return cards_out
