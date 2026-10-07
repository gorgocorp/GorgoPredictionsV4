"""Definición de una pierna de parlay, su descripción y su liquidación."""

import math
from dataclasses import dataclass, replace

from app.sports.nba.engine.player_model import STAT_LABELS

OPPOSITE = {"home": "away", "away": "home", "over": "under", "under": "over"}


@dataclass(frozen=True)
class LegSpec:
    """Una apuesta concreta.

    market:
      ml          ganador (side = home/away)
      spread      handicap (side = home/away, line = handicap de ese lado, ej. -5.5)
      total       total del partido (side = over/under)
      team_total  puntos de un equipo (team = home/away, side = over/under)
      player      prop de jugador (stat, player_id, side = over/under)
    """

    market: str
    side: str
    line: float | None = None
    team: str | None = None
    stat: str | None = None
    player_id: int | None = None

    def opposite(self) -> "LegSpec":
        """El otro lado de la misma apuesta. En handicap también cambia el signo: Home -5.5 <-> Away +5.5."""
        line = -self.line if self.market == "spread" and self.line is not None else self.line
        return replace(self, side=OPPOSITE[self.side], line=line)

    def group_key(self) -> tuple:
        """Identifica el mercado sin el lado (para emparejar Over/Under, Home/Away)."""
        line = self.line
        if self.market == "spread" and line is not None and self.side == "away":
            line = -line  # Home -5.5 y Away +5.5 son el mismo mercado
        return (self.market, line, self.team, self.stat, self.player_id)


def describe(spec: LegSpec, home: str, away: str, player: str | None = None) -> str:
    team_of = {"home": home, "away": away}
    if spec.market == "ml":
        return f"Gana {team_of[spec.side]}"
    if spec.market == "spread":
        return f"{team_of[spec.side]} {spec.line:+g}"
    if spec.market == "total":
        word = "Más" if spec.side == "over" else "Menos"
        return f"{word} de {spec.line:g} pts en el partido"
    if spec.market == "team_total":
        word = "más" if spec.side == "over" else "menos"
        return f"{team_of[spec.team]} {word} de {spec.line:g} pts"
    if spec.market == "player":
        label = STAT_LABELS[spec.stat]
        if spec.side == "over":
            return f"{player} {math.floor(spec.line) + 1}+ {label}"
        return f"{player} menos de {spec.line:g} {label}"
    raise ValueError(f"mercado desconocido: {spec.market}")


def settle(spec: LegSpec, home_points: float, away_points: float, player_value: float | None = None) -> bool | None:
    """True si la pierna se ganó, False si se perdió, None si no aplica (jugador sin datos)."""
    margin = home_points - away_points
    if spec.market == "ml":
        return margin > 0 if spec.side == "home" else margin < 0
    if spec.market == "spread":
        own_margin = margin if spec.side == "home" else -margin
        return own_margin + spec.line > 0
    if spec.market == "total":
        total = home_points + away_points
        return total > spec.line if spec.side == "over" else total < spec.line
    if spec.market == "team_total":
        points = home_points if spec.team == "home" else away_points
        return points > spec.line if spec.side == "over" else points < spec.line
    if spec.market == "player":
        if player_value is None:
            return None
        return player_value > spec.line if spec.side == "over" else player_value < spec.line
    raise ValueError(f"mercado desconocido: {spec.market}")
