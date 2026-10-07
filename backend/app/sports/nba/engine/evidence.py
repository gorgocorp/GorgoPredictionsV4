"""Valor real de cada pierna para el historial y tus apuestas ("qué pasó en realidad").

Funciones puras (sin base de datos) para poder probarlas aisladas.
"""

from typing import Any

from app.sports.nba.engine.player_model import STAT_LABELS

FINISHED = ("FT", "AOT")
CANCELLED = ("POST", "CANC", "ABD", "AWD")
STAT_VALUE = {
    "points": lambda r: r["points"],
    "rebounds": lambda r: r["rebounds"],
    "assists": lambda r: r["assists"],
    "threes": lambda r: r["fg3_made"],
    "fgm": lambda r: r["fgm"],
    "pra": lambda r: r["points"] + r["rebounds"] + r["assists"],
    "pr": lambda r: r["points"] + r["rebounds"],
    "pa": lambda r: r["points"] + r["assists"],
    "ra": lambda r: r["rebounds"] + r["assists"],
}


def _short(name: str) -> str:
    return name.split(" ")[-1]


def leg_outcome(r: dict[str, Any]) -> dict[str, Any]:
    """Valor real de una pierna: {"value": número o None, "text": explicación corta}.

    `r` trae: market, side, line, team, stat, status, home_total, away_total, home_name, away_name,
    y para props: seconds_played, points, rebounds, assists, fg3_made, fgm, game_has_stats.
    """
    status = r["status"]
    if status in CANCELLED:
        return {"value": None, "text": "Partido pospuesto o cancelado"}
    if status not in FINISHED:
        return {"value": None, "text": "Programado" if status == "NS" else "En juego"}

    home, away = r["home_total"], r["away_total"]
    market = r["market"]
    if market == "ml":
        winner = r["home_name"] if home > away else r["away_name"]
        return {"value": home - away, "text": f"Ganó {_short(winner)} {max(home, away)}-{min(home, away)}"}
    if market == "spread":
        own_home = r["side"] == "home"
        team = r["home_name"] if own_home else r["away_name"]
        margin = (home - away) if own_home else (away - home)
        verb = "ganó" if margin > 0 else "perdió"
        return {"value": margin, "text": f"{_short(team)} {verb} por {abs(margin)}"}
    if market == "total":
        return {"value": home + away, "text": f"Total: {home + away} pts ({away}-{home})"}
    if market == "team_total":
        team, points = (r["home_name"], home) if r["team"] == "home" else (r["away_name"], away)
        return {"value": points, "text": f"{_short(team)} anotó {points}"}
    if market == "player":
        if r.get("seconds_played") is None:
            return {"value": None, "text": "No jugó" if r.get("game_has_stats") else "Sin estadísticas todavía"}
        if r["seconds_played"] == 0:
            return {"value": None, "text": "No jugó"}
        value = STAT_VALUE[r["stat"]](r)
        return {"value": value, "text": f"{value} {STAT_LABELS[r['stat']]}"}
    raise ValueError(f"mercado desconocido: {market}")
