"""Calibración de los resultados públicos (app/core/results.py): lo prometido por pierna contra lo que pasó."""

import pytest

from app.core.results import calibration, kind, promised


def leg(pick_id, p_model, p_market, result):
    return {"pick_id": pick_id, "p_model": p_model, "p_market": p_market, "result": result}


def test_each_leg_promises_the_lower_of_model_and_market():
    assert promised(leg(1, 0.88, 0.74, "won")) == 0.74
    assert promised(leg(1, 0.70, 0.79, "won")) == 0.70
    assert promised(leg(1, 0.70, None, "won")) == 0.70


def test_calibration_counts_each_pick_once_and_skips_unsettled_legs():
    legs = [
        leg(1, 0.80, 0.75, "won"),
        leg(1, 0.80, 0.75, "won"),  # el mismo pick en el parlay de 3 piernas
        leg(2, 0.90, 0.72, "lost"),
        leg(3, 0.95, 0.93, "won"),
        leg(4, 0.99, 1.0 - 1e-9, "won"),
        leg(5, 0.66, 0.70, "void"),
        leg(6, 0.66, 0.70, None),
    ]
    total, bins = calibration(legs)
    assert total["settled"] == 4 and total["won"] == 3
    assert total["promised"] == pytest.approx((0.75 + 0.72 + 0.93 + 0.99) / 4)
    assert [(b["lo"], b["hi"], b["n"]) for b in bins] == [(0.7, 0.8, 2), (0.9, 1.0, 2)]  # rangos vacíos no salen
    assert bins[0]["promised"] == pytest.approx(0.735) and bins[0]["actual"] == 0.5


def test_no_settled_legs():
    assert calibration([]) == ({"settled": 0, "won": 0, "promised": None}, [])


def test_kind_of_parlay():
    assert [kind(m) for m in ("prob", "week", "weekend")] == ["daily", "week", "weekend"]
