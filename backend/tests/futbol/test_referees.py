from datetime import date, timedelta

import pandas as pd
import pytest

from app.sports.futbol.engine.cards_model import fit_cards_model
from app.sports.futbol.engine.history import History
from app.sports.futbol.engine.referees import Referees, covers, name_tokens

LIGUE_1, LA_LIGA, LIGA_MX, CHAMPIONSHIP, PREMIER, CHAMPIONS = 61, 140, 262, 40, 39, 2


@pytest.mark.parametrize(
    "name, tokens",
    [
        ("Jeremy Stinat, France", ("jeremy", "stinat")),
        ("J. Stinat", ("j", "stinat")),
        ("Alejandro Hernández", ("alejandro", "hernandez")),
        ("Hilfer, Leandro Rey, Argentina", ("leandro", "rey", "hilfer")),
        ("A. M. Matonte Cabrera", ("a", "m", "matonte", "cabrera")),
        ("Paweł Raczkowski, Poland", ("pawel", "raczkowski")),
        ("Lothar D'hondt, Belgium", ("lothar", "dhondt")),
        ("Bryan Ferreyra,", ("bryan", "ferreyra")),
        (None, ()),
        ("", ()),
    ],
)
def test_name_tokens(name, tokens):
    assert name_tokens(name) == tokens


def test_covers():
    full = name_tokens("Adonai Escobedo Gonzalez, Mexico")
    for short in ("A. Escobedo", "A. Escobedo Gonzalez", "Adonai Escobedo", "Adonai Escobedo Gonzalez"):
        assert covers(full, name_tokens(short)), short
    assert covers(name_tokens("Andre Filipe Domingues Narciso"), name_tokens("A. Narciso"))
    assert covers(name_tokens("Sander van der Eijk"), name_tokens("S. van der Eijk"))
    assert not covers(full, name_tokens("E. Escobedo"))  # otra inicial
    assert not covers(full, name_tokens("Alberto Escobedo"))  # otro nombre
    assert not covers(full, name_tokens("A. Escobedo Garcia"))  # otro apellido
    assert not covers(name_tokens("A. Escobedo"), full)  # al revés: la abreviada no cubre a la completa
    assert not covers(name_tokens("Sander van der Eijk"), name_tokens("S. van"))  # sólo una partícula


def _build(rows):
    """rows: (nombre, liga, día del año 2025)."""
    names, leagues, days = zip(*rows)
    return Referees.build(names, leagues, [date(2025, 1, 1) + timedelta(days=d) for d in days])


def test_abbreviated_and_full_names_are_one_referee():
    refs = _build([("J. Stinat", LIGUE_1, 10), ("J. Stinat", LIGUE_1, 17), ("Jeremy Stinat", LIGUE_1, 200),
                   ("Jeremy Stinat, France", LIGUE_1, 210), ("Jérémy Stinat, France", CHAMPIONS, 215)])
    keys = {refs.key(n, lg) for n, lg in [("J. Stinat", LIGUE_1), ("Jeremy Stinat, France", LIGUE_1),
                                          ("Jeremy Stinat", CHAMPIONS), ("Jérémy Stinat, France", CHAMPIONS)]}
    assert keys == {"jeremy stinat"}


def test_abbreviation_is_resolved_within_its_league():
    # 'M. Ortiz' es una persona en La Liga y otra en la Liga MX.
    refs = _build([("Miguel Angel Ortiz Arias, Spain", LA_LIGA, 200), ("Marco Antonio Ortiz Nava, Mexico", LIGA_MX, 201),
                   ("M. Ortiz", LA_LIGA, 10), ("M. Ortiz", LIGA_MX, 10)])
    assert refs.key("M. Ortiz", LA_LIGA) == "miguel angel ortiz arias"
    assert refs.key("M. Ortiz", LIGA_MX) == "marco antonio ortiz nava"


def test_ambiguous_abbreviation_stays_apart():
    refs = _build([("Stephen Martin", CHAMPIONSHIP, 200), ("Steve Martin", CHAMPIONSHIP, 230), ("S. Martin", CHAMPIONSHIP, 10)])
    assert refs.key("S. Martin", CHAMPIONSHIP) == f"s martin @{CHAMPIONSHIP}"
    assert refs.key("Stephen Martin", CHAMPIONSHIP) != refs.key("Steve Martin", CHAMPIONSHIP)


def test_matches_a_day_apart_are_different_referees():
    refs = _build([("Josh Smith, England", PREMIER, 200), ("J. Smith", PREMIER, 201)])
    assert refs.key("J. Smith", PREMIER) == f"j smith @{PREMIER}"
    refs = _build([("Josh Smith, England", PREMIER, 200), ("J. Smith", PREMIER, 203)])
    assert refs.key("J. Smith", PREMIER) == "josh smith"


def test_referee_known_only_from_cups():
    refs = _build([("Anthony Taylor, England", CHAMPIONS, 200), ("A. Taylor", PREMIER, 10)])
    assert refs.key("A. Taylor", PREMIER) == "anthony taylor"


def test_new_names_resolve_to_known_referees():
    refs = _build([("J. Stinat", LIGUE_1, 10), ("A. Escobedo", LIGA_MX, 12)])
    assert refs.key("Jeremy Stinat, France", LIGUE_1) == f"j stinat @{LIGUE_1}"
    assert refs.key("Adonai Escobedo Gonzalez, Mexico", LIGA_MX) == f"a escobedo @{LIGA_MX}"
    assert refs.key("Adonai Escobedo Gonzalez, Mexico", LA_LIGA) is None  # la abreviada es de otra liga
    assert refs.key("Jeremy Stinat, France", CHAMPIONS) == f"j stinat @{LIGUE_1}"  # en copas, en cualquier liga
    assert refs.key("Nadie Conocido", LIGUE_1) is None
    assert refs.key(None, LIGUE_1) is None


def test_new_name_prefers_the_known_name_that_covers_it():
    # 'J. Pinheiro' quedó ambigua (dos árbitros la cubren); 'Joao Pinheiro' es 'Joao Pedro Pinheiro'.
    portugal = 94
    refs = _build([("Joao Pedro Pinheiro, Portugal", portugal, 200), ("Jose Antonio de Almeida Pinheiro", portugal, 230),
                   ("J. Pinheiro", portugal, 10)])
    assert refs.key("J. Pinheiro", portugal) == f"j pinheiro @{portugal}"
    assert refs.key("Joao Pinheiro", portugal) == "joao pedro pinheiro"
    # Sin apodos inventados: 'Andrew' no es 'Andy'.
    assert _build([("Andy Madley, England", CHAMPIONSHIP, 200)]).key("Andrew Madley", CHAMPIONSHIP) is None


def _history(rows: list[dict]) -> History:
    f = pd.DataFrame(rows)
    f["match_date"] = pd.to_datetime(f["match_date"])
    return History(fixtures=f, player_stats=pd.DataFrame(), team_names={}, player_names={}, league_names={})


def test_cards_model_pools_the_referee_across_name_formats():
    # Stinat saca muchas tarjetas con su nombre abreviado; el modelo debe reconocerlo con el nombre completo.
    start, rows = date(2025, 1, 4), []
    for i in range(120):
        home, away = (1 + i % 4, 1 + (i + 1 + i // 4) % 4)
        if home == away:
            away = 1 + (home % 4)
        stinat = i % 4 == 0
        rows.append({
            "id": i, "league_id": LIGUE_1, "season": 2024, "round": "R", "match_date": start + timedelta(days=3 * i),
            "starts_at": None, "status": "FT", "is_finished": True, "home_team_id": home, "away_team_id": away,
            "ft_home": 1, "ft_away": 1, "referee": "J. Stinat" if stinat else f"Otro Arbitro{i % 7}, France",
            "home_xg": None, "away_xg": None, "home_cards": 5 if stinat else 2, "away_cards": 5 if stinat else 2,
            "home_shots_on": None, "away_shots_on": None,
        })
    model = fit_cards_model(_history(rows), start + timedelta(days=3 * 120))
    with_stinat = model.predict(1, 2, LIGUE_1, "Jeremy Stinat, France", 2024).total
    unknown = model.predict(1, 2, LIGUE_1, "Nadie Conocido, France", 2024).total
    assert model.referees.key("Jeremy Stinat, France", LIGUE_1) == f"j stinat @{LIGUE_1}"
    assert with_stinat > unknown * 1.3
