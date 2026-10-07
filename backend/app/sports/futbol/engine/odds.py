"""Momios: conversiones, interpretación de selecciones de API-Football y probabilidad del mercado."""

import html
import re
import statistics
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from app.sports.futbol.engine.legs import LegSpec

SHARP_BOOKMAKER = "Pinnacle"

# Mercados de partido completo (90 minutos) por bet_id, verificados con momios reales.
TEAM_BETS = {
    1: "1x2",  # Match Winner: Home / Draw / Away
    12: "dc",  # Double Chance: Home/Draw, Home/Away, Draw/Away
    5: "total",  # Goals Over/Under: "Over 2.5"
    16: "team_total_home",  # Total - Home
    17: "team_total_away",  # Total - Away
    8: "btts",  # Both Teams Score: Yes / No
    10: "score",  # Exact Score: "2:1"
    80: "cards",  # Cards Over/Under
    82: "team_cards_home",  # Home Team Total Cards
    83: "team_cards_away",  # Away Team Total Cards
}

# Props de jugador: bet_id -> (estadística, línea cuando la selección es sólo el nombre).
# Los mercados "Home/Away ..." son el mismo mercado partido por equipo.
PLAYER_BETS = {
    92: ("goals", 0.5),  # Anytime Goal Scorer
    231: ("goals", 0.5),  # Home Anytime Goal Scorer
    218: ("goals", 0.5),  # Away Anytime Goal Scorer
    95: ("goals", 1.5),  # To Score Two or More Goals
    237: ("goals", 1.5),  # Home To Score Two or More Goals
    236: ("goals", 1.5),  # Away To Score Two or More Goals
    257: ("ga", 0.5),  # Player to Score or Assist
    258: ("ga", 0.5),
    259: ("ga", 0.5),
    102: ("cards", 0.5),  # Player to be booked
    251: ("cards", 0.5),
    242: ("shots_on", None),  # Player Shots On Target: sólo con línea explícita
    264: ("shots_on", None),  # Player Shots On Target Total
    265: ("shots", None),  # Player Shots Total
}
# Se ignoran a propósito los mercados de remates por equipo (269, 270, 275, 276): en las
# muestras de Bet365 traían precios de otro mercado (gol de cabeza).

# Mercados que se guardan: el resto de los ~70 que publica cada casa no se usa.
USED_BET_IDS = frozenset(TEAM_BETS) | frozenset(PLAYER_BETS)

DC_SIDES = {"Home/Draw": "1x", "Draw/Away": "x2", "Home/Away": "12"}
_OU = re.compile(r"^(Over|Under) (\d+(?:\.\d+)?)$")
_SCORE = re.compile(r"^(\d+):(\d+)$")
_PLAYER_OU = re.compile(r"^(.+?) - (Over|Under) (\d+(?:\.\d+)?)$")
_PLAYER_PLUS = re.compile(r"^(.+?) - (\d+)\+?$")
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
_NOT_PLAYERS = {"no goalscorer", "no goal", "own goal", "other", "any other player"}
# Letras que NFKD no descompone en ASCII ("Ødegaard", "Szczęsny" sí; "Łukasz" no).
_LETTERS = str.maketrans({"ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "ß": "ss", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ı": "i", "œ": "oe"})


def american(decimal_odd: float) -> str:
    if decimal_odd >= 2.0:
        return f"+{round((decimal_odd - 1) * 100)}"
    return f"{round(-100 / (decimal_odd - 1))}"


def fair_odd(p: float) -> float:
    return 1.0 / p if p > 0 else float("inf")


def _is_half(line: float) -> bool:
    """Sólo líneas de medio punto: evitan la devolución (push) y las líneas asiáticas (.25/.75)."""
    return abs(line * 2 - round(line * 2)) < 1e-9 and round(line * 2) % 2 == 1


@dataclass(frozen=True)
class ParsedSelection:
    spec: LegSpec
    player_name: str | None = None  # para props: nombre tal como viene en la casa


def parse_selection(bet_id: int, bet_name: str | None, selection: str) -> ParsedSelection | None:
    market = TEAM_BETS.get(bet_id)
    if market == "1x2":
        side = {"Home": "home", "Draw": "draw", "Away": "away"}.get(selection)
        return ParsedSelection(LegSpec("1x2", side)) if side else None
    if market == "dc":
        side = DC_SIDES.get(selection)
        return ParsedSelection(LegSpec("dc", side)) if side else None
    if market == "btts":
        side = {"Yes": "yes", "No": "no"}.get(selection)
        return ParsedSelection(LegSpec("btts", side)) if side else None
    if market == "score":
        m = _SCORE.match(selection)
        return ParsedSelection(LegSpec("score", f"{int(m[1])}-{int(m[2])}")) if m else None
    if market in ("total", "cards") or (market or "").startswith(("team_total", "team_cards")):
        m = _OU.match(selection)
        if not m or not _is_half(float(m[2])):
            return None
        team = "home" if market.endswith("_home") else "away" if market.endswith("_away") else None
        base = market.removesuffix("_home").removesuffix("_away")
        return ParsedSelection(LegSpec(base, m[1].lower(), float(m[2]), team=team))

    player = PLAYER_BETS.get(bet_id)
    if player:
        stat, default_line = player
        m = _PLAYER_OU.match(selection)
        if m and _is_half(float(m[3])):
            return ParsedSelection(LegSpec("player", m[2].lower(), float(m[3]), stat=stat), player_name=m[1])
        m = _PLAYER_PLUS.match(selection)
        if m:
            # "Nombre - 2" = 2 o más, equivalente a Over 1.5.
            return ParsedSelection(LegSpec("player", "over", int(m[2]) - 0.5, stat=stat), player_name=m[1])
        if default_line is not None and selection.strip().lower() not in _NOT_PLAYERS and " - " not in selection:
            return ParsedSelection(LegSpec("player", "over", default_line, stat=stat), player_name=selection.strip())
    return None


def _tokens(name: str) -> list[str]:
    text = unicodedata.normalize("NFKD", html.unescape(name).translate(_LETTERS)).encode("ascii", "ignore").decode().lower()
    text = text.replace("'", "").replace("-", " ")
    text = re.sub(r"[^a-z. ]", "", text)
    return [t for t in text.replace(".", ". ").split() if t.rstrip(".") not in _SUFFIXES]


def _full_match(book_name: str, stats_name: str) -> bool:
    book = sorted(t.rstrip(".") for t in _tokens(book_name))
    return bool(book) and book == sorted(t.rstrip(".") for t in _tokens(stats_name))


def names_match(book_name: str, stats_name: str) -> bool:
    """Empata "Viktor Gyokeres" (casa) con "Viktor Gyökeres" o "V. Gyokeres" (estadísticas)."""
    book = [t.rstrip(".") for t in _tokens(book_name)]
    stats = _tokens(stats_name)
    if not book or not stats:
        return False
    if _full_match(book_name, stats_name):
        return True
    initials = [t.rstrip(".") for t in stats if t.endswith(".") and len(t.rstrip(".")) == 1]
    rest = [t for t in stats if not t.endswith(".")]
    if len(initials) == 1 and rest:
        return book[0].startswith(initials[0]) and book[1:] == rest
    return False


def match_player(book_name: str, candidates: dict[int, str]) -> int | None:
    """Busca el jugador entre `candidates` (id -> nombre). None si no hay o hay más de uno.

    El nombre completo tiene prioridad sobre la inicial. Si la casa da más nombres que las
    estadísticas ("Gabriel Magalhaes" vs "Gabriel"), no se adivina.
    """
    full = [pid for pid, name in candidates.items() if _full_match(book_name, name)]
    if full:
        return full[0] if len(full) == 1 else None
    found = [pid for pid, name in candidates.items() if names_match(book_name, name)]
    return found[0] if len(found) == 1 else None


@dataclass(frozen=True)
class Quote:
    spec: LegSpec
    bookmaker: str
    odd: float


def market_probabilities(quotes: Iterable[Quote]) -> dict[LegSpec, float]:
    """Probabilidad sin comisión (devig) de cada selección cuyo mercado está completo.

    - Dos resultados (más/menos, sí/no): normaliza el par.
    - 1X2: normaliza los tres; la doble oportunidad sale de sumar dos de ellos.
    Usa Pinnacle si cotiza el mercado completo; si no, la mediana de las casas que sí.
    """
    quotes = list(quotes)
    by_book: dict[tuple, dict[str, float]] = defaultdict(dict)
    specs: dict[tuple, dict[str, LegSpec]] = defaultdict(dict)
    for q in quotes:
        if q.spec.market in ("score", "dc"):
            continue
        by_book[(q.spec.group_key(), q.bookmaker)][q.spec.side] = q.odd
        specs[q.spec.group_key()][q.spec.side] = q.spec

    fair: dict[LegSpec, list[tuple[str, float]]] = defaultdict(list)
    for (group, bookmaker), sides in by_book.items():
        needed = 3 if group[0] == "1x2" else 2
        if len(sides) != needed:
            continue
        inv = {side: 1 / odd for side, odd in sides.items()}
        total = sum(inv.values())
        for side, value in inv.items():
            fair[specs[group][side]].append((bookmaker, value / total))
        if group[0] == "1x2":
            p = {side: value / total for side, value in inv.items()}
            for dc, (a, b) in {"1x": ("home", "draw"), "x2": ("draw", "away"), "12": ("home", "away")}.items():
                fair[LegSpec("dc", dc)].append((bookmaker, p[a] + p[b]))

    result = {}
    for spec, values in fair.items():
        sharp = [p for book, p in values if book == SHARP_BOOKMAKER]
        result[spec] = sharp[0] if sharp else statistics.median(p for _, p in values)
    return result
