"""Candidatos (piernas evaluadas) y armado de parlays de N piernas, para cualquier deporte.

Regla: una pierna por partido. Dos piernas del mismo partido están correlacionadas ("Boston gana" y
"Tatum 30+", "Gana el América" y "Más de 2.5 goles") y multiplicar sus probabilidades sería engañoso.
"""

import math
from dataclasses import dataclass, field
from typing import Any

PARLAY_SIZES = range(2, 9)


@dataclass
class Candidate:
    sport: str
    external_id: int  # partido en el proveedor de su deporte (nba.games.id / futbol.fixtures.id)
    matchup: str
    spec: Any  # LegSpec del deporte
    description: str
    p_model: float
    odd: float | None = None
    bookmaker: str | None = None
    p_market: float | None = None
    # Probabilidad sin comisión de Pinnacle (referencia del CLV); None si no cotiza el mercado completo.
    p_sharp: float | None = None
    hits: list[tuple[int, int]] = field(default_factory=list)  # [(aciertos, partidos)] p. ej. últimos 10 y 25 partidos
    # Estado del jugador en props: "questionable" (en duda) o, en fútbol, "starter" con alineación confirmada.
    player_status: str | None = None
    book_odds: dict[str, float] = field(default_factory=dict)  # momio de cada casa de PRICE_BOOKMAKERS que lo cotiza

    @property
    def match_key(self) -> tuple[str, int]:
        """Identifica el partido entre deportes (los IDs de los proveedores chocan entre sí)."""
        return (self.sport, self.external_id)

    @property
    def fair_odd(self) -> float:
        return 1.0 / self.p_model

    @property
    def listed_odd(self) -> float | None:
        """Momio de la casa del sistema o, si no la cotiza, el mejor de las otras casas de PRICE_BOOKMAKERS."""
        return self.odd or max(self.book_odds.values(), default=None)

    @property
    def ev(self) -> float | None:
        """Valor esperado por unidad apostada: p·momio − 1."""
        return self.p_model * self.odd - 1.0 if self.odd else None

    @property
    def edge(self) -> float | None:
        return self.p_model - self.p_market if self.p_market is not None else None


@dataclass
class Parlay:
    legs: list[Candidate]

    @property
    def probability(self) -> float:
        return math.prod(c.p_model for c in self.legs)

    @property
    def odd(self) -> float | None:
        if any(c.odd is None for c in self.legs):
            return None
        return math.prod(c.odd for c in self.legs)

    @property
    def fair_odd(self) -> float:
        return 1.0 / self.probability

    @property
    def ev(self) -> float | None:
        odd = self.odd
        return self.probability * odd - 1.0 if odd else None


@dataclass(frozen=True)
class ParlayFilters:
    min_prob: float = 0.60
    max_prob: float = 0.97
    min_odd: float = 1.15  # descarta piernas que casi no pagan (contra listed_odd; sin momio, contra el justo)
    min_ev: float | None = 0.0  # sólo con momio; None = no filtrar por EV
    require_odds: bool = True  # momio de la casa del sistema
    require_listed: bool = False  # momio de alguna casa de PRICE_BOOKMAKERS (aunque no sea la del sistema)
    include_questionable: bool = False  # props de jugadores "en duda" (si no juegan, se anulan)


# Configuración estándar con la que el sistema registra y mide sus parlays (la misma en los dos deportes).
# Ninguna usa líneas que no cotiza ninguna casa: el parlay se tiene que poder apostar.
MODES = {
    "prob": (
        "Máxima probabilidad",
        ParlayFilters(min_prob=0.60, max_prob=0.92, min_odd=1.15, min_ev=None, require_odds=False, require_listed=True),
    ),
    "ev": (
        "Máximo valor (sólo piernas con EV positivo contra la casa)",
        ParlayFilters(min_prob=0.60, max_prob=0.97, min_odd=1.15, min_ev=0.0, require_odds=True),
    ),
}

SCORERS = {
    # Máxima probabilidad de acertar el parlay completo.
    "prob": lambda c: c.p_model,
    # Máximo valor esperado: maximiza el producto de p·momio.
    "ev": lambda c: c.p_model * c.odd if c.odd else 0.0,
}


def eligible(candidates: list[Candidate], filters: ParlayFilters) -> list[Candidate]:
    out = []
    for c in candidates:
        if c.player_status == "questionable" and not filters.include_questionable:
            continue
        if not (filters.min_prob <= c.p_model <= filters.max_prob):
            continue
        if c.odd is None and filters.require_odds:
            continue
        price = c.listed_odd
        if price is None and filters.require_listed:
            continue
        if (price or c.fair_odd) < filters.min_odd:
            continue
        if c.odd is not None and filters.min_ev is not None and c.ev < filters.min_ev:
            continue
        out.append(c)
    return out


def build_parlay(candidates: list[Candidate], n_legs: int, mode: str, filters: ParlayFilters) -> Parlay | None:
    """Mejor parlay de `n_legs` piernas: la mejor pierna de cada partido y luego los mejores partidos.

    Como el objetivo es un producto (de p o de p·momio) y hay una pierna por partido,
    elegir la mejor de cada partido y luego las N mejores da el óptimo exacto.
    """
    score = SCORERS[mode]
    best_by_match: dict[tuple[str, int], Candidate] = {}
    for c in eligible(candidates, filters):
        current = best_by_match.get(c.match_key)
        if current is None or score(c) > score(current):
            best_by_match[c.match_key] = c
    if len(best_by_match) < n_legs:
        return None
    legs = sorted(best_by_match.values(), key=score, reverse=True)[:n_legs]
    return Parlay(legs)
