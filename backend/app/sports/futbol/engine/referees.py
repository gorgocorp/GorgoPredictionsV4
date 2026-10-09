"""Identidad de los árbitros: API-Football publica a la misma persona con varios nombres.

'J. Stinat' (hasta 2025), 'Jeremy Stinat' y 'Jeremy Stinat, France' son el mismo árbitro; también cambian los
acentos ('Hernández'), el orden ('Hilfer, Leandro Rey, Argentina') y cuántos nombres y apellidos se escriben
('A. Escobedo', 'Adonai Escobedo Gonzalez'). La API no da un ID de árbitro, así que las variantes se agrupan con
reglas conservadoras (ante la duda, quedan separadas, como árbitros distintos):

- Un nombre cubre a otro si empieza con la misma inicial y contiene sus demás palabras en el mismo orden:
  'Adonai Escobedo Gonzalez' cubre a 'A. Escobedo' y a 'Adonai Escobedo'. Un nombre se junta con el árbitro
  más completo que lo cubre.
- Una forma abreviada sólo se busca dentro de su liga: 'M. Ortiz' es Miguel Ángel Ortiz Arias en La Liga y
  Marco Antonio Ortiz Nava en la Liga MX. Las de copas internacionales, en cualquier liga; y a un árbitro que
  sólo conocemos de copas ('Anthony Taylor, England' en Champions) se le busca en cualquier liga.
- Si la cubren dos árbitros posibles ('S. Martin': Stephen Martin y Steve Martin), no se junta con ninguno.
- Dos variantes con partidos a un día o menos de distancia son personas distintas: un árbitro no dirige dos
  partidos tan seguidos.

Se arma con los partidos que el modelo usa (anteriores a su fecha de corte): nada de información futura.
"""

import bisect
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

from app.sports.futbol.config import CUPS

# Partidos a esta distancia o menos (en días) no pueden ser del mismo árbitro.
CONFLICT_DAYS = 1
# Palabras que no identifican un apellido por sí solas ('S. van der Eijk').
PARTICLES = frozenset({"de", "da", "das", "do", "dos", "del", "la", "le", "van", "der", "den", "von", "di", "el", "ben", "y", "e"})
# Letras que Unicode no descompone en letra + acento ('Paweł' y 'Pawel').
_PLAIN = str.maketrans({"ł": "l", "ø": "o", "đ": "d", "ı": "i"})
_CUP_SCOPE = 0  # las copas son un solo ámbito (los árbitros de UEFA dirigen Champions y Europa League)

Tokens = tuple[str, ...]


@lru_cache(maxsize=4096)
def name_tokens(name: str | None) -> Tokens:
    """'Jeremy Stinat, France' -> ('jeremy', 'stinat'); 'J. Stinat' -> ('j', 'stinat');
    'Hilfer, Leandro Rey, Argentina' -> ('leandro', 'rey', 'hilfer')."""
    if not name or not isinstance(name, str):
        return ()
    parts = [p.strip() for p in name.split(",")]
    # 'Apellidos, Nombres, País' o 'Nombre, País' (el país no se usa: la forma abreviada no lo trae).
    text = f"{parts[1]} {parts[0]}" if len(parts) >= 3 else parts[0]
    text = unicodedata.normalize("NFKD", text.lower().translate(_PLAIN))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return tuple(re.findall(r"[^\W\d_]+", re.sub(r"['’-]", "", text)))


def _initial(token: str) -> bool:
    return len(token) == 1


def covers(full: Tokens, short: Tokens) -> bool:
    """¿`short` puede ser `full` escrito con iniciales o con menos palabras?"""
    if len(full) < 2 or len(short) < 2:
        return False
    if (full[0][0] != short[0]) if _initial(short[0]) else (full[0] != short[0]):
        return False
    j, surname = 1, False
    for token in short[1:]:
        while j < len(full) and not (full[j][0] == token if _initial(token) else full[j] == token):
            j += 1
        if j == len(full):
            return False
        surname = surname or (not _initial(token) and token not in PARTICLES)
        j += 1
    return surname


def _scope(tokens: Tokens, league: int) -> int | None:
    """Ámbito de una variante: un nombre completo vale en cualquier liga; uno abreviado, sólo en la suya."""
    if not _initial(tokens[0]):
        return None
    return _CUP_SCOPE if league in CUPS else league


def _specificity(tokens: Tokens) -> tuple[int, int]:
    return sum(not _initial(t) for t in tokens), len(tokens)


@dataclass
class _Referee:
    key: str
    name: Tokens
    leagues: set[int]
    days: list[int]  # ordinales de las fechas de sus partidos, ordenados

    def conflicts(self, days: list[int]) -> bool:
        for d in days:
            i = bisect.bisect_left(self.days, d - CONFLICT_DAYS)
            if i < len(self.days) and self.days[i] <= d + CONFLICT_DAYS:
                return True
        return False


@dataclass
class Referees:
    """Árbitros conocidos a una fecha de corte y a cuál pertenece cada nombre."""

    _known: dict[tuple[Tokens, int | None], str] = field(default_factory=dict)
    _referees: list[_Referee] = field(default_factory=list)
    _by_word: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))

    @classmethod
    def build(cls, names, leagues, days) -> "Referees":
        """Agrupa los nombres de una lista de partidos (nombre, liga y fecha de cada uno)."""
        variants: dict[tuple[Tokens, int | None], tuple[set[int], set[int]]] = {}
        for name, league, day in zip(names, leagues, days):
            tokens = name_tokens(name)
            if not tokens:
                continue
            league, day = int(league), _ordinal(day)
            seen_leagues, seen_days = variants.setdefault((tokens, _scope(tokens, league)), (set(), set()))
            seen_leagues.add(league)
            seen_days.add(day)

        out = cls()
        # Primero los nombres más completos, que son los que pueden cubrir a los demás.
        order = sorted(variants, key=lambda v: (*_specificity(v[0]), len(variants[v][1]), v[0], v[1] or 0), reverse=True)
        for tokens, scope in order:
            leagues_seen, days_seen = variants[(tokens, scope)]
            days_sorted = sorted(days_seen)
            found = out._candidates(tokens, leagues_seen, days_sorted)
            if len(found) == 1:
                ref = out._referees[found[0]]
                ref.leagues |= leagues_seen
                ref.days = sorted(set(ref.days) | days_seen)
            else:
                ref = out._add(tokens, scope, leagues_seen, days_sorted)
            out._known[(tokens, scope)] = ref.key
        return out

    def key(self, name: str | None, league: int) -> str | None:
        """Clave del árbitro de un partido; None si el nombre no es de ningún árbitro conocido (o si es ambiguo)."""
        tokens = name_tokens(name)
        if not tokens:
            return None
        if (known := self._known.get((tokens, _scope(tokens, int(league))))) is not None:
            return known
        # Un nombre nuevo se busca primero entre los conocidos que lo cubren ('Joao Pinheiro' es 'Joao Pedro
        # Pinheiro', no alguna de las 'J. Pinheiro' ambiguas); si no hay, entre los que él completa:
        # 'Jeremy Stinat, France' la primera vez que la API lo escribe completo, cuando sólo se conocía 'J. Stinat'.
        leagues = {int(league)}
        found = self._candidates(tokens, leagues, []) or self._candidates(tokens, leagues, [], completes=True)
        return self._referees[found[0]].key if len(found) == 1 else None

    def _candidates(self, tokens: Tokens, leagues: set[int], days: list[int], completes: bool = False) -> list[int]:
        """Árbitros ya conocidos que pueden ser este nombre (con `completes`, los que este nombre completa)."""
        domestic = leagues - CUPS
        ids = sorted({i for t in tokens[1:] if not _initial(t) for i in self._by_word.get(t, ())})
        return [
            i for i in ids
            if (covers(tokens, self._referees[i].name) if completes else covers(self._referees[i].name, tokens))
            and (not domestic or self._referees[i].leagues & domestic or self._referees[i].leagues <= CUPS)
            and not self._referees[i].conflicts(days)
        ]

    def _add(self, tokens: Tokens, scope: int | None, leagues: set[int], days: list[int]) -> _Referee:
        key = " ".join(tokens) if scope is None else f"{' '.join(tokens)} @{scope}"
        ref = _Referee(key, tokens, set(leagues), days)
        self._referees.append(ref)
        for t in set(tokens[1:]):
            if not _initial(t):
                self._by_word[t].append(len(self._referees) - 1)
        return ref


def _ordinal(day) -> int:
    return day.toordinal() if isinstance(day, date) else int(day)
