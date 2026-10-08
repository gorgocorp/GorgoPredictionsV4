"""Momios: conversiones, interpretación de selecciones de API-Basketball y probabilidad del mercado."""

import html
import re
import statistics
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from app.config import SHARP_BOOKMAKER
from app.sports.nba.engine.legs import LegSpec

# Mercados de partido completo por bet_id (estables en la API).
TEAM_BETS = {2: "ml", 3: "spread", 4: "total", 28: "team_total_home", 29: "team_total_away"}

# Props de jugador por nombre de mercado.
PLAYER_BETS = {
    "Player Points": "points",
    "Player Points Milestones": "points",
    "Player Assists": "assists",
    "Home Player Assists": "assists",
    "Away Player Assists": "assists",
    "Player Rebounds Milestones": "rebounds",
    "Home Player Rebounds": "rebounds",
    "Away Player Rebounds": "rebounds",
    "Player Threes Made": "threes",
    "Player Points and Rebounds": "pr",
    "Player Points and Assists": "pa",
}

_OU = re.compile(r"^(Over|Under) (\d+(?:\.\d+)?)$")
_HANDICAP = re.compile(r"^(Home|Away) ([+-]?\d+(?:\.\d+)?)$")
_PLAYER_OU = re.compile(r"^(.+?) - (Over|Under) (\d+(?:\.\d+)?)$")
_PLAYER_MILESTONE = re.compile(r"^(.+?) - (\d+)\+?$")
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def american(decimal_odd: float) -> str:
    if decimal_odd >= 2.0:
        return f"+{round((decimal_odd - 1) * 100)}"
    return f"{round(-100 / (decimal_odd - 1))}"


def fair_odd(p: float) -> float:
    return 1.0 / p if p > 0 else float("inf")


def _is_half(line: float) -> bool:
    """Sólo líneas de medio punto: evitan el empate (push) y su devolución."""
    return abs(line * 2 - round(line * 2)) < 1e-9 and round(line * 2) % 2 == 1


@dataclass(frozen=True)
class ParsedSelection:
    spec: LegSpec | None
    player_name: str | None = None  # para props: nombre tal como viene en la casa


def parse_selection(bet_id: int, bet_name: str | None, selection: str) -> ParsedSelection | None:
    market = TEAM_BETS.get(bet_id)
    if market == "ml":
        if selection in ("Home", "Away"):
            return ParsedSelection(LegSpec("ml", selection.lower()))
        return None
    if market == "spread":
        # Ojo: el número es SIEMPRE el handicap del local. "Home +5.5" = local +5.5;
        # "Away +5.5" = el otro lado de esa misma línea = visitante -5.5 (verificado con
        # precios reales: ambos forman un par ~50/50 y "Away -3.5" paga 1.25).
        m = _HANDICAP.match(selection)
        if m and _is_half(float(m[2])):
            home_line = float(m[2])
            side = m[1].lower()
            return ParsedSelection(LegSpec("spread", side, home_line if side == "home" else -home_line))
        return None
    if market == "total" or (market or "").startswith("team_total"):
        m = _OU.match(selection)
        if not m or not _is_half(float(m[2])):
            return None
        team = None if market == "total" else market.rsplit("_", 1)[1]
        return ParsedSelection(LegSpec("total" if team is None else "team_total", m[1].lower(), float(m[2]), team=team))

    stat = PLAYER_BETS.get(bet_name or "")
    if stat:
        m = _PLAYER_OU.match(selection)
        if m and _is_half(float(m[3])):
            return ParsedSelection(LegSpec("player", m[2].lower(), float(m[3]), stat=stat), player_name=m[1])
        m = _PLAYER_MILESTONE.match(selection)
        if m:
            # "Nombre - 20" = 20 o más, equivalente a Over 19.5.
            return ParsedSelection(LegSpec("player", "over", int(m[2]) - 0.5, stat=stat), player_name=m[1])
    return None


def _tokens(name: str) -> list[str]:
    text = unicodedata.normalize("NFKD", html.unescape(name)).encode("ascii", "ignore").decode().lower()
    text = text.replace("'", "").replace("-", " ")  # Day'Ron -> dayron; Gilgeous-Alexander -> 2 palabras
    text = re.sub(r"[^a-z. ]", "", text)
    return [t for t in text.replace(".", ". ").split() if t.rstrip(".") not in _SUFFIXES]


def _full_match(book_name: str, stats_name: str) -> bool:
    book = sorted(t.rstrip(".") for t in _tokens(book_name))
    return bool(book) and book == sorted(t.rstrip(".") for t in _tokens(stats_name))


def names_match(book_name: str, stats_name: str) -> bool:
    """Empata "Anthony Edwards" (casa) con "Edwards Anthony" o "A. Edwards" (estadísticas)."""
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


def match_full_name(book_name: str, candidates: dict[int, str]) -> int | None:
    """Sólo coincidencia de nombre completo y única (para búsquedas amplias, sin iniciales)."""
    full = [pid for pid, name in candidates.items() if _full_match(book_name, name)]
    return full[0] if len(full) == 1 else None


def match_player(book_name: str, candidates: dict[int, str]) -> int | None:
    """Busca el jugador entre `candidates` (id -> nombre). None si no hay o hay más de uno.

    El nombre completo tiene prioridad sobre la inicial: "Trae Young" empata con "Young Trae"
    aunque también exista un "T. Young".
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


def _fair_by_bookmaker(quotes: Iterable[Quote]) -> dict[LegSpec, dict[str, float]]:
    """Probabilidad sin comisión (devig) de cada selección según cada casa que cotiza sus dos lados."""
    quotes = list(quotes)
    by_book: dict[tuple, dict[str, float]] = defaultdict(dict)
    for q in quotes:
        by_book[(q.spec.group_key(), q.bookmaker)][q.spec.side] = q.odd

    fair: dict[LegSpec, dict[str, float]] = defaultdict(dict)
    specs: dict[tuple, dict[str, LegSpec]] = defaultdict(dict)
    for q in quotes:
        specs[q.spec.group_key()][q.spec.side] = q.spec
    for (group, bookmaker), sides in by_book.items():
        if len(sides) != 2:
            continue
        (side_a, odd_a), (side_b, odd_b) = sides.items()
        inv_a, inv_b = 1 / odd_a, 1 / odd_b
        fair[specs[group][side_a]][bookmaker] = inv_a / (inv_a + inv_b)
        fair[specs[group][side_b]][bookmaker] = inv_b / (inv_a + inv_b)
    return fair


def market_probabilities(quotes: Iterable[Quote]) -> dict[LegSpec, float]:
    """Probabilidad del mercado de cada selección con sus dos lados cotizados.

    Usa Pinnacle si cotiza ambos lados; si no, la mediana de las casas que sí.
    """
    return {
        spec: books[SHARP_BOOKMAKER] if SHARP_BOOKMAKER in books else statistics.median(books.values())
        for spec, books in _fair_by_bookmaker(quotes).items()
    }


def sharp_probabilities(quotes: Iterable[Quote]) -> dict[LegSpec, float]:
    """Probabilidad sin comisión de Pinnacle, sólo donde cotiza los dos lados: la referencia del CLV.

    A diferencia de `market_probabilities`, nunca recurre a otras casas: con una sola casa que pone un lado en el
    mínimo (1.01), el devig da probabilidades muy infladas a los momios altos.
    """
    return {
        spec: books[SHARP_BOOKMAKER]
        for spec, books in _fair_by_bookmaker(quotes).items()
        if SHARP_BOOKMAKER in books
    }
