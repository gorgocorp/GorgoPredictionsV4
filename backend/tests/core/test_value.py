"""Reglas del parlay con valor (app/core/value.py): cuándo se publica, qué piernas entran y cómo se mide su CLV."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.config import LOCAL_TZ
from app.core.value import ValueLeg, due_days, legs_clv, select_legs

START = datetime(2030, 1, 8, 18, 0, tzinfo=timezone.utc)


def local(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2030, 1, day, hour, minute, tzinfo=LOCAL_TZ)


@pytest.mark.parametrize(
    "now, days",
    [
        (local(7, 19, 59), ["2030-01-07"]),  # antes de las 20: sólo hoy (por si no salió la víspera)
        (local(7, 20), ["2030-01-07", "2030-01-08"]),  # desde las 20, también mañana
        (local(7, 23, 59), ["2030-01-07", "2030-01-08"]),
        (local(8, 0, 1), ["2030-01-08"]),
    ],
)
def test_the_parlay_is_due_from_the_evening_before(now, days):
    assert [d.isoformat() for d in due_days(now)] == days


def test_publication_hour_is_local_even_if_now_is_utc():
    assert due_days(datetime(2030, 1, 8, 1, 59, tzinfo=timezone.utc)) == [date(2030, 1, 7)]  # 19:59 en el centro
    assert due_days(datetime(2030, 1, 8, 2, 0, tzinfo=timezone.utc)) == [date(2030, 1, 7), date(2030, 1, 8)]


def test_no_parlay_before_the_trial_starts():
    assert due_days(datetime(2026, 10, 22, 21, 0, tzinfo=LOCAL_TZ)) == []
    assert due_days(datetime(2026, 10, 23, 21, 0, tzinfo=LOCAL_TZ)) == [date(2026, 10, 24)]


def leg(pick_id, match_id, p_model, p_market, odd, hours=0) -> ValueLeg:
    return ValueLeg(pick_id, match_id, "total", f"pierna {pick_id}", p_model, p_market, odd, START + timedelta(hours=hours))


def test_the_book_must_pay_more_than_the_fair_odd_of_both_model_and_market():
    legs = [
        leg(1, 1, 0.74, 0.55, 1.75),  # 1.75 × 55% = 0.96: sólo el modelo ve valor
        leg(2, 2, 0.50, 0.58, 1.80),  # 1.80 × 50% = 0.90: sólo el mercado ve valor
        leg(3, 3, 0.65, 0.62, 1.66),  # 1.66 × 62% = 1.03: los dos
        leg(4, 4, 0.40, 0.38, 3.00),  # momio de 3 o más: no entra
        leg(5, 5, 0.70, 0.62, 2.10),  # 2.10 × 62% = 1.30: a más de 20% del justo, dato malo
        leg(6, 6, 0.62, 0.60, 1.70),  # 1.70 × 60% = 1.02: los dos
    ]
    assert [x.pick_id for x in select_legs(legs)] == [3, 6]


def test_promises_the_lower_probability_one_leg_per_match():
    legs = [
        leg(1, 1, 0.66, 0.63, 1.62),
        leg(2, 1, 0.70, 0.66, 1.55),  # mismo partido: queda la que más se promete
        leg(3, 2, 0.66, 0.64, 1.60),
        leg(4, 3, 0.66, 0.64, 1.62),  # a igual promesa, la que paga más
    ]
    chosen = select_legs(legs)
    assert [x.pick_id for x in chosen] == [2, 4]
    assert [x.probability for x in chosen] == [0.66, 0.64]
    assert chosen[1].edge == pytest.approx(1.62 * 0.64 - 1)


def clv_leg(odd, p_sharp, published_h, evaluated_h, start_h) -> dict:
    return {
        "odd": odd,
        "p_sharp": p_sharp,
        "published_at": START + timedelta(hours=published_h),
        "evaluated_at": START + timedelta(hours=evaluated_h),
        "starts_at": START + timedelta(hours=start_h),
    }


def test_clv_uses_the_published_odd_against_pinnacle_at_the_close():
    c = legs_clv([
        clv_leg(1.70, 0.62, 0, 9.75, 10),  # +5.4%
        clv_leg(1.60, 0.60, 0, 9.75, 10),  # −4%
        clv_leg(2.00, 0.55, 0, 9.75, 10),  # +10%
        clv_leg(1.70, 0.62, 0, 7, 10),  # última evaluación 3 h antes: sin cierre
        clv_leg(1.70, None, 0, 9.75, 10),  # Pinnacle no cotizaba al cierre
        clv_leg(1.70, 0.62, 8.5, 9.75, 10),  # publicada a 1 h 15 min del cierre: sin movimiento que medir
    ])
    assert c["n"] == 3
    assert c["avg"] == pytest.approx((0.054 - 0.04 + 0.10) / 3)
    assert c["median"] == pytest.approx(0.054)
    assert c["beat_rate"] == pytest.approx(2 / 3)
    assert c["excluded"] == {"no_close": 1, "no_reference": 1, "short_window": 1}


def test_clv_without_measurable_legs():
    assert legs_clv([]) == {"n": 0, "avg": None, "median": None, "beat_rate": None,
                            "excluded": {"no_close": 0, "no_reference": 0, "short_window": 0}}
