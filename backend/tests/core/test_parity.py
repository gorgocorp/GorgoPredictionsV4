"""Comparación de `parity` (app.parity.compare) con tarjetas ya serializadas, sin correr los motores."""

from datetime import date

from app.parity import compare

DAY = date(2026, 10, 21)


def card(*legs: dict) -> dict:
    return {"match": 1001, "starts_at": "2026-10-21 23:30:00+00:00", "projection": {"home": 112.5}, "legs": list(legs)}


def leg(**overrides) -> dict:
    row = {
        "key": [1001, "ml", "home", None, None, None, None], "description": "Gana local", "p_model": 0.6, "odd": 1.9,
        "bookmaker": "Bet365", "p_market": 0.52, "book_odds": {"Bet365": 1.9, "1xBet": 1.92}, "hits": [],
        "player_status": None,
    }
    return {**row, **overrides}


def test_bookmakers_that_only_v4_keeps_are_not_differences():
    new = leg(book_odds={"Bet365": 1.9, "1xBet": 1.92, "Pinnacle": 1.95})
    assert compare("nba", DAY, [card(leg())], [card(new)]).ok


def test_prices_of_the_legacy_bookmakers_must_match():
    for book_odds in (
        {"Bet365": 1.85, "1xBet": 1.92, "Pinnacle": 1.95},  # otro precio de Bet365
        {"Bet365": 1.9, "Pinnacle": 1.95},  # falta 1xBet
    ):
        result = compare("nba", DAY, [card(leg())], [card(leg(book_odds=book_odds))])
        assert len(result.problems) == 1 and "book_odds" in result.problems[0]
