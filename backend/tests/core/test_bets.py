import pytest

from app.core.bets import settle_bet, summarize_bets


def legs(*results, odds=None):
    odds = odds or [1.83, 1.55, 1.87, 2.45]
    return [{"result": r, "odd": o} for r, o in zip(results, odds)]


def test_lost_if_any_leg_lost_even_with_pending():
    assert settle_bet(50, 13.01, legs("won", "lost", None, None)) == {"result": "lost", "settled_odd": 13.01, "payout": 0.0}


def test_pending_until_all_legs_settled():
    assert settle_bet(50, 13.01, legs("won", "won", None, "won")) is None


def test_won_uses_ticket_odd():
    assert settle_bet(50, 13.0, legs("won", "won", "won", "won")) == {"result": "won", "settled_odd": 13.0, "payout": 650.0}


def test_void_leg_is_removed_like_the_bookmaker_does():
    out = settle_bet(50, 13.01, legs("won", "void", "won", "won"))
    assert out["result"] == "won"
    assert out["settled_odd"] == pytest.approx(1.83 * 1.87 * 2.45, abs=1e-3)
    assert out["payout"] == pytest.approx(50 * 1.83 * 1.87 * 2.45, abs=0.01)


def test_all_void_returns_stake():
    assert settle_bet(50, 13.01, legs("void", "void", "void", "void")) == {"result": "void", "settled_odd": 1.0, "payout": 50.0}


def test_summary_profit_roi_and_expectations():
    bets = [
        {"stake": 50, "odd": 13.0, "model_probability": 0.10, "result": "won", "payout": 650.0},
        {"stake": 100, "odd": 2.0, "model_probability": 0.55, "result": "lost", "payout": 0.0},
        {"stake": 20, "odd": 3.0, "model_probability": 0.40, "result": None, "payout": None},
        {"stake": 30, "odd": 4.0, "model_probability": 0.30, "result": "void", "payout": 30.0},
    ]
    s = summarize_bets(bets)
    assert (s["bets"], s["pending"], s["won"], s["lost"], s["void"]) == (4, 1, 1, 1, 1)
    assert s["staked"] == 180 and s["returned"] == 680 and s["profit"] == 500
    assert s["roi"] == pytest.approx(500 / 180)
    assert s["expected_wins"] == pytest.approx(0.65)
    assert s["book_expected_wins"] == pytest.approx(1 / 13 + 1 / 2)
    assert s["pending_stake"] == 20
