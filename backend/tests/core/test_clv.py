"""CLV contra el cierre de Pinnacle (core.tracking.clv_data): qué piernas cuentan y por qué, sin base de datos."""

import pandas as pd
import pytest

from app.core.tracking import clv_data

START = pd.Timestamp("2026-10-21T23:30:00Z")
CLOSE = START - pd.Timedelta(minutes=15)


def leg(**overrides) -> dict:
    """Pierna con valor publicada 10 h antes a 2.10 (Pinnacle 47%) cuyo cierre de Pinnacle fue 52%."""
    row = {
        "market": "ml", "first_odd": 2.10, "first_p_model": 0.55, "first_p_market": 0.47, "first_p_sharp": 0.47,
        "p_sharp": 0.52, "first_priced_at": START - pd.Timedelta(hours=10), "evaluated_at": CLOSE, "starts_at": START,
    }
    return {**row, **overrides}


def frame(*legs: dict) -> pd.DataFrame:
    return pd.DataFrame(list(legs))


def test_clv_is_the_published_odd_against_the_pinnacle_close():
    summary, by_market = clv_data(frame(
        leg(),  # 2.10 × 52% − 1 = +9.2%
        leg(market="total", first_odd=1.95, first_p_model=0.60, first_p_market=0.50, first_p_sharp=0.50, p_sharp=0.49),
        leg(first_odd=2.50, first_p_model=0.45, first_p_market=0.40, first_p_sharp=0.40, p_sharp=0.472),  # +18%
        leg(first_odd=1.80, first_p_model=0.45, first_p_market=0.53, first_p_sharp=0.53, p_sharp=0.48),  # sin valor
    ))
    clvs = [2.10 * 0.52 - 1, 1.95 * 0.49 - 1, 2.50 * 0.472 - 1]
    value = summary["value"]
    assert value["n"] == 3
    assert value["avg"] == pytest.approx(sum(clvs) / 3)
    assert value["median"] == pytest.approx(2.10 * 0.52 - 1)  # la mediana no la mueve el +18%
    assert value["beat_rate"] == pytest.approx(2 / 3)
    # Pinnacle se movió +5, −1 y +7.2 pts hacia esas piernas.
    assert (value["n_move"], value["avg_move"]) == (3, pytest.approx((0.05 - 0.01 + 0.072) / 3))
    assert summary["all"]["n"] == 4  # la referencia incluye la pierna sin valor
    assert summary["long_shots"] is None
    assert summary["excluded"] == {"no_close": 0, "no_reference": 0, "short_window": 0, "doubtful": 0}
    assert summary["hours_before"] == pytest.approx(10)
    assert by_market == {
        "ml": {"n": 2, "avg": pytest.approx((clvs[0] + clvs[2]) / 2)},
        "total": {"n": 1, "avg": pytest.approx(clvs[1])},
    }


def test_legs_that_do_not_count_and_why():
    summary, _ = clv_data(frame(
        leg(),  # cuenta
        leg(evaluated_at=START - pd.Timedelta(hours=2)),  # su última lectura fue 2 h antes del inicio
        leg(evaluated_at=START - pd.Timedelta(hours=2), p_sharp=None),  # dos motivos: cuenta el primero
        leg(p_sharp=None),  # Pinnacle no cotizaba su mercado al cierre
        leg(first_priced_at=CLOSE - pd.Timedelta(minutes=45)),  # publicada 45 min antes del cierre
        leg(first_odd=1.90, first_p_model=0.60, first_p_sharp=0.30),  # 1.90 × 30% = 0.57: precio dudoso
        leg(first_odd=1.80, first_p_model=0.45, p_sharp=None),  # sin valor: no entra en los motivos
    ))
    assert summary["value"]["n"] == 1
    assert summary["excluded"] == {"no_close": 2, "no_reference": 1, "short_window": 1, "doubtful": 1}
    assert summary["all"]["n"] == 1


def test_doubtful_price_uses_the_market_when_pinnacle_was_missing_at_publication():
    summary, _ = clv_data(frame(
        leg(first_p_sharp=None, first_p_market=0.35),  # 2.10 × 35% = 0.735: dudoso contra el precio del mercado
        leg(first_p_sharp=None, first_p_market=None),  # sin precio justo al publicarse: no se puede descartar
    ))
    assert summary["excluded"]["doubtful"] == 1
    assert summary["value"]["n"] == 1
    assert (summary["value"]["n_move"], summary["value"]["avg_move"]) == (0, None)  # sin Pinnacle al publicarse


def test_long_shots_are_reported_apart():
    # "América más de 4.5 goles" a 19: el modelo le da 5.6%, Pinnacle 5% al publicarse y 5.2% al cierre.
    shot = leg(market="team_total", first_odd=19.0, first_p_model=0.056, first_p_market=0.071, first_p_sharp=0.05,
               p_sharp=0.052)
    summary, by_market = clv_data(frame(leg(), shot))
    assert summary["long_shots"]["n"] == 1
    assert summary["long_shots"]["avg"] == pytest.approx(19.0 * 0.052 - 1)
    assert (summary["value"]["n"], summary["all"]["n"]) == (1, 1)  # ninguna de las dos lo incluye
    assert set(by_market) == {"ml"}


def test_without_any_pinnacle_price_nothing_counts():
    # Columnas de Pinnacle todas NULL (llegan como object): ninguna pierna cuenta, sin errores.
    summary, by_market = clv_data(frame(leg(p_sharp=None, first_p_sharp=None), leg(p_sharp=None, first_p_sharp=None)))
    assert (summary["value"], summary["all"], summary["long_shots"]) == (None, None, None)
    assert summary["excluded"]["no_reference"] == 2
    assert by_market == {}


def test_without_published_legs_there_is_no_clv():
    unpublished = leg(first_odd=None, first_p_model=None, first_p_market=None, first_p_sharp=None, first_priced_at=None)
    assert clv_data(frame(unpublished)) == (None, {})
