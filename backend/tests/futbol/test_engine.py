import math

import numpy as np
import pytest

from app.sports.futbol.engine.dist import prob_at_least, prob_over
from app.sports.futbol.engine.legs import LegSpec, describe, settle
from app.sports.futbol.engine.odds import Quote, american, market_probabilities, match_player, names_match, parse_selection
from app.core.parlay import Candidate, ParlayFilters, build_parlay
from app.sports.futbol.engine.picks import book_odds, model_line_specs, team_probability
from app.sports.futbol.engine.player_model import PlayerProjection
from app.sports.futbol.engine.team_model import MatchPrediction, score_matrix
from app.sports.futbol.engine.cards_model import CardsPrediction

# ---------------------------------------------------------------- momios


def test_parse_result_markets():
    assert parse_selection(1, "Match Winner", "Draw").spec == LegSpec("1x2", "draw")
    assert parse_selection(12, "Double Chance", "Home/Draw").spec == LegSpec("dc", "1x")
    assert parse_selection(12, "Double Chance", "Draw/Away").spec == LegSpec("dc", "x2")
    assert parse_selection(8, "Both Teams Score", "No").spec == LegSpec("btts", "no")
    assert parse_selection(10, "Exact Score", "2:1").spec == LegSpec("score", "2-1")


def test_parse_totals_only_half_lines():
    assert parse_selection(5, "Goals Over/Under", "Over 2.5").spec == LegSpec("total", "over", 2.5)
    assert parse_selection(5, "Goals Over/Under", "Over 2.25") is None  # línea asiática
    assert parse_selection(5, "Goals Over/Under", "Under 2") is None  # push posible
    assert parse_selection(17, "Total - Away", "Under 1.5").spec == LegSpec("team_total", "under", 1.5, team="away")
    assert parse_selection(80, "Cards Over/Under", "Over 4.5").spec == LegSpec("cards", "over", 4.5)
    assert parse_selection(82, "Home Team Total Cards", "Under 2.5").spec == LegSpec("team_cards", "under", 2.5, team="home")


def test_parse_player_markets():
    scorer = parse_selection(92, "Anytime Goal Scorer", "Viktor Gyokeres")
    assert scorer.player_name == "Viktor Gyokeres"
    assert scorer.spec == LegSpec("player", "over", 0.5, stat="goals")
    assert parse_selection(95, "To Score Two or More Goals", "Erling Haaland").spec.line == 1.5
    assert parse_selection(257, "Player to Score or Assist", "Bukayo Saka").spec.stat == "ga"
    assert parse_selection(92, "Anytime Goal Scorer", "No Goalscorer") is None
    shots = parse_selection(242, "Player Shots On Target", "Bukayo Saka - Over 1.5")
    assert (shots.player_name, shots.spec.stat, shots.spec.line) == ("Bukayo Saka", "shots_on", 1.5)
    assert parse_selection(242, "Player Shots On Target", "Bukayo Saka") is None  # sin línea: no se adivina
    assert parse_selection(275, "Away Player Shots On Target Total", "Bukayo Saka") is None  # mercado mal etiquetado


@pytest.mark.parametrize(
    "book, stats, expected",
    [
        ("Viktor Gyokeres", "Viktor Gyökeres", True),
        ("Martin Odegaard", "M. Ødegaard", True),
        ("Lukasz Fabianski", "Łukasz Fabiański", True),
        ("Bukayo Saka", "B. Saka", True),
        ("Alexis Mac Allister", "Alexis Mac Allister", True),
        ("Gabriel Jesus", "Gabriel Martinelli", False),
    ],
)
def test_names_match(book, stats, expected):
    assert names_match(book, stats) is expected


def test_match_player_rejects_ambiguous():
    assert match_player("Bukayo Saka", {1: "B. Saka", 2: "Bukayo Saka"}) == 2
    assert match_player("Gabriel Jesus", {1: "G. Jesus", 2: "G. Jesus"}) is None


def test_market_probabilities_three_way_and_double_chance():
    quotes = [
        Quote(LegSpec("1x2", "home"), "Pinnacle", 2.0),
        Quote(LegSpec("1x2", "draw"), "Pinnacle", 4.0),
        Quote(LegSpec("1x2", "away"), "Pinnacle", 4.0),
        Quote(LegSpec("1x2", "home"), "Bet365", 1.8),
        Quote(LegSpec("1x2", "draw"), "Bet365", 3.5),
        Quote(LegSpec("1x2", "away"), "Bet365", 4.2),
    ]
    probs = market_probabilities(quotes)
    assert probs[LegSpec("1x2", "home")] == pytest.approx(0.5)  # Pinnacle manda
    assert probs[LegSpec("dc", "x2")] == pytest.approx(0.5)
    assert sum(probs[LegSpec("1x2", s)] for s in ("home", "draw", "away")) == pytest.approx(1.0)


def test_market_probabilities_needs_both_sides():
    probs = market_probabilities([Quote(LegSpec("total", "over", 2.5), "Bet365", 1.8)])
    assert probs == {}


def test_book_odds_keeps_configured_bookmakers():
    spec = LegSpec("1x2", "home")
    quotes = [Quote(spec, "Bet365", 1.80), Quote(spec, "1XBET", 1.86), Quote(spec, "Pinnacle", 1.90)]
    assert book_odds(quotes, ["Bet365", "1xBet"]) == {"Bet365": 1.80, "1xBet": 1.86}
    assert book_odds(quotes, ["Betano"]) == {}


def test_american_odds():
    assert american(2.5) == "+150"
    assert american(1.5) == "-200"


# ---------------------------------------------------------------- distribuciones y marcadores


def test_poisson_closed_form():
    assert prob_at_least(1.3, 1.3, 1) == pytest.approx(1 - math.exp(-1.3))
    assert prob_over(2.0, 2.0, 1.5) == pytest.approx(1 - math.exp(-2) * 3)


def test_score_matrix_sums_to_one_and_dixon_coles_adds_draws():
    m = score_matrix(1.4, 1.1, rho=-0.1)
    assert m.sum() == pytest.approx(1.0)
    plain = score_matrix(1.4, 1.1, rho=0.0)
    assert np.trace(m) > np.trace(plain)


def test_match_prediction_markets_are_consistent():
    pred = MatchPrediction.from_rates(1.6, 1.0, rho=-0.06)
    assert pred.p_home() + pred.p_draw() + pred.p_away() == pytest.approx(1.0)
    assert pred.p_total_over(0.5) > pred.p_total_over(2.5) > pred.p_total_over(4.5)
    assert pred.p_team_over("home", 0.5) == pytest.approx(1 - pred.matrix[0, :].sum())
    assert pred.p_btts() == pytest.approx(pred.matrix[1:, 1:].sum())
    assert pred.top_scores(1)[0][0] in ("1-0", "1-1")
    symmetric = MatchPrediction.from_rates(1.2, 1.2, rho=-0.06)
    assert symmetric.p_home() == pytest.approx(symmetric.p_away())


def test_model_line_specs_two_sides_add_up():
    pred = MatchPrediction.from_rates(1.7, 0.9, rho=-0.06)
    cards = CardsPrediction(home=2.1, away=2.6, dispersion_team=1.1, dispersion_total=1.2)
    specs = model_line_specs(pred, cards)
    assert {s.market for s in specs} == {"1x2", "dc", "btts", "total", "team_total", "score", "cards", "team_cards"}
    for spec in specs:
        if spec.side in ("over", "under", "yes", "no"):
            p = team_probability(spec, pred, cards) + team_probability(spec.opposite(), pred, cards)
            assert p == pytest.approx(1.0)
    one_x = team_probability(LegSpec("dc", "1x"), pred, cards)
    assert one_x == pytest.approx(pred.p_home() + pred.p_draw())


def test_player_projection_is_conditional_on_playing():
    proj = PlayerProjection(rate90=0.6, dispersion=1.0, p_start=0.6, p_sub=0.2, min_start=85, min_sub=20)
    starter = PlayerProjection(rate90=0.6, dispersion=1.0, p_start=1.0, p_sub=0.0, min_start=85, min_sub=20)
    # Sin alineación mezcla titular y suplente; confirmado como titular, sube.
    assert proj.p_at_least(1) < starter.p_at_least(1)
    assert starter.p_at_least(1) == pytest.approx(1 - math.exp(-0.6 * 85 / 90))
    assert proj.p_over(0.5) == proj.p_at_least(1)


# ---------------------------------------------------------------- piernas


@pytest.mark.parametrize(
    "spec, h, a, expected",
    [
        (LegSpec("1x2", "draw"), 1, 1, True),
        (LegSpec("dc", "x2"), 2, 1, False),
        (LegSpec("dc", "12"), 0, 1, True),
        (LegSpec("total", "under", 2.5), 2, 1, False),
        (LegSpec("team_total", "over", 0.5, team="away"), 3, 0, False),
        (LegSpec("btts", "yes"), 2, 1, True),
        (LegSpec("btts", "no"), 0, 0, True),
        (LegSpec("score", "2-1"), 2, 1, True),
    ],
)
def test_settle_goal_markets(spec, h, a, expected):
    assert settle(spec, h, a) is expected


def test_settle_cards_and_players():
    assert settle(LegSpec("cards", "over", 4.5), 1, 0, 3, 2) is True
    assert settle(LegSpec("cards", "over", 4.5), 1, 0, None, 2) is None
    assert settle(LegSpec("team_cards", "under", 1.5, team="away"), 1, 0, 3, 1) is True
    scorer = LegSpec("player", "over", 0.5, stat="goals", player_id=7)
    assert settle(scorer, 1, 0, player_value=1) is True
    assert settle(scorer, 1, 0, player_value=None) is None


def test_describe_in_spanish():
    assert describe(LegSpec("dc", "1x"), "América", "Chivas") == "América o empate"
    assert describe(LegSpec("total", "over", 2.5), "A", "B") == "Más de 2.5 goles"
    assert describe(LegSpec("score", "2-1"), "América", "Chivas") == "Marcador exacto América 2-1 Chivas"
    assert describe(LegSpec("team_cards", "over", 1.5, team="away"), "A", "Chivas") == "Chivas más de 1.5 tarjetas"
    assert describe(LegSpec("player", "over", 0.5, stat="goals", player_id=1), "A", "B", "H. Martín") == "H. Martín anota"
    assert describe(LegSpec("player", "over", 1.5, stat="shots_on", player_id=1), "A", "B", "Saka") == "Saka 2+ remates a puerta"
    assert describe(LegSpec("player", "over", 0.5, stat="cards", player_id=1), "A", "B", "Saka") == "Saka recibe tarjeta"


# ---------------------------------------------------------------- parlays


def _cand(fixture_id, p, odd=None):
    return Candidate("futbol", fixture_id, "A vs B", LegSpec("1x2", "home"), f"f{fixture_id}", p, odd=odd)


def test_build_parlay_one_leg_per_fixture_and_best_first():
    cands = [_cand(1, 0.80), _cand(1, 0.85), _cand(2, 0.70), _cand(3, 0.65), _cand(4, 0.50)]
    filters = ParlayFilters(min_prob=0.6, min_odd=1.0, min_ev=None, require_odds=False)
    parlay = build_parlay(cands, 3, "prob", filters)
    assert [c.p_model for c in parlay.legs] == [0.85, 0.70, 0.65]
    assert parlay.probability == pytest.approx(0.85 * 0.70 * 0.65)
    assert build_parlay(cands, 4, "prob", filters) is None


def test_build_parlay_ev_mode_uses_price():
    cands = [_cand(1, 0.80, 1.20), _cand(1, 0.60, 1.90), _cand(2, 0.70, 1.50)]
    filters = ParlayFilters(min_prob=0.55, min_odd=1.1, min_ev=0.0)
    parlay = build_parlay(cands, 2, "ev", filters)
    assert parlay.odd == pytest.approx(1.90 * 1.50)


def test_build_parlay_skips_questionable_players_by_default():
    doubtful = _cand(1, 0.90)
    doubtful.player_status = "questionable"
    cands = [doubtful, _cand(1, 0.70), _cand(2, 0.80)]
    filters = ParlayFilters(min_prob=0.6, max_prob=0.95, min_odd=1.0, min_ev=None, require_odds=False)
    assert [c.p_model for c in build_parlay(cands, 2, "prob", filters).legs] == [0.80, 0.70]
