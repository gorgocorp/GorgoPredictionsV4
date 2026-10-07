"""Definición de una pierna de parlay, su descripción y su liquidación (a 90 minutos)."""

import math
from dataclasses import dataclass, replace

from app.sports.futbol.engine.player_model import STAT_LABELS

OPPOSITE = {"over": "under", "under": "over", "yes": "no", "no": "yes", "home": "away", "away": "home"}
MARKETS = ("1x2", "dc", "total", "team_total", "btts", "score", "cards", "team_cards", "player")


@dataclass(frozen=True)
class LegSpec:
    """Una apuesta concreta.

    market:
      1x2         resultado (side = home/draw/away)
      dc          doble oportunidad (side = 1x/12/x2)
      total       goles del partido (side = over/under, line)
      team_total  goles de un equipo (team = home/away, side = over/under, line)
      btts        ambos anotan (side = yes/no)
      score       marcador exacto (side = "2-1", local-visitante)
      cards       tarjetas del partido (side = over/under, line)
      team_cards  tarjetas de un equipo (team, side, line)
      player      prop de jugador (stat, player_id, side = over/under, line)
    """

    market: str
    side: str
    line: float | None = None
    team: str | None = None
    stat: str | None = None
    player_id: int | None = None

    def opposite(self) -> "LegSpec":
        """El otro lado de una apuesta de dos resultados (más/menos, sí/no)."""
        return replace(self, side=OPPOSITE[self.side])

    def group_key(self) -> tuple:
        """Identifica el mercado sin el lado (para emparejar Over/Under, Sí/No, 1/X/2)."""
        return (self.market, self.line, self.team, self.stat, self.player_id)


def describe(spec: LegSpec, home: str, away: str, player: str | None = None) -> str:
    team_of = {"home": home, "away": away}
    m, side = spec.market, spec.side
    if m == "1x2":
        return "Empate" if side == "draw" else f"Gana {team_of[side]}"
    if m == "dc":
        return {"1x": f"{home} o empate", "x2": f"{away} o empate", "12": "No hay empate"}[side]
    if m == "total":
        return f"{'Más' if side == 'over' else 'Menos'} de {spec.line:g} goles"
    if m == "team_total":
        return f"{team_of[spec.team]} {'más' if side == 'over' else 'menos'} de {spec.line:g} goles"
    if m == "btts":
        return "Ambos anotan" if side == "yes" else "No anotan ambos"
    if m == "score":
        h, a = side.split("-")
        return f"Marcador exacto {home} {h}-{a} {away}"
    if m == "cards":
        return f"{'Más' if side == 'over' else 'Menos'} de {spec.line:g} tarjetas"
    if m == "team_cards":
        return f"{team_of[spec.team]} {'más' if side == 'over' else 'menos'} de {spec.line:g} tarjetas"
    if m == "player":
        if side == "under":
            return f"{player} menos de {spec.line:g} {STAT_LABELS[spec.stat]}"
        k = math.floor(spec.line) + 1
        if spec.stat == "goals":
            return f"{player} anota" if k == 1 else f"{player} {k}+ goles"
        if spec.stat == "ga":
            return f"{player} anota o asiste"
        if spec.stat == "assists":
            return f"{player} da asistencia" if k == 1 else f"{player} {k}+ asistencias"
        if spec.stat == "cards":
            return f"{player} recibe tarjeta"
        return f"{player} {k}+ {STAT_LABELS[spec.stat]}"
    raise ValueError(f"mercado desconocido: {m}")


def settle(
    spec: LegSpec,
    home_goals: float,
    away_goals: float,
    home_cards: float | None = None,
    away_cards: float | None = None,
    player_value: float | None = None,
) -> bool | None:
    """True si se ganó, False si se perdió, None si falta el dato (tarjetas o jugador)."""
    m, side = spec.market, spec.side

    def over_under(value: float | None) -> bool | None:
        if value is None:
            return None
        return value > spec.line if side == "over" else value < spec.line

    if m == "1x2":
        return {"home": home_goals > away_goals, "draw": home_goals == away_goals, "away": home_goals < away_goals}[side]
    if m == "dc":
        return {"1x": home_goals >= away_goals, "x2": home_goals <= away_goals, "12": home_goals != away_goals}[side]
    if m == "total":
        return over_under(home_goals + away_goals)
    if m == "team_total":
        return over_under(home_goals if spec.team == "home" else away_goals)
    if m == "btts":
        both = home_goals > 0 and away_goals > 0
        return both if side == "yes" else not both
    if m == "score":
        h, a = (int(x) for x in side.split("-"))
        return home_goals == h and away_goals == a
    if m == "cards":
        if home_cards is None or away_cards is None:
            return None
        return over_under(home_cards + away_cards)
    if m == "team_cards":
        return over_under(home_cards if spec.team == "home" else away_cards)
    if m == "player":
        return over_under(player_value)
    raise ValueError(f"mercado desconocido: {m}")
