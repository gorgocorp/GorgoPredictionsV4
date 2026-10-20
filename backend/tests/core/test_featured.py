"""Reglas de los parlays destacados (app/core/featured.py): cuándo se publican y qué piernas entran."""

from datetime import datetime, timedelta, timezone

import pytest

from app.config import LOCAL_TZ
from app.core.featured import FeaturedLeg, due_windows, select_legs

START = datetime(2030, 1, 7, 18, 0, tzinfo=timezone.utc)  # lunes


def local(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2030, 1, day, hour, minute, tzinfo=LOCAL_TZ)


@pytest.mark.parametrize(
    "now, due",
    [
        (local(7, 7, 59), []),  # lunes antes de las 8
        (local(7, 8), [("week", "2030-01-07", "2030-01-13")]),
        (local(9, 22), [("week", "2030-01-07", "2030-01-13")]),  # miércoles
        (local(10, 8), [("week", "2030-01-07", "2030-01-13"), ("weekend", "2030-01-11", "2030-01-13")]),  # jueves
        (local(13, 23, 30), [("week", "2030-01-07", "2030-01-13"), ("weekend", "2030-01-11", "2030-01-13")]),
        (local(14, 7), []),  # el lunes siguiente antes de las 8: la semana anterior ya terminó
    ],
)
def test_each_featured_is_due_from_its_publication_until_its_window_ends(now, due):
    assert [(w.mode, s.isoformat(), e.isoformat()) for w, s, e in due_windows(now)] == due


def test_publication_hour_is_local_even_if_now_is_utc():
    assert due_windows(datetime(2030, 1, 7, 13, 59, tzinfo=timezone.utc)) == []  # 7:59 en el centro de México
    assert [w.mode for w, _, _ in due_windows(datetime(2030, 1, 7, 14, 0, tzinfo=timezone.utc))] == ["week"]


def leg(pick_id, match_id, p_model, p_market, price, market="total", odd="price", hours=0) -> FeaturedLeg:
    return FeaturedLeg(
        pick_id, match_id, market, f"pierna {pick_id}", p_model, p_market, price if odd == "price" else odd, price,
        START + timedelta(hours=hours),
    )


def test_promises_the_lower_of_model_and_market():
    assert leg(1, 1, 0.82, 0.74, 1.30).probability == 0.74
    assert leg(1, 1, 0.70, 0.74, 1.30).probability == 0.70


def test_legs_must_pay_at_least_the_minimum_and_both_model_and_market_must_agree():
    legs = [
        leg(1, 1, 0.90, 0.80, 1.20),  # paga menos de 1.30: casi segura, relleno
        leg(2, 2, 0.75, 0.55, 1.75),  # el mercado no la ve probable
        leg(3, 3, 0.58, 0.72, 1.35),  # el modelo no la ve probable
        leg(4, 4, 0.80, 0.80, 1.60),  # 1.60 × 80% = 1.28: precio a más de 20% del justo, dato malo
        leg(5, 5, 0.74, 0.72, 1.33),
        leg(6, 6, 0.73, 0.70, 1.38, odd=None),  # sólo la cotiza otra casa: también cuenta
    ]
    assert [x.pick_id for x in select_legs(legs)] == [5, 6]


def test_one_leg_per_match_and_at_most_two_of_the_same_market():
    legs = [
        leg(1, 1, 0.78, 0.75, 1.30),
        leg(2, 1, 0.80, 0.76, 1.30, market="btts"),  # mismo partido: queda la más probable de las dos
        leg(3, 2, 0.77, 0.75, 1.31),
        leg(4, 3, 0.77, 0.75, 1.32),
        leg(5, 4, 0.76, 0.74, 1.31),  # tercera de goles totales: no entra
        leg(6, 5, 0.70, 0.70, 1.40, market="dc"),
    ]
    assert [x.pick_id for x in select_legs(legs)] == [2, 4, 3, 6]  # a igual probabilidad, la que paga más


def test_sizes_are_nested_and_capped():
    legs = [leg(i, i, 0.80 - i / 100, 0.75 - i / 100, 1.30, market=f"m{i}") for i in range(1, 9)]
    chosen = select_legs(legs)
    assert [x.pick_id for x in chosen] == [1, 2, 3, 4, 5]
    assert select_legs(legs, 3) == chosen[:3]
