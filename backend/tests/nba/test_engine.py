import math

import pytest

from app.sports.nba.engine.legs import LegSpec, describe, settle
from app.sports.nba.engine.odds import (
    Quote, american, market_probabilities, match_player, names_match, parse_selection, sharp_probabilities,
)
from app.core.parlay import Candidate, ParlayFilters, build_parlay
from app.sports.nba.engine.picks import book_odds
from app.sports.nba.engine.player_model import Projection, prob_at_least, prob_at_least_normal
from app.sports.nba.engine.team_model import GamePrediction, TeamModelParams
from app.core.tracking import should_store
from app.sports.nba.sport import SPORT as NBA

# ---------------------------------------------------------------- momios


def test_parse_handicap_number_is_home_line():
    # "Away +5.5" es el otro lado de "Home +5.5": visitante -5.5.
    home = parse_selection(3, "Asian Handicap", "Home +5.5").spec
    away = parse_selection(3, "Asian Handicap", "Away +5.5").spec
    assert (home.side, home.line) == ("home", 5.5)
    assert (away.side, away.line) == ("away", -5.5)
    assert home.group_key() == away.group_key()
    # "Away -3.5" = visitante +3.5
    assert parse_selection(3, "Asian Handicap", "Away -3.5").spec.line == 3.5


def test_parse_skips_whole_lines_and_garbage():
    assert parse_selection(3, "Asian Handicap", "Away +4") is None
    assert parse_selection(4, "Over/Under", "Over 227") is None
    assert parse_selection(11, "Asian Handicap 2nd Qtr", "Draw/Away") is None


def test_parse_totals_and_team_totals():
    assert parse_selection(4, "Over/Under", "Over 226.5").spec == LegSpec("total", "over", 226.5)
    spec = parse_selection(29, "Away Team Total Goals (Including OT)", "Under 110.5").spec
    assert spec == LegSpec("team_total", "under", 110.5, team="away")


def test_parse_player_props():
    ms = parse_selection(999, "Player Points Milestones", "Anthony Edwards - 20")
    assert ms.player_name == "Anthony Edwards"
    assert (ms.spec.stat, ms.spec.side, ms.spec.line) == ("points", "over", 19.5)
    ou = parse_selection(999, "Player Points and Assists", "LaMelo Ball - Under 17.5")
    assert (ou.player_name, ou.spec.stat, ou.spec.side, ou.spec.line) == ("LaMelo Ball", "pa", "under", 17.5)


@pytest.mark.parametrize(
    "book, stats, expected",
    [
        ("Anthony Edwards", "Edwards Anthony", True),
        ("Amari Bailey", "A. Bailey", True),
        ("Shai Gilgeous-Alexander", "Gilgeous-Alexander Shai", True),
        ("Luka Dončić", "Doncic Luka", True),
        ("Jaren Jackson Jr.", "Jackson Jaren", True),
        ("Jalen Williams", "Jaylin Williams", False),
        ("Anthony Davis", "A. Bailey", False),
        ("Day'Ron Sharpe", "Sharpe Day&apos;Ron", True),
        ("Day'Ron Sharpe", "D. Sharpe", True),
    ],
)
def test_names_match(book, stats, expected):
    assert names_match(book, stats) is expected


def test_match_player_prefers_full_name_over_initial():
    assert match_player("Trae Young", {1: "T. Young", 2: "Young Trae"}) == 2


def test_match_player_rejects_ambiguous():
    # Con nombre completo disponible, la inicial no genera ambigüedad.
    assert match_player("Jalen Williams", {1: "J. Williams", 2: "Williams Jalen", 3: "Williams Jaylin"}) == 2
    # Sólo iniciales: dos candidatos posibles -> no se adivina.
    assert match_player("Jalen Williams", {1: "J. Williams", 4: "Jalen Williams Jr. Smith"}) == 1
    assert match_player("Jalen Williams", {1: "J. Williams", 5: "J. Williams"}) is None


def test_market_probabilities_prefers_pinnacle_and_removes_vig():
    over, under = LegSpec("total", "over", 220.5), LegSpec("total", "under", 220.5)
    quotes = [
        Quote(over, "Bet365", 1.80), Quote(under, "Bet365", 2.00),
        Quote(over, "Pinnacle", 1.95), Quote(under, "Pinnacle", 1.95),
    ]
    probs = market_probabilities(quotes)
    assert probs[over] == pytest.approx(0.5)
    assert probs[under] == pytest.approx(0.5)


def test_sharp_probabilities_need_both_sides_from_pinnacle():
    over, under = LegSpec("total", "over", 220.5), LegSpec("total", "under", 220.5)
    quotes = [Quote(over, "Bet365", 1.80), Quote(under, "Bet365", 2.00), Quote(over, "Pinnacle", 1.95)]
    # Pinnacle sólo cotiza un lado: el mercado usa Bet365 y no hay referencia para el CLV.
    assert market_probabilities(quotes)[over] == pytest.approx((1 / 1.8) / (1 / 1.8 + 1 / 2.0))
    assert sharp_probabilities(quotes) == {}
    quotes.append(Quote(under, "Pinnacle", 1.95))
    assert sharp_probabilities(quotes) == pytest.approx({over: 0.5, under: 0.5})


def test_book_odds_keeps_configured_bookmakers():
    spec = LegSpec("ml", "home")
    quotes = [Quote(spec, "Bet365", 1.54), Quote(spec, "1XBET", 1.48), Quote(spec, "Pinnacle", 1.55)]
    assert book_odds(quotes, ["Bet365", "1xBet"]) == {"Bet365": 1.54, "1xBet": 1.48}
    assert book_odds(quotes, ["Betano"]) == {}


def test_store_range_counts_odds_of_any_price_bookmaker():
    # Pierna sin momio de Bet365 pero con momio de 1xBet: se guarda con el rango de "con momio".
    leg = Candidate("nba", 1, "A @ B", LegSpec("total", "over", 230.5), "Más de 230.5", p_model=0.03, book_odds={"1xBet": 9.0})
    assert should_store(leg, NBA)
    assert not should_store(Candidate("nba", 1, "A @ B", LegSpec("total", "over", 230.5), "Más de 230.5", p_model=0.03), NBA)


def test_american_odds():
    assert american(2.5) == "+150"
    assert american(1.5) == "-200"


# ---------------------------------------------------------------- distribuciones


def test_poisson_case_matches_closed_form():
    # Sin sobredispersión: P(X >= 1) = 1 - e^-mean
    assert prob_at_least(2.0, 2.0, 1) == pytest.approx(1 - math.exp(-2.0))


def test_negative_binomial_has_fatter_tail_than_poisson():
    assert prob_at_least(5.0, 15.0, 12) > prob_at_least(5.0, 5.0, 12)


def test_normal_discretized_median():
    # Media 20: "20 o más" ≈ P(X >= 19.5) ≈ un poco más de 50%.
    assert 0.5 < prob_at_least_normal(20.0, 49.0, 20) < 0.56


def test_projection_over_line():
    proj = Projection(20.0, 49.0, normal=True)
    assert proj.p_over(19.5) == pytest.approx(proj.p_at_least(20))


# ---------------------------------------------------------------- equipos y piernas


def test_game_prediction_symmetry():
    pred = GamePrediction(110.0, 110.0, TeamModelParams())
    assert pred.p_home_win() == pytest.approx(0.5)
    assert pred.p_total_over(220.0) == pytest.approx(0.5)
    fav = GamePrediction(115.0, 105.0, TeamModelParams())
    assert fav.p_home_win() > 0.7
    assert fav.p_margin_over(10.0) == pytest.approx(0.5)


@pytest.mark.parametrize(
    "spec, home, away, expected",
    [
        (LegSpec("ml", "home"), 110, 100, True),
        (LegSpec("spread", "home", -5.5), 110, 105, False),
        (LegSpec("spread", "away", 5.5), 110, 105, True),
        (LegSpec("total", "over", 214.5), 110, 105, True),
        (LegSpec("team_total", "under", 104.5, team="away"), 110, 105, False),
    ],
)
def test_settle_team_legs(spec, home, away, expected):
    assert settle(spec, home, away) is expected


def test_settle_player_leg():
    spec = LegSpec("player", "over", 19.5, stat="points", player_id=1)
    assert settle(spec, 100, 90, player_value=20) is True
    assert settle(spec, 100, 90, player_value=None) is None


def test_describe_in_spanish():
    assert describe(LegSpec("spread", "away", -5.5), "Kings", "Lakers") == "Lakers -5.5"
    spec = LegSpec("player", "over", 4.5, stat="fgm", player_id=1)
    assert describe(spec, "A", "B", "Tatum") == "Tatum 5+ tiros de campo anotados"


# ---------------------------------------------------------------- parlays


def _cand(game_id, p, odd=None):
    return Candidate("nba", game_id, "A @ B", LegSpec("ml", "home"), f"g{game_id}", p, odd=odd)


def test_build_parlay_one_leg_per_game_and_best_first():
    cands = [_cand(1, 0.80), _cand(1, 0.85), _cand(2, 0.70), _cand(3, 0.65), _cand(4, 0.50)]
    filters = ParlayFilters(min_prob=0.6, min_odd=1.0, min_ev=None, require_odds=False)
    parlay = build_parlay(cands, 3, "prob", filters)
    assert [c.p_model for c in parlay.legs] == [0.85, 0.70, 0.65]
    assert parlay.probability == pytest.approx(0.85 * 0.70 * 0.65)
    assert build_parlay(cands, 4, "prob", filters) is None  # el juego 4 no pasa el mínimo


def test_build_parlay_ev_mode_uses_price():
    cands = [_cand(1, 0.80, 1.20), _cand(1, 0.60, 1.90), _cand(2, 0.70, 1.50)]
    filters = ParlayFilters(min_prob=0.55, min_odd=1.1, min_ev=0.0)
    parlay = build_parlay(cands, 2, "ev", filters)
    # Juego 1: 0.60·1.90 = 1.14 > 0.80·1.20 = 0.96 (esta última tiene EV negativo y se descarta)
    assert parlay.legs[0].odd == 1.90 or parlay.legs[1].odd == 1.90
    assert parlay.odd == pytest.approx(1.90 * 1.50)
    assert parlay.ev == pytest.approx(0.60 * 0.70 * 1.90 * 1.50 - 1)


def test_model_line_specs_cover_all_team_markets():
    from app.sports.nba.engine.picks import _team_probability, model_line_specs

    pred = GamePrediction(115.2, 108.9, TeamModelParams())
    specs = model_line_specs(pred)
    markets = {s.market for s in specs}
    assert markets == {"ml", "spread", "total", "team_total"}
    assert all(s.line is None or (s.line * 2) % 2 == 1 for s in specs)  # sólo medios puntos
    # Cada línea viene con sus dos lados y sus probabilidades suman 1.
    for spec in specs:
        assert _team_probability(spec, pred) + _team_probability(spec.opposite(), pred) == pytest.approx(1.0)
    # La línea central del total queda cerca de 50%.
    center = [s for s in specs if s.market == "total" and s.side == "over" and abs(s.line - pred.total) < 1]
    assert 0.45 < _team_probability(center[0], pred) < 0.55


def test_build_parlay_skips_questionable_players_by_default():
    doubtful = _cand(1, 0.90)
    doubtful.player_status = "questionable"
    cands = [doubtful, _cand(1, 0.70), _cand(2, 0.80)]
    filters = ParlayFilters(min_prob=0.6, max_prob=0.95, min_odd=1.0, min_ev=None, require_odds=False)
    assert [c.p_model for c in build_parlay(cands, 2, "prob", filters).legs] == [0.80, 0.70]
    with_doubtful = ParlayFilters(min_prob=0.6, max_prob=0.95, min_odd=1.0, min_ev=None, require_odds=False, include_questionable=True)
    assert build_parlay(cands, 2, "prob", with_doubtful).legs[0].p_model == 0.90


def test_capped_points_uses_best_players_within_minutes():
    from app.sports.nba.engine.roster import capped_points

    # 60 minutos: el de 20 pts juega sus 30 y el de 10 pts los otros 30.
    assert capped_points([(10.0, 30.0), (20.0, 30.0), (5.0, 30.0)], 60) == pytest.approx(30.0)
    # Si sobran minutos, todos juegan lo suyo.
    assert capped_points([(10.0, 30.0)], 60) == pytest.approx(10.0)
    # Un fichaje sólo suma lo que mejora sobre el jugador que desplaza.
    before = capped_points([(10.0, 30.0), (8.0, 30.0)], 60)
    after = capped_points([(10.0, 30.0), (8.0, 30.0), (15.0, 30.0)], 60)
    assert after - before == pytest.approx(7.0)


def test_preseason_adjustments():
    from app.sports.nba.engine.picks import adjust_projection, adjust_team_probability

    assert adjust_team_probability("ml", 0.80, preseason=True) == pytest.approx(0.5 + 0.48 * 0.30)
    assert adjust_team_probability("spread", 0.30, preseason=True) == pytest.approx(0.5 - 0.48 * 0.20)
    assert adjust_team_probability("total", 0.80, preseason=True) == 0.80  # totales: sin ajuste
    assert adjust_team_probability("ml", 0.80, preseason=False) == 0.80
    proj = adjust_projection(Projection(20.0, 49.0, normal=True), preseason=True)
    assert (proj.mean, proj.var, proj.normal) == (15.0, pytest.approx(36.75), True)
    assert adjust_projection(Projection(20.0, 49.0), preseason=False).mean == 20.0
